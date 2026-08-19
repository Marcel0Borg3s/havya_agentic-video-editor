"""OpenRouter adapter for Google ADK.

Registers an OpenRouter-backed LLM with the ADK registry so that
Agent(model="openrouter/...") works transparently. Requires the
``OPENROUTER_API_KEY`` environment variable.

Usage::

    import src.models.openrouter_llm  # register on import

    agent = Agent(
        name="director",
        model="openrouter/meta-llama/llama-4-scout",
        instruction="...",
    )
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import AsyncGenerator

import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.base_llm_connection import BaseLlmConnection
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

from src.ai_config import AI_API_KEY, AI_BASE_URL, AI_MODEL_NAME

logger = logging.getLogger(__name__)


class OpenRouterLlm(BaseLlm):
    """LLM implementation that proxies to OpenRouter's OpenAI-compatible API."""

    api_key: str = ""
    base_url: str = ""

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"^openrouter/.+$"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        api_key = self.api_key or AI_API_KEY
        if not api_key:
            raise RuntimeError(
                "AI_API_KEY (or OPENROUTER_API_KEY) environment variable is not set."
            )

        # Strip the "openrouter/" prefix to get the real model name.
        model_name = re.sub(r"^openrouter/", "", self.model)

        # Use configured base URL if not set on instance.
        base_url = self.base_url or AI_BASE_URL

        # Convert ADK Contents → OpenAI messages format.
        messages = self._convert_contents(llm_request)

        # Convert ADK tools → OpenAI tools format.
        tools = self._convert_tools(llm_request)

        # Convert ADK response schema → response_format if present.
        response_format = self._convert_response_format(llm_request)

        payload: dict = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/havya-agentic-video-editor",
            "X-Title": "Havya Video Editor",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Convert OpenAI response → ADK LlmResponse.
        yield self._convert_response(data, llm_request)

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_contents(llm_request: LlmRequest) -> list[dict]:
        """Convert ADK Content list → OpenAI messages list."""
        messages: list[dict] = []
        for content in llm_request.contents:
            role = content.role or "user"
            if role == "model":
                role = "assistant"

            parts_text: list[str] = []
            tool_calls: list[dict] = []
            tool_call_id: str | None = None

            for part in content.parts or []:
                if getattr(part, "text", None):
                    parts_text.append(part.text)
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    tool_calls.append({
                        "id": f"call_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            "args": json.dumps(dict(fc.args)) if fc.args else "{}",
                        },
                    })
                if getattr(part, "function_response", None):
                    fr = part.function_response
                    tool_call_id = f"call_0"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(dict(fr.response)) if fr.response else "{}",
                    })

            if tool_calls:
                msg: dict = {"role": "assistant", "tool_calls": tool_calls}
                if parts_text:
                    msg["content"] = "\n".join(parts_text)
                messages.append(msg)
            elif role == "tool" or tool_call_id:
                continue  # already handled above
            else:
                text = "\n".join(parts_text) if parts_text else ""
                messages.append({"role": role, "content": text})

        # Inject system instruction as system message if present.
        if llm_request.config and llm_request.config.system_instruction:
            sys_text = ""
            si = llm_request.config.system_instruction
            if isinstance(si, str):
                sys_text = si
            elif hasattr(si, "parts"):
                sys_text = "\n".join(
                    p.text for p in si.parts if getattr(p, "text", None)
                )
            if sys_text:
                messages.insert(0, {"role": "system", "content": sys_text})

        return messages

    @staticmethod
    def _convert_tools(llm_request: LlmRequest) -> list[dict]:
        """Convert ADK tools → OpenAI function-calling tools."""
        if not llm_request.tools_dict:
            return []
        tools = []
        for name, tool in llm_request.tools_dict.items():
            schema = {}
            if hasattr(tool, "get_type_declaration"):
                try:
                    schema = tool.get_type_declaration()
                except Exception:
                    pass
            elif hasattr(tool, "_raw_function"):
                fn = tool._raw_function
                if hasattr(fn, "__doc__") and fn.__doc__:
                    schema = {"description": fn.__doc__[:200]}

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.get("description", f"Tool: {name}"),
                    "parameters": schema.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                },
            })
        return tools

    @staticmethod
    def _convert_response_format(llm_request: LlmRequest) -> dict | None:
        """Convert ADK output_schema → OpenAI response_format."""
        cfg = llm_request.config
        if not cfg:
            return None
        # Check if there's a response_schema
        schema = getattr(cfg, "response_schema", None)
        if schema is None:
            return None
        try:
            if hasattr(schema, "model_json_schema"):
                json_schema = schema.model_json_schema()
            elif isinstance(schema, dict):
                json_schema = schema
            else:
                return None
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": json_schema,
                },
            }
        except Exception:
            return None

    @staticmethod
    def _convert_response(
        data: dict, llm_request: LlmRequest
    ) -> LlmResponse:
        """Convert OpenAI chat completion response → ADK LlmResponse."""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content_text = message.get("content", "")

        # Parse JSON content if response_schema was set.
        parsed = None
        cfg = llm_request.config
        if cfg and getattr(cfg, "response_schema", None) and content_text:
            schema = cfg.response_schema
            try:
                if hasattr(schema, "model_validate_json"):
                    parsed = schema.model_validate_json(content_text)
                elif hasattr(schema, "model_validate"):
                    parsed = schema.model_validate(json.loads(content_text))
            except Exception:
                pass

        parts = []
        if content_text:
            parts.append(types.Part(text=content_text))
        if parsed is not None:
            # Store parsed result as a thought so ADK picks it up.
            parts.append(types.Part(
                text=json.dumps(
                    parsed.model_dump() if hasattr(parsed, "model_dump") else parsed,
                    ensure_ascii=False,
                ),
                thought=True,
            ))

        # Handle tool calls from the response.
        tool_calls = message.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            args_str = func.get("args", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
            parts.append(types.Part(
                function_call=types.FunctionCall(
                    name=func.get("name", ""),
                    args=args,
                )
            ))

        usage = data.get("usage", {})
        return LlmResponse(
            content=types.Content(role="model", parts=parts) if parts else None,
            turn_complete=True,
            finish_reason=types.FinishReason.STOP,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=usage.get("prompt_tokens", 0),
                candidates_token_count=usage.get("completion_tokens", 0),
                total_token_count=usage.get("total_tokens", 0),
            ),
        )


# Register on import so Agent(model="openrouter/...") works.
LLMRegistry.register(OpenRouterLlm)

"""Provider abstraction for AI calls.

Routes to Gemini (native) or OpenRouter (httpx) based on AI_PROVIDER env var.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx

from src.config import AI_PROVIDER
from src.ai_config import AI_API_KEY, AI_BASE_URL, AI_MODEL_NAME
from src.ai_provider_base import AIProvider


class OpenAICompatibleProvider(AIProvider):
    """Provider for OpenAI-compatible APIs (OpenRouter, OpenCode, etc.)."""

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        result = call_openrouter(
            prompt, system=system, temperature=temperature
        )
        return result["text"]

    def is_available(self) -> bool:
        return bool(AI_API_KEY)


def _extract_frame(video_path: str, output: str = "/tmp/frame.jpg") -> str:
    """Extract a single frame from a video for vision model analysis."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "select=eq(n\\,0)", "-vframes", "1",
        "-q:v", "2", output,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


def _extract_frames_grid(video_path: str, output: str = "/tmp/grid.jpg") -> str:
    """Extract 6 evenly-spaced frames as a grid for analysis."""
    # Get duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip() or "10")

    # Extract 6 frames at evenly spaced intervals
    frames = []
    for i in range(6):
        t = duration * i / 5
        frame_path = f"/tmp/frame_{i}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t), "-i", video_path,
            "-vframes", "1", "-q:v", "2", frame_path,
        ], capture_output=True, check=True)
        frames.append(frame_path)

    # Create a 3x2 grid using ffmpeg
    subprocess.run([
        "ffmpeg", "-y",
        "-i", frames[0], "-i", frames[1], "-i", frames[2],
        "-i", frames[3], "-i", frames[4], "-i", frames[5],
        "-filter_complex",
        "[0]scale=320:180[v0];[1]scale=320:180[v1];[2]scale=320:180[v2];"
        "[3]scale=320:180[v3];[4]scale=320:180[v4];[5]scale=320:180[v5];"
        "[v0][v1][v2]hstack=3[top];"
        "[v3][v4][v5]hstack=3[bottom];"
        "[top][bottom]vstack=2[out]",
        "-map", "[out]", "-q:v", "2", output,
    ], capture_output=True, check=True)

    return output


def call_openrouter(
    prompt: str,
    *,
    system: str = "",
    video_path: str | None = None,
    response_schema: Any = None,
    temperature: float = 0.7,
) -> dict:
    """Call OpenRouter's chat completions API.

    If video_path is provided, extracts frames and sends as base64 images.
    """
    api_key = AI_API_KEY
    if not api_key:
        raise RuntimeError("AI_API_KEY (or OPENROUTER_API_KEY) not set")

    model = AI_MODEL_NAME

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})

    user_content: list[dict] = []

    # If video provided, extract frames and add as images.
    if video_path and Path(video_path).exists():
        try:
            grid_path = _extract_frames_grid(video_path)
            with open(grid_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })
        except Exception:
            # Fallback: single frame
            try:
                frame_path = _extract_frame(video_path)
                with open(frame_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                })
            except Exception:
                pass  # No video frames available

    user_content.append({"type": "text", "text": prompt})
    messages.append({"role": "user", "content": user_content})

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    # Add JSON response format if schema provided.
    if response_schema is not None:
        if hasattr(response_schema, "model_json_schema"):
            json_schema = response_schema.model_json_schema()
        elif isinstance(response_schema, dict):
            json_schema = response_schema
        else:
            json_schema = None

        if json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": json_schema,
                },
            }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/havya-agentic-video-editor",
        "X-Title": "Havya Video Editor",
    }

    resp = httpx.post(
        f"{AI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"text": content, "raw": data}

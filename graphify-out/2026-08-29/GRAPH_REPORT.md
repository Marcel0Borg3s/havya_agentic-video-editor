# Graph Report - agentic-video-editor  (2026-08-29)

## Corpus Check
- 114 files · ~110,411 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 32 nodes · 43 edges · 4 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0dd10921`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run_director_openrouter
- call_openrouter
- director_openrouter.py
- OpenAICompatibleProvider

## God Nodes (most connected - your core abstractions)
1. `run_director_openrouter()` - 10 edges
2. `call_openrouter()` - 8 edges
3. `_generate_fallback_plan()` - 6 edges
4. `_validate_and_fix_entries()` - 5 edges
5. `OpenAICompatibleProvider` - 5 edges
6. `_repair_json()` - 3 edges
7. `_shots_to_text()` - 3 edges
8. `_debug_log_prompt()` - 3 edges
9. `_extract_frame()` - 3 edges
10. `_extract_frames_grid()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `run_director_openrouter()` --calls--> `call_openrouter()`  [EXTRACTED]
  src/agents/director_openrouter.py → src/ai_provider.py

## Import Cycles
- None detected.

## Communities (4 total, 0 thin omitted)

### Community 0 - "run_director_openrouter"
Cohesion: 0.27
Nodes (10): CreativeBrief, EditPlan, EditPlanEntry, FootageIndex, _generate_fallback_plan(), Generate a fallback plan when LLM fails or returns bad entries., Run the Director via OpenRouter without ADK tool calling. Reads the…, Validate LLM entries and fix incorrect trim values. The LLM often returns… (+2 more)

### Community 1 - "call_openrouter"
Cohesion: 0.28
Nodes (8): Any, call_openrouter(), _extract_frame(), _extract_frames_grid(), Provider abstraction for AI calls. Routes to Gemini (native) or OpenRouter…, Call OpenRouter's chat completions API. If video_path is provided, extracts…, Extract a single frame from a video for vision model analysis., Extract 6 evenly-spaced frames as a grid for analysis.

### Community 2 - "director_openrouter.py"
Cohesion: 0.25
Nodes (7): _debug_log_prompt(), Director agent using OpenRouter (bypasses ADK)., Repair common LLM JSON issues and parse progressively., Log prompt details for debugging., Format shots for the prompt with analysis data., _repair_json(), _shots_to_text()

### Community 3 - "OpenAICompatibleProvider"
Cohesion: 0.40
Nodes (3): AIProvider, OpenAICompatibleProvider, Provider for OpenAI-compatible APIs (OpenRouter, OpenCode, etc.).

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `call_openrouter()` connect `call_openrouter` to `run_director_openrouter`, `director_openrouter.py`, `OpenAICompatibleProvider`?**
  _High betweenness centrality (0.568) - this node is a cross-community bridge._
- **Why does `run_director_openrouter()` connect `run_director_openrouter` to `call_openrouter`, `director_openrouter.py`?**
  _High betweenness centrality (0.411) - this node is a cross-community bridge._
- **Why does `OpenAICompatibleProvider` connect `OpenAICompatibleProvider` to `call_openrouter`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
# Graph Report - agentic-video-editor  (2026-08-29)

## Corpus Check
- 114 files · ~110,535 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 46 nodes · 60 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ca6f93c2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run_director_openrouter
- call_openrouter
- director_openrouter.py
- OpenAICompatibleProvider
- run_editor_openrouter
- assets.py
- _validate_and_fix_entries
- _repair_json
- _debug_log_prompt

## God Nodes (most connected - your core abstractions)
1. `run_director_openrouter()` - 10 edges
2. `call_openrouter()` - 8 edges
3. `_generate_fallback_plan()` - 6 edges
4. `OpenAICompatibleProvider` - 5 edges
5. `run_editor_openrouter()` - 5 edges
6. `_validate_and_fix_entries()` - 5 edges
7. `_resolve_shot()` - 4 edges
8. `normalize_asset()` - 3 edges
9. `assemble_with_assets()` - 3 edges
10. `_extract_frame()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `run_director_openrouter()` --calls--> `call_openrouter()`  [EXTRACTED]
  src/agents/director_openrouter.py → src/ai_provider.py

## Import Cycles
- None detected.

## Communities (9 total, 2 thin omitted)

### Community 0 - "run_director_openrouter"
Cohesion: 0.50
Nodes (5): CreativeBrief, _generate_fallback_plan(), Generate a fallback plan when LLM fails or returns bad entries., Run the Director via OpenRouter without ADK tool calling. Reads the…, run_director_openrouter()

### Community 1 - "call_openrouter"
Cohesion: 0.28
Nodes (8): Any, call_openrouter(), _extract_frame(), _extract_frames_grid(), Provider abstraction for AI calls. Routes to Gemini (native) or OpenRouter…, Call OpenRouter's chat completions API. If video_path is provided, extracts…, Extract a single frame from a video for vision model analysis., Extract 6 evenly-spaced frames as a grid for analysis.

### Community 2 - "director_openrouter.py"
Cohesion: 0.50
Nodes (3): Director agent using OpenRouter (bypasses ADK)., Format shots for the prompt with analysis data., _shots_to_text()

### Community 3 - "OpenAICompatibleProvider"
Cohesion: 0.40
Nodes (3): AIProvider, OpenAICompatibleProvider, Provider for OpenAI-compatible APIs (OpenRouter, OpenCode, etc.).

### Community 4 - "run_editor_openrouter"
Cohesion: 0.24
Nodes (9): EditPlan, FootageIndex, Shot, _merge_ass_files(), Editor using OpenRouter mode — deterministic FFmpeg execution. Executes FFmpeg…, Merge multiple ASS files with time offsets for sequential clips. Args:…, Execute the EditPlan using FFmpeg tools directly (no LLM)., _resolve_shot() (+1 more)

### Community 5 - "assets.py"
Cohesion: 0.40
Nodes (5): assemble_with_assets(), normalize_asset(), Media-asset normalization and assembly helpers., Normalize an external asset to the editor's delivery format., Assemble optional opening/content/closing videos into one MP4. External assets…

### Community 6 - "_validate_and_fix_entries"
Cohesion: 0.67
Nodes (3): EditPlanEntry, Validate LLM entries and fix incorrect trim values. The LLM often returns…, _validate_and_fix_entries()

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `call_openrouter()` connect `call_openrouter` to `run_director_openrouter`, `director_openrouter.py`, `OpenAICompatibleProvider`?**
  _High betweenness centrality (0.372) - this node is a cross-community bridge._
- **Why does `run_director_openrouter()` connect `run_director_openrouter` to `call_openrouter`, `director_openrouter.py`, `run_editor_openrouter`, `_validate_and_fix_entries`, `_repair_json`, `_debug_log_prompt`?**
  _High betweenness centrality (0.369) - this node is a cross-community bridge._
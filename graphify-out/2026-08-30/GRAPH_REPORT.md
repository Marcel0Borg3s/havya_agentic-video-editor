# Graph Report - agentic-video-editor  (2026-08-30)

## Corpus Check
- 114 files · ~110,677 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 69 nodes · 99 edges · 6 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `181e060e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run_director_openrouter
- call_openrouter
- _process_video
- _words_for_shot
- run_editor_openrouter
- assets.py

## God Nodes (most connected - your core abstractions)
1. `_process_video()` - 12 edges
2. `run_director_openrouter()` - 10 edges
3. `call_openrouter()` - 7 edges
4. `preprocess_footage()` - 7 edges
5. `_generate_fallback_plan()` - 6 edges
6. `_validate_and_fix_entries()` - 5 edges
7. `OpenAICompatibleProvider` - 5 edges
8. `_transcribe_words()` - 5 edges
9. `_words_for_shot()` - 5 edges
10. `run_editor_openrouter()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `run_director_openrouter()` --calls--> `call_openrouter()`  [INFERRED]
  src/agents/director_openrouter.py → src/ai_provider.py

## Import Cycles
- None detected.

## Communities (6 total, 0 thin omitted)

### Community 0 - "run_director_openrouter"
Cohesion: 0.18
Nodes (15): CreativeBrief, EditPlanEntry, _debug_log_prompt(), _generate_fallback_plan(), Director agent using OpenRouter (bypasses ADK)., Repair common LLM JSON issues and parse progressively., Generate a fallback plan when LLM fails or returns bad entries., Run the Director via OpenRouter without ADK tool calling. Reads the… (+7 more)

### Community 1 - "call_openrouter"
Cohesion: 0.18
Nodes (11): AIProvider, Any, call_openrouter(), _extract_frame(), _extract_frames_grid(), OpenAICompatibleProvider, Provider abstraction for AI calls. Routes to Gemini (native) or OpenRouter…, Call OpenRouter's chat completions API. If video_path is provided, extracts… (+3 more)

### Community 2 - "_process_video"
Cohesion: 0.23
Nodes (15): Path, _detect_roll_type(), _detect_shots(), _log(), preprocess_footage(), _process_video(), Pre-processing pipeline: scene detection + transcription. Walks an input…, Detect shots in a video and assemble Shot objects with aligned transcripts. (+7 more)

### Community 3 - "_words_for_shot"
Cohesion: 0.29
Nodes (7): _normalize_word_text(), Collapse whitespace in a transcribed word while keeping punctuation., Render a token stream into readable caption/transcript text., Return word timestamps whose midpoint falls within the shot window., _words_for_shot(), _words_to_text(), WordTimestamp

### Community 4 - "run_editor_openrouter"
Cohesion: 0.24
Nodes (9): EditPlan, FootageIndex, Shot, _merge_ass_files(), Editor using OpenRouter mode — deterministic FFmpeg execution. Executes FFmpeg…, Merge multiple ASS files with time offsets for sequential clips. Args:…, Execute the EditPlan using FFmpeg tools directly (no LLM)., _resolve_shot() (+1 more)

### Community 5 - "assets.py"
Cohesion: 0.40
Nodes (5): assemble_with_assets(), normalize_asset(), Media-asset normalization and assembly helpers., Normalize an external asset to the editor's delivery format., Assemble optional opening/content/closing videos into one MP4. External assets…

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_director_openrouter()` connect `run_director_openrouter` to `call_openrouter`, `run_editor_openrouter`?**
  _High betweenness centrality (0.398) - this node is a cross-community bridge._
- **Why does `preprocess_footage()` connect `_process_video` to `run_editor_openrouter`?**
  _High betweenness centrality (0.328) - this node is a cross-community bridge._
- **Why does `call_openrouter()` connect `call_openrouter` to `run_director_openrouter`?**
  _High betweenness centrality (0.293) - this node is a cross-community bridge._
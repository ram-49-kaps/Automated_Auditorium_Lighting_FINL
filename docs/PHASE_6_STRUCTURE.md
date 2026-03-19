# Phase 6 — Orchestration & Pipeline Control

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 6 orchestrates the entire pipeline: it calls Phases 1→2→3→4 per scene, then Phase 5 and Phase 7 post-loop. It manages phase state, handles fatal and non-fatal errors, and produces the final `PipelineResult`.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / `run_pipeline_test.py` | String path |
| `PipelineConfig` | User configuration | Pydantic model |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| `PipelineResult` | Caller | Per-phase statuses, durations, outputs |

## 4. Internal Components

### Classes

| File | Component | Description |
|------|-----------|-------------|
| `pipeline_runner.py` | `PipelineRunner` | Main orchestrator — `.run(script_path)` |
| `config_models.py` | `PipelineConfig` | Phase toggles, LLM config |
| `config_models.py` | `PipelineResult` | Aggregated phase results |
| `state_tracker.py` | `StateTracker` | Tracks phase timing, scene progress |
| `errors.py` | `HardFailureError` | Exception for fatal phase failures |
| `batch_executor.py` | `BatchExecutor` | Multi-script batch execution |

### PipelineConfig Options

| Option | Default | Description |
|--------|---------|-------------|
| `enable_phase_5` | `False` | Enable simulation rendering |
| `enable_phase_7` | `False` | Enable metrics & tracing |
| `enable_phase_8` | `False` | Enable hardware (not implemented) |
| `use_llm` | `True` | Enable LLM mode in Phase 4 |

### Pipeline Execution Order

```
1. Phase 1: parse_script(path) → scenes[]
2. For each scene:
   a. Phase 2: emotion_analyze(scene) → enriched_scene
   b. Phase 3: build_context_for_llm(emotion, text) → rag_context
   c. Phase 4: generate_instruction(scene, context) → instruction
3. Phase 5: render(instructions) [if enabled]
4. Phase 7: trace + metrics(instructions, scenes) [if enabled]
```

### Phase Failure Classification

| Phase | Failure Mode | Pipeline Action |
|-------|-------------|-----------------|
| Phase 1 | HARD | Pipeline halts, `HardFailureError` raised |
| Phase 2 | SOFT | Defaults to `neutral`, continues |
| Phase 3 | HARD | Pipeline halts |
| Phase 4 | HARD | Pipeline halts (after fallback attempt) |
| Phase 5 | SOFT | Logs warning, continues |
| Phase 7 | SOFT | Logs warning, continues |

### Defensive Data Handling

Phase 6 includes `isinstance` checks when extracting `scene["content"]` and `scene["emotion"]` to handle variations in data format from earlier phases (string vs dict).

## 5. Boundaries

- Phase 6 does **NOT** modify outputs from any phase
- Phase 6 does **NOT** generate lighting instructions
- Phase 6 does **NOT** perform emotion analysis or RAG retrieval
- Phase 6 does **NOT** compute metrics (delegates to Phase 7)
- Phase 6 only routes data and manages state

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| `HardFailureError` from any phase | Fatal | Pipeline halts, `final_status=FAILED` |
| Unexpected exception | Fatal | Pipeline halts, logged |
| Soft phase failure | Non-fatal | Logs warning, continues with defaults |

## 7. Current Limitations

- No parallel scene processing — scenes execute sequentially
- `PipelineResult` stores per-phase results but does not aggregate per-scene outputs for external access
- Batch executor exists but is not currently used by `run_pipeline_test.py`

# Phase 6 — Orchestration & Pipeline Control

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 6 orchestrates all phases: calls Phases 1→2→3→4 per scene, then Phase 5 and Phase 7 post-loop. Manages state, handles errors, produces `PipelineResult`.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / `run_pipeline_test.py` | String |
| `PipelineConfig` | User configuration | Pydantic model |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| `PipelineResult` | Caller | Per-phase statuses, durations, outputs |

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `pipeline_runner.py` | `PipelineRunner` | Main orchestrator |
| `config_models.py` | `PipelineConfig` | `enable_phase_5`, `enable_phase_7`, `use_llm` |
| `config_models.py` | `PipelineResult` | Aggregated results |
| `state_tracker.py` | `StateTracker` | Phase timing, scene progress |
| `errors.py` | `HardFailureError` | Fatal exception |
| `batch_executor.py` | `BatchExecutor` | Multi-script batch mode |

### Execution Order

```
Phase 1 → for each scene: Phase 2 → 3 → 4 → Phase 5 → Phase 7
```

### Defensive Data Handling

`isinstance` checks on `scene["content"]` and `scene["emotion"]` handle format variations from earlier phases.

## 5. Boundaries

- Does **NOT** modify outputs from any phase
- Does **NOT** generate lighting instructions
- Does **NOT** compute metrics
- Only routes data and manages state

## 6. Failure Handling

| Phase | Type | Action |
|-------|------|--------|
| 1, 3, 4 | **HARD** | Pipeline halts |
| 2, 5, 7 | **SOFT** | Logs, continues with defaults |

## 7. Current Limitations

- Sequential scene processing (no parallelism)
- `PipelineResult` does not expose per-scene instructions externally
- Batch executor not used by default test script

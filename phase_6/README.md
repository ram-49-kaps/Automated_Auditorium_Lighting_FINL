# Phase 6 — Orchestration & Pipeline Control

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## Purpose

Phase 6 orchestrates the entire pipeline. It calls Phases 1→2→3→4 per scene, then Phase 5 and Phase 7 post-loop. It manages state, handles errors, and produces `PipelineResult`.

## Components

| File | Component | Description |
|------|-----------|-------------|
| `pipeline_runner.py` | `PipelineRunner` | Main orchestrator (`.run(script_path)`) |
| `config_models.py` | `PipelineConfig` | Phase toggles and runtime config |
| `config_models.py` | `PipelineResult` | Aggregated phase results |
| `state_tracker.py` | `StateTracker` | Phase timing and scene progress |
| `errors.py` | `HardFailureError` | Fatal exception type |
| `batch_executor.py` | `BatchExecutor` | Multi-script batch execution |

## Quick Start

```python
from phase_6 import PipelineRunner, PipelineConfig

config = PipelineConfig(
    enable_phase_5=True,
    enable_phase_7=True,
    use_llm=False  # Baseline mode
)

runner = PipelineRunner(config)
result = runner.run("data/raw_scripts/Script-1.txt")
print(result.final_status)  # PhaseStatus.SUCCESS
```

## Execution Order

```
Phase 1 (parse) → for each scene: Phase 2 → 3 → 4 → Phase 5 → Phase 7
```

## Boundaries

- Phase 6 does **NOT** modify outputs from any phase
- Phase 6 only routes data and manages state

## Failure Handling

- **Hard fail**: Phase 1, 3, 4 — pipeline halts
- **Soft fail**: Phase 2, 5, 7 — logs warning, continues with defaults

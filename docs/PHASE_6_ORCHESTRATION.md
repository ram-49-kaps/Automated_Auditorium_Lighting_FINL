# Phase 6 — Orchestration & Pipeline Control

> Updated: 2026-02-22. Reflects actual backend architecture with FastAPI + pipeline_runner.

## 1. Purpose

Phase 6 orchestrates all phases: calls Phases 1→2→3→4 per scene, then Phase 5 and Phase 7 post-loop. Manages state, handles errors, produces `PipelineResult`.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / Frontend upload | String (via `/api/upload`) |
| `PipelineConfig` | Default configuration | Dataclass |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| `PipelineResult` | Caller / Frontend | Per-phase statuses, durations, outputs |
| `lighting_instructions.json` | `data/jobs/{job_id}/` | Persisted JSON with lighting + script data |

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `backend/pipeline_runner.py` | `run_pipeline()` | Main orchestrator — runs Phase 1→2→3→4 |
| `backend/app.py` | `FastAPI` | REST API: upload, results, simulation launch, health |
| `backend/config_models.py` | `PipelineConfig`, `PipelineResult` | Configuration and result dataclasses |
| `backend/state_tracker.py` | `StateTracker` | Phase timing and scene progress tracking |
| `backend/errors.py` | `HardFailureError`, `SoftFailureError` | Custom exception classes |
| `backend/batch_executor.py` | `BatchExecutor` | Multi-script batch processing |
| `backend/websocket_manager.py` | `ConnectionManager` | WebSocket connection pool for real-time updates |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/upload` | Upload script, start processing |
| `GET` | `/api/results/{job_id}` | Get job results |
| `POST` | `/api/launch/{job_id}` | Launch 3D simulation |
| `GET` | `/api/jobs` | List all jobs |

### Execution Order

```
Upload → Phase 1 (parse) → for each scene: Phase 2 (emotion) → Phase 3 (RAG) → Phase 4 (lighting) → Save → Phase 5 (optional)
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
- Batch executor not used by default API endpoint

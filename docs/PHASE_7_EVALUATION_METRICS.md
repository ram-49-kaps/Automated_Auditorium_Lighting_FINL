# Phase 7 — Evaluation & Metrics

> Updated: 2026-02-22. All components implemented and verified.

## 1. Purpose

Phase 7 observes execution traces and computes research-grade metrics for lighting decisions. It is fully removable without affecting system execution. It enables quantitative comparison between baseline (rule-based) and GenAI (LLM) modes.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Processed scenes | Phase 6 loop | `List[Dict]` |
| Lighting instructions | Phase 4 / Phase 6 | `List[LightingInstruction]` dicts |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Trace file | `data/traces/trace_<uuid>.json` | JSON |
| Metrics report | Console + Phase 7 output | Dict |

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `trace_logger.py` | `TraceLogger` | Logs input/output hashes per scene, saves trace |
| `metrics.py` | `MetricsEngine` | Coverage, diversity, drift, determinism, stability |
| `schemas.py` | `TraceEntry`, `TraceLog`, `RAGContextRef` | Dataclass trace models |
| `evaluation/consistency.py` | `compute_jaccard_similarity` | Set overlap metric |
| `evaluation/consistency.py` | `compute_determinism_score` | Structural match (group IDs + intensity ε + transitions) |
| `evaluation/consistency.py` | `compute_drift_score` | Sequence stability metric |
| `evaluation/consistency.py` | `extract_group_ids` | Group ID extraction helper |
| `evaluation/coverage.py` | `compute_group_coverage` | Group utilization ratio |
| `evaluation/coverage.py` | `compute_parameter_diversity` | Parameter spread per instruction |
| `evaluation/stability.py` | `compute_cross_run_stability` | Multi-run consistency |

### Pipeline Integration

```python
# In pipeline_runner.py:
trace_logger = TraceLogger(output_dir="data/traces/", seed=42)
for scene, instruction in zip(scenes, instructions):
    trace_logger.log_decision(scene, instruction)
trace_logger.save()

metrics_engine = MetricsEngine(available_groups={...})
report = metrics_engine.generate_report(instructions)
```

## Current Metrics (5/5 Groups)

| Metric | Value | Definition |
|--------|-------|------------|
| Coverage | 1.0 | `|groups_used| / |available_groups|` (5 of 5) |
| Drift Score | 0.0 | `avg(1 - Jaccard)` — all scenes use same 5 groups |
| Intensity Range | 7.5–90.0 | Per-scene intensity diversity (0-100 scale) |
| Transition Types | 1 | `fade` only |
| Determinism | 1.0 | Guaranteed in rule-based mode |

### Available Groups

`front_wash`, `back_light`, `side_fill`, `specials`, `ambient`

## 5. Boundaries

Phase 7 is **OBSERVATIONAL ONLY**. It does NOT:
- Import from Phase 4 or other phases
- Call LLM APIs
- Modify lighting intent
- Influence execution

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| Import error | **SOFT** | Skipped, pipeline continues |
| Metrics error | **SOFT** | Logs warning, pipeline continues |

Phase 7 is OPTIONAL — non-fatal.

## 7. Current Limitations

- Cross-run stability requires multiple pipeline runs (not automated)
- No automated report export (console output only)
- Ablation and baseline experiment configs not automated

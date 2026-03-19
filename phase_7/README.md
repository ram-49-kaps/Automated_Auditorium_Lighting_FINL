# Phase 7 — Evaluation & Metrics

**Owner:** Friend B  
**Purpose:** Observational logging and metrics for research paper support

---

## ⚠️ CRITICAL RULE

> **Phase 7 must be fully removable without affecting system execution or outputs.**

This phase:
- ❌ Does NOT call Phase 4 functions
- ❌ Does NOT invoke LLM
- ❌ Does NOT modify lighting intent
- ❌ Does NOT influence execution

---

## Data Sources

Phase 7 reads ONLY from:
- `data/lighting_cues/*.json` (pre-generated LightingInstructions)
- `tests/fixtures/phase_7/` (pre-generated test data)

**NEVER** import or call functions from other phases.

---

## RAG Context ID Policy

If logging RAG context, ONLY opaque identifiers are allowed:

| Allowed | Forbidden |
|---------|-----------|
| ✅ `document_id` | ❌ Chunk text |
| ✅ `chunk_id` | ❌ Embeddings |
| | ❌ Similarity scores |

---

## Determinism Definition

Determinism is defined **structurally** (not bytewise):
- Same `group_ids` selected
- Same `transition.type` values
- Intensity within ε = ±0.05

---

## Module Structure

```
phase_7/
├── README.md              ← This file
├── schemas.py             ← Internal pydantic models
├── trace_logger.py        ← Trace capture module
├── metrics.py             ← Unified metrics engine
├── demo.py                ← Standalone demo script
├── evaluation/
│   ├── consistency.py     ← Jaccard + drift
│   ├── coverage.py        ← Group coverage
│   └── stability.py       ← Cross-run stability
└── experiment_configs/
    ├── baseline.yaml
    └── ablation.yaml
```

---

## Forbidden Actions

| Action | Reason |
|--------|--------|
| `from phase_4 import *` | Phase isolation |
| Call LLM APIs | Phase 4 responsibility |
| Query RAG | Phase 3 responsibility |
| Score "good/bad" lighting | Quality ≠ evaluation |

---

*Last updated: 2026-02-05*

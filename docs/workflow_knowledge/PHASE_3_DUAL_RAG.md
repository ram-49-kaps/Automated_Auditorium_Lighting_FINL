# Phase 3 — Dual RAG Knowledge Retrieval

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 3 retrieves contextual knowledge for lighting decisions via FAISS-based similarity search across two knowledge bases: auditorium fixtures (54 documents) and lighting semantics rules (7 rules).

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Emotion label | Phase 2 | String (e.g., `fear`, `neutral`) |
| Scene text | Phase 1 | String |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| RAG context string | Phase 4 (LLM prompt) | Formatted text via `build_context_for_llm` |
| Palette dict | Phase 4 (rule-based fallback) | Dict via `retrieve_palette` |

Baseline context: 1891–2132 chars per scene.

## 4. Internal Components

### Phase3Retriever (`rag_retriever.py`)

| Method | Purpose |
|--------|---------|
| `retrieve_auditorium_context(query, k=5)` | FAISS search on fixture index |
| `retrieve_semantics_context(emotion, script_type, k=3)` | FAISS search on semantics index |
| `build_context_for_llm(emotion, scene_text)` | Adapter: merges fixture + semantics → text string |
| `retrieve_palette(emotion)` | Adapter: maps semantics → palette dict for Phase 4 fallback |

### Knowledge Ingestion (`ingestion/knowledge_ingestion.py`)

| Source | Documents | Index Output |
|--------|-----------|--------------|
| `knowledge/auditorium/fixtures.json` | 54 fixtures | `rag/auditorium/index.faiss` + `.pkl` |
| `knowledge/semantics/baseline_semantics.json` | 7 rules | `rag/lighting_semantics/index.faiss` + `.pkl` |

Embeddings model: `sentence-transformers/all-MiniLM-L6-v2` (via `langchain-huggingface`).

### FAISS Indexes (Python 3.11)

| Index | `.faiss` size | `.pkl` size |
|-------|---------------|-------------|
| Auditorium | 82,989 B | 18,013 B |
| Semantics | 10,797 B | 2,881 B |

### Palette Adapter Output Shape

```python
{
    "primary_colors": [{"name": "warm_amber", "rgb": [255, 191, 0]}],
    "intensity": {"default": 80},
    "transition": {"type": "fade", "duration": 2.0},
    "color_temperature": "warm"
}
```

## 5. Boundaries

- Does **NOT** make lighting decisions (Phase 4)
- Does **NOT** call LLM APIs
- Does **NOT** modify scene data or emotions
- Does **NOT** render or simulate lighting

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| FAISS index missing | **HARD FAIL** | Pipeline halts |
| Deserialization error | **HARD FAIL** | Pipeline halts |
| No results | Returns empty | "No RAG context available" |

Phase 3 is REQUIRED.

## 7. Current Limitations

- `allow_dangerous_deserialization=True` required (local indexes only)
- Full rebuild required for knowledge changes (no incremental updates)
- Must rebuild indexes if Python or dependency versions change

### Rebuild Command

```bash
conda activate venv_ALG_311
python -m phase_3.ingestion.knowledge_ingestion
```

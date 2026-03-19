# Phase 3 — Dual RAG Knowledge Retrieval

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 3 provides contextual knowledge for lighting decisions by performing FAISS-based similarity search across two knowledge bases: auditorium fixtures and lighting semantics rules.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Emotion label | Phase 2 | String (e.g., `fear`, `neutral`) |
| Scene text | Phase 1 | String |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| RAG context string | Phase 4 (LLM prompt) | Formatted text (via `build_context_for_llm`) |
| Palette dict | Phase 4 (rule-based fallback) | Dict (via `retrieve_palette`) |

Baseline context length: 1891–2132 characters per scene.

## 4. Internal Components

### Phase3Retriever (`rag_retriever.py`)

| Method | Purpose | Called By |
|--------|---------|-----------|
| `retrieve_auditorium_context(query, k=5)` | FAISS search on fixture index | Internal |
| `retrieve_semantics_context(emotion, script_type, k=3)` | FAISS search on semantics index | Internal |
| `build_context_for_llm(emotion, scene_text)` | Merges fixture + semantics into text string | Phase 6 (pipeline) |
| `retrieve_palette(emotion)` | Maps semantics → palette dict for Phase 4 fallback | Phase 4 (rule-based) |

### Knowledge Ingestion (`ingestion/knowledge_ingestion.py`)

Builds FAISS indexes from source JSON files:

| Source | Documents | Output |
|--------|-----------|--------|
| `knowledge/auditorium/fixtures.json` | 54 fixtures | `rag/auditorium/index.faiss` + `.pkl` |
| `knowledge/semantics/baseline_semantics.json` | 7 rules | `rag/lighting_semantics/index.faiss` + `.pkl` |

Embeddings: `sentence-transformers/all-MiniLM-L6-v2` via `langchain-huggingface`.

### FAISS Indexes (Rebuilt for Python 3.11)

| Index | File Size (faiss) | File Size (pkl) |
|-------|-------------------|-----------------|
| Auditorium | 82,989 bytes | 18,013 bytes |
| Semantics | 10,797 bytes | 2,881 bytes |

### Palette Adapter (`retrieve_palette`)

Maps semantics metadata into the dict shape Phase 4's `_build_group_instructions` expects:

```python
{
    "primary_colors": [{"name": "warm_amber", "rgb": [255, 191, 0]}],
    "intensity": {"default": 80},
    "transition": {"type": "fade", "duration": 2.0},
    "color_temperature": "warm"
}
```

Color mappings: amber, yellow, pink, red, orange, blue, purple, dark_blue, cold_white, blackout.
Speed mappings: slow→4.0s, medium→2.0s, fast→0.5s.

## 5. Boundaries

- Phase 3 does **NOT** make lighting decisions
- Phase 3 does **NOT** call any LLM API
- Phase 3 does **NOT** modify scene data or emotion labels
- Phase 3 does **NOT** render or simulate lighting

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| FAISS index missing | **HARD FAIL** | Pipeline halts |
| Deserialization error | **HARD FAIL** | Pipeline halts |
| No results returned | Returns empty | `build_context_for_llm` returns "No RAG context available" |

Phase 3 is REQUIRED — the pipeline depends on RAG context for lighting decisions.

## 7. Current Limitations

- `allow_dangerous_deserialization=True` is required for LangChain FAISS loading (local indexes only)
- Indexes must be rebuilt if Python version or dependency versions change significantly
- No incremental index updates — full rebuild required for any knowledge changes

### Rebuild Command

```bash
conda activate venv_ALG_311
python -m phase_3.ingestion.knowledge_ingestion
```

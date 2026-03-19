# Phase 4 — Lighting Decision Engine

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 4 generates a `LightingInstruction` for each scene. It supports two modes: a deterministic rule-based engine (baseline) and an LLM-enhanced engine (GenAI mode, pending SDK upgrade).

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Enriched scene dict | Phase 2 / Phase 6 | Dict with `emotion`, `content`, `timing` |
| RAG context string | Phase 3 | Formatted text from `build_context_for_llm` |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| `LightingInstruction` | Phase 5, Phase 7, `data/lighting_cues/` | Pydantic model / dict |

### LightingInstruction Structure

```python
{
    "scene_id": "scene_001",
    "groups": [
        {
            "group_id": "front_wash",
            "parameters": {"intensity": 0.75, "color": {...}},
            "transition": {"type": "fade", "duration": 2.0}
        }
    ]
}
```

Baseline produces 2 groups per scene: `front_wash` and `back_light`.

## 4. Internal Components

### Classes

| Component | Description |
|-----------|-------------|
| `LightingDecisionEngine` | Main class — creates LLM chain or falls back to rules |
| `LightingInstruction` | Pydantic output model |
| `GroupInstruction` | Per-group parameters (Pydantic) |
| `SimpleRetriever` | Hardcoded palette fallback (used if Phase 3 unavailable) |

### Key Methods

| Method | Description |
|--------|-------------|
| `__init__(use_llm, api_key)` | Initializes engine; selects LLM or rule-based mode |
| `generate_instruction(scene_data)` | Produces `LightingInstruction` for one scene |
| `_create_llm_chain()` | Builds LangChain chain: `ChatPromptTemplate → ChatOpenAI → PydanticOutputParser` |
| `_rule_based_generation(emotion, scene_text)` | Deterministic fallback using `retrieve_palette` |
| `_build_group_instructions(palette)` | Converts palette dict → group instruction list |

### Configuration (in `config.py`)

| Config | Value | Description |
|--------|-------|-------------|
| `LLM_MODEL` | `gpt-4` | OpenAI model |
| `LLM_TEMPERATURE` | `0.0` | Deterministic output |
| `LLM_MAX_TOKENS` | `500` | Bill spike prevention |
| `FALLBACK_TO_RULES` | `True` | Auto-fallback on LLM failure |
| `LANGCHAIN_VERBOSE` | `False` | Debug logging |

### Operating Modes

| Mode | Config | Status | Description |
|------|--------|--------|-------------|
| Rule-based | `use_llm=False` | ✅ Active | Deterministic, uses `retrieve_palette` from Phase 3 |
| GenAI (LLM) | `use_llm=True` | ⚠ Blocked | LangChain chain with GPT-4 + Pydantic structured output |

## 5. Boundaries

- Phase 4 does **NOT** perform rendering or simulation (that is Phase 5)
- Phase 4 does **NOT** perform RAG retrieval (that is Phase 3)
- Phase 4 does **NOT** detect emotions (that is Phase 2)
- Phase 4 does **NOT** compute metrics or log traces (that is Phase 7)

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| LLM API error | Caught | Falls back to rule-based if `FALLBACK_TO_RULES=True` |
| Rule-based failure | **HARD FAIL** | Pipeline halts via `HardFailureError` |
| Missing API key | Caught | `use_llm` set to `False` automatically |
| Output parsing error | Caught | Falls back to rule-based |

Phase 4 is REQUIRED — pipeline halts if both LLM and rule-based paths fail.

## 7. Current Limitations

- LLM mode blocked by `langchain-openai==0.1.6` / `openai==1.30.1` proxy arg conflict
- Rule-based mode uses only 2 of 5 available groups (coverage = 0.4)
- `dotenv` loaded at module level; `.env` file must exist for import to succeed
- `SimpleRetriever` hardcoded palettes only used if Phase 3 retriever is unavailable

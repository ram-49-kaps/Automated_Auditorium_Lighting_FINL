# Phase 4 — Lighting Decision Engine

> Updated: 2026-02-22. Reflects 5/5 group coverage and correct output schema.

## 1. Purpose

Phase 4 generates a `LightingInstruction` for each scene. It supports two modes: deterministic rule-based (baseline) and LLM-enhanced (GenAI, pending SDK upgrade). The rule-based path uses emotion-to-palette mappings from Phase 3's semantics retrieval.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Enriched scene dict | Phase 2 / Phase 6 | Dict with `emotion`, `content`, `timing` |
| RAG context | Phase 3 | Text string (LLM mode) or palette dict (rule-based) |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| `LightingInstruction` | Phase 5, Phase 7 | Dict conforming to `contracts/lighting_instruction_schema.json` |

Each instruction contains 5 groups: `front_wash`, `back_light`, `side_fill`, `specials`, `ambient`.

## 4. Internal Components

| Component | Description |
|-----------|-------------|
| `LightingDecisionEngine` | Main class — selects LLM or rule-based |
| `LightingInstruction` | Pydantic output model |
| `GroupInstruction` | Per-group parameters |
| `SimpleRetriever` | Hardcoded palette fallback |
| `_create_llm_chain()` | LangChain: `ChatPromptTemplate → ChatOpenAI → PydanticOutputParser` |
| `_rule_based_generation()` | Deterministic fallback using `retrieve_palette` |

### Configuration (`config.py`)

| Config | Value | Description |
|--------|-------|-------------|
| `LLM_MODEL` | `gpt-4` | OpenAI model |
| `LLM_TEMPERATURE` | `0.3` | Slight creativity allowed |
| `LLM_MAX_TOKENS` | `500` | Bill spike prevention |
| `FALLBACK_TO_RULES` | `True` | Auto-fallback on LLM failure |

### Operating Modes

| Mode | Status | Description |
|------|--------|-------------|
| Rule-based (baseline) | ✅ Active | Deterministic, uses `retrieve_palette`, 5/5 groups |
| GenAI (LLM) | ⚠ Blocked | `langchain-openai` proxy arg conflict |

### Output Structure

| Field | Type | Description |
|-------|------|-------------|
| `scene_id` | string | From Phase 1 |
| `emotion` | string | Primary emotion driving lighting |
| `time_window` | object | `{start_time, end_time}` |
| `groups` | array | 5 groups with `group_id`, `parameters`, `transition` |
| `metadata` | object | Debug/reasoning info |

Intensity scale: **0–100** (percentage).

## 5. Boundaries

- Does **NOT** render or simulate (Phase 5)
- Does **NOT** perform RAG retrieval (Phase 3)
- Does **NOT** detect emotions (Phase 2)
- Does **NOT** compute metrics (Phase 7)

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| LLM API error | Caught | Falls back to rule-based |
| Rule-based failure | **HARD FAIL** | Pipeline halts |
| Missing API key | Caught | `use_llm` set to `False` |

Phase 4 is REQUIRED — halts if both paths fail.

## 7. Current Limitations

- LLM mode blocked by `langchain-openai==0.1.6` / `openai==1.30.1` conflict
- `dotenv` loaded at module level; `.env` must exist

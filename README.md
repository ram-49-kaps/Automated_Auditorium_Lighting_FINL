# Automated Auditorium Lighting System

Lighting automation for auditorium environments using Generative AI. The system reads time-stamped play or event scripts and produces lighting cue sequences matching each scene's mood, emotion, and context.

> **Current State**: `baseline-rule-engine-stable` — deterministic rule-based pipeline fully operational (Phases 1–7). GenAI mode pending SDK upgrade.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Phase 6: Orchestration                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Phase 1  │→ │ Phase 2  │→ │ Phase 3  │→ │ Phase 4  │        │
│  │ Parsing  │  │ Emotion  │  │   RAG    │  │ Decision │        │
│  │          │  │ Analysis │  │ Retrieval│  │  Engine  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │                                          │               │
│       ▼                                          ▼               │
│  ┌──────────┐                              ┌──────────┐         │
│  │ Phase 0  │                              │ Phase 5  │         │
│  │Contracts │                              │Simulation│         │
│  │ (Schema) │                              │          │         │
│  └──────────┘                              └──────────┘         │
│                                                  │               │
│                                                  ▼               │
│                                            ┌──────────┐         │
│                                            │ Phase 7  │         │
│                                            │Evaluation│         │
│                                            │ Metrics  │         │
│                                            └──────────┘         │
│                                                  │               │
│                                                  ▼               │
│                                            ┌──────────┐         │
│                                            │ Phase 8  │         │
│                                            │ Hardware │         │
│                                            │ (Future) │         │
│                                            └──────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

## Phase Summary

| Phase | Directory | Purpose | Status |
|-------|-----------|---------|--------|
| 0 | `contracts/` | JSON schema definitions (locked) | ✅ Stable |
| 1 | `phase_1/` | Script parsing & scene extraction | ✅ Stable |
| 2 | `phase_2/` | ML-based emotion analysis (DistilRoBERTa) | ✅ Stable |
| 3 | `phase_3/` | Dual FAISS RAG retrieval (fixtures + semantics) | ✅ Rebuilt |
| 4 | `phase_4/` | Lighting decision engine (rule-based + LLM) | ✅ Rule-based |
| 5 | `phase_5/` | 3D simulation & visualization | ✅ Stable |
| 6 | `phase_6/` | Pipeline orchestration & state tracking | ✅ Stable |
| 7 | `phase_7/` | Trace logging & evaluation metrics | ✅ Wired |
| 8 | `phase_8/` | DMX/hardware execution | 🔮 Future |

## Supported Input Formats

| Format | Extension | Status |
|--------|-----------|--------|
| Plain Text | `.txt` | ✅ Full Support |
| PDF | `.pdf` | ✅ Full Support |
| Word | `.docx` | ✅ Full Support |

## Quick Start

### Prerequisites

```bash
# Create Conda environment (Python 3.11)
conda create -n venv_ALG_311 python=3.11
conda activate venv_ALG_311

# Install dependencies
pip install -r requirements.txt
```

### Run Baseline Pipeline

```bash
# Execute rule-based pipeline (all phases)
python run_pipeline_test.py
```

Expected output:
```
Phase 1: success  → {'scene_count': 10}
Phase 2: success  → {'emotion': 'neutral'}
Phase 3: success  → {'context_length': 2132}
Phase 4: success  → {'groups_count': 2}
Phase 5: success
Phase 7: success  → {'entries': 10, 'drift_score': 0.333}
```

### Configuration

Edit `phase_6/config_models.py` or pass to `PipelineConfig`:

```python
config = PipelineConfig(
    enable_phase_5=True,   # Simulation rendering
    enable_phase_7=True,   # Metrics & tracing
    use_llm=False          # Rule-based (baseline)
)
```

### Enable LLM Mode (GenAI)

> **⚠ Warning**: LLM mode is currently blocked by a `langchain-openai==0.1.6` / `openai==1.30.1` proxy arg conflict. Upgrade `langchain-openai>=0.1.7` before enabling.

```python
# In run_pipeline_test.py
config = PipelineConfig(
    use_llm=True   # Requires OPENAI_API_KEY in .env
)
```

Safe limits in `config.py`:
- `LLM_TEMPERATURE = 0.0` (deterministic)
- `LLM_MAX_TOKENS = 500` (bill spike prevention)
- `LLM_MODEL = "gpt-4"`
- `FALLBACK_TO_RULES = True` (auto-fallback on LLM failure)

### Rebuild FAISS Indexes

```bash
conda activate venv_ALG_311
python -m phase_3.ingestion.knowledge_ingestion
```

This rebuilds from source JSON files in `phase_3/knowledge/`:
- Auditorium fixtures: 54 documents → `phase_3/rag/auditorium/`
- Lighting semantics: 7 rules → `phase_3/rag/lighting_semantics/`

### Enable Metrics

Set `enable_phase_7=True` in pipeline config. Outputs:
- Trace file: `data/traces/trace_<uuid>.json`
- Console metrics: drift score, coverage, diversity

## Baseline Metrics (Rule-Based)

| Metric | Value | Description |
|--------|-------|-------------|
| Drift Score | 0.333 | How much lighting changes between consecutive scenes (0=stable, 1=chaotic) |
| Coverage | 0.4 | Groups used / total (2 of 5: `front_wash`, `back_light`) |
| Diversity | 0.075–0.24 | Intensity range per scene |
| Transition Types | 1 | `fade` only in baseline |
| Determinism | 1.0 | Same input always produces same output (rule-based guarantee) |

### Metrics Definitions

- **Drift Score**: Average (1 − Jaccard similarity) between consecutive scene instructions. Lower = more stable.
- **Coverage**: `|groups_used| / |available_groups|`. Available groups: `front_wash`, `back_light`, `side_fill`, `specials`, `ambient`.
- **Diversity**: Per-scene spread of parameters (intensity range, transition type variety, color count).
- **Determinism**: Structural match between two runs with identical input. Defined by group ID match + intensity within ε=0.05 + transition type match.

## Research Positioning

This system implements a **dual-mode** architecture:

1. **Deterministic Baseline** (rule-based) — provides reproducible, predictable lighting decisions from hand-coded rules mapped to emotions and fixture semantics.
2. **GenAI Augmentation** (LLM-enhanced) — uses GPT-4 via LangChain for creative, context-aware lighting decisions. Structured output via Pydantic.
3. **Comparative Evaluation** (Phase 7) — metrics engine enables quantitative comparison between baseline and GenAI modes: determinism, drift, coverage, diversity, and cross-run stability.

This architecture supports research claims about AI-generated lighting quality by providing a measurable baseline for comparison.

## Known Issues

| Issue | Impact | Resolution |
|-------|--------|------------|
| `langchain-openai==0.1.6` proxy conflict | LLM mode crashes | Upgrade to `langchain-openai>=0.1.7` |
| Scene IDs default to `unknown` | Metrics lack scene identifiers | Phase 1 parser does not set `scene_id` |
| Rule-based uses 2/5 groups | Low coverage metric | Expected; GenAI mode will use more |
| HuggingFace `resume_download` warning | Non-fatal console noise | Cosmetic; no action needed |

## Project Structure

```
Automated_Auditorium_Lighting/
├── contracts/              # Phase 0: JSON schemas (locked)
├── phase_1/                # Script parsing & scene extraction
├── phase_2/                # Emotion analysis (DistilRoBERTa)
├── phase_3/                # Dual RAG (FAISS indexes + retriever)
├── phase_4/                # Lighting decision engine
├── phase_5/                # 3D simulation & visualization
├── phase_6/                # Pipeline orchestration
├── phase_7/                # Evaluation & metrics
├── phase_8/                # Hardware execution (future)
├── data/                   # Scripts, outputs, traces
├── docs/                   # Documentation
├── config.py               # Global configuration
├── run_pipeline_test.py    # Pipeline entry point
└── requirements.txt        # Python dependencies
```

See `docs/DIRECTORY_STRUCTURE.md` for the complete file tree.

## License

[Your License]
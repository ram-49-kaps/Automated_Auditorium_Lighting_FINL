# Phase 2 — Emotion Enrichment

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 2 classifies the dominant emotion of each scene's text using a pre-trained ML model. The detected emotion drives RAG retrieval (Phase 3) and lighting decisions (Phase 4).

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene dict | Phase 1 / Phase 6 | Dict with `content` text string |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Enriched scene dict | Phase 3, Phase 4 | Original scene + `emotion.primary_emotion` |

Emotion labels: `neutral`, `fear`, `surprise`, `joy`, `anger`, `sadness`, `disgust`.

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `emotion_analyzer.py` | `EmotionAnalyzer` | HuggingFace transformer pipeline wrapper |
| `__init__.py` | Public export | Exports `EmotionAnalyzer` |

### Model Details

| Property | Value |
|----------|-------|
| Model | `j-hartmann/emotion-english-distilroberta-base` |
| Framework | HuggingFace Transformers |
| Inference | Local (no API calls) |
| Output | Emotion label + confidence score |

## 5. Boundaries

- Does **NOT** modify scene text
- Does **NOT** call LLM APIs (local model only)
- Does **NOT** perform RAG retrieval or lighting decisions
- Does **NOT** access FAISS indexes

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| Model load failure | **SOFT** | Defaults to `neutral` |
| Inference error | **SOFT** | Defaults to `neutral` |
| Empty text | **SOFT** | Returns `neutral` |

Phase 2 is OPTIONAL — pipeline continues with `neutral` on failure.

## 7. Current Limitations

- Single emotion per scene (no multi-label)
- Confidence score not used downstream
- HuggingFace `resume_download` deprecation warning (cosmetic)
- `TOKENIZERS_PARALLELISM` warning in Conda

## Baseline Results (Script-1.txt)

| Emotion | Scene Count |
|---------|-------------|
| neutral | 6 |
| fear | 3 |
| surprise | 1 |

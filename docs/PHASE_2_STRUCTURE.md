# Phase 2 — Emotion Analysis

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 2 classifies the dominant emotion of each scene's text using a pre-trained ML model. The detected emotion drives Phase 3 RAG retrieval and Phase 4 lighting decisions.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene dict | Phase 1 / Phase 6 | Dict with `content` (text string) |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Enriched scene dict | Phase 3, Phase 4 | Original scene + `emotion.primary_emotion` |

Detected emotion labels: `neutral`, `fear`, `surprise`, `joy`, `anger`, `sadness`, `disgust`.

## 4. Internal Components

### Classes & Functions

| File | Component | Description |
|------|-----------|-------------|
| `emotion_analyzer.py` | `EmotionAnalyzer` | Wraps HuggingFace transformer pipeline |
| `__init__.py` | Public import | Exports `EmotionAnalyzer` |

### Model

| Property | Value |
|----------|-------|
| Model | `j-hartmann/emotion-english-distilroberta-base` |
| Framework | HuggingFace Transformers |
| Input | Text string (scene content) |
| Output | Emotion label + confidence score |

## 5. Boundaries

- Phase 2 does **NOT** modify scene text or structure
- Phase 2 does **NOT** call any LLM API (uses local ML model only)
- Phase 2 does **NOT** perform RAG retrieval or lighting decisions
- Phase 2 does **NOT** access FAISS indexes

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| Model load failure | **SOFT** | Defaults emotion to `neutral`, pipeline continues |
| Inference error | **SOFT** | Defaults emotion to `neutral`, pipeline continues |
| Empty scene text | **SOFT** | Returns `neutral` |

Phase 2 is OPTIONAL — the pipeline continues with `neutral` if emotion detection fails.

## 7. Current Limitations

- Single emotion per scene (no multi-label classification)
- Confidence score is computed but not currently used in downstream phases
- HuggingFace `resume_download` deprecation warning is cosmetic and non-fatal
- `TOKENIZERS_PARALLELISM` warning when running in Conda — set environment variable to suppress

### Baseline Results (Script-1.txt)

| Scenes | Emotion |
|--------|---------|
| 6 | neutral |
| 3 | fear |
| 1 | surprise |

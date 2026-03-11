# Phase 2 — Emotion Enrichment

> Updated: 2026-02-22. Reflects chunked analysis and anti-neutral bias fixes.

## 1. Purpose

Phase 2 classifies the dominant emotion of each scene's text using a pre-trained ML model. The detected emotion drives RAG retrieval (Phase 3) and lighting decisions (Phase 4).

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene dict | Phase 1 / Phase 6 | Dict with `content.text` string |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Enriched scene dict | Phase 3, Phase 4 | Original scene + `emotion.primary_emotion`, `emotion.primary_score`, `emotion.all_scores` |

Emotion labels: `neutral`, `fear`, `surprise`, `joy`, `anger`, `sadness`, `disgust`.

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `emotion_analyzer.py` | `EmotionAnalyzer` | HuggingFace transformer pipeline wrapper with chunked analysis |
| `__init__.py` | Public export | Exports `EmotionAnalyzer` |

### Model Details

| Property | Value |
|----------|-------|
| Model | `j-hartmann/emotion-english-distilroberta-base` |
| Framework | HuggingFace Transformers |
| Inference | Local (no API calls) |
| Output | Emotion label + confidence score for all 7 emotions |

### Chunked Analysis (Long Text Fix)

For texts over 400 characters, the analyzer:
1. Splits text into ~400-char chunks
2. Runs ML inference on each chunk
3. Averages emotion scores across chunks
4. Returns the aggregated top emotion

### Anti-Neutral Bias

If "neutral" is the top predicted emotion but another emotion scores ≥ 0.25, the stronger non-neutral emotion is promoted. This prevents scripts with subtle emotional content from being blanket-classified as neutral.

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
- HuggingFace `resume_download` deprecation warning (cosmetic)

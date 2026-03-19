# Phase 1 — Script Ingestion

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 1 reads raw script files (.txt, .pdf, .docx), detects format, cleans text, segments into scenes, generates timestamps, and builds standardized JSON for downstream phases.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / Phase 6 | `.txt`, `.pdf`, `.docx` |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Scene list | Phase 2, Phase 6 | `List[Dict]` — `content`, `timing`, `metadata` |
| JSON file | `data/standardized_output/` | Persisted JSON |

## 4. Internal Components

| File | Class/Function | Description |
|------|----------------|-------------|
| `format_detector.py` | `FormatDetector` | Detects screenplay / stage play / generic format |
| `text_cleaner.py` | `TextCleaner` | Normalizes whitespace, encoding |
| `scene_segmenter.py` | `SceneSegmenter` | Splits at SCENE/ACT/INT/EXT headings |
| `timestamp_generator.py` | `TimestampGenerator` | Estimates timing from word count (`WORDS_PER_MINUTE` config) |
| `json_builder.py` | `JSONBuilder` | Assembles scenes into JSON with metadata |
| `__init__.py` | `parse_script()` | Public entry point |

## 5. Boundaries

- Does **NOT** perform emotion analysis (Phase 2)
- Does **NOT** call LLMs or ML models
- Does **NOT** access FAISS indexes (Phase 3)
- Does **NOT** generate lighting instructions (Phase 4)

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| File not found | **HARD FAIL** | Pipeline halts |
| Unsupported format | **HARD FAIL** | Pipeline halts |
| Zero scenes extracted | **HARD FAIL** | Pipeline halts |

Phase 1 is REQUIRED — pipeline cannot continue without scenes.

## 7. Current Limitations

- Scene IDs default to `unknown` — no unique identifier generation
- No OCR for scanned PDFs
- Legacy `.doc` format not supported
- Timestamp estimation based on word count only

## Execution Flow

```
Input File → FormatDetector → TextCleaner → SceneSegmenter → TimestampGenerator → JSONBuilder → Scene List
```

## Baseline Results (Script-1.txt)

- 10 scenes extracted
- Formats supported: `.txt` (tested), `.pdf` and `.docx` (available)

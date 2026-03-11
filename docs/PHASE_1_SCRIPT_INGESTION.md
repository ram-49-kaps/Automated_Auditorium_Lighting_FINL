# Phase 1 — Script Ingestion

> Updated: 2026-02-22. Reflects current pipeline with scene ID generation and process_script() entry point.

## 1. Purpose

Phase 1 reads raw script files (.txt, .pdf, .docx), detects format, cleans text, segments into scenes, generates timestamps, and builds standardized JSON for downstream phases.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / Phase 6 | `.txt`, `.pdf`, `.docx` |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Scene list | Phase 2, Phase 6 | `List[Dict]` — `scene_id`, `content`, `timing` |
| JSON file | `data/standardized_output/` | Persisted JSON |

Scene output conforms to `contracts/scene_schema.json`.

## 4. Internal Components

| File | Function | Description |
|------|----------|-------------|
| `format_detector.py` | `detect_format()` | Detects screenplay / timestamped / dialogue / act format |
| `text_cleaner.py` | `clean_text()` | Normalizes whitespace, preserves em-dashes and markers |
| `scene_segmenter.py` | `segment_scenes()` | Context-aware splitting by INT./EXT./ACT/timestamps/dialogue |
| `timestamp_generator.py` | `generate_timestamps()` | Estimates timing from word count (`WORDS_PER_MINUTE` config) |
| `json_builder.py` | `build_complete_output()` | Assembles scenes into JSON with metadata |
| `__init__.py` | `process_script()` | Public entry point — runs full pipeline in one call |

### Scene Segmentation Priority

1. Timestamps (`00:00 – 03:00`)
2. Screenplay headers (`INT.`/`EXT.`/`FADE IN`/`CUT TO`)
3. Act/Scene structure
4. Dialogue blocks (speaker changes)
5. Generic word-count fallback

### Scene IDs

Generated as `scene_001`, `scene_002`, etc. (sequential, zero-padded).

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

## 7. Configuration

| Config | Value | Description |
|--------|-------|-------------|
| `MAX_WORDS_PER_SCENE` | 400 | Maximum words before splitting a scene |
| `MIN_WORDS_PER_SCENE` | 50 | Minimum words to form a valid scene |
| `WORDS_PER_MINUTE` | 150 | Speaking speed for timestamp estimation |

## Execution Flow

```
Input File → detect_format() → clean_text() → segment_scenes() → generate_timestamps() → merge + scene_ids → Scene List
```

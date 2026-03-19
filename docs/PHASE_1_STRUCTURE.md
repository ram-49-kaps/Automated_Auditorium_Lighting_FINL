# Phase 1 — Script Parsing & Scene Extraction

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 1 reads raw script files in multiple formats (.txt, .pdf, .docx), detects the script format (screenplay, stage play, or generic), cleans the text, segments it into discrete scenes, generates timing estimates, and assembles a standardized JSON structure for downstream phases.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script file path | User / Phase 6 | `.txt`, `.pdf`, `.docx` |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| List of scene dicts | Phase 2, Phase 6 | `List[Dict]` with `content`, `timing`, `metadata` |
| Standardized JSON | `data/standardized_output/` | JSON file |

## 4. Internal Components

### Classes & Functions

| File | Component | Description |
|------|-----------|-------------|
| `format_detector.py` | `FormatDetector` | Detects screenplay vs stage play vs generic format |
| `text_cleaner.py` | `TextCleaner` | Normalizes whitespace, encoding, removes artifacts |
| `scene_segmenter.py` | `SceneSegmenter` | Splits text at heading patterns (SCENE, ACT, INT/EXT) |
| `timestamp_generator.py` | `TimestampGenerator` | Estimates timing from word count using `WORDS_PER_MINUTE` config |
| `json_builder.py` | `JSONBuilder` | Assembles scenes into final JSON with metadata |
| `__init__.py` | `parse_script()` | Public entry point called by Phase 6 |

### Configuration (in `config.py`)

| Config | Default | Description |
|--------|---------|-------------|
| `WORDS_PER_MINUTE` | 150 | Speaking rate for timestamp estimation |

## 5. Boundaries

- Phase 1 does **NOT** perform emotion analysis (that is Phase 2)
- Phase 1 does **NOT** call any LLM or ML model
- Phase 1 does **NOT** interact with FAISS indexes
- Phase 1 does **NOT** generate lighting instructions

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| File not found | **HARD FAIL** | Pipeline halts via `HardFailureError` |
| Unsupported format | **HARD FAIL** | Pipeline halts |
| Zero scenes extracted | **HARD FAIL** | Pipeline halts |
| PDF extraction error | **HARD FAIL** | Requires PyPDF2 installed |
| DOCX read error | **HARD FAIL** | Requires python-docx installed |

Phase 1 is REQUIRED — the pipeline cannot continue without at least one scene.

## 7. Current Limitations

- Scene IDs are not generated; scenes default to `unknown` in downstream phases
- No OCR support for scanned PDFs
- Legacy `.doc` format is not supported (must convert to `.docx`)
- Timestamp estimation is based on word count only, not actual timing metadata in the script

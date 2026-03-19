# Phase 1 — Script → Scene Structure Processing

> **Entry point:** `phase_1.run_phase_1(script_path)` → `(scenes, metadata)`

Phase 1 converts an arbitrary script file into a list of schema-conformant scene JSON objects with timestamps. It handles **any script format** — screenplays, dialogue scripts, event schedules, cue sheets, and plain text — through a format-agnostic pipeline that uses structural signals, not hard-coded format assumptions.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Sub-Phase Breakdown](#sub-phase-breakdown)
  - [Phase 1A — Text Acquisition](#phase-1a--text-acquisition)
  - [Phase 1B — Immutable Structuring](#phase-1b--immutable-structuring)
  - [Chunk Preprocessing](#chunk-preprocessing)
  - [Phase 1C Call 1 — LLM Scene Segmentation](#phase-1c-call-1--llm-scene-segmentation)
  - [Boundary Snapping (Post-LLM)](#boundary-snapping-post-llm)
  - [Phase 1C Call 2 — Hybrid Timestamp Assignment](#phase-1c-call-2--hybrid-timestamp-assignment)
  - [Phase 1D — Deterministic Validation & Fallback](#phase-1d--deterministic-validation--fallback)
  - [Phase 1E — Scene JSON Construction](#phase-1e--scene-json-construction)
- [File Map](#file-map)
- [Dependencies](#dependencies)
- [Configuration Reference](#configuration-reference)
- [Output Schema](#output-schema)
- [Generalization — How It Handles Any Script](#generalization--how-it-handles-any-script)
- [Failure Hierarchy](#failure-hierarchy)

---

## Architecture Overview

```
Script File (.txt, .pdf, .docx)
    │
    ▼
┌──────────────────────────────────────────────────┐
│ Phase 1A — Text Acquisition                      │
│   Direct extract → OCR fallback (Mistral)        │
│   Outputs: AcquisitionResult (text + provenance)  │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Phase 1B — Immutable Structuring                 │
│   UTF-8 NFC → newline normalize → invis. cleanup │
│   SHA-256 hash → 1-based line index              │
│   Outputs: ImmutableText (FROZEN, never modified) │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Chunk Preprocessor                               │
│   Structural anchors → sliding window → overlap  │
│   Outputs: List[ChunkInfo] (line-numbered text)  │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Phase 1C Call 1 — LLM Scene Segmentation         │
│   Qwen2.5-7B via HuggingFace Inference API      │
│   Per-chunk → merge → boundary snap to INT./EXT. │
│   Fallback: Rule-based marker segmentation       │
│   Outputs: scenes with scene_id, start/end line  │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Phase 1C Call 2 — Hybrid Timestamp Engine        │
│   Regex extract → confidence scoring →           │
│   map to scenes → fill gaps with word-count est. │
│   → monotonic enforcement                        │
│   Outputs: scenes + start_time/end_time/duration │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Phase 1D — Validation & Fallback                 │
│   Overlap check → gap check → coverage check     │
│   Retry LLM → fallback to rules → HARD FAIL     │
│   Outputs: validated scenes                      │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│ Phase 1E — Scene JSON Construction               │
│   Text slicing from ImmutableText → schema valid │
│   Outputs: scene_schema.json conformant dicts    │
└──────────────────────────────────────────────────┘
```

---

## Sub-Phase Breakdown

### Phase 1A — Text Acquisition

**File:** `phase_1/text_acquisition.py` (342 lines)

Extracts raw text from the input file. Format-agnostic — handles `.txt`, `.pdf`, `.docx`, and any text-readable format.

**Flow:**
1. Detect file extension
2. Attempt **direct extraction** via `utils/file_io.read_script()`
3. If direct extraction fails or returns empty AND file is `.pdf` → **OCR fallback** using Mistral OCR API
4. Validate quality (avg line length, noise ratio)
5. If OCR confidence < threshold → **HARD STOP** (no silent corruption)

**Key classes:**

| Class | Purpose |
|-------|---------|
| `AcquisitionResult` | Container: `text`, `source_method`, `confidence`, `ocr_used`, `quality_checks_passed` |
| `AcquisitionHardStop` | Exception: unrecoverable acquisition failure |

**Quality gates (OCR only):**
- Confidence ≥ `OCR_CONFIDENCE_THRESHOLD` (0.85)
- Avg line length between `OCR_AVG_LINE_LENGTH_MIN` (10) and `OCR_AVG_LINE_LENGTH_MAX` (500)
- Character noise ratio ≤ `OCR_NOISE_RATIO_MAX` (0.05)

> [!NOTE]
> OCR is only triggered for PDF files. `.txt` and `.docx` always use direct extraction. If direct extraction succeeds, OCR is never attempted — quality warnings are logged but don't block the pipeline.

---

### Phase 1B — Immutable Structuring

**File:** `phase_1/immutable_structurer.py` (189 lines)

Creates a **frozen, auditable coordinate system** from the acquired text. After this step, the text is **NEVER modified** by any downstream module.

**Operations (in order):**
1. **UTF-8 NFC normalization** — canonical Unicode representation
2. **Newline normalization** — `\r\n` → `\n`, bare `\r` → `\n`. No blank-line collapsing (blanks are structural signals)
3. **Invisible character cleanup** — removes 18 types of zero-width/invisible Unicode characters (BOM, zero-width spaces, soft hyphens, etc.)
4. **SHA-256 hash** — fingerprint of final text for audit trail
5. **1-based line indexing** — `Dict[int, str]` mapping line numbers to content
6. **Structural metadata extraction** — identifies blank lines, uppercase headers, separator lines

**Key classes:**

| Class | Fields |
|-------|--------|
| `ImmutableText` | `lines` (1-based dict), `sha256_hash`, `total_lines`, `structural_metadata`, `raw_text`, `source_method` |
| `StructuralMetadata` | `blank_line_indices`, `uppercase_line_indices`, `separator_line_indices`, `total_non_blank_lines` |

**Separator detection** uses a regex pattern that catches `INT.`, `EXT.`, `ACT`, `SCENE`, `---`, `===`, `***` markers. This is used for chunking hints, NOT for scene segmentation.

---

### Chunk Preprocessing

**File:** `phase_1/chunk_preprocessor.py` (285 lines)

Splits the immutable text into overlapping chunks before sending to the LLM. Required because LLMs have token limits and long scripts must be processed in pieces.

**Algorithm:**
1. Find **structural anchors** (separator lines, uppercase headers, blank-line clusters)
2. Split at anchors into structural chunks respecting `CHUNK_MAX_LINES` (150)
3. Add `CHUNK_OVERLAP_LINES` (10) overlap between adjacent chunks for boundary context
4. If script ≤ 150 lines → single chunk (no splitting needed)

**Merge rules (deterministic, applied after all chunks processed):**
1. **Earlier chunk wins** — if overlap zone has duplicate scene, keep earlier chunk's version
2. **Deduplicate by `start_line`** — identical `start_line` = same scene, keep earlier
3. **Global monotonic ordering** — `start_line[i] < start_line[i+1]`

**Key classes:**

| Class | Fields |
|-------|--------|
| `ChunkInfo` | `chunk_id`, `start_line`, `end_line`, `line_numbered_text`, `overlap_start`, `total_lines` |

> [!TIP]
> The line-numbered text format (`1: FADE IN:\n2: \n3: INT. HOUSE...`) is critical — it gives the LLM explicit line number references to include in its JSON output, making scene boundaries verifiable.

---

### Phase 1C Call 1 — LLM Scene Segmentation

**File:** `phase_1/llm_scene_segmenter.py` (377 lines)

Uses **Qwen2.5-7B-Instruct** via HuggingFace Inference API to identify scene boundaries. The LLM receives line-numbered text and returns a JSON array of `{scene_id, start_line, end_line}`.

**Flow:**
1. For each chunk → call HF Inference API with system prompt + user prompt
2. Parse JSON response (handles clean JSON, markdown code blocks, partial JSON)
3. Validate scene structure (start_line/end_line present and valid)
4. If API call fails → retry once → rule-based fallback for that chunk
5. Merge chunk results using deterministic merge rules
6. Assign sequential `scene_id`s (`scene_001`, `scene_002`, ...)

**LLM system prompt rules (key lines from the code):**
- Every `INT.` / `EXT.` line **must** start a new scene (mandatory boundaries)
- `ACT` / `SCENE` markers and dramatic shifts are additional split candidates
- `FADE IN`, `CUT TO` are **NOT** scene boundaries (transitions within scenes)
- Output is **pure JSON array** only — no markdown or explanation

**Rule-based fallback** uses 6 marker patterns:
1. `INT.` or `EXT.` (location headers)
2. `ACT I`, `ACT 2`, etc.
3. `SCENE I`, `SCENE 2`, etc.
4. Full uppercase lines ≥ 10 chars
5. Lines ending in `DAY` / `NIGHT` / `DAWN` / `DUSK` / `CONTINUOUS`

**If no markers found at all** (e.g. plain text with no screenplay formatting), the entire script is treated as a single scene.

> [!IMPORTANT]
> The LLM is configured with **temperature = 0** for deterministic output. The `HF_API_TOKEN` must be set in `.env` for the LLM path to work. If not set, the pipeline falls back to rule-based segmentation automatically.

---

### Boundary Snapping (Post-LLM)

**File:** `phase_1/__init__.py` (lines 144-209)

A **deterministic post-processing step** applied after LLM segmentation. It snaps scene boundaries to `INT.`/`EXT.` markers in the script.

**Algorithm:**
1. Scan all lines for `INT.` / `EXT.` / `INTERIOR` / `EXTERIOR` markers
2. If **no markers found** → keep LLM boundaries unchanged (dialogue scripts, plain text)
3. If markers found → create one scene per marker, with end_line = next marker - 1
4. Content before the first marker becomes a `prologue` scene
5. Reassign sequential `scene_id`s

**Why this exists:** The LLM might split a scene 2 lines before an `INT.` marker or 1 line after. This step ensures boundaries always align precisely with structural markers, making the output deterministic regardless of LLM variance. For scripts without any `INT./EXT.` markers, this step is a no-op.

---

### Phase 1C Call 2 — Hybrid Timestamp Assignment

**File:** `phase_1/timestamp_engine.py` (381 lines)

Assigns `start_time`, `end_time`, and `duration` (in seconds) to each scene. Uses a hybrid approach: extract explicit timestamps from the script if they exist, otherwise estimate from word count.

**Algorithm:**
1. **Regex extract** — scan the entire immutable text for 6 timestamp patterns:

   | Pattern | Example | Confidence |
   |---------|---------|------------|
   | `[Approx. Timestamp: HH:MM:SS]` | `[Approx. Timestamp: 00:01:30]` | 0.95 |
   | `[HH:MM:SS]` or `[MM:SS]` | `[00:30]` | 0.90 |
   | `HH:MM:SS` standalone | `01:30:00` | 0.85 |
   | `MM:SS` standalone | `05:30` | 0.70 |
   | `N.Ns` decimal seconds | `10.5s` | 0.80 |
   | `Ns` integer seconds | `30s` | 0.60 |

2. **Rule-based validation** — reject negative, reject > 12 hours, check monotonicity
3. **Map to scenes** — match candidates to scenes by line number proximity (±2 lines tolerance)
4. **Fill gaps** — scenes without extracted timestamps get estimated times based on:
   - Previous scene's end time + `SCENE_TRANSITION_BUFFER` (2s)
   - Word count estimation: `(words / WORDS_PER_MINUTE) * 60` (minimum 2s)
5. **Monotonic enforcement** — if timestamps aren't increasing, push forward and reduce confidence

**Output keys:** `start_time`, `end_time`, `duration`, `timestamp_confidence`, `timestamp_source` (extracted/estimated/adjusted)

> [!NOTE]
> This engine is format-agnostic. A script with `[Approx. Timestamp: 00:01:30]` markers, a script with `[3:45]` brackets, a script with `90s` markers, and a script with no timestamps at all — all are handled. When no timestamps exist, the engine uses word-count estimation to produce reasonable timing.

---

### Phase 1D — Deterministic Validation & Fallback

**File:** `phase_1/validation_layer.py` (326 lines)

Validates the LLM + timestamp output before passing to Phase 1E. Implements a **retry hierarchy** with strict quality gates.

**Scene structure validation rules:**
- No overlapping line ranges
- No gaps > `SCENE_GAP_TOLERANCE_LINES` (2 lines)
- `start_line < end_line` for every scene
- `start_line ≥ 1` and `end_line ≤ total_lines`
- Non-blank line coverage ≥ `SCENE_COVERAGE_THRESHOLD` (80%)

**Timestamp validation rules:**
- All scenes must have `start_time`
- `end_time ≥ start_time`
- `duration ≥ 0`
- Monotonic increasing `start_time` across scenes
- No jumps > `TIMESTAMP_MAX_JUMP_SECONDS` (1800s / 30 min)

**Retry hierarchy:**
```
Validate LLM output
    → PASS → continue
    → FAIL → retry_callback (re-run LLM + timestamps)
                → PASS → continue
                → FAIL → fallback_callback (rule-based segmentation)
                            → PASS → continue
                            → FAIL (strict) → try LENIENT mode
                                                → PASS → flag manual_review_required
                                                → FAIL → HARD FAIL (ValidationHardFail)
```

**Special behavior:** OCR-sourced text that requires LLM retry is flagged `manual_review_required = True`.

---

### Phase 1E — Scene JSON Construction

**File:** `phase_1/scene_json_builder.py` (209 lines)

Builds the final output conforming to `contracts/scene_schema.json`.

**Key behaviors:**
- **Text** is sliced deterministically from `ImmutableText.lines` (not from any intermediate buffer)
- **Emotion** is always `null` — Phase 2's job
- **Explicit lighting** is always `[]` — Phase 4's job
- **Script type** is detected via simple heuristic (presence of `INT./EXT.`, timestamps, cue/schedule markers)
- **Location** is extracted from `INT./EXT.` header lines if present, otherwise `null`
- Output is validated against `contracts/scene_schema.json` (if `jsonschema` is installed)

**Script type detection (format-agnostic):**

| Condition | Type Assigned |
|-----------|--------------|
| Has `INT./EXT.` + timestamps | `timestamped_drama` |
| Has `INT./EXT.` only | `raw_drama` |
| Has AM/PM schedule markers | `event_schedule` |
| Has "cue" + "light" near each other | `cue_sheet` |
| Has timestamps only | `timestamped_drama` |
| None of the above | `raw_drama` |

---

## File Map

```
phase_1/
├── __init__.py              # Orchestrator: run_phase_1() + boundary snapping
├── text_acquisition.py      # 1A: File → text (direct + OCR fallback)
├── immutable_structurer.py  # 1B: Text → frozen line-indexed structure
├── chunk_preprocessor.py    # Chunking: sliding window with overlap
├── llm_scene_segmenter.py   # 1C Call 1: LLM + rule-based segmentation
├── timestamp_engine.py      # 1C Call 2: Hybrid timestamp assignment
├── validation_layer.py      # 1D: Validation with retry hierarchy
└── scene_json_builder.py    # 1E: Schema-conformant JSON output
```

---

## Dependencies

### Python Standard Library
- `re`, `json`, `os`, `hashlib`, `unicodedata`, `logging`, `dataclasses`, `typing`, `statistics`, `pathlib`

### Internal Project Modules
- `config` — all tuning parameters (see [Configuration Reference](#configuration-reference))
- `utils.file_io` — `read_script()` used by Phase 1A for direct text extraction

### External Packages (Required)

| Package | Used By | Purpose |
|---------|---------|---------|
| `huggingface_hub` | `llm_scene_segmenter.py` | `InferenceClient` for HF API calls |
| `python-dotenv` | `llm_scene_segmenter.py`, `text_acquisition.py` | Load `.env` for API keys |

### External Packages (Optional)

| Package | Used By | Purpose | If Missing |
|---------|---------|---------|------------|
| `jsonschema` | `scene_json_builder.py` | Schema validation of output | Skipped with warning |
| `mistralai` | `text_acquisition.py` | Mistral OCR for PDFs | OCR path unavailable, direct extraction only |
| `PyPDF2` | `utils/file_io.py` | PDF text extraction | PDF support disabled |
| `python-docx` | `utils/file_io.py` | DOCX text extraction | DOCX support disabled |

### Environment Variables

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `HF_API_TOKEN` | For LLM path | HuggingFace Inference API token |
| `MISTRAL_API_KEY` | For OCR path | Mistral OCR API key (PDF files only) |

> [!TIP]
> If neither `HF_API_TOKEN` nor `MISTRAL_API_KEY` is set, Phase 1 still works — it falls back to rule-based segmentation and word-count timestamp estimation. The pipeline is **fully functional without any API keys** for `.txt` files.

---

## Configuration Reference

All settings in `config.py`:

### Timing
| Setting | Default | Used By |
|---------|---------|---------|
| `WORDS_PER_MINUTE` | 150 | `timestamp_engine.py` — word-count duration estimation |
| `SCENE_TRANSITION_BUFFER` | 2 (seconds) | `timestamp_engine.py` — gap between scenes |

### Chunking
| Setting | Default | Used By |
|---------|---------|---------|
| `CHUNK_MAX_LINES` | 150 | `chunk_preprocessor.py` — max lines per LLM chunk |
| `CHUNK_OVERLAP_LINES` | 10 | `chunk_preprocessor.py` — overlap for boundary context |

### LLM (Phase 1C)
| Setting | Default | Used By |
|---------|---------|---------|
| `PHASE1_LLM_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | `llm_scene_segmenter.py` |
| `PHASE1_LLM_TEMPERATURE` | 0.0 | `llm_scene_segmenter.py` — deterministic |
| `PHASE1_LLM_MAX_RETRIES` | 1 | `llm_scene_segmenter.py` |
| `PHASE1_LLM_MAX_NEW_TOKENS` | 2048 | `llm_scene_segmenter.py` |

### Validation (Phase 1D)
| Setting | Default | Used By |
|---------|---------|---------|
| `SCENE_GAP_TOLERANCE_LINES` | 2 | `validation_layer.py` — max gap between scenes |
| `SCENE_COVERAGE_THRESHOLD` | 0.80 | `validation_layer.py` — min non-blank line coverage |
| `TIMESTAMP_MAX_JUMP_SECONDS` | 1800 (30 min) | `validation_layer.py`, `timestamp_engine.py` |

### OCR (Phase 1A)
| Setting | Default | Used By |
|---------|---------|---------|
| `OCR_CONFIDENCE_THRESHOLD` | 0.85 | `text_acquisition.py` |
| `OCR_PROVIDER` | `"mistral"` | `text_acquisition.py` |
| `OCR_AVG_LINE_LENGTH_MIN` | 10 | `text_acquisition.py` — quality gate |
| `OCR_AVG_LINE_LENGTH_MAX` | 500 | `text_acquisition.py` — quality gate |
| `OCR_NOISE_RATIO_MAX` | 0.05 | `text_acquisition.py` — quality gate |

---

## Output Schema

Each scene dict conforms to `contracts/scene_schema.json`:

```json
{
  "scene_id": "scene_001",
  "script_type": "timestamped_drama",
  "time_window": {
    "start": 0.0,
    "end": 90.0
  },
  "duration": 90.0,
  "text": "INT. LIVING ROOM – NIGHT\nEmma sits by the window...",
  "location": "LIVING ROOM",
  "emotion": null,
  "explicit_lighting": []
}
```

**Required fields:** `scene_id`, `script_type`, `time_window`, `text`  
**Optional fields:** `location`, `emotion` (Phase 2 fills this), `explicit_lighting`, `duration`

**Supported `script_type` values:** `timestamped_drama`, `raw_drama`, `event_schedule`, `cue_sheet`, `mixed`

---

## Generalization — How It Handles Any Script

Phase 1 is **not tuned for any specific script**. Here's how it handles different formats:

| Script Type | Acquisition | Segmentation | Timestamps |
|-------------|-------------|--------------|------------|
| **Screenplay with INT./EXT.** | Direct text read | LLM + boundary snap to markers | Extracted from `[Approx. Timestamp: ...]` if present, else estimated |
| **Dialogue script (no INT./EXT.)** | Direct text read | LLM identifies dramatic shifts | Word-count estimation (no markers to extract) |
| **Event schedule** | Direct text read | LLM splits by events | Extracted from AM/PM or `HH:MM` timestamps |
| **PDF script** | Direct → OCR fallback | Same as above | Same as above |
| **Plain text (no formatting)** | Direct text read | LLM or single-scene fallback | Word-count estimation |
| **Cue sheet** | Direct text read | Split by cue markers | Extracted if present |

**Key generalization mechanisms:**
1. **Boundary snapping is conditional** — only activates if `INT./EXT.` markers exist. Dialogue scripts, event schedules, and plain text skip this step entirely.
2. **Timestamp extraction uses 6 regex patterns** — covers `[HH:MM:SS]`, `MM:SS`, `Ns`, `N.Ns`, and custom bracket formats. Scripts without any timestamp format get word-count estimation.
3. **Rule-based fallback is multi-marker** — uses `INT./EXT.`, `ACT/SCENE`, uppercase headers, and time-of-day endings (`DAY`/`NIGHT`/`DAWN`/`DUSK`). Scripts with none of these become a single scene.
4. **LLM system prompt is format-neutral** — instructs the model to identify "scene boundaries" based on location changes, dramatic shifts, and structural markers, not specific formatting conventions.
5. **`SCENE_MARKERS` in config.py** — only contains `INT.`, `EXT.`, `INTERIOR`, `EXTERIOR`. These are used by the old segmenter (not the new Phase 1C LLM path), but they no longer include transitions like `FADE IN` or `CUT TO`.

---

## Failure Hierarchy

Phase 1 has strict failure governance — **no silent data corruption is allowed**.

```
File not found         → FileNotFoundError
Empty text (direct)    → AcquisitionHardStop
OCR low confidence     → AcquisitionHardStop
OCR quality fail       → AcquisitionHardStop
LLM API fail           → retry → rule-based fallback
Validation fail        → retry LLM → rule-based fallback → lenient → HARD FAIL
Schema validation fail → jsonschema.ValidationError
```

Every failure path either produces valid output through fallback or raises an unrecoverable exception — never silently returns garbage.

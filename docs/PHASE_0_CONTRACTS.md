# Phase 0 — Contracts & Schema Definitions

> Updated: 2026-02-22. Aligned with current pipeline output.

## 1. Purpose

Phase 0 defines the JSON schemas that serve as contracts between phases. These schemas ensure that data flowing between phases conforms to a predictable structure.

## 2. Inputs

Phase 0 has no runtime inputs. Schemas are static files.

## 3. Outputs

| Schema | File | Used By |
|--------|------|---------|
| Scene Schema | `contracts/scene_schema.json` | Phase 1 output, Phase 2/4 input |
| Fixture Schema | `contracts/fixture_schema.json` | Phase 3 knowledge |
| Lighting Instruction Schema | `contracts/lighting_instruction_schema.json` | Phase 4 output, Phase 5/7 input |
| Lighting Semantics Schema | `contracts/lighting_semantics_schema.json` | Phase 3 semantics knowledge |

## 4. Internal Components

### Schema Files

| File | Description |
|------|-------------|
| `scene_schema.json` | Scene structure: `scene_id`, `content` (text, word_count, type, header, location), `timing` (start_time, end_time, duration), `emotion` (primary_emotion, primary_score, all_scores, method) |
| `fixture_schema.json` | Fixture structure: `fixture_id`, `group_id`, `fixture_type`, `position`, `capabilities`, `constraints` |
| `lighting_instruction_schema.json` | Lighting output: `scene_id`, `emotion`, `time_window` (start_time, end_time), `groups[]` (group_id, parameters, transition), `metadata` |
| `lighting_semantics_schema.json` | Semantics rules: `context_type`, `context_value`, `source`, `priority`, `conflict_priority`, `layer_compatibility`, `blending_mode`, `rules` |

## 5. Boundaries

- Phase 0 does **NOT** execute any code at runtime
- Phase 0 does **NOT** validate data (validation happens in consuming phases)
- Phase 0 does **NOT** generate or transform data
- Schemas are reference documents only

## 6. Failure Handling

No runtime failure modes. Schema violations in other phases are caught by Pydantic models or manual validation in consuming code.

## 7. Key Conventions

| Convention | Value |
|---|---|
| Time keys | `start_time` / `end_time` (not `start`/`end`) |
| Intensity scale | 0–100 percentage |
| Emotion field | Top-level `primary_emotion` (string) |
| Transition duration | `duration_seconds` (not `duration`) |
| Scene IDs | `scene_001`, `scene_002`, ... |

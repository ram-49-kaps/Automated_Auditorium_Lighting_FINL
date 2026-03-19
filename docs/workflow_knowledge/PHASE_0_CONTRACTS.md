# Phase 0 — Contracts & Schema Definitions

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

## 1. Purpose

Phase 0 defines the JSON schemas that serve as contracts between phases. These schemas are locked and must not be modified without cross-phase review. They ensure that data flowing between phases conforms to a predictable structure.

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
| `scene_schema.json` | Defines scene structure: `scene_id`, `content`, `timing`, `emotion`, `metadata` |
| `fixture_schema.json` | Defines fixture structure: `fixture_id`, `name`, `type`, `position`, `dmx_channels` |
| `lighting_instruction_schema.json` | Defines lighting output: `scene_id`, `groups[]` with `group_id`, `parameters`, `transition` |
| `lighting_semantics_schema.json` | Defines semantics rules: `context_type`, `context_value`, `rules` |

## 5. Boundaries

- Phase 0 does **NOT** execute any code at runtime
- Phase 0 does **NOT** validate data (validation happens in consuming phases)
- Phase 0 does **NOT** generate or transform data
- Schemas are reference documents only

## 6. Failure Handling

No runtime failure modes. Schema violations in other phases are caught by Pydantic models or manual validation in consuming code.

## 7. Current Limitations

- Schemas are not enforced at runtime via JSON Schema validation — phases use Pydantic models instead
- No versioning system for schema changes
- No automated cross-phase compatibility testing

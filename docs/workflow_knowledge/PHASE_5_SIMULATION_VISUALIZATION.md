# Phase 5 — Simulation & Visualization

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-18.

## 1. Purpose

Phase 5 renders lighting instructions into a **High-Fidelity 3D Simulation**.
It acts as a **bridge** to the **External Simulation Prototype**, translating abstract Phase 4 instructions into physical fixture commands and launching the sophisticated Three.js visualization.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Lighting instructions | Phase 4 / Phase 6 | `List[LightingInstruction]` dicts |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| JSON Data Export | External Prototype | `external_prototype/data/lighting_instructions.json` |
| Live Visualization | User (Browser) | 3D Simulation at `http://localhost:8081` |

## 4. Internal Components

| File | Component | Description |
|------|-----------|-------------|
| `server.py` | `SimulationLauncher` | Exports data & launches the External Prototype (WebSocket Backend + HTTP Frontend) |
| `threejs_adapter.py` | `InstructionExporter` | Translates Phase 4 data (groups, semantic colors) to Prototype format |
| `playback_engine.py` | `PlaybackEngine` | *Legacy compatibility for Phase 6 pipeline* |
| `scene_renderer.py` | `SceneRenderer` | *Legacy compatibility* |
| `color_utils.py` | Color utilities | Used by Exporter for semantic color resolution |
| `__init__.py` | Module exports | Exposes `launch_simulation` |

## 5. Boundaries

- Phase 5 does **NOT** contain the simulation logic itself (that lives in `external_prototype/`)
- Phase 5 does **NOT** modify lighting instructions (only translates format)
- Phase 5 does **NOT** call LLMs
- Phase 5 does **NOT** compute metrics (Phase 7)

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| Prototype missing | **SOFT** | Logs warning, pipeline continues without visualization |
| Rendering error | **SOFT** | Handled within the external prototype (JS console) |

Phase 5 is OPTIONAL — non-fatal.

## 7. Current Limitations

- Visualization requires the external prototype files to be present
- Standalone mode requires `conda` environment with `websockets`
- No headless video export (real-time only)

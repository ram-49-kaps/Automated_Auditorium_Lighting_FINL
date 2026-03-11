# Phase 5 — Simulation & Visualization

> Updated: 2026-02-22. Reflects actual simulation architecture with test_controller.py and Three.js frontend.

## 1. Purpose

Phase 5 renders lighting instructions into a visual 3D simulation. The Three.js-based 3D auditorium visualization is served via a WebSocket controller and displays real-time lighting cue playback.

## 2. Inputs

| Input | Source | Format |
|-------|--------|--------|
| Lighting instructions | Phase 4 / Phase 6 | `List[LightingInstruction]` dicts via `current_show.json` |
| Script data | Phase 1 | Scene text and metadata |

## 3. Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| 3D Simulation | User (browser at `localhost:8081`) | Interactive Three.js visualization |
| Real-time cue display | Control panel | Scene text, emotion, timing, fixture status |

## 4. Internal Components

### Simulation Controller (`external_simulation_prototype/`)

| File | Component | Description |
|------|-----------|-------------|
| `test_controller.py` | `SimulationController` | Main controller: loads cues, manages playback timing, sends state via WebSocket |
| `module_1/index.html` | Frontend | Three.js 3D auditorium, control panel, cue list, progress bar |
| `module_1/js/main.js` | Frontend logic | WebSocket client, scene rendering, cue list rendering, fixture status |
| `module_1/js/auditorium.js` | 3D scene | Three.js auditorium geometry: stage, walls, seats, trusses, fixtures |

### Legacy Components (available but not primary)

| File | Component | Description |
|------|-----------|-------------|
| `playback_engine.py` | `PlaybackEngine` | Sequences lighting cues with timing |
| `scene_renderer.py` | `SceneRenderer` | Renders scenes (headless or visual) |
| `color_utils.py` | Color utilities | RGB, HSL, color temperature conversion |
| `threejs_adapter.py` | `ThreeJSAdapter` | Adapts data for Three.js frontend |
| `server.py` | Flask server | Browser visualization endpoint |

### Cue Display Features

- **Active cue**: Full scene text displayed in expanded readable format
- **Inactive cues**: Compact preview (55 chars) with emotion badge
- **Scene headers**: Prepended in `[brackets]` (e.g. `[FADE IN]`, `[INT. KITCHEN]`)
- **Progress bar**: YouTube-style with elapsed/total timing
- **Scene duration**: Clamped between 8–120 seconds

## 5. Boundaries

- Does **NOT** call LLMs
- Does **NOT** modify lighting instructions
- Does **NOT** generate new lighting data
- Does **NOT** compute metrics (Phase 7)

## 6. Failure Handling

| Failure | Type | Behavior |
|---------|------|----------|
| Rendering error | **SOFT** | Logs warning, pipeline continues |
| Missing fixtures | **SOFT** | Renders with defaults |
| WebSocket disconnect | **SOFT** | Reconnects automatically |

Phase 5 is OPTIONAL — non-fatal.

## 7. Current Limitations

- No video export
- Single auditorium model (no custom venue support)

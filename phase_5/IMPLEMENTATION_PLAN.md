# Phase 5 Implementation Plan: Simulation & Visualization

## 🎯 Goal
Create a reliable "lighting playback engine" that turns Phase 4 `LightingInstruction` objects into a convincing visual simulation.
**Focus**: Demo-facing, Jury-facing, Teacher-facing.
**Strict Constraint**: No AI, No Decision Making, No Hardware Control.

## 🛠️ Architecture & Components

### 1. Data Flow
`LightingInstruction` (JSON) → `PlaybackEngine` (Timeline) → `SceneRenderer` (State) → `ThreeJSAdapter` (Format) → `WebSocket` → `Three.js Frontend`

### 2. Directory Structure
```
phase_5/
├── __init__.py
├── color_utils.py          # Semantic color mapping "warm_amber" -> "#FFB347"
├── playback_engine.py      # Timeline controller (Play/Pause/Seek)
├── scene_renderer.py       # Maintains current visual state of auditorium
├── threejs_adapter.py      # Bridges Python state to Three.js compatible JSON
├── server.py               # FastAPI server + WebSocket endpoint (Entry point)
├── static/                 
│   └── index.html          # Three.js Visualization Frontend
└── README.md               # User guide
```

## 📝 Implementation Steps

### Step 1: Foundation & Utilities
- **`color_utils.py`**: Modify to implement `get_hex_from_semantic(name)`. Define a dictionary of common theatrical colors.
- **`scene_renderer.py`**: Create class `SceneRenderer`.
    - Holds state: `groups: Dict[str, LightState]` (where `LightState` has intensity, color, focus).
    - Method `update(instruction, progress)` to apply changes.

### Step 2: Playback Engine
- **`playback_engine.py`**: Refactor existing code.
    - Input: List of `LightingInstruction` objects.
    - Logic: Manage time `t`, find active instruction, calculate interpolation (linear fade) between states if transition is defined.
    - Output: Call `scene_renderer.update()`.

### Step 3: Adapter & Frontend API
- **`threejs_adapter.py`**:
    - Method `to_frontend_format(renderer_state)` -> JSON payload for frontend.
    - Defines virtual positions for groups (e.g., "front_wash" -> {x: 0, y: 5, z: 2}).
- **`server.py`**:
    - FastAPI app.
    - Endpoint `/` serves `index.html`.
    - WebSocket `/ws`: Broadcasts `threejs_adapter` output at 30fps.

### Step 4: Visualization Frontend (Three.js)
- **`static/index.html`**:
    - Setup generic Three.js scene (Stage floor, Ambient light).
    - Create `SpotLight` objects for each group defined in Adapter.
    - WebSocket loop: Receive state -> Update `light.intensity`, `light.color`.

### Step 5: Integration & Demo
- Create `demo_data.json` satisfying `LightingInstruction` schema.
- Run server and verify:
    - Lights turn on/off.
    - Colors change correctly.
    - Fades are smooth.

## 🚫 Constraints Checklist
- [ ] No LLM/RAG usage.
- [ ] No DMX/OSC/MIDI generation.
- [ ] No modification of `contracts` or Phase 4 outputs.
- [ ] "Bad intent" is rendered faithfully.

## 🗓 Execution Order
1. `color_utils.py` (Update)
2. `scene_renderer.py` (Create)
3. `threejs_adapter.py` (Create)
4. `playback_engine.py` (Update)
5. `server.py` & `static/index.html` (Create)
6. Test with Sample Data.

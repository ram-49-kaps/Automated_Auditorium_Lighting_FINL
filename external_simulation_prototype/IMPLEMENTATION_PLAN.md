# External Simulation Prototype (Phase 9 Concept)
**High-Fidelity Auditorium Digital Twin**

* **Status**: 🚧 PROTOTYPING / INDEPENDENT
* **Relationship**: Completely decoupled from Main System.
* **Goal**: Build the *world*, not the brain. Focus on geometry, realism, and fixture modeling.

> **Crucial Note**: This prototype intentionally duplicates no logic from the main system. It exists to validate spatial and physical assumptions only.

---

## 🏗️ Architecture Philosophy
This is a **standalone simulation project**. It does not import from, depend on, or interact with the main codebase. It shares *concept only*: the `LightingInstruction` schema is its future interface.

### The "Rules of Independence"
1. **No imports** from `phase_x` or `contracts`.
2. **No reliance** on the existing server or demo code.
3. **No commitment** to current Git branches (Local experiment only).

### New: Constraints & Guardrails
*   **Adapter is Stateless**: The integration layer must NOT implement timelines, transitions, or interpolation. It is instantaneous (State A -> Render).
*   **Physically-Inspired Only**: Visual realism > Lux accuracy. No photometric IES rabbit holes.
*   **Fixture Ceiling**: Focus on geometry/orientation, not manufacturer profiles or console specifics.
*   **One-Way Map**: Mapping is strictly `Logical Group` -> `Physical Fixtures`. No reverse inference.

---

## 📂 Implementation Plan

### Step 1: Foundation (The World)
*   **`world/geometry.py`**:
    *   Define the coordinate system (meters, not abstract units).
    *   Define the Stage geometry (e.g., 10m x 8m x 1m platform).
    *   Define Trusses/Pipes positions (e.g., FOH at Z=10m, LX1 at Z=8m).

### Step 2: Fixture Library (The Assets)
*   **`fixtures/models.py`**:
    *   Define high-fidelity fixture classes prioritizing **geometry** and **beam representation**.
    *   Attributes: `beam_angle`, `pan_tilt_limits`.
    *   **Prohibited**: Console-specific channel mapping, manufacturer photometric tables.

### Step 3: Patch & Scenegraph (The Setup)
*   **`world/layout.py`**:
    *   Place specific fixture instances onto the Trusses.
    *   Assign unique IDs (e.g., `lx1_unit_3`).
    *   **Mapping**: Define the One-Way dictionary: `Front Wash Group` -> `[Fixture 1, Fixture 2, Fixture 3]`.

### Step 4: The Visualization Core (The Engine)
*   **`visualization/server.py` & `index.html`**:
    *   A Rich Three.js Standalone renderer.
    *   Focus: **Physically-inspired lighting**. Shadows, cones, falloff.
    *   **Not Accurate**: Do not tune for exact Lux values. Tune for "convincing visual".

### Step 5: Adapter Interface (Instantaneous Control)
*   **`adapter_mock.py`**:
    *   Demonstrates how `LightingInstruction` controls the world.
    *   **Rule**: Must be **Stateless and Instantaneous**.
        *   ❌ `fade_to(100, duration=5)`
        *   ✅ `set_state(100)`
    *   Time and interpolation are the responsibility of the external driver (Phase 5/6), never this simulation.

---

## 🛠 Directory Structure
```
external_simulation_prototype/
├── __init__.py
├── world/
│   ├── geometry.py             # Meters, dimensions
│   └── layout.py               # Fixture placement & Group Mapping
├── fixtures/
│   ├── base.py                 # Parent class
│   └── lib.py                  # Specific models (Source4, PAR64)
├── visualization/
│   ├── index.html              # High-fidelity Three.js renderer
│   └── server.py               # Independent server
├── adapter_mock.py             # Stateless interface example
└── IMPLEMENTATION_PLAN.md      # This file
```

## 📅 Execution Order
1. **Setup**: Structure & Rules.
2. **World**: define `geometry.py`.
3. **Fixtures**: define `lib.py` (Geometry-focused).
4. **Layout**: define `layout.py` (One-way mapping).
5. **Vis**: Build the separate Three.js engine.
6. **Verify**: Test with `adapter_mock` (Instant changes only).

# 3D Auditorium Simulation Implementation Plan

## Overview
This document outlines the step-by-step specific implementation plan to create a photorealistic 3D digital twin of the auditorium, integrating the specific lighting rig provided.

## Coordinate System Mapping
To translate the provided fixture data to the 3D world:
- **JSON X** -> **Three.js X** (Left/Right)
- **JSON Y** -> **Three.js Z** (Depth/Distance). *Positive = Front of House, Negative = Upstage.*
- **JSON Z** -> **Three.js Y** (Height). *0 = Floor, 6.0 = Grid Height.*

---

## Module 1: Project & Asset Foundation
**Objective:** specific setup of accurate materials and basic scene.
1.  **File Structure Setup**:
    - `static/js/three/` - Core 3D Modules.
    - `static/assets/` - Texture maps.
    - `static/data/fixtures.json` - Storing the user-provided layout.
2.  **Asset Generation (Textures)**:
    - **Stage Wood**: High-resolution polished oak wood texture with normal maps for "Real Wooden" look.
    - **Proscenium Wood**: Vertical slat dark walnut texture.
    - **Carpet**: Maroon/Brown fabric with leaf pattern.
    - **Acoustic Panels**: White fabric texture for geometric shapes.
3.  **Scene Initialization**:
    - Setup `Three.js` scene with `sRGBEncoding` for realistic lighting.
    - Setup `PerspectiveCamera` at typical audience view.
    - Setup `OrbitControls` limited to seating area.

## Module 2: Architectural "Shell" Construction
**Objective:** "Same to Same" modeling of the room.
1.  **The Stage (Origin)**:
    - Create geometry for the stage platform using the **Real Wood** assets.
    - Dimensions based on grid size (approx 16m wide, 10m deep).
    - Add proscenium arch with curved top and dark wood pillars.
2.  **The Auditorium (House)**:
    - Build stepped (raked) floor for seating.
    - **Seating**: Use InstancedMesh to place ~200 maroon cinema chairs in curved rows.
    - **Walls**: Implement the two-tone design (Wood bottom, White Geometric shapes top).
    - **Ceiling**: Create black "void" ceiling with specific **Circular Clouds** (White/Blue discs).
3.  **Backstage/Masking**:
    - Add 4 sets of **Blue** side legs (wings).
    - Add large white projection screen (16:9).

## Module 3: Lighting Rig Implementation
**Objective:** Place the specific hardware listed in JSON.
1.  **Data Ingestion**:
    - Create `static/data/fixtures.json` with the exact JSON content provided.
    - Write loader script to parse this JSON.
2.  **Fixture Modeling**:
    - Create/Load Low-poly models for:
        - `Profile` (FOH Spots)
        - `Fresnel` (FOH Wash)
        - `MovingHead_Hanging` (Inverted)
        - `MovingHead_Floor` (Floor standing)
        - `Blinder` (Square 4-cell)
        - `Par` (RGB cylindrical)
3.  **Placement Logic**:
    - Iterate through JSON.
    - Instantiate correct model at `(x, json_z, json_y)`.
    - **FOH Truss**: Generate a black truss beam at Z=10, Y=6. Mount FOH lights.
    - **Stage Grid**: Generate black wire grid structure over stage. Mount Stage lights.
4.  **Orientation**:
    - **FOH Lights**: target (`lookAt`) `(x, 1.5, 0)` (Face height on stage).
    - **Stage Overhead**: target `(x, 0, z)` (Straight down).
    - **Blinders**: Angled slightly forward/down.

## Module 4: Simulation & Physics
**Objective:** Realistic beams and control.
1.  **Light Sources**:
    - Attach `THREE.SpotLight` objects to profiles/moving heads.
    - Attach `THREE.RectAreaLight` or wide angle `SpotLight` to blinders.
    - Use `THREE.PointLight` for soft washes (Fresnels).
2.  **Volumetrics (Haziness)**:
    - Create "Cone" meshes for every fixture.
    - Apply custom shader to cones to simulate light beams interacting with dust/haze.
    - Link opacity of cone to light intensity.
3.  **Shadows**:
    - Enable `castShadow` for all main light sources.
    - Ensure stage floor `receivesShadow`.

## Module 5: Integration & Control
**Objective:** Connect backend to visualization.
1.  **State Mapping**:
    - Update `viewer.js` to find 3D objects by `fixture_id`.
    - Map DMX channels to 3D properties:
        - Dimmer -> `light.intensity` + `beam.opacity`
        - RGB -> `light.color`
        - Pan/Tilt -> `fixture_head.rotation`
2.  **Animation Loop**:
    - Add interpolation (LERP) for smooth movement and fading.

## Execution Order
1. **Approve Plan**: User confirms this structure.
2. **Phase 1**: Set up basic scene + Load JSON.
3. **Phase 2**: Build Room to photo specs.
4. **Phase 3**: Install Fixtures from JSON.
5. **Phase 4**: Connect logic.

# Phase 7 Evaluation Frontend Dashboard

Build a premium React + Vite single-page app inside `Phase-7-frontend/` that visualises the Phase 7 evaluation output. The app will load JSON data (evaluation reports + lighting cues) from `public/data/` and render an interactive dashboard — no backend required.

## Data Sources

The frontend will bundle two sample JSON files copied from `phase_7_testing_output/`:

| File | Content |
|------|---------|
| `Script-8_evaluation.json` | 16-scene evaluation report with per-scene verdicts |
| `Script-8_cues.json` | Lighting cue instructions (groups, transitions, graph metadata) |

## Proposed Changes

### Scaffolding

#### [NEW] [Phase-7-frontend/](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend)

Initialise with `npx -y create-vite@latest ./ -- --template react`. Folder will contain `package.json`, `vite.config.js`, `index.html`, `src/`, `public/`.

---

### Public Data

#### [NEW] public/data/Script-8_evaluation.json
#### [NEW] public/data/Script-8_cues.json

Copied from `phase_7_testing_output/` so the app can `fetch()` them at runtime.

---

### Core Components (all under `src/`)

#### [NEW] [App.jsx](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/App.jsx)
- Root layout: dark-mode sidebar + content area
- Loads JSON data, stores in state, passes to children
- Tab navigation: **Overview**, **Scene Timeline**, **Lighting Cues**

#### [NEW] [components/OverviewDashboard.jsx](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/components/OverviewDashboard.jsx)
- Hero card with overall verdict (PASS / WARN / FAIL) + badge
- Summary stat cards: total scenes, pass/warn/fail counts, can_proceed flag
- Verdict distribution donut (CSS-only, no chart library)
- Timestamp display

#### [NEW] [components/SceneTimeline.jsx](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/components/SceneTimeline.jsx)
- Horizontal/vertical strip of scenes, each coloured by verdict
- Click a scene → opens `SceneDetail`
- Shows scene_id + final_verdict at a glance

#### [NEW] [components/SceneDetail.jsx](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/components/SceneDetail.jsx)
- 9-metric check grid (schema, confidence, consistency, drift, conflict, coherence, stability, narrative, human_alignment)
- Collapsible details panel showing issues (conflict_details, narrative_issues, drift_issues, etc.)
- Coherence score gauge
- Emotion consistency breakdown (group variances table)

#### [NEW] [components/LightingCueViewer.jsx](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/components/LightingCueViewer.jsx)
- Per-scene card showing:
  - Time window (start → end)
  - Fixture groups with intensity bars, colours, transitions
  - Emotion tag + technique
  - Graph path score + provenance chain
  - Safety check badges

#### [NEW] [index.css](file:///f:/CHRIST-UNIVERSITY/Trimester-3/Research_Project/Automated_Lighting/Phase-7-frontend/src/index.css)
- Dark theme with deep navy/charcoal base
- Glassmorphism cards with subtle blur
- Accent colours: green (PASS), amber (WARN), red (FAIL)
- Smooth transitions & hover micro-animations
- Google Font: Inter

---

## Verification Plan

### Automated Tests
1. **Build check**: `npm run build` should succeed with zero errors.
2. **Dev server**: `npm run dev` should start Vite on a local port.

### Manual Verification (via browser)
1. Open the dev server URL in a browser and verify:
   - Overview dashboard shows correct counts (16 scenes, 0 pass, 16 warn, 0 fail, overall WARN)
   - Scene timeline renders 16 scene pills, all amber
   - Clicking a scene shows the 9-check detail grid
   - Lighting cues tab shows 16 scene cards with groups and intensity bars
   - Layout is responsive and visually polished (dark theme, animations)

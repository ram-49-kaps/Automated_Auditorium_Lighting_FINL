# Automated Auditorium Lighting — Architecture Flowcharts

> All diagrams rendered at 3x resolution from Mermaid source files in `docs/flowcharts/`

---

## 1. Master Pipeline

![Master Pipeline](flowcharts/master_pipeline.png)

---

## 2. Phase 6 — Pipeline Orchestrator (Control Flow)

![Phase 6 Orchestrator](flowcharts/phase6_orchestrator.png)

---

## 3. Phase 1 — Script Parsing & Scene Extraction (Detailed)

![Phase 1 Detail](flowcharts/phase1_detail.png)

---

## 4. Phase 2 — Emotion Analysis

![Phase 2 Emotion](flowcharts/phase2_emotion.png)

---

## 5. Phase 3 — RAG Knowledge Retrieval

![Phase 3 RAG](flowcharts/phase3_rag.png)

---

## 6. Phase 4 — Lighting Decision Engine

![Phase 4 Lighting](flowcharts/phase4_lighting.png)

---

## 7. Phase 5 — Simulation & Visualization

![Phase 5 Simulation](flowcharts/phase5_simulation.png)

---

## 8. Phase 7 — Evaluation & Metrics v2

![Phase 7 Evaluation](flowcharts/phase7_evaluation.png)

---

> **Source files:** All Mermaid `.mmd` source files are in `docs/flowcharts/` if you need to edit and re-render.
> **Re-render command:** `cd docs/flowcharts && for f in *.mmd; do npx -y @mermaid-js/mermaid-cli -i "$f" -o "${f%.mmd}.png" -c mermaid-config.json -s 3 --backgroundColor transparent; done`

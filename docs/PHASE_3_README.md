# PHASE 3: Knowledge Layer (Dual RAG) - Implementation Log

## Overview
**Phase 3** is the "Knowledge Layer" of the Automated Auditorium Lighting system. Its sole purpose is to provide **grounded, read-only context** to the decision-making AI (Phase 4). It separates "Physical Reality" (What lights exist) from "Design Principles" (How they should look).

This phase explicitly **does not make decisions**. It acts as a librarian, retrieving relevant facts so the LLM can make informed choices.

---

## 🏗 Architecture Decisions

### 1. Dual RAG Separation
We rejected a single "Knowledge Base" in favor of **Two Separate Vector Stores**:
*   **RAG-1 (Auditorium)**: Strictly physical data. No emotion, no opinions.
    *   *Query Input*: Visual requirements (e.g., "spotlight", "wash").
*   **RAG-2 (Semantics)**: Strictly design biases. No hardware data.
    *   *Query Input*: Emotion & Script Type (e.g., "Fear", "Formal").

**Why?**
If we mixed them, a query for "Fear" might return a specific light fixture that was coincidentally tagged with "scary," falsely limiting the AI's choices. By keeping them separate, we allow the AI to combine *Any Rule* with *Any Capable Fixture*.

### 2. Schema-First Development (Contract Enforcement)
Before any data was entered, we defined strict JSON schemas (`data/schemas/`).
*   **Constraint**: Every fixture *must* have a `group_id` to allow logical grouping (e.g., "FOH_WASH" instead of "Spot #1").
*   **Constraint**: Capabilities are strict Enums (`rgb`, `dim`, `pan_tilt`) to prevent typo-driven failures in Phase 8 (Hardware).

### 3. "Source of Truth" vs. "Compiled Index"
*   **JSON Files (`data/knowledge/`)**: The human-readable source. This is the only place edits happen.
*   **FAISS Index (`rag/`)**: The machine-readable "compiled" output. We treat this as a build artifact, not source code.

---

## 🛠 Implementation Steps

### Step 1: Physical Reality Modeling (`fixtures.json`)
We modeled the specific college auditorium based on visual evidence (Lighting Plot Images).
*   **Iterative Refinement**:
    *   *Draft 1*: Generic Layout.
    *   *Correction 1*: Identified 24 Stage PARs.
    *   *Correction 2*: Upgraded logic to recognize all 24 PARs as **RGB capable** (initially thought 50% were warm white).
    *   *Correction 3*: Identified the 12 Blinders (4 columns x 3 rows).
    *   *Correction 4*: Removed 1 Smoke Machine and replaced it with a **Floor Moving Head** based on photographic evidence.
*   **Result**: A digital twin of the stage with exact 3D coordinates (x,y,z) ready for Phase 5 Simulation.

### Step 2: Semantic Baselining (`baseline_semantics.json`)
We seeded the Design Brain with 7 core rules covering:
*   **Emotions**: Fear (Cold/Dark), Joy (Bright/Colorful), Sadness (Blue/Dim), Anger (Red/Fast).
*   **Contexts**: Formal Event (Neutral/Static), Drama (High Contrast).
*   **Priority System**: Added a `priority` float (0.0-1.0) to allow specific rules (e.g., "Fire Safety") to override general mood rules in the future.

### Step 3: Ingestion Engine (`knowledge_ingestion.py`)
Built a script to compilation the raw JSON into FAISS Vector Stores.
*   **Tech Stack**: LangChain + HuggingFace Embeddings (`all-MiniLM-L6-v2`) + FAISS CPU.
*   **Formatting**: We formulated a dense string representation for each document to ensure high retrieval accuracy (e.g., combining `fixture_type` + `capabilities` + `position` into one search block).

### Step 4: Verification (`validate_phase3.py`)
We proved the system works via a Validation Suite passing 3 distinct scenarios:
1.  **"Ghost/Horror"**: Correctly retrieved *Smoke Machines*, *Floor Movers*, and *Fear Rules*.
2.  **"Dean's Speech"**: Correctly retrieved *FOH Profiles* (Spotlights) and *Formal Rules*.
3.  **"Dance Number"**: Correctly retrieved *RGB PARs* and *Joy Rules*.

---

## 📂 File Structure Created

```text
/data
  /schemas
    ├── fixture_schema.json           # The Hardware Contract
    └── lighting_semantics_schema.json # The Design Contract
  /knowledge
    /auditorium
      └── fixtures.json               # The Real Inventory
    /semantics
      └── baseline_semantics.json     # The Design Rules

/pipeline
  ├── knowledge_ingestion.py          # JSON -> FAISS Compiler
  └── rag_retriever.py                # Runtime Retrieval Engine

/rag                                  # COMPILED INDEXES (Do Not Edit)
  ├── /auditorium
  └── /lighting_semantics

/tests
  └── validate_phase3.py              # Verification Script
```

## 🚀 Handoff Notes (For Next Phase)
*   **Phase 4 (Decision Engine)**: Should import `rag_retriever.py` and call `auditorium_db.similarity_search()` and `semantics_db.similarity_search()`.
*   **Phase 5 (Visualizer)**: Should read `data/knowledge/auditorium/fixtures.json` to spawn the 3D lights in Three.js.
*   **Phase 8 (Hardware)**: Should map the `fixture_id` from `fixtures.json` to the physical DMX Address/Osc Path.

---
**Status**: ✅ Phase 3 Complete & Validated.
**Date**: Feb 2026

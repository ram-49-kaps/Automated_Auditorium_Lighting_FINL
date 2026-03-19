# System Interfaces

This document outlines the interfaces and data contracts between all 13 modules of the Automated Auditorium Lighting pipeline, covering from script ingestion to hardware DMX output and frontend interactions.

## 1. Module: Phase 1 (Script Ingestion)
- **Directory:** `phase_1/`
- **Entry Point:** `phase_1/__init__.py::run_phase_1(filepath, model)`
- **Input:** 
  - `filepath` (str): Absolute or relative path to a `.txt`, `.pdf`, or `.docx` script file.
  - `model` (str, optional): The LLM model to use (e.g., `'Rule-Based (No LLM)'`). If `'rule_based'`, skips LLM segmentation.
- **Output:** `(scene_objects: List[Dict], metadata: Dict)`
  - `scene_objects`: List containing objects like `{"scene_id": "scene_001", "text": "...", "time_window": {"start_time": 0, "end_time": 10}, "emotion": None, "explicit_lighting": []}`
  - `metadata`: Dict containing `{"doc_type": "...", "genre": "...", "narrative_context": "..."}`
- **Called By:** `backend/pipeline_runner.py::run_pipeline()`
- **Depends On:** `phase_1.text_acquisition` (PDF/DOCX extraction), `phase_1.immutable_structurer`, `phase_1.llm_scene_segmenter`, `phase_1.scene_json_builder`

## 2. Module: Phase 2 (Emotion Analysis)
- **Directory:** `phase_2/`
- **Entry Point:** `phase_2/__init__.py::run_phase_2(scene, narrative_context, model)`
- **Input:** 
  - `scene` (dict): A single scene dict from Phase 1.
  - `narrative_context` (str): Narrative arc summary from Phase 1 metadata. Empty if `model == 'rule_based'`.
  - `model` (str): The LLM model to use.
- **Output:** `emotion_data` (dict)
  - Result: `{"primary_emotion": "joy", "confidence": 0.85, "secondary_emotions": [...], "energy_level": 7, "valence": 8}`
  - NOTE: Normalization layer in `pipeline_runner.py::analyze_emotion` intercepts this output to guarantee `energy_level` and `valence` presence.
- **Called By:** `backend/pipeline_runner.py::analyze_emotion()`
- **Depends On:** `phase_2.emotion_analyzer` (DistilRoBERTa fallback classifier)

## 3. Module: Phase 3 (RAG Knowledge Retrieval)
- **Directory:** `phase_3/`
- **Entry Point:** `phase_3/rag_pipeline.py::RuleRetriever.retrieve_rules(query, context)`
- **Input:** 
  - `query` (str): Usually the primary emotion (e.g., "joy", "tension").
  - `context` (str): Additional context like explicit cues or genre.
- **Output:** `List[str]` (List of retrieved lighting rules, e.g., `["Joy usually requires warm front wash with amber tones..."]`)
- **Called By:** `phase_4/lighting_decision_engine.py` (when `use_llm=True`)
- **Depends On:** Vector database (FAISS/Chroma) and embedding models (SentenceTransformers)

## 4. Module: Phase 4 (Lighting Decision Engine)
- **Directory:** `phase_4/`
- **Entry Point:** `phase_4/__init__.py::run_phase_4(scene_data, retrieved_rules, model)`
- **Input:** 
  - `scene_data` (dict): Complete scene with `.text`, `.emotion` (dict), and `.explicit_lighting`.
  - `retrieved_rules` (list): Rules retrieved from Phase 3.
  - `model` (str): The requested model. If `'rule_based'`, sets internal `use_llm=False`.
- **Output:** `lighting_instructions` (dict)
  - Formatted as: `{"scene_id": "...", "emotion": {"primary_emotion": "..."}, "time_window": {...}, "groups": [{"group_id": "FRONT_WASH", "parameters": {"intensity": 80, "color": "#FFCC00", "transition": {"type": "fade", "duration": 2.0}}}, ...]}`
- **Called By:** `backend/pipeline_runner.py::generate_lighting()`
- **Depends On:** `phase_4.lighting_decision_engine.LightingDecisionEngine`

## 5. Module: Phase 5 (Simulation / Visualization)
- **Directory:** `phase_5/`
- **Entry Point:** `phase_5/visualizer.py::Visualizer.run_visualization()`
- **Input:** Complete `lighting_instructions` array mapped against a virtual DMX universe.
- **Output:** Returns visualization metadata/status (creates a local rendered window if run standalone).
- **Role:** Python-based internal simulator to preview lighting state changes before hardware output. Superseded largely by the Web/JS Simulation.
- **Called By:** Standalone diagnostics or DMX pre-flight tests.

## 6. Module: Phase 6 (Pipeline Orchestration)
- **Directory:** `phase_6/`
- **Entry Point:** `phase_6/orchestrator.py`
- **Role:** Originally designed as the top-level executor for Phases 1-5. Has been deprecated in favor of `backend/pipeline_runner.py` which provides better async/streaming integration with the web backend.

## 7. Module: Phase 7 (Evaluation & Feedback)
- **Directory:** `phase_7/`
- **Entry Point:** `phase_7/feedback_processor.py::FeedbackProcessor.process_feedback(user_feedback, original_output)`
- **Input:**
  - `user_feedback` (dict): Adjustments made by the lighting engineer (e.g., "reduce intensity by 10%").
  - `original_output` (dict): The original lighting JSON.
- **Output:** Updates the localized RL model / fine-tuning dataset to improve future LLM prompts or heuristic weights.
- **Called By:** `backend/app.py` via the `/api/feedback` endpoint.

## 8. Module: Phase 8 (DMX / Hardware Output)
- **Directory:** `phase_8/`
- **Entry Point:** `phase_8/dmx_controller.py::DMXController.send_cues(lighting_instructions)`
- **Input:** Final processed JSON lighting instructions.
- **Output:** DMX512 packets transmitted via Art-Net / sACN.
- **Role:** Translates logical groups ("FRONT_WASH", intensity 80, color #FFAA00) into 512-channel DMX byte arrays.

## 9. Module: Event Processing
- **Directory:** `event_processing/`
- **Entry Point:** `event_processing/event_pipeline_runner.py::run_event_pipeline(filepath, model)`
- **Input:** `filepath` (str), `model` (str)
- **Output:** `(lighting_instructions: List[Dict], metadata: Dict)`
  - Similar output to standard pipeline, but structured for time-bound event segments (like speakers, Q&A, breaks).
- **Called By:** `backend/pipeline_runner.py` (when `script_type == "event_schedule"`)
- **Depends On:** `event_processing.event_scene_segmenter`, `event_processing.event_lighting_engine`

## 10. Module: Experimental Full-Context Pipeline
- **Directory:** `experimental_full_context_pipeline/`
- **Entry Point:** `experimental_full_context_pipeline/__init__.py::run_pipeline(filepath, model)`
- **Input:** `filepath` (str), `model` (str)
- **Output:** `lighting_instructions` (List[Dict])
- **Role:** Single-pass alternative to the multi-stage pipeline. Parses scenes, infers emotion, and plots lighting in one LLM call.
- **Called By:** `backend/pipeline_runner.py::run_full_context_pipeline()`

## 11. Module: Backend API (FastAPI)
- **Directory:** `backend/`
- **Entry Point:** `backend/app.py`
- **Role:** Web server handling file uploads, managing job IDs, streaming processing status, and serving the final JSON.
- **Key Endpoints:** `/api/upload`, `/api/status/{job_id}`, `/api/results/{job_id}`
- **Outputs To:** Frontend React UI. Runs the heavy `pipeline_runner.py` in background tasks.

## 12. Module: Frontend React UI
- **Directory:** `frontend/`
- **Entry Point:** `npm run dev` (`frontend/src/App.jsx`)
- **Role:** User interface for script upload, configuration (LLM vs Rule-Based, Drama vs Event), and monitoring processing status via Server-Sent Events (SSE).
- **Communicates With:** `backend/app.py` via standard REST/SSE endpoints.

## 13. Module: External Simulation Prototype
- **Directory:** `external_simulation_prototype/`
- **Entry Point:** WebSocket connection (`test_controller.py`) + UI interaction (`module_1/index.html`)
- **Role:** Presents the `lighting_instructions.json` output via a 3D Three.js visualizer.
- **Input:** JSON payload from backend containing full cue list.
- **Data Mapping (`test_controller.py`):**
  - Reads `scene.emotion` dict (extracts `primary_emotion`) for scene labels and smoke triggers.
  - Uses `GROUP_TO_FIXTURES` to map arbitrary logical groups (e.g., `"FRONT_WASH"`) to specific DMX fixture addresses.
  - Maps common color names to Hex using `COLOR_MAP`.
  - Supports "OVERRIDE" websocket messages to instantly change scene themes.

# Directory Structure

> Reflects `baseline-rule-engine-stable` tag. Last updated: 2026-02-12.

```
Automated_Auditorium_Lighting/
│
├── .env                            # OPENAI_API_KEY (for GenAI mode)
│
├── contracts/                      # Phase 0: Schema Definitions (Locked)
│   ├── fixture_schema.json
│   ├── lighting_instruction_schema.json
│   ├── lighting_semantics_schema.json
│   └── scene_schema.json
│
├── data/
│   ├── raw_scripts/                # Input scripts (.txt, .pdf, .docx)
│   │   ├── Script-1.txt
│   │   └── Script-10.pdf
│   ├── cleaned_scripts/            # Intermediate cleaned text
│   ├── segmented_scripts/          # Segmented scenes
│   ├── standardized_output/        # Phase 1 JSON output
│   │   ├── Script-1.json
│   │   ├── Script-1_processed.json
│   │   ├── Script-10_processed.json
│   │   └── Script-20_processed.json
│   ├── lighting_cues/              # Phase 4 output
│   │   └── Script-1_cues.json
│   ├── traces/                     # Phase 7 trace logs
│   │   └── trace_<uuid>.json
│   └── logs/
│
├── docs/
│   ├── PROJECT_STRUCTURE.md
│   ├── DIRECTORY_STRUCTURE.md      ← (this file)
│   ├── audit_1_to_6.md
│   ├── PHASE_1_STRUCTURE.md
│   ├── PHASE_2_STRUCTURE.md
│   ├── PHASE_3_README.md
│   ├── PHASE_4_STRUCTURE.md
│   ├── PHASE_6_STRUCTURE.md
│   └── workflow_knowledge/
│       ├── PHASE_0_CONTRACTS.md
│       ├── PHASE_1_SCRIPT_INGESTION.md
│       ├── PHASE_2_EMOTION_ENRICHMENT.md
│       ├── PHASE_3_DUAL_RAG.md
│       ├── PHASE_4_LIGHTING_DECISION_ENGINE.md
│       ├── PHASE_5_SIMULATION_VISUALIZATION.md
│       ├── PHASE_6_ORCHESTRATION.md
│       └── PHASE_7_EVALUATION_METRICS.md
│
├── phase_1/                        # Script Parsing & Scene Extraction
│   ├── __init__.py
│   ├── format_detector.py
│   ├── json_builder.py
│   ├── scene_segmenter.py
│   ├── text_cleaner.py
│   └── timestamp_generator.py
│
├── phase_2/                        # Emotion Analysis
│   ├── __init__.py
│   └── emotion_analyzer.py
│
├── phase_3/                        # Dual RAG (Knowledge Layer)
│   ├── __init__.py
│   ├── rag_retriever.py            # Phase3Retriever class
│   ├── ingestion/
│   │   └── knowledge_ingestion.py
│   ├── knowledge/
│   │   ├── auditorium/
│   │   │   └── fixtures.json       # 54 fixtures
│   │   └── semantics/
│   │       └── baseline_semantics.json  # 7 rules
│   ├── rag/
│   │   ├── auditorium/
│   │   │   ├── index.faiss
│   │   │   └── index.pkl
│   │   └── lighting_semantics/
│   │       ├── index.faiss
│   │       └── index.pkl
│   └── schemas/
│       ├── fixture_knowledge_schema.json
│       └── lighting_semantics_knowledge_schema.json
│
├── phase_4/                        # Lighting Decision Engine
│   ├── __init__.py
│   └── lighting_decision_engine.py
│
├── phase_5/                        # Simulation & Visualization
│   ├── __init__.py
│   ├── README.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── color_utils.py
│   ├── playback_engine.py
│   ├── scene_renderer.py
│   ├── server.py
│   ├── threejs_adapter.py
│   └── static/
│       └── index.html
│
├── phase_6/                        # Orchestration & Pipeline Control
│   ├── __init__.py
│   ├── README.md
│   ├── batch_executor.py
│   ├── config_models.py
│   ├── errors.py
│   ├── pipeline_runner.py
│   └── state_tracker.py
│
├── phase_7/                        # Logging & Evaluation
│   ├── __init__.py
│   ├── README.md
│   ├── demo.py
│   ├── metrics.py
│   ├── schemas.py
│   ├── trace_logger.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── consistency.py
│   │   ├── coverage.py
│   │   └── stability.py
│   └── experiment_configs/
│       ├── ablation.yaml
│       └── baseline.yaml
│
├── phase_8/                        # Hardware Execution (Future)
│   ├── __init__.py
│   ├── dmx_adapter.py
│   ├── lightkey_control.py
│   ├── lightkey_midi_control.py
│   ├── osc_sender.py
│   ├── setup_midi.py
│   └── mappings/
│       └── dmx_mappings.json
│
├── api/
│   ├── __init__.py
│   ├── routes.py
│   └── websocket.py
│
├── static/
│   ├── css/style.css
│   └── js/
│       ├── viewer.js
│       └── websocket_client.js
│
├── templates/
│   ├── index.html
│   └── components/fixture_card.html
│
├── tests/
├── utils/
│   ├── __init__.py
│   └── file_io.py
│
├── app.py
├── config.py
├── main.py
├── main_phase2.py
├── main_visualize.py
├── requirements.txt
├── rules.md
└── run_pipeline_test.py
```

---

## Phase Summary

| Phase | Directory | Purpose | Failure Mode |
|-------|-----------|---------|--------------|
| 0 | `contracts/` | Schema definitions (locked) | N/A |
| 1 | `phase_1/` | Script parsing & scene extraction | Hard fail |
| 2 | `phase_2/` | Emotion analysis | Soft — defaults to neutral |
| 3 | `phase_3/` | Dual RAG knowledge retrieval | Hard fail |
| 4 | `phase_4/` | Lighting decision engine | Hard fail (after fallback) |
| 5 | `phase_5/` | Simulation & visualization | Soft — log & continue |
| 6 | `phase_6/` | Orchestration & pipeline control | Controller |
| 7 | `phase_7/` | Logging & evaluation | Soft — log & continue |
| 8 | `phase_8/` | Hardware execution (future) | Not implemented |

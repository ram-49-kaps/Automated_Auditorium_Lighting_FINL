# Project Workflow

> Reflects Graph RAG Architecture Integration. Last updated: 2026-02-22.

```
Automated_Auditorium_Lighting/
│
├── contracts/                      # Phase 0: Schema Definitions (Locked)
│   ├── fixture_schema.json
│   ├── lighting_instruction_schema.json
│   ├── lighting_semantics_schema.json
│   └── scene_schema.json
│
├── phase_1/                        # Script Parsing & Scene Extraction
│   ├── __init__.py
│   ├── format_detector.py
│   ├── json_builder.py
│   ├── scene_segmenter.py
│   ├── text_cleaner.py
│   └── timestamp_generator.py
│
├── phase_2/                        # Emotion Analysis (Llama 3.1 8B + DistilRoBERTa Fallback)
│   ├── __init__.py
│   └── emotion_analyzer.py
│
├── phase_3/                        # Phase 3-G: Graph RAG Retriever Layer
│   ├── __init__.py
│   ├── rag_retriever.py            # GraphRetriever (Neo4j / Cypher queries)
│   ├── book_ingestion/
│   │   ├── graph_importer.py       # Converts BookChunkMetadata -> Neo4j triples
│   │   └── graph_models.py         # Pydantic models for graph nodes/edges
│   └── knowledge/
│       ├── auditorium/
│       │   └── fixtures.json       # Fixture definitions imported into Graph
│       └── semantics/
│
├── phase_4/                        # Phase 4: Lighting Decision Engine (Graph RAG Modified)
│   ├── __init__.py
│   ├── rag_lighting_engine.py      # Orchestrator consuming GraphRetrievalResult
│   ├── strategy_generator.py       # Base Strategy Generator (Graph + LoRA Hybrid)
│   ├── strategy_converter.py       # Converts Strategy -> LightingInstruction
│   └── lighting_decision_engine.py
│
├── phase_5/                        # Simulation & Visualization
│   ├── __init__.py
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
│   ├── batch_executor.py
│   ├── config_models.py            # PipelineConfig
│   ├── errors.py                   # HardFailureError
│   ├── pipeline_runner.py          # PipelineRunner (main orchestrator)
│   └── state_tracker.py
│
├── phase_7/                        # Evaluation & Metrics
│   ├── __init__.py
│   ├── metrics.py                  # MetricsEngine (Trace + Graph Metrics)
│   ├── schemas.py                  # TraceEntry, TraceLog
│   ├── trace_logger.py             # TraceLogger
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── consistency.py          # Jaccard, determinism, drift
│   │   ├── coverage.py             # Group coverage, parameter diversity
│   │   └── stability.py            # Cross-run stability
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
├── data/
│   ├── raw_scripts/                # Input scripts (.txt, .pdf, .docx)
│   ├── cleaned_scripts/            # Intermediate cleaned text
│   ├── segmented_scripts/          # Segmented scenes
│   ├── standardized_output/        # Phase 1 JSON output
│   ├── lighting_cues/              # Phase 4 lighting instructions
│   ├── traces/                     # Phase 7 trace logs
│   ├── evaluations/                # Phase 7 evaluation reports
│   └── logs/                       # General logs
│
├── docs/                           # Documentation
│   ├── PROJECT_WORKFLOW.md         # This file
│   ├── DIRECTORY_STRUCTURE.md
│   ├── audit_1_to_6.md
│   ├── flowcharts/                 # Mermaid system flowcharts
│   ├── ARCHITECTURE_FLOWCHARTS.md  # Vector visual architecture flow
│   └── workflow_knowledge/         # Detailed per-phase documentation
│
├── api/                            # Web API (Flask routes)
│   ├── __init__.py
│   ├── routes.py
│   └── websocket.py
│
├── static/                         # Web frontend assets
│   ├── css/style.css
│   └── js/
│       ├── viewer.js
│       └── websocket_client.js
│
├── templates/                      # HTML templates
│   ├── index.html
│   └── components/fixture_card.html
│
├── tests/                          # Test files
├── utils/                          # Utilities
│   ├── __init__.py
│   └── file_io.py
│
├── .env                            # Environment variables (HF_API_TOKEN, GRAPH_DB_URI)
├── app.py                          # Flask application
├── config.py                       # Global configuration (GRAPH_DB_URI, GRAPH_FALLBACK_TO_FAISS)
├── requirements.txt                # Python dependencies
├── rules.md                        # Development rules
└── run_pipeline_test.py            # Pipeline entry point
```

## Workflow Phase Summary

| Phase | Directory | Purpose | Graph RAG Integration Details |
|-------|-----------|---------|-------------------------------|
| 0 | `contracts/` | Schema definitions (locked) | Unchanged. |
| 1 | `phase_1/` | Script parsing & scene extraction | Provides `scene_type`, `location`, `time_of_day`. |
| 2 | `phase_2/` | Emotion analysis (Llama 8B / RoBERTa) | Provides complex emotional layers (`primary`, `secondary`, `accent`) mapped directly to Graph nodes. |
| 3 | `phase_3/` | **Graph RAG Retriever** (Neo4j) | Translates Emoton -> LightingStyle -> Technique -> Fixture. Returns `GraphRetrievalResult` (ranked paths + reasoning subgraphs). Features constraint-aware structural pruning. |
| 4 | `phase_4/` | Lighting Decision Engine | Consumes `GraphRetrievalResult`. Uses LoRA fine-tuned LLM or StrategyGenerator for synthesis. Contains hard symbolic safety filter. |
| 5 | `phase_5/` | 3D simulation & visualization | Visualizes Graph-derived cues in 3D Web interface. |
| 6 | `phase_6/` | Pipeline orchestration | Passes Graph payload between phases. Continues on non-fatal failures. |
| 7 | `phase_7/` | Evaluation Gate | Logs `reasoning_subgraph`. Measures Path Coverage, Constraint Satisfaction Ratio (CSR). |
| 8 | `phase_8/` | Hardware Execution | DMX/OSC/MIDI endpoints (isolated from RAG mechanics). |

### Hybrid Graph RAG Information Flow
The core retrieval workflow conceptually flows as:
1. **Scene Input** → Phase 2 extracts `emotion` (e.g. `fear`).
2. **Graph Traversal** (Phase 3) → queries `(Emotion:fear) -[EVOKES]-> (LightingStyle) -[USES]-> (Technique) -[REQUIRES]-> (Fixture)`.
3. **Safety Pruning** (Phase 3) → paths violating `SafetyRule` nodes are dropped.
4. **Strategy Ranking** (Phase 3/4) → Remaining paths scored via graph distance and vector embedding.
5. **Synthesis** (Phase 4) → Ranked paths plus context fed to Lighting Engine LLM to generate `LightingInstruction`. 
6. **Symbolic Verification** (Phase 4) → Hard checks against JSON bounds.

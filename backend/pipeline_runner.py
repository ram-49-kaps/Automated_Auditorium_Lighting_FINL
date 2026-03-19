
import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Callable, Coroutine, Dict, Any
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Ensure Environment Variables are available (GROQ/OPENAI keys for Phase 4 Memory)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Unified LLM Client
from utils.openai_client import set_active_model

# Phase 1 Imports
from phase_1 import run_phase_1
from utils import read_script, get_file_info

# Phase 2 Imports
from phase_2 import analyze_emotion, analyze_all_scenes
from phase_2.graph_rag import build_scene_graph, retrieve_emotion_context

# Phase 3 Imports
from phase_3.rag_retriever import get_retriever

# Phase 4 Imports
from phase_4.lighting_decision_engine import LightingDecisionEngine

# Experimental Full-Context Pipeline Imports
from experimental_full_context_pipeline.full_context_llm_processor import (
    process_full_script,
    ScriptTooLongError,
)
from experimental_full_context_pipeline.emotion_vector_model import (
    smooth_emotion_sequence,
    recalculate_dominant_emotion,
    calculate_emotional_drift_score,
)
from experimental_full_context_pipeline.deterministic_lighting_engine import (
    generate_all_lighting,
    calculate_lighting_continuity_score,
    get_emotion_palette,
    EMOTION_PALETTES,
)
from experimental_full_context_pipeline.config_full_context import (
    OUTPUT_DIR as FC_OUTPUT_DIR,
    LLM_MODEL as FC_DEFAULT_MODEL,
)


async def run_full_context_pipeline(
    job_id: str,
    filepath: str,
    ws_callback: Callable[[Dict], Coroutine],
    model: str = None,
    script_type: str = "theatrical_script",
):
    """
    Runs the full-context (single-pass) experimental pipeline.
    Sends progress updates via ws_callback using the same phase-based pattern.
    Converts output to the same format expected by ResultsPage and simulation.
    """
    if model:
        set_active_model(model)
        
    try:
        # Override model if specified
        if model and model != "ollama/local":
            import experimental_full_context_pipeline.config_full_context as fc_config
            fc_config.LLM_MODEL = model
            # Also patch the processor module's reference
            import experimental_full_context_pipeline.full_context_llm_processor as fc_proc
            fc_proc.LLM_MODEL = model

        # =====================================================================
        # PHASE 1: LOAD SCRIPT (single-pass — no chunking)
        # =====================================================================
        await ws_callback({
            "phase": 1,
            "status": "running",
            "detail": "Reading script file (full-context mode)...",
            "progress": 0,
        })

        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".pdf":
                # Use Phase 1's text acquisition (handles PDF extraction + OCR)
                from phase_1.text_acquisition import acquire_text
                acq_result = acquire_text(filepath)
                script_text = acq_result.text
                print(f"📄 PDF extracted via {acq_result.source_method} "
                      f"(confidence: {acq_result.confidence:.2f}, "
                      f"OCR used: {acq_result.ocr_used})")
            else:
                # Plain text files (.txt, .fountain, etc.)
                with open(filepath, "r", encoding="utf-8") as f:
                    script_text = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")

        file_info = get_file_info(filepath)

        await ws_callback({
            "phase": 1,
            "status": "complete",
            "stats": {
                "lines": len(script_text.splitlines()),
                "chars": len(script_text),
                "format": file_info.get("extension", "txt"),
                "mode": "single_pass_full_context",
            },
            "progress": 10,
        })

        # =====================================================================
        # PHASE 2: FULL-SCRIPT LLM PROCESSING (scene segmentation + emotions)
        # =====================================================================
        await ws_callback({
            "phase": 2,
            "status": "running",
            "detail": "Sending full script to LLM (single-pass analysis)...",
            "progress": 10,
        })

        llm_result = process_full_script(script_text)
        scenes = llm_result["scenes"]
        metadata = llm_result["metadata"]

        await ws_callback({
            "phase": 2,
            "status": "running",
            "detail": f"LLM returned {len(scenes)} scenes. Smoothing emotions...",
            "progress": 50,
        })

        # Smooth emotion vectors
        scenes = smooth_emotion_sequence(scenes)
        dominant = recalculate_dominant_emotion(scenes, exclude_neutral=True)
        metadata["dominant_emotion"] = dominant

        # Build emotion summary
        emotion_summary = {}
        for scene in scenes:
            label = scene["emotion"]["label"]
            emotion_summary[label] = emotion_summary.get(label, 0) + 1

        # Genre classification
        genre_map = {
            "joy": "comedy", "sadness": "drama", "fear": "thriller",
            "anger": "drama", "surprise": "adventure", "disgust": "horror",
            "neutral": "drama", "nostalgia": "drama", "mystery": "thriller",
            "romantic": "romance", "hope": "drama", "triumph": "adventure",
            "tension": "thriller", "despair": "drama", "serenity": "drama",
            "confusion": "mystery", "amusement": "comedy", "excitement": "adventure",
            "chaotic_energy": "comedy", "comedic_energy": "comedy",
        }
        genre = genre_map.get(dominant, "drama")

        await ws_callback({
            "phase": 2,
            "status": "complete",
            "stats": emotion_summary,
            "progress": 60,
        })

        # =====================================================================
        # PHASE 3: SKIP (no RAG in full-context mode)
        # =====================================================================
        await ws_callback({
            "phase": 3,
            "status": "complete",
            "detail": "Bypassed — full-context mode uses deterministic lighting",
            "stats": {"rules": "Deterministic (no RAG)"},
            "progress": 65,
        })

        # =====================================================================
        # PHASE 4: DETERMINISTIC LIGHTING
        # =====================================================================
        await ws_callback({
            "phase": 4,
            "status": "running",
            "detail": "Generating deterministic lighting from emotion vectors...",
            "progress": 65,
        })

        lighting_states = generate_all_lighting(scenes)
        continuity_score = calculate_lighting_continuity_score(lighting_states)

        # --- Convert to standard lighting_instructions format ---
        # The existing pipeline outputs: { scene_id, time_window, groups[], emotion, metadata }
        # We need to produce the same shape.

        lighting_cues = []
        total_scenes = len(scenes)

        # Generate time windows (estimated from scene count)
        words_per_minute = 150
        scene_duration_default = 30.0  # seconds

        current_time = 0.0
        scene_objects = []

        for i, (scene, state) in enumerate(zip(scenes, lighting_states)):
            # Estimate duration from scene text length if available
            scene_text = scene.get("text", scene.get("location", ""))
            duration = scene_duration_default

            start_time = current_time
            end_time = start_time + duration
            current_time = end_time

            # Build scene object (for script_data)
            scene_obj = {
                "scene_id": scene.get("scene_id", f"scene_{i+1:03d}"),
                "content": {
                    "header": scene.get("location", ""),
                    "text": scene_text if isinstance(scene_text, str) else "",
                },
                "time_window": {
                    "start": start_time,
                    "end": end_time,
                    "start_time": start_time,
                    "end_time": end_time,
                },
                "emotion": {
                    "primary_emotion": scene["emotion"]["label"],
                    "primary_score": scene["emotion"]["confidence"],
                    "energy_level": scene["emotion"]["energy"],
                    "valence": scene["emotion"]["valence"],
                },
                "doc_type": "theatrical_script",
            }
            scene_objects.append(scene_obj)

            # Build lighting instruction (for lighting_instructions)
            palette = state["palette"]
            intensity = state["intensity"]
            warmth = state["warmth"]

            # Determine transition type from emotion
            energy = scene["emotion"]["energy"]
            if energy > 0.7:
                trans_type = "cut"
                trans_dur = 0.0
            else:
                trans_type = "fade"
                trans_dur = 2.0

            # Determine color temperature from warmth
            if warmth > 0.3:
                color_temp = "warm"
            elif warmth < -0.3:
                color_temp = "cool"
            else:
                color_temp = "neutral"

            groups = [
                {
                    "group_id": "front_wash",
                    "parameters": {
                        "intensity": round(intensity * 0.9, 1),
                        "color": palette["primary"],
                        "color_temperature": color_temp,
                        "focus_area": "center_stage",
                    },
                    "transition": {"type": trans_type, "duration_seconds": trans_dur},
                },
                {
                    "group_id": "back_light",
                    "parameters": {
                        "intensity": round(intensity * 0.6, 1),
                        "color": palette["secondary"],
                        "color_temperature": color_temp,
                        "focus_area": "upstage",
                    },
                    "transition": {"type": trans_type, "duration_seconds": trans_dur},
                },
                {
                    "group_id": "side_fill",
                    "parameters": {
                        "intensity": round(intensity * 0.5, 1),
                        "color": palette["secondary"],
                        "color_temperature": color_temp,
                        "focus_area": "full_stage",
                    },
                    "transition": {"type": "fade", "duration_seconds": max(trans_dur, 1.5)},
                },
                {
                    "group_id": "specials",
                    "parameters": {
                        "intensity": round(intensity * 0.4, 1),
                        "color": palette["primary"],
                        "color_temperature": color_temp,
                        "focus_area": "center_stage",
                    },
                    "transition": {"type": "fade", "duration_seconds": max(trans_dur, 2.0)},
                },
                {
                    "group_id": "ambient",
                    "parameters": {
                        "intensity": round(intensity * 0.3, 1),
                        "color": palette["anchor"],
                        "color_temperature": color_temp,
                        "focus_area": "full_stage",
                    },
                    "transition": {"type": "fade", "duration_seconds": max(trans_dur, 3.0)},
                },
            ]

            cue = {
                "scene_id": scene.get("scene_id", f"scene_{i+1:03d}"),
                "emotion": scene["emotion"]["label"],
                "time_window": {
                    "start_time": start_time,
                    "end_time": end_time,
                },
                "groups": groups,
                "metadata": {
                    "energy": scene["emotion"]["energy"],
                    "valence": scene["emotion"]["valence"],
                    "confidence": scene["emotion"]["confidence"],
                    "pipeline_mode": "single_pass_full_context",
                    "blended": state["blended"],
                },
            }
            lighting_cues.append(cue)

            # Progress update
            await ws_callback({
                "phase": 4,
                "status": "running",
                "detail": f"Generating cue {i+1} of {total_scenes}...",
                "progress": 65 + int((i / total_scenes) * 25),
            })

        await ws_callback({
            "phase": 4,
            "status": "complete",
            "stats": {"cues_generated": len(lighting_cues)},
            "progress": 90,
        })

        # =====================================================================
        # FINALIZE & SAVE
        # =====================================================================
        await ws_callback({
            "phase": 6,
            "status": "running",
            "detail": "Finalizing output package...",
            "progress": 90,
        })

        # Drift metrics
        drift = calculate_emotional_drift_score(scenes)

        final_output = {
            "metadata": {
                "source_file": os.path.basename(filepath),
                "doc_type": "theatrical_script",
                "genre": genre,
                "total_scenes": total_scenes,
                "dominant_emotion": dominant,
                "emotion_distribution": emotion_summary,
                "narrative_context": "",
                "pipeline_mode": "single_pass_full_context",
                "llm_model": model or FC_DEFAULT_MODEL,
                "emotional_arc_shape": metadata.get("emotional_arc_shape", "unknown"),
                "genre_inferred": metadata.get("genre_inferred", genre),
                "drift_score": drift,
                "lighting_continuity_score": continuity_score,
            },
            "script_data": scene_objects,
            "lighting_instructions": lighting_cues,
        }

        # Save to job directory
        job_dir = os.path.dirname(filepath)
        output_path = os.path.join(job_dir, "lighting_instructions.json")

        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)

        await ws_callback({
            "phase": 6,
            "status": "complete",
            "stats": {"output_file": "lighting_instructions.json"},
            "redirect": f"/results/{job_id}",
            "progress": 100,
        })

    except ScriptTooLongError as e:
        await ws_callback({
            "phase": "error",
            "status": "failed",
            "detail": f"Script too long for single-pass mode: {str(e)}",
            "progress": 0,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        await ws_callback({
            "phase": "error",
            "status": "failed",
            "detail": f"Full-context pipeline failed: {str(e)}",
            "progress": 0,
        })


async def run_pipeline(job_id: str, filepath: str, ws_callback: Callable[[Dict], Coroutine], model: str = None, script_type: str = "theatrical_script"):
    """
    Runs the full lighting automation pipeline (Phase 1 -> Phase 4).
    Uses the consolidated run_phase_1() entry point.
    Sends progress updates via ws_callback.
    The model parameter is stored in metadata for future per-phase LLM routing.
    script_type: 'theatrical_script' or 'event_schedule' — user-selected.
    """
    if model:
        set_active_model(model)
        
    try:
        # =========================================================================
        # PHASE 1: SCRIPT PARSING (consolidated run_phase_1)
        # =========================================================================
        await ws_callback({
            "phase": 1, 
            "status": "running", 
            "detail": "Reading and parsing script file...",
            "progress": 0
        })
        
        file_info = get_file_info(filepath)
        
        try:
            scene_objects, p1_metadata = run_phase_1(filepath, model=model)
        except Exception as e:
            raise Exception(f"Phase 1 failed: {e}")
        
        total_scenes = len(scene_objects)
        
        # Use the user-selected script type instead of auto-detecting
        doc_type = script_type

        await ws_callback({
            "phase": 1, 
            "status": "complete", 
            "stats": {
                "lines": p1_metadata.get("total_lines", 0),
                "scenes": total_scenes,
                "format": file_info.get("extension", "txt"),
                "doc_type": doc_type
            },
            "progress": 20
        })

        # =========================================================================
        # PHASE 2: EMOTION ANALYSIS (V3 Multi-Head + Graph RAG)
        # =========================================================================
        await ws_callback({
            "phase": 2, 
            "status": "running", 
            "detail": f"Analyzing emotions for {total_scenes} scenes (V3 Multi-Head + Graph RAG)...",
            "progress": 20
        })
        
        emotion_summary = {}
        
        # Build full script text for V3 full-script analysis
        full_script_text = "\n\n".join(
            scene.get("text", "") or scene.get("content", {}).get("text", "")
            for scene in scene_objects
        )
        
        # Try V3 full-script analysis first
        try:
            analyzed_scenes = analyze_all_scenes(full_script_text, scene_objects)
            await ws_callback({
                "phase": 2,
                "status": "running",
                "detail": "V3 Multi-Head analysis complete. Building Graph RAG...",
                "progress": 30
            })
        except Exception as e:
            print(f"V3 analysis failed ({e}), falling back to per-scene analysis")
            analyzed_scenes = []
            for i, scene in enumerate(scene_objects):
                await ws_callback({
                    "phase": 2,
                    "status": "running",
                    "detail": f"Analyzing scene {i+1} of {total_scenes}...",
                    "progress": 20 + int((i/total_scenes)*15)
                })
                await asyncio.sleep(0.1)
                
                text_content = scene.get("text") or scene.get("content", {}).get("text", "")
                if not text_content and isinstance(scene.get("content"), str):
                    text_content = scene.get("content")
                scene_dict = {
                    "scene_id": scene.get("scene_id", f"scene_{i+1:03d}"),
                    "text": text_content
                }
                result = analyze_emotion(scene_dict)
                analyzed_scenes.append(result)
        
        # Apply emotion results to scenes
        for i, scene in enumerate(scene_objects):
            if i < len(analyzed_scenes):
                emo_result = analyzed_scenes[i]
                if isinstance(emo_result, dict):
                    current_emotion = emo_result.get("emotion", emo_result)
                    
                    if isinstance(current_emotion, dict):
                        primary_em = current_emotion.get("primary", current_emotion.get("primary_emotion", "neutral"))
                        confidence = float(current_emotion.get("confidence",
                            current_emotion.get("primary_confidence",
                            current_emotion.get("primary_score", 0.5))))
                        
                        EMOTION_ENERGY_MAP = {
                            "joy": (0.75, 0.8), "sadness": (0.25, -0.7), "fear": (0.7, -0.6),
                            "anger": (0.9, -0.8), "surprise": (0.8, 0.3), "disgust": (0.5, -0.5),
                            "neutral": (0.4, 0.0), "anxiety": (0.7, -0.5), "nostalgia": (0.3, 0.2),
                            "romantic": (0.4, 0.7), "tension": (0.8, -0.4), "hope": (0.6, 0.6),
                            "betrayal": (0.7, -0.7), "triumph": (0.9, 0.9), "despair": (0.2, -0.9),
                            "serenity": (0.2, 0.5), "awe": (0.6, 0.5), "jealousy": (0.7, -0.6),
                        }
                        default_energy, default_valence = EMOTION_ENERGY_MAP.get(primary_em, (0.5, 0.0))
                        energy_level = float(current_emotion.get("energy_level",
                            current_emotion.get("energy", default_energy)))
                        valence = float(current_emotion.get("valence", default_valence))
                        
                        secondary_emotions = current_emotion.get("secondary_emotions", [])
                        if not secondary_emotions and current_emotion.get("secondary"):
                            secondary_emotions = [{
                                "emotion": current_emotion["secondary"],
                                "score": current_emotion.get("secondary_confidence", 0.3)
                            }]
                        
                        normalized_emotion = {
                            "primary_emotion": primary_em,
                            "primary": primary_em,
                            "confidence": confidence,
                            "primary_score": confidence,
                            "energy_level": energy_level,
                            "valence": valence,
                            "secondary_emotions": secondary_emotions,
                        }
                        scene_objects[i]["emotion"] = normalized_emotion
                        
                        # Preserve v3_metrics for Phase 4 V3 Override Hierarchy
                        if "v3_metrics" in emo_result:
                            scene_objects[i]["v3_metrics"] = emo_result["v3_metrics"]
                        
                        primary = primary_em
                    else:
                        scene_objects[i]["emotion"] = {
                            "primary_emotion": "neutral", "primary": "neutral",
                            "confidence": 0.5, "primary_score": 0.5,
                            "energy_level": 0.5, "valence": 0.0, "secondary_emotions": [],
                        }
                        primary = "neutral"
                else:
                    scene_objects[i]["emotion"] = {
                        "primary_emotion": "neutral", "primary": "neutral",
                        "confidence": 0.5, "primary_score": 0.5,
                        "energy_level": 0.5, "valence": 0.0, "secondary_emotions": [],
                    }
                    primary = "neutral"
            else:
                scene_objects[i]["emotion"] = {
                    "primary_emotion": "neutral", "primary": "neutral",
                    "confidence": 0.5, "primary_score": 0.5,
                    "energy_level": 0.5, "valence": 0.0, "secondary_emotions": [],
                }
                primary = "neutral"
            
            emotion_summary[primary] = emotion_summary.get(primary, 0) + 1
        
        # Build Graph RAG scene graph
        try:
            scene_graph = build_scene_graph(scene_objects)
        except Exception as e:
            print(f"Graph RAG failed ({e}), continuing without")
            scene_graph = None

        # ... (Genre calculation remains same) ...
        # Calculate genre — exclude neutral from dominant emotion
        non_neutral = {k: v for k, v in emotion_summary.items() if k != "neutral"}
        if non_neutral:
            dominant_emotion = max(non_neutral.items(), key=lambda x: x[1])[0]
        else:
            dominant_emotion = "neutral"
        genre_map = {
            "joy": "comedy", "sadness": "drama", "fear": "thriller",
            "anger": "drama", "surprise": "adventure", "disgust": "horror",
            "neutral": "drama",
            "nostalgia": "drama", "mystery": "thriller", "romantic": "romance",
            "anticipation": "thriller", "hope": "drama", "triumph": "adventure",
            "tension": "thriller", "despair": "drama", "serenity": "drama",
            "confusion": "mystery", "awe": "fantasy", "jealousy": "drama",
            "chaotic_energy": "comedy", "comedic_energy": "comedy",
            "amusement": "comedy", "excitement": "adventure"
        }
        genre = genre_map.get(dominant_emotion, "drama")

        await ws_callback({
            "phase": 2, 
            "status": "complete", 
            "stats": emotion_summary,
            "progress": 40
        })

        # =========================================================================
        # PHASE 3: KNOWLEDGE RETRIEVAL (RAG)
        # =========================================================================
        if doc_type == "event_schedule":
            await ws_callback({
                "phase": 3, 
                "status": "complete", 
                "detail": "Bypassing Knowledge Retrieval for Event...",
                "stats": {"rules": "Hardcoded Presets"},
                "progress": 50
            })
        else:
            await ws_callback({
                "phase": 3, 
                "status": "running", 
                "detail": "Initializing Knowledge Layer (Dual RAG)...",
                "progress": 40
            })
            
            # Initialize the retriever singleton to ensure it's loaded
            retriever = get_retriever()
            
            # We don't necessarily need to query it here, as Phase 4 will use it.
            # But let's verify it works by retrieving context for the dominant emotion
            try:
                 # Just a warm-up query
                 _ = retriever.retrieve_semantics_context(dominant_emotion, genre)
            except Exception as e:
                print(f"Phase 3 Warning: {e}")

            await ws_callback({
                "phase": 3, 
                "status": "complete", 
                "detail": "Knowledge Layer Ready",
                "stats": {"rules_loaded": "Dynamic"},
                "progress": 50
            })

        # =========================================================================
        # PHASE 4: LIGHTING DESIGN Engine
        # =========================================================================
        await ws_callback({
            "phase": 4, 
            "status": "running", 
            "detail": "Generating lighting cues...",
            "progress": 50
        })
        
        # Initialize Decision Engine
        # For rule_based model: always use rule engine, no LLM
        use_llm = model != "rule_based"
             
        engine = LightingDecisionEngine(use_llm=use_llm)
        
        lighting_cues = []
        
        # Normalize scene_objects to Phase 4 expected format
        for i, scene in enumerate(scene_objects):
            # Ensure content dict exists
            if "content" not in scene:
                scene["content"] = {"text": scene.get("text", ""), "header": scene.get("location", "")}
            elif isinstance(scene["content"], str):
                scene["content"] = {"text": scene["content"], "header": ""}
            
            # Ensure timing dict exists with Phase 4 keys
            if "timing" not in scene:
                tw = scene.get("time_window", {})
                scene["timing"] = {
                    "start_time": tw.get("start", tw.get("start_time", scene.get("start_time", 0.0))),
                    "end_time": tw.get("end", tw.get("end_time", scene.get("end_time", 0.0))),
                    "duration": scene.get("duration", tw.get("end", 0.0) - tw.get("start", 0.0)),
                }
            
            # Ensure emotion is never None
            if not scene.get("emotion") or not isinstance(scene.get("emotion"), dict):
                scene["emotion"] = {
                    "primary_emotion": "neutral",
                    "primary": "neutral",
                    "confidence": 0.5,
                    "primary_score": 0.5,
                    "energy_level": 0.5,
                    "valence": 0.0,
                }
        
        for i, scene_data in enumerate(scene_objects):
            # Update progress for EVERY scene
            await ws_callback({
                "phase": 4, 
                "status": "running", 
                "detail": f"Designing cue {i+1} of {total_scenes}...",
                "progress": 50 + int((i/total_scenes)*40)
            })
            
            # Artificial delay for visualization
            await asyncio.sleep(0.1)
            
            # Generate instruction (V3 Override Hierarchy applied internally)
            instruction = engine.generate_instruction(scene_data)
            
            # Phase 4 currently returns a Pydantic object (LightingInstruction)
            # We need to serialize it to dict for JSON
            instruction_dict = instruction.dict()
            lighting_cues.append(instruction_dict)

        await ws_callback({
            "phase": 4, 
            "status": "complete", 
            "stats": {"cues_generated": len(lighting_cues)},
            "progress": 90
        })

        # =========================================================================
        # FINALIZE & SAVE
        # =========================================================================
        await ws_callback({
            "phase": 6, 
            "status": "running", 
            "detail": "Finalizing output package...",
            "progress": 90
        })
        
        # Construct Final JSON
        final_output = {
            "metadata": {
                "source_file": os.path.basename(filepath),
                "doc_type": doc_type,
                "genre": genre,
                "total_scenes": total_scenes,
                "dominant_emotion": dominant_emotion,
                "emotion_distribution": emotion_summary,
            },
            "script_data": scene_objects,
            "lighting_instructions": lighting_cues
        }
        
        # Save to job directory
        job_dir = os.path.dirname(filepath) # Assuming upload logic puts file in job dir
        output_path = os.path.join(job_dir, "lighting_instructions.json")
        
        with open(output_path, 'w') as f:
            json.dump(final_output, f, indent=2)
            
        await ws_callback({
            "phase": 6, 
            "status": "complete", 
            "stats": {"output_file": "lighting_instructions.json"},
            "redirect": f"/results/{job_id}", # Tell client to go to results
            "progress": 100
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await ws_callback({
            "phase": "error",
            "status": "failed",
            "detail": f"Pipeline failed: {str(e)}",
            "progress": 0
        })

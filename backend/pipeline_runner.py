
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

# Phase 1 Imports
from phase_1 import (
    detect_format, clean_text, extract_stage_directions, 
    segment_scenes, build_scene_json, build_complete_output, 
    classify_document
)
from utils import read_script, get_file_info

# Phase 2 Imports
from phase_2 import analyze_emotion

# Phase 3 Imports
from phase_3.rag_retriever import get_retriever

# Phase 4 Imports
from phase_4.lighting_decision_engine import LightingDecisionEngine

async def run_pipeline(job_id: str, filepath: str, ws_callback: Callable[[Dict], Coroutine]):
    """
    Runs the full lighting automation pipeline (Phase 1 -> Phase 4).
    Sends progress updates via ws_callback.
    """
    try:
        # =========================================================================
        # PHASE 1: SCRIPT PARSING
        # =========================================================================
        await ws_callback({
            "phase": 1, 
            "status": "running", 
            "detail": "Reading and parsing script file...",
            "progress": 0
        })
        
        # 1.1 Read File (run in thread to avoid blocking event loop)
        try:
            raw_text = await asyncio.to_thread(read_script, filepath)
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")
            
        file_info = get_file_info(filepath)
            
        # 1.2 Detect Format & Classify Document
        format_info = detect_format(raw_text)
        classification = classify_document(raw_text)
        doc_type = classification["doc_type"]
        
        if doc_type == "unknown_document":
            raise ValueError(f"Invalid document: {classification['reason']}")
        
        # 1.3 Clean & Segment
        cleaned_text = clean_text(raw_text, preserve_structure=True)
        stage_directions = extract_stage_directions(raw_text)
        
        scenes = await asyncio.to_thread(segment_scenes, cleaned_text, format_info)
        
        scenes = await asyncio.to_thread(segment_scenes, cleaned_text, format_info)
        
        scene_objects = [] # Stores partial scene dictionaries

        await ws_callback({
            "phase": 1, 
            "status": "complete", 
            "stats": {
                "lines": len(cleaned_text.splitlines()),
                "scenes": len(scenes),
                "format": format_info['estimated_format'],
                "doc_type": doc_type
            },
            "progress": 20
        })

        # =========================================================================
        # PHASE 2: EMOTION ANALYSIS (Graph RAG Enhanced)
        # =========================================================================
        await ws_callback({
            "phase": 2, 
            "status": "running", 
            "detail": f"Building scene graph for {len(scenes)} scenes...",
            "progress": 20
        })
        
        # Build scene graph for cross-scene context
        from phase_2.graph_rag import build_scene_graph, retrieve_emotion_context
        scene_graph = build_scene_graph(scenes)
        
        emotion_summary = {}
        
        # Phase 2 Loop
        total_scenes = len(scenes)
        
        if doc_type == "event_schedule":
            await ws_callback({"phase": 2, "status": "running", "detail": "Bypassing Emotion Analysis for Event...", "progress": 40})
            emotion_summary = {"neutral": total_scenes}
            emotion_results = []
            for i, scene in enumerate(scenes):
                emotion_results.append({
                    "primary_emotion": "neutral",
                    "confidence": 1.0,
                    "secondary_emotions": [],
                    "sentiment_score": 0.0,
                    "theatrical_context": {"predicted_theme": "event", "confidence": 1.0}
                })
        else:
            await ws_callback({
                "phase": 2,
                "status": "running",
                "detail": f"Analyzing {total_scenes} scenes with full narrative context...",
                "progress": 30
            })
            
            from phase_2 import analyze_all_scenes
            
            emotion_results = await asyncio.to_thread(
                analyze_all_scenes,
                full_script=cleaned_text,
                scenes=scenes,
            )
            
        # =========================================================================
        # NEW PHASE 1.5: TIMESTAMPS (Emotion Aware)
        # =========================================================================
        await ws_callback({
            "phase": 2, # Bundle UI wise with phase 2
            "status": "running",
            "detail": "Estimating scene timeline & pacing...",
            "progress": 35
        })
        
        from phase_1 import assign_timestamps_hybrid
        
        # Map emotions by scene_id for the timestamp estimator
        emotion_map = {}
        if emotion_results:
            for emo in emotion_results:
                if emo and "scene_id" in emo:
                    emotion_map[emo["scene_id"]] = emo
                    
        timestamps = assign_timestamps_hybrid(scenes, emotion_map)
        
        # Now that we have both timestamps and emotions, build the final Scene Objects
        for i, (scene, timestamp, emotion_analysis) in enumerate(zip(scenes, timestamps, emotion_results)):
            if not isinstance(emotion_analysis, dict):
                emotion_analysis = {}
                
            # Update Graph RAG with the full-context emotion results
            scene_graph.update_scene_emotion(
                scene_position=i,
                primary=emotion_analysis.get("primary_emotion", "neutral"),
                confidence=emotion_analysis.get("confidence", 0.0),
            )
            
            # Track stats
            primary = emotion_analysis.get("primary_emotion", "neutral")
            emotion_summary[primary] = emotion_summary.get(primary, 0) + 1
            
            # Build scene structure
            scene_json = build_scene_json(
                scene_id=f"scene_{i+1:03d}",
                scene_data=scene,
                timestamp=timestamp,
                emotion_analysis=emotion_analysis
            )
            
            # Include new narrative fields if present
            if "narrative_role" in emotion_analysis:
                scene_json["narrative_role"] = emotion_analysis["narrative_role"]
            if "mood_shift" in emotion_analysis:
                scene_json["mood_shift"] = emotion_analysis["mood_shift"]
                
            scene_json["doc_type"] = doc_type
            scene_objects.append(scene_json)

        # ... (Genre calculation remains same) ...
        # Calculate genre
        dominant_emotion = max(emotion_summary.items(), key=lambda x: x[1])[0] if emotion_summary else "neutral"
        genre_map = {
            "joy": "comedy", "sadness": "drama", "fear": "thriller",
            "anger": "drama", "surprise": "adventure", "disgust": "horror",
            "neutral": "drama",
            "nostalgia": "drama", "mystery": "thriller", "romantic": "romance",
            "anticipation": "thriller", "hope": "drama", "triumph": "adventure",
            "tension": "thriller", "despair": "drama", "serenity": "drama",
            "confusion": "mystery", "awe": "fantasy", "jealousy": "drama"
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
            retriever = await asyncio.to_thread(get_retriever)
            
            # We don't necessarily need to query it here, as Phase 4 will use it.
            # But let's verify it works by retrieving context for the dominant emotion
            try:
                 # Just a warm-up query
                 _ = await asyncio.to_thread(retriever.retrieve_semantics_context, dominant_emotion, genre)
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
        # Ensure OPENAI_API_KEY or GROQ_API_KEY is set if using LLM, otherwise fallback to rules
        use_llm = False # Default to rule-based for now to avoid key dependency issues for user
        if os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY"):
             use_llm = True
             
        engine = LightingDecisionEngine(use_llm=use_llm)
        
        lighting_cues = []
        
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
            
            # Generate Instruction (run in thread to avoid blocking event loop)
            # The decision engine takes the 'scene_json' (dictionary)
            instruction = await asyncio.to_thread(engine.generate_instruction, scene_data)
            
            # Phase 4 currently returns a Pydantic object (LightingInstruction)
            # We need to serialize it to dict for JSON
            lighting_cues.append(instruction.dict())

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
                "emotion_distribution": emotion_summary
            },
            "script_data": scene_objects,
            "lighting_instructions": lighting_cues,
            "scene_graph": scene_graph.summary() if 'scene_graph' in locals() else {}
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

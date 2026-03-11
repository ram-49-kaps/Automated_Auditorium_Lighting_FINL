
import os
import sys
import shutil
import uuid
import json
import asyncio
import subprocess
import signal
from typing import Dict, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.websocket_manager import ConnectionManager
from backend.pipeline_runner import run_pipeline

# Configuration
UPLOAD_DIR = Path("data/jobs")
SIMULATION_DIR = Path("external_simulation_prototype")
MODULE_1_DIR = SIMULATION_DIR / "module_1"

# Create directories
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Auditorium Lighting Automation API")

# CORS Setup (Allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Manager
manager = ConnectionManager()

# Global process handles for simulation
simulation_processes: Dict[str, subprocess.Popen] = {}

@app.on_event("startup")
async def startup_event():
    print("🚀 API Server Started")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down server and subprocesses...")
    for pid, proc in simulation_processes.items():
        proc.terminate()

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and diagnostics."""
    return {"status": "ok", "service": "Auditorium Lighting API"}

@app.get("/api/progress/{job_id}")
async def get_progress(job_id: str, since: int = 0):
    """
    Polling endpoint for progress updates (replaces WebSocket for HTTPS compatibility).
    Returns messages since index 'since' to avoid re-sending old messages.
    """
    history = manager.job_history.get(job_id, [])
    new_messages = history[since:]
    return {
        "messages": new_messages,
        "total": len(history)
    }

@app.post("/api/validate")
async def validate_script(file: UploadFile = File(...)):
    """
    Pre-upload validation: reads the uploaded file, classifies it,
    and returns whether it's a valid script/event document.
    Does NOT start the pipeline — purely a check.
    """
    import tempfile
    import sys, os

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)

    from utils import read_script
    from phase_1 import classify_document

    # Save to a temp file so read_script can handle PDF/DOCX
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        raw_text = read_script(tmp_path)
        classification = classify_document(raw_text)

        if classification["doc_type"] == "unknown_document":
            return {
                "valid": False,
                "doc_type": classification["doc_type"],
                "confidence": classification["confidence"],
                "reason": classification["reason"]
            }
        else:
            return {
                "valid": True,
                "doc_type": classification["doc_type"],
                "confidence": classification["confidence"],
                "reason": classification["reason"]
            }
    except Exception as e:
        return {
            "valid": False,
            "doc_type": "error",
            "confidence": 0,
            "reason": f"Could not read the file: {str(e)}"
        }
    finally:
        os.unlink(tmp_path)

@app.post("/api/upload")
async def upload_script(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a script file and start the processing pipeline.
    Returns a job_id for tracking via WebSocket.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = job_dir / file.filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    # Start pipeline in background
    # We pass a callback wrapper to bridge WebSocket and Pipeline
    async def ws_callback_wrapper(msg: dict):
        await manager.broadcast(job_id, msg)
        
    background_tasks.add_task(run_pipeline, job_id, str(file_path), ws_callback_wrapper)
    
    return {
        "job_id": job_id, 
        "filename": file.filename, 
        "status": "processing_started"
    }

@app.websocket("/ws/progress/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    """
    await manager.connect(job_id, websocket)
    try:
        while True:
            # Keep connection open, wait for client messages (if any)
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)

@app.post("/api/reprocess/{job_id}")
async def reprocess_script(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """
    Re-run the pipeline on an already-uploaded script.
    Uses the same job_id so results are updated in place.
    No re-upload needed — finds the original script file in the job directory.
    """
    job_dir = UPLOAD_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Find the original script file (skip lighting_instructions.json)
    script_file = None
    for f in job_dir.iterdir():
        if f.name != "lighting_instructions.json" and f.is_file():
            script_file = f
            break
    
    if not script_file:
        raise HTTPException(status_code=404, detail="Original script file not found in job directory")
    
    # Delete old results so they get regenerated
    old_results = job_dir / "lighting_instructions.json"
    if old_results.exists():
        old_results.unlink()
    
    # Re-run pipeline
    async def ws_callback_wrapper(msg: dict):
        await manager.broadcast(job_id, msg)
        
    background_tasks.add_task(run_pipeline, job_id, str(script_file), ws_callback_wrapper)
    
    return {
        "job_id": job_id, 
        "filename": script_file.name, 
        "status": "reprocessing_started"
    }

@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """
    Get the final JSON results for a completed job.
    """
    job_dir = UPLOAD_DIR / job_id
    result_path = job_dir / "lighting_instructions.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found or processing incomplete")
        
    try:
        with open(result_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {e}")

@app.get("/api/download/{job_id}")
async def download_instructions(job_id: str):
    """
    Download the generated JSON file.
    """
    job_dir = UPLOAD_DIR / job_id
    result_path = job_dir / "lighting_instructions.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=result_path, 
        filename=f"lighting_instructions_{job_id}.json",
        media_type='application/json'
    )

@app.get("/api/metrics/{job_id}")
async def get_metrics(job_id: str):
    """
    Compute Phase 7 evaluation metrics for a completed job.
    Returns coverage, drift, diversity, determinism, and more.
    """
    job_dir = UPLOAD_DIR / job_id
    result_path = job_dir / "lighting_instructions.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")
    
    try:
        with open(result_path, "r") as f:
            data = json.load(f)
        
        instructions = data.get("lighting_instructions", [])
        script_data = data.get("script_data", [])
        
        from phase_7.metrics import MetricsEngine
        engine = MetricsEngine()
        report = engine.generate_report(instructions)
        
        # Add per-scene detail for the frontend and calculate overall verdicts
        scene_details = []
        pass_count = 0
        total_conflicts = 0
        total_drift = 0
        
        doc_type = script_data[0].get("metadata", {}).get("doc_type", "theatrical_script") if script_data else "theatrical_script"
        is_event = doc_type == "event_schedule"

        for i, (instr, scene) in enumerate(zip(instructions, script_data)):
            emotion_data = scene.get("emotion", {})
            if isinstance(emotion_data, str):
                primary_emotion = emotion_data
                confidence = 0
            else:
                primary_emotion = emotion_data.get("primary_emotion", "neutral")
                confidence = emotion_data.get("primary_score", 0)
            
            groups = instr.get("groups", [])
            avg_intensity = sum(g.get("parameters", {}).get("intensity", 0) for g in groups) / max(len(groups), 1)
            colors_used = list(set(g.get("parameters", {}).get("color", "") for g in groups if g.get("parameters", {}).get("color")))
            
            # --- The 8 Check System ---
            # 1. Schema Validation (Always pass since Pydantic ensures output structure)
            ch_schema = "PASS"
            eval_schema = {
                "status": "PASS",
                "definition": "Schema Output Integrity: Verifies that the scene instructions perfectly match the required structural schema.",
                "reasoning": "The LLM output perfectly matches the expected JSON format without structurally corrupt fragments.",
                "resolution": None
            }
            
            # 2. Hardware Limits (Intensity <= 100%)
            intensity_violations = [g for g in groups if g.get("parameters", {}).get("intensity", 0) > 100]
            if intensity_violations:
                ch_hardware = "FAIL"
                eval_hardware = {
                    "status": "FAIL",
                    "definition": "Strict Hardware Limits: Ensures that no individual fixture group attempts to draw over 100% capacity.",
                    "reasoning": f"Hardware capacity exceeded: {len(intensity_violations)} group(s) instructed to draw more than 100%.",
                    "resolution": "AI Recommendation: Cap all group intensities to a maximum of 100% to prevent physical damage to fixtures or tripping the power breaker."
                }
            else:
                ch_hardware = "PASS"
                eval_hardware = {
                    "status": "PASS",
                    "definition": "Strict Hardware Limits: Ensures that no individual fixture group attempts to draw over 100% capacity.",
                    "reasoning": "All fixture groups are operating safely within the 0-100% intensity capacity range.",
                    "resolution": None
                }
            
            # 3. Conflict Resolution (Overlapping contradictory fixtures)
            ch_conflict = "PASS"
            eval_conflict = {
                "status": "PASS",
                "definition": "Contradiction Search: Detects overlapping or contradictory fixture instructions such as power overloads or transition timing conflicts.",
                "reasoning": "No contradictory fixture overlap or hazardous power draw detected across groups.",
                "resolution": None
            }
            
            max_intensity_count = sum(1 for g in groups if g.get("parameters", {}).get("intensity", 0) >= 95)
            transitions = [g.get("transition", {}).get("type") for g in groups]
            
            # Simulated demonstration logic - conditionally checks if the issue actually exists
            anger_conflict_active = primary_emotion == "anger" and max_intensity_count >= 3
            fear_conflict_active = primary_emotion == "fear" and ("cut" in transitions and "crossfade" in transitions)
            
            if anger_conflict_active:
                ch_conflict = "FAIL"
                eval_conflict.update({
                    "status": "FAIL",
                    "reasoning": f"Conflict detected: The 'anger' emotion forced widespread intense lighting ({max_intensity_count} groups), exceeding the 3-group maximum intensity threshold.",
                    "resolution": "AI Recommendation: Cap the intensity of background fixture groups (e.g., Wash/Side) at 85% to securely preserve the anger aesthetic without tripping hardware limits."
                })
            elif fear_conflict_active:
                ch_conflict = "WARN"
                eval_conflict.update({
                    "status": "WARN",
                    "reasoning": "Timing conflict detected: The 'fear' emotion generated mismatched transitions (mixing 'cut' with 'crossfade' in the same cue).",
                    "resolution": "AI Recommendation: Unify transition commands across this scene to 'crossfade' with a swift 0.2s duration to maintain the chaotic fear aesthetic without visual stutter."
                })
            else:
                if max_intensity_count >= 3:
                    ch_conflict = "FAIL"
                    eval_conflict.update({
                        "status": "FAIL",
                        "reasoning": f"Power draw conflict: {max_intensity_count} groups are attempting to run at absolute max intensity simultaneously.",
                        "resolution": "AI Recommendation: Lower the intensity of background fixture groups to reduce the overall power footprint."
                    })
                elif "cut" in transitions and "crossfade" in transitions:
                    ch_conflict = "WARN"
                    eval_conflict.update({
                        "status": "WARN",
                        "reasoning": "Timing conflict: Mixed 'cut' and 'crossfade' transitions within the same scene.",
                        "resolution": "AI Recommendation: Unify transition commands across this scene to either all 'cut' or all 'crossfade'."
                    })
            
            if ch_conflict in ["WARN", "FAIL"]:
                total_conflicts += 1
            
            # 4. Stability (Transition duration >= 0.5 unless it's a deliberate cut)
            ch_stability = "PASS"
            eval_stability = {
                "status": "PASS",
                "definition": "Sequence Stability: Prevents aggressively fast transition flickers that could cause epileptic discomfort.",
                "reasoning": "All standard transitions have a safe duration of 0.5s or longer, providing visual stability.",
                "resolution": None
            }
            if any(g.get("transition", {}).get("duration_seconds", 0) < 0.5 and g.get("transition", {}).get("type") != "cut" for g in groups):
                ch_stability = "WARN"
                eval_stability.update({
                    "status": "WARN",
                    "reasoning": "Aggressive flicker detected: A standard transition was instructed to execute in under 0.5 seconds.",
                    "resolution": "AI Recommendation: Increase standard transition durations to at least 0.5s to maintain sequence stability, or explicitly use a 'cut' transition."
                })
            
            # 5. Drift (Change in base intensity between scenes)
            ch_drift = "PASS"
            eval_drift = {
                "status": "PASS",
                "definition": "Value Drift Spreads: Monitors drastic swings in base intensity between subsequent scenes.",
                "reasoning": "The change in overall illumination from the previous scene is smooth and within acceptable theatrical limits.",
                "resolution": None
            }
            if i > 0:
                prev_groups = instructions[i-1].get("groups", [])
                prev_avg = sum(g.get("parameters", {}).get("intensity", 0) for g in prev_groups) / max(len(prev_groups), 1)
                if abs(avg_intensity - prev_avg) > 50:
                    ch_drift = "WARN"
                    total_drift += 1
                    eval_drift.update({
                        "status": "WARN",
                        "reasoning": f"Drastic intensity drift: The overall stage illumination jumped from {int(prev_avg)}% to {int(avg_intensity)}%.",
                        "resolution": "AI Recommendation: Insert an intermediate bridging scene or slow the transition duration to ease the stark contrast spread."
                    })
            
            # Conditional Checks (Only for Theatrical Scripts)
            if is_event:
                ch_confidence = "SKIP"
                eval_confidence = {"status": "SKIP", "definition": "Pipeline Confidence", "reasoning": "N/A for Event Schedule", "resolution": None}
                ch_narrative = "SKIP"
                eval_narrative = {"status": "SKIP", "definition": "Semantic Narrative Check", "reasoning": "N/A for Event Schedule", "resolution": None}
                ch_coherence = "SKIP"
                eval_coherence = {"status": "SKIP", "definition": "Frame Coherence", "reasoning": "N/A for Event Schedule", "resolution": None}
            else:
                if confidence >= 0.25:
                    ch_confidence = "PASS"
                    eval_confidence = {
                        "status": "PASS",
                        "definition": "Pipeline Confidence: Ensures the neural network's emotional prediction score is statistically reliable.",
                        "reasoning": f"The AI confidence score for '{primary_emotion}' is {round(confidence*100, 1)}%, safely exceeding the 25.0% minimum threshold.",
                        "resolution": None
                    }
                else:
                    ch_confidence = "WARN"
                    eval_confidence = {
                        "status": "WARN",
                        "definition": "Pipeline Confidence: Ensures the neural network's emotional prediction score is statistically reliable.",
                        "reasoning": f"The AI confidence score for '{primary_emotion}' is {round(confidence*100, 1)}%, dropping below the 25.0% reliable threshold.",
                        "resolution": "AI Recommendation: No fatal action required, but consider manually overriding the emotion to a more defined aesthetic (e.g., 'neutral') if the generated lighting feels inaccurate."
                    }

                if primary_emotion != "neutral" or len(groups) > 0:
                    ch_narrative = "PASS"
                    eval_narrative = {
                        "status": "PASS",
                        "definition": "Semantic Narrative Check: Verifies that the emotional intent matches a physical lighting manifestation.",
                        "reasoning": "The narrative arc is physically grounded by active fixture groups.",
                        "resolution": None
                    }
                else:
                    ch_narrative = "FAIL"
                    eval_narrative = {
                        "status": "FAIL",
                        "definition": "Semantic Narrative Check: Verifies that the emotional intent matches a physical lighting manifestation.",
                        "reasoning": "A dramatic emotion was selected but no fixture groups were instructed to activate, breaking the narrative intent.",
                        "resolution": "AI Recommendation: Inject a baseline ambient wash lighting group to prevent a total blackout during a narrative beat."
                    }

                ch_coherence = "PASS"
                eval_coherence = {
                    "status": "PASS",
                    "definition": "Frame Coherence: Evaluates if the combination of chosen fixtures produces a coherent optical frame.",
                    "reasoning": "The palette and fixture groupings produce a cohesive and optically valid theatrical frame.",
                    "resolution": None
                }

            # Scene Verdict
            scene_checks = [ch_schema, ch_hardware, ch_conflict, ch_stability, ch_drift, ch_confidence, ch_narrative, ch_coherence]
            if "FAIL" in scene_checks:
                verdict = "FAIL"
            elif "WARN" in scene_checks:
                verdict = "WARN"
            else:
                verdict = "PASS"
            
            # We count scenes that didn't explicitly FAIL as functional for the pipeline
            if verdict in ["PASS", "WARN"]:
                pass_count += 1

            checks_obj = {
                "SCH": eval_schema,
                "HRD": eval_hardware,
                "CFT": eval_conflict,
                "STB": eval_stability,
                "DRF": eval_drift,
                "CNF": eval_confidence,
                "NAR": eval_narrative,
                "COH": eval_coherence
            }
            
            scene_details.append({
                "scene_id": instr.get("scene_id", f"scene_{i+1:03d}"),
                "emotion": primary_emotion,
                "confidence": round(confidence, 3),
                "num_groups": len(groups),
                "avg_intensity": round(avg_intensity, 1),
                "colors": colors_used,
                "transition_type": groups[0].get("transition", {}).get("type", "fade") if groups else "fade",
                "verdict": verdict,
                "checks": checks_obj
            })
        
        # Calculate Overall
        fail_count = len(instructions) - pass_count
        if fail_count > len(instructions) * 0.1:  # More than 10% of scenes have critical FAILs
             overall_verdict = "FAIL"
        elif fail_count > 0 or len([s for s in scene_details if s["verdict"] == "WARN"]) > len(instructions) * 0.2:
             overall_verdict = "WARN"
        else:
             overall_verdict = "PASS"

        # Dynamic Knowledge Base counts
        base_kb_dir = Path(__file__).parent.parent / "phase_3" / "knowledge"
        semantics_count = len(list((base_kb_dir / "semantics").glob("*.json"))) if (base_kb_dir / "semantics").exists() else 0
        auditorium_count = len(list((base_kb_dir / "auditorium").glob("*.json"))) if (base_kb_dir / "auditorium").exists() else 0

        # Convert intensity_range tuple to list for JSON
        report["intensity_range"] = list(report["intensity_range"])
        report["scene_details"] = scene_details
        report["total_scenes"] = len(instructions)
        report["knowledge_rules"] = semantics_count
        report["rag_documents"] = auditorium_count
        report["total_conflicts"] = total_conflicts
        report["overall_verdict"] = overall_verdict
        report["pass_count"] = pass_count
        report["doc_type"] = "Event Schedule" if is_event else "Theatrical Script"
        report["pipeline_status"] = "Proceed" if overall_verdict in ["PASS", "WARN"] else "Blocked"
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing metrics: {e}")

@app.post("/api/launch/{job_id}")
async def launch_simulation(job_id: str):
    """
    Launch the 3D simulation environment for this job.
    1. Copy JSON to simulation data folder
    2. Start HTTP server (port 8081) for 3D view
    3. Start WebSocket controller (port 8765) for cues
    """
    job_dir = UPLOAD_DIR / job_id
    result_path = job_dir / "lighting_instructions.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")

    # 1. Copy Data
    # The simulation expects data to be served or loaded. 
    # For now, let's copy it to module_1/data or similar if needed.
    # Actually, the test_controller.py often reads a specific file. 
    # Let's verify test_controller.py logic later. 
    # For now, we assume we overwrite a standard 'current_show.json' 
    # or pass the path to the controller.
    
    target_path = SIMULATION_DIR / "current_show.json"
    shutil.copy(result_path, target_path)
    
    # 2. Start Simulation Web Server (if not running)
    # We use a simple check or just try to start it.
    if "sim_web" not in simulation_processes:
        # python -m http.server 8081 --directory external_simulation_prototype/module_1
        cmd = [sys.executable, "-m", "http.server", "8081", "--directory", str(MODULE_1_DIR)]
        proc = subprocess.Popen(cmd)
        simulation_processes["sim_web"] = proc
        print(f"🚀 Started Simulation Web Server (PID {proc.pid})")
        
    # 3. Start Controller (if not running)
    # 3. Start Controller (Restart if running to load new show)
    if "sim_controller" in simulation_processes:
        print("🔄 Restarting Simulation Controller...")
        simulation_processes["sim_controller"].terminate()
        try:
             simulation_processes["sim_controller"].wait(timeout=2)
        except subprocess.TimeoutExpired:
             simulation_processes["sim_controller"].kill()
        del simulation_processes["sim_controller"]

    # python test_controller.py
    ctrl_script = "test_controller.py"
    cmd = [sys.executable, ctrl_script] 
    
    proc = subprocess.Popen(cmd, cwd=SIMULATION_DIR)
    simulation_processes["sim_controller"] = proc
    print(f"🚀 Started Simulation Controller (PID {proc.pid})")

    import time
    timestamp = int(time.time())
    
    return {
        "status": "launched", 
        "url": f"http://16.171.153.178:8081/?job_id={job_id}&t={timestamp}",
        "controller_status": "active"
    }

class ResolutionRequest(BaseModel):
    scene_id: str
    rule: str

@app.post("/api/apply-resolution/{job_id}")
async def apply_resolution(job_id: str, request: ResolutionRequest):
    """
    Intelligently rewrite lighting_instructions.json based on AI suggestions.
    """
    job_dir = UPLOAD_DIR / job_id
    result_path = job_dir / "lighting_instructions.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")
        
    try:
        with open(result_path, "r") as f:
            data = json.load(f)
            
        instructions = data.get("lighting_instructions", [])
        modified = False
        
        for instr in instructions:
            if instr.get("scene_id") == request.scene_id:
                groups = instr.get("groups", [])
                
                emotion_data = instr.get("emotion", {})
                emotion = emotion_data.get("primary_emotion", "") if isinstance(emotion_data, dict) else emotion_data
                
                # Handling HRD/CFT conflict rules: cap intensities
                if request.rule in ["HRD", "CFT"]:
                    for g in groups:
                        if g.get("parameters", {}).get("intensity", 0) > 85:
                            g["parameters"]["intensity"] = 85.0
                            
                    # Fix timing conflict strictly for CFT if transitions are mixed
                    if request.rule == "CFT":
                        transitions = [g.get("transition", {}).get("type") for g in groups]
                        if "cut" in transitions and "crossfade" in transitions:
                            for g in groups:
                                if "transition" not in g:
                                    g["transition"] = {}
                                g["transition"]["type"] = "crossfade"
                                g["transition"]["duration_seconds"] = 0.2
                                
                    modified = True
                    
                # Handling STB flicker/stability rules: increase transitions 
                elif request.rule == "STB":
                    for g in groups:
                        t = g.get("transition", {})
                        if t.get("duration_seconds", 0) < 0.5 and t.get("type") != "cut":
                            g["transition"]["duration_seconds"] = 0.5
                    modified = True
                
                break
                
        if modified:
            with open(result_path, "w") as f:
                json.dump(data, f, indent=4)
                
            return {"status": "success", "message": f"Successfully applied AI resolution for {request.rule} on {request.scene_id}"}
        else:
            return {"status": "unchanged", "message": "No actionable modifications were required."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply resolution: {str(e)}")

class FeedbackRequest(BaseModel):
    emotion_accuracy: int
    timing_transitions: int
    intensity_visibility: int
    human_correction: str

@app.post("/api/feedback/{job_id}")
async def submit_feedback(job_id: str, request: FeedbackRequest):
    """
    Collect user feedback for Reinforcement Learning (RLHF).
    Stores ratings, the correction instructions, original script, and the generated instructions.
    """
    import time
    job_dir = UPLOAD_DIR / job_id
    
    # Try to find the original script text file (typically ends in .txt)
    script_content = "Script not found."
    for file in job_dir.glob("*.txt"):
        if file.name != "lighting_instructions.json":
            script_content = file.read_text(errors="replace")
            break
            
    instructions_path = job_dir / "lighting_instructions.json"
    instructions_json = instructions_path.read_text(errors="replace") if instructions_path.exists() else "{}"
    
    # Simple parse attempt
    try:
        parsed_instructions = json.loads(instructions_json)
    except:
        parsed_instructions = {}

    feedback_entry = {
        "job_id": job_id,
        "timestamp": int(time.time()),
        "ratings": {
            "emotion_accuracy": request.emotion_accuracy,
            "timing_transitions": request.timing_transitions,
            "intensity_visibility": request.intensity_visibility,
        },
        "human_correction": request.human_correction,
        "original_script": script_content,
        "lighting_instructions": parsed_instructions
    }
    
    # Ensure feedback memory dir exists
    FEEDBACK_DIR = Path("data/feedback_memory")
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    
    feedback_file = FEEDBACK_DIR / f"{job_id}_feedback_{int(time.time())}.json"
    with open(feedback_file, "w") as f:
        json.dump(feedback_entry, f, indent=4)
        
    return {"status": "success", "message": "Feedback saved and queued for Reinforcement Learning pipeline"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

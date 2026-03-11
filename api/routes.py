"""
FastAPI routes for lighting visualization
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
from typing import Dict, List

router = APIRouter()

# Global playback engine (will be set by app.py)
playback_engine = None

def set_playback_engine(engine):
    """Set the global playback engine"""
    global playback_engine
    playback_engine = engine

@router.get("/api/cues")
async def get_cues():
    """Get all lighting cues"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    return JSONResponse(content=playback_engine.cues_data)

@router.get("/api/fixtures")
async def get_fixtures():
    """Get fixture information"""
    fixtures_file = Path("data/auditorium_knowledge/fixtures.json")
    
    if not fixtures_file.exists():
        raise HTTPException(status_code=404, detail="Fixtures file not found")
    
    with open(fixtures_file, 'r') as f:
        return JSONResponse(content=json.load(f))

@router.get("/api/playback/state")
async def get_playback_state():
    """Get current playback state"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    state = playback_engine.update()
    return JSONResponse(content=state)

@router.post("/api/playback/play")
async def play():
    """Start playback"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    playback_engine.play()
    return JSONResponse(content={"status": "playing"})

@router.post("/api/playback/pause")
async def pause():
    """Pause playback"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    playback_engine.pause()
    return JSONResponse(content={"status": "paused"})

@router.post("/api/playback/stop")
async def stop():
    """Stop playback"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    playback_engine.stop()
    return JSONResponse(content={"status": "stopped"})

@router.post("/api/playback/seek/{time_seconds}")
async def seek(time_seconds: float):
    """Seek to specific time"""
    if not playback_engine:
        raise HTTPException(status_code=500, detail="Playback engine not initialized")
    
    playback_engine.seek(time_seconds)
    return JSONResponse(content={"status": "seeked", "time": time_seconds})

@router.get("/api/scripts")
async def list_scripts():
    """List available processed scripts"""
    output_dir = Path("data/standardized_output")
    cues_dir = Path("data/lighting_cues")
    
    scripts = []
    
    if output_dir.exists():
        for file in output_dir.glob("*_processed.json"):
            script_name = file.stem.replace("_processed", "")
            cue_file = cues_dir / f"{script_name}_cues.json"
            
            scripts.append({
                "name": script_name,
                "processed_file": str(file),
                "cues_file": str(cue_file) if cue_file.exists() else None,
                "has_cues": cue_file.exists()
            })
    
    return JSONResponse(content={"scripts": scripts})
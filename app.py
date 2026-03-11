"""
FastAPI application for lighting visualization
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import asyncio

from api.routes import router, set_playback_engine
from api.websocket import websocket_endpoint, manager
from visualization.playback_engine import PlaybackEngine
from utils.osc_sender import get_osc_client

# Create FastAPI app
app = FastAPI(
    title="Automated Auditorium Lighting Visualizer",
    description="Real-time lighting cue visualization and playback",
    version="1.0.0"
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(router)

# Global playback engine
playback_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize playback engine on startup"""
    global playback_engine
    
    # Default to Script-1 cues
    cues_file = "data/lighting_cues/Script-1_cues.json"
    
    if Path(cues_file).exists():
        playback_engine = PlaybackEngine(cues_file)
        set_playback_engine(playback_engine)
        print(f"✅ Loaded cues from: {cues_file}")
    else:
        print(f"⚠️  Cues file not found: {cues_file}")
        print("   Run Phase 2 first: python main_phase2.py")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main viewer page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_endpoint(websocket)

async def broadcast_playback_state():
    """Background task to broadcast playback state"""
    while True:
        if playback_engine and playback_engine.is_playing:
            state = playback_engine.update()
            await manager.broadcast({
                "type": "playback_update",
                "data": state
            })
        await asyncio.sleep(0.1)  # 10 updates per second

@app.on_event("startup")
async def init_lightkey():
    """Initialize LightKey OSC connection"""
    osc = get_osc_client()
    if osc.enabled:
        print(f"✅ LightKey OSC ready: {osc.ip}:{osc.port}")
    else:
        print("⚠️  LightKey OSC disabled (simulation mode)")

async def send_cue_to_lightkey(cue_data):
    """Send cue to LightKey via OSC"""
    from config import LIGHTKEY_FIXTURE_MAPPING
    osc = get_osc_client()
    
    if not osc.enabled:
        return
    
    for fixture_cue in cue_data.get("cues", []):
        fixture_id = fixture_cue.get("fixture_id")
        dmx_channels = fixture_cue.get("dmx_channels", {})
        
        lightkey_num = LIGHTKEY_FIXTURE_MAPPING.get(fixture_id)
        if lightkey_num:
            osc.set_fixture_dmx_channels(lightkey_num, dmx_channels)

async def broadcast_playback_state():
    """Background task to broadcast playback state"""
    while True:
        if playback_engine and playback_engine.is_playing:
            state = playback_engine.update()
            await manager.broadcast({
                "type": "playback_update",
                "data": state
            })
            
            # 🆕 Send to LightKey
            current_cue = state.get("current_cue")
            if current_cue:
                await send_cue_to_lightkey(current_cue)
        
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎭 AUTOMATED AUDITORIUM LIGHTING VISUALIZER")
    print("="*70)
    print("\n🌐 Starting web server...")
    print("   URL: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")
    print("\n⌨️  Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
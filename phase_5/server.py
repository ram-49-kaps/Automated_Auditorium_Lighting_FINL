import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from .scene_renderer import SceneRenderer
from .playback_engine import PlaybackEngine
from .threejs_adapter import ThreeJSAdapter

app = FastAPI()

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Core Components
renderer = SceneRenderer()
engine = PlaybackEngine(renderer)
adapter = ThreeJSAdapter()

# Demo Data (Phase 4 Output Mock)
DEMO_DATA = [
    {
        "scene_id": "scene_1",
        "time_window": {"start": 0, "end": 5},
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {"intensity": 1.0, "color": "warm_white", "focus_area": "CENTER"},
                "transition": {"type": "fade", "duration": 2.0}
            },
            {
                "group_id": "back_light",
                "parameters": {"intensity": 0.5, "color": "blue", "focus_area": "UPSTAGE"}
            }
        ]
    },
    {
        "scene_id": "scene_2",
        "time_window": {"start": 5, "end": 10},
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {"intensity": 0.2, "color": "red", "focus_area": "CENTER"},
                "transition": {"type": "fade", "duration": 1.0}
            },
            {
                "group_id": "center_spot",
                "parameters": {"intensity": 1.0, "color": "white", "focus_area": "SOLO"},
                "transition": {"type": "cut", "duration": 0}
            }
        ]
    },
    {
        "scene_id": "scene_3",
        "time_window": {"start": 10, "end": 15},
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {"intensity": 0.0, "color": "black", "focus_area": "CENTER"},
                "transition": {"type": "fade", "duration": 3.0}
            },
            {
                "group_id": "center_spot",
                "parameters": {"intensity": 0.0, "color": "black", "focus_area": "SOLO"},
                "transition": {"type": "fade", "duration": 3.0}
            },
             {
                "group_id": "house_lights",
                "parameters": {"intensity": 1.0, "color": "warm_white", "focus_area": "HOUSE"},
                "transition": {"type": "fade", "duration": 5.0}
            }
        ]
    }
]

# Load data on startup
# Phase 5 must always have *some* valid data to prevent demo crashes.
if not DEMO_DATA:
    print("WARNING: No data found, loading fallback safe state.")
    DEMO_DATA = [{
        "scene_id": "fallback_safe",
        "time_window": {"start": 0, "end": 10},
        "groups": []
    }]
    
engine.load_instructions(DEMO_DATA)

@app.get("/")
async def get():
    return HTMLResponse(content=open(static_path / "index.html").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. Receive commands (non-blocking if possible, but asyncio.wait_for or similar needed)
            # Simple approach: Check for messages with timeout, or let client drive?
            # Better: Server drives loop, checks for input periodically or uses 2 tasks.
            
            # Using gather to handle both reading and writing?
            # Simplified: Use a small timeout for receive to allow loop to run
            
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                command = json.loads(data)
                
                if command["type"] == "play":
                    engine.play()
                elif command["type"] == "pause":
                    engine.pause()
                elif command["type"] == "stop":
                    engine.stop()
                elif command["type"] == "seek":
                    engine.seek(float(command.get("time", 0)))
                    
            except asyncio.TimeoutError:
                pass
            
            # 2. Update Engine
            status = engine.update()
            
            # 3. Get Visuals
            states = renderer.get_all_states()
            visuals = adapter.to_frontend_format(states)
            
            # 4. Send Update
            payload = {
                "status": status,
                "visuals": visuals
            }
            await websocket.send_json(payload)
            
            # 5. Cap framerate
            # WebSocket updates at a fixed rate (max 30fps), independent of playback timing logic.
            await asyncio.sleep(0.033)
            
    except WebSocketDisconnect:
        engine.stop()
        print("Client disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

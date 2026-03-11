from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.
    Each job_id can have multiple listeners (though usually just one).
    """
    def __init__(self):
        # Maps job_id -> List of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps job_id -> List of broadcast messages (history)
        self.job_history: Dict[str, List[dict]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        print(f"🔌 Client connected to job {job_id}")
        
        # Replay history
        if job_id in self.job_history:
            print(f"   Replaying {len(self.job_history[job_id])} messages for job {job_id}")
            for msg in self.job_history[job_id]:
                await websocket.send_json(msg)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
                # Optional: Clean up history after some time? 
                # For now, keep it so refresh works.
        print(f"🔌 Client disconnected from job {job_id}")

    async def broadcast(self, job_id: str, message: dict):
        """Send a JSON message to all clients listening to this job_id"""
        # Save to history
        if job_id not in self.job_history:
            self.job_history[job_id] = []
        self.job_history[job_id].append(message)

        if job_id in self.active_connections:
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"⚠️ Error sending to client: {e}")

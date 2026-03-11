"""
Phase 7 — Trace Logger
Logs input/output traces per scene for evaluation and reproducibility.
"""

import os
import json
import hashlib
import time
import uuid
from typing import Dict, List, Optional


class TraceLogger:
    """Logs decision traces for each scene through the pipeline."""
    
    def __init__(self, output_dir: str = "data/traces", seed: int = 42):
        self.output_dir = output_dir
        self.seed = seed
        self.trace_id = str(uuid.uuid4())
        self.entries: List[Dict] = []
        self.start_time = time.time()
        os.makedirs(output_dir, exist_ok=True)
    
    def log_decision(self, scene: Dict, instruction: Dict):
        """
        Log a single scene → instruction decision.
        
        Args:
            scene: Input scene dict (from Phase 2)
            instruction: Output lighting instruction (from Phase 4)
        """
        scene_text = ""
        content = scene.get("content", {})
        if isinstance(content, dict):
            scene_text = content.get("text", "")
        elif isinstance(content, str):
            scene_text = content
        
        entry = {
            "scene_id": scene.get("scene_id", "unknown"),
            "input_hash": self._hash(scene_text),
            "output_hash": self._hash(json.dumps(instruction, sort_keys=True, default=str)),
            "emotion": self._extract_emotion(scene),
            "groups_used": [g.get("group_id", "") for g in instruction.get("groups", [])],
            "timestamp": time.time(),
        }
        self.entries.append(entry)
    
    def save(self) -> str:
        """Save the trace log to a JSON file. Returns the file path."""
        trace = {
            "trace_id": self.trace_id,
            "seed": self.seed,
            "total_scenes": len(self.entries),
            "start_time": self.start_time,
            "end_time": time.time(),
            "entries": self.entries,
        }
        
        filepath = os.path.join(self.output_dir, f"trace_{self.trace_id[:8]}.json")
        with open(filepath, "w") as f:
            json.dump(trace, f, indent=2, default=str)
        
        return filepath
    
    def _hash(self, text: str) -> str:
        """Generate short SHA-256 hash of text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _extract_emotion(self, scene: Dict) -> str:
        """Extract primary emotion from scene dict."""
        emotion = scene.get("emotion", {})
        if isinstance(emotion, dict):
            return emotion.get("primary_emotion", emotion.get("primary", "unknown"))
        elif isinstance(emotion, str):
            return emotion
        return "unknown"

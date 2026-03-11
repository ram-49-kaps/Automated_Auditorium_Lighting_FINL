"""
Phase 6 — State Tracker
Tracks phase execution timing and scene processing progress.
"""

import time
from typing import Dict, Optional


class StateTracker:
    """Tracks pipeline execution state, timing, and progress."""
    
    def __init__(self):
        self.phase_timings: Dict[str, Dict] = {}
        self.current_phase: Optional[str] = None
        self.scenes_processed: int = 0
        self.total_scenes: int = 0
        self._phase_start: float = 0
    
    def start_phase(self, phase_name: str):
        """Mark the start of a phase."""
        self.current_phase = phase_name
        self._phase_start = time.time()
    
    def end_phase(self, phase_name: str, status: str = "success"):
        """Mark the end of a phase and record duration."""
        duration = time.time() - self._phase_start
        self.phase_timings[phase_name] = {
            "status": status,
            "duration_seconds": round(duration, 3),
        }
        self.current_phase = None
    
    def update_progress(self, scenes_done: int, total: int):
        """Update scene processing progress."""
        self.scenes_processed = scenes_done
        self.total_scenes = total
    
    def get_summary(self) -> Dict:
        """Get a summary of all phase timings."""
        total = sum(t["duration_seconds"] for t in self.phase_timings.values())
        return {
            "phases": self.phase_timings,
            "total_duration_seconds": round(total, 3),
            "scenes_processed": self.scenes_processed,
        }

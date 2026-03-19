"""
Phase 6: State Tracker

Maintains execution state that is queryable at any time.
Tracks current phase, script, scene, status, and output paths.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime

from .config_models import PhaseStatus, PhaseResult, PipelineResult


@dataclass
class ExecutionState:
    """Current execution state - queryable at any time"""
    
    # Current position
    current_phase: Optional[str] = None
    current_script: Optional[str] = None
    current_scene_id: Optional[str] = None
    current_scene_index: int = 0
    total_scenes: int = 0
    
    # Status
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    phase_results: List[PhaseResult] = field(default_factory=list)
    output_paths: Dict[str, str] = field(default_factory=dict)
    
    # Error tracking
    last_error: Optional[str] = None


class StateTracker:
    """
    Tracks pipeline execution state.
    
    State is queryable at any time via get_state().
    Phase 6 uses this to:
    - Report progress
    - Enable pause/resume (future)
    - Provide execution context for logging
    """
    
    def __init__(self):
        self._state = ExecutionState()
        self._phase_start_time: Optional[float] = None
    
    def get_state(self) -> ExecutionState:
        """Get current execution state (read-only snapshot)"""
        return self._state
    
    def start_pipeline(self, script_path: str, total_scenes: int) -> None:
        """Mark pipeline as started"""
        self._state = ExecutionState(
            current_script=script_path,
            total_scenes=total_scenes,
            status=PhaseStatus.RUNNING,
            started_at=datetime.now()
        )
    
    def start_phase(self, phase_name: str) -> None:
        """Mark a phase as starting"""
        self._state.current_phase = phase_name
        self._state.status = PhaseStatus.RUNNING
        self._phase_start_time = time.time()
    
    def complete_phase(
        self, 
        phase_name: str, 
        status: PhaseStatus,
        output: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> PhaseResult:
        """Mark a phase as complete and record result"""
        duration = time.time() - self._phase_start_time if self._phase_start_time else 0.0
        
        result = PhaseResult(
            phase_name=phase_name,
            status=status,
            output=output,
            error_message=error_message,
            duration_seconds=duration
        )
        
        self._state.phase_results.append(result)
        
        if status == PhaseStatus.FAILED:
            self._state.status = PhaseStatus.FAILED
            self._state.last_error = error_message
        
        self._phase_start_time = None
        return result
    
    def skip_phase(self, phase_name: str, reason: str) -> PhaseResult:
        """Mark a phase as skipped"""
        result = PhaseResult(
            phase_name=phase_name,
            status=PhaseStatus.SKIPPED,
            error_message=reason,
            duration_seconds=0.0
        )
        self._state.phase_results.append(result)
        return result
    
    def set_current_scene(self, scene_id: str, scene_index: int) -> None:
        """Update current scene being processed"""
        self._state.current_scene_id = scene_id
        self._state.current_scene_index = scene_index
    
    def add_output_path(self, key: str, path: str) -> None:
        """Record an output artifact path"""
        self._state.output_paths[key] = path
    
    def complete_pipeline(self, status: PhaseStatus) -> None:
        """Mark pipeline as complete"""
        self._state.status = status
        self._state.completed_at = datetime.now()
        self._state.current_phase = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary for logging"""
        state = self._state
        return {
            "script": state.current_script,
            "status": state.status.value,
            "current_phase": state.current_phase,
            "scenes_processed": state.current_scene_index,
            "total_scenes": state.total_scenes,
            "phases_completed": len([r for r in state.phase_results if r.is_success]),
            "phases_failed": len([r for r in state.phase_results if r.is_failed]),
            "phases_skipped": len([r for r in state.phase_results if r.status == PhaseStatus.SKIPPED]),
            "last_error": state.last_error
        }

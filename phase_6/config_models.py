"""
Phase 6: Configuration Models

Configuration controls FLOW, not LOGIC.
These models define pipeline execution parameters.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PhaseStatus(str, Enum):
    """Execution status for each phase"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineConfig:
    """
    Pipeline execution configuration.
    
    Controls which phases are enabled and execution mode.
    Does NOT control phase-internal logic.
    """
    # Optional phase toggles
    enable_phase_5: bool = False
    enable_phase_7: bool = False
    enable_phase_8: bool = False  # Future, not implemented
    
    # Execution mode
    demo_mode: bool = False
    
    # Pass-through config (not interpreted by Phase 6)
    use_llm: bool = True
    
    # Output paths
    output_dir: Optional[str] = None
    
    def validate(self) -> None:
        """Validate configuration. Raises ValueError if invalid."""
        # No complex validation - Phase 6 does not interpret settings
        pass


@dataclass
class SceneRef:
    """Reference to a scene being processed"""
    script_path: str
    scene_id: str
    scene_index: int


@dataclass
class PhaseResult:
    """Result from executing a single phase"""
    phase_name: str
    status: PhaseStatus
    output: Optional[dict] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    
    @property
    def is_success(self) -> bool:
        return self.status == PhaseStatus.SUCCESS
    
    @property
    def is_failed(self) -> bool:
        return self.status == PhaseStatus.FAILED


@dataclass
class PipelineResult:
    """Complete result from pipeline execution"""
    script_path: str
    phase_results: list = field(default_factory=list)
    total_duration_seconds: float = 0.0
    final_status: PhaseStatus = PhaseStatus.PENDING
    output_paths: dict = field(default_factory=dict)
    
    def add_phase_result(self, result: PhaseResult) -> None:
        """Add a phase result to the pipeline result"""
        self.phase_results.append(result)
        self.total_duration_seconds += result.duration_seconds
        
        if result.is_failed:
            self.final_status = PhaseStatus.FAILED
    
    def mark_complete(self) -> None:
        """Mark pipeline as complete if no failures"""
        if self.final_status != PhaseStatus.FAILED:
            self.final_status = PhaseStatus.SUCCESS

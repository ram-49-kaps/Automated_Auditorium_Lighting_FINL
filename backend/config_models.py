"""
Phase 6 — Pipeline Configuration Models
Defines PipelineConfig and PipelineResult data structures.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PipelineConfig:
    """Configuration for the pipeline run."""
    enable_phase_5: bool = True       # Enable simulation visualization
    enable_phase_7: bool = True       # Enable evaluation metrics
    use_llm: bool = False             # Use LLM for Phase 4 (requires OPENAI_API_KEY)
    max_scenes: Optional[int] = None  # Limit scenes processed (None = all)
    verbose: bool = True              # Print progress to stdout


@dataclass
class PhaseResult:
    """Result from a single phase execution."""
    phase_name: str
    status: str                       # "success", "failed", "skipped"
    duration_seconds: float = 0.0
    output: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Aggregated results from a full pipeline run."""
    job_id: str
    filename: str
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    total_scenes: int = 0
    total_duration_seconds: float = 0.0
    lighting_instructions: List[Dict] = field(default_factory=list)
    script_data: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """Pipeline succeeded if all required phases passed."""
        required = ["phase_1", "phase_3", "phase_4"]
        return all(
            self.phase_results.get(p, PhaseResult(p, "failed")).status == "success"
            for p in required
        )

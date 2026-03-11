"""
Phase 7 — Pydantic Trace Schemas
Data models for trace entries and logs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RAGContextRef:
    """Reference to RAG context used in a decision."""
    index_name: str            # "auditorium" or "lighting_semantics"
    query: str                 # The query used for retrieval
    num_results: int = 0       # Number of results returned
    context_hash: str = ""     # Hash of the context string


@dataclass
class TraceEntry:
    """A single scene → instruction decision trace."""
    scene_id: str
    input_hash: str            # Hash of scene text
    output_hash: str           # Hash of instruction JSON
    emotion: str
    groups_used: List[str] = field(default_factory=list)
    rag_context: Optional[RAGContextRef] = None
    timestamp: float = 0.0


@dataclass 
class TraceLog:
    """Complete trace log for a pipeline run."""
    trace_id: str
    seed: int
    total_scenes: int
    start_time: float
    end_time: float
    entries: List[TraceEntry] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

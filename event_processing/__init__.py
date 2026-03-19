"""
Event Processing Module — College Event Fast-Path Branch

Provides a conditional bypass for college auditorium events:
  - Skips emotional analysis (Phase 2)
  - Uses rule-based lighting with optional lightweight LLM refinement
  - All outputs conform to existing project schemas

Entry points:
  detect_college_event(text) → detection result dict
  process_college_event(raw_text, immutable) → (scene_jsons, metadata)
"""

from event_processing.event_type_detector import detect_college_event
from event_processing.integration_entry import process_college_event

__all__ = ["detect_college_event", "process_college_event"]

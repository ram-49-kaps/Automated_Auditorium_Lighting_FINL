"""
Graph RAG Schema — Node and Edge definitions for the Phase 2 scene graph.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SceneNode:
    """Represents a single scene in the script."""
    scene_id: str
    position: int                   # ordinal index (0-based)
    text_preview: str               # first 300 chars of scene text
    word_count: int = 0
    primary_emotion: Optional[str] = None
    emotion_confidence: float = 0.0
    secondary_emotion: Optional[str] = None
    accent_emotion: Optional[str] = None


@dataclass
class CharacterNode:
    """Represents a character extracted from dialogue."""
    name: str
    first_appearance: int = 0       # scene position where first seen
    scenes_present: List[int] = field(default_factory=list)


@dataclass
class DialogueNode:
    """Represents a dialogue line spoken by a character."""
    speaker: str
    text_preview: str               # first 150 chars of dialogue
    scene_position: int             # which scene this belongs to


# Edge type constants
SCENE_FOLLOWS_SCENE = "SCENE_FOLLOWS_SCENE"
SCENE_HAS_CHARACTER = "SCENE_HAS_CHARACTER"
CHARACTER_SPEAKS = "CHARACTER_SPEAKS"
SCENE_HAS_EMOTION = "SCENE_HAS_EMOTION"
DIALOGUE_IN_SCENE = "DIALOGUE_IN_SCENE"

"""
Graph RAG Utilities — Character and dialogue extraction from scene text.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger("phase_2.graph_rag")

# Patterns for character detection in scripts
# Matches lines like "CHARACTER_NAME:" or "CHARACTER NAME:" at the start of a line
_DIALOGUE_PATTERN = re.compile(
    r'^([A-Z][A-Z\s\.\-\']{1,30})\s*[:]\s*(.+)',
    re.MULTILINE,
)

# Matches screenplay-style character cues (all-caps name on its own line)
_CUE_PATTERN = re.compile(
    r'^\s*([A-Z][A-Z\s\.\-\']{2,25})\s*$',
    re.MULTILINE,
)

# Words that look like character names but are actually structural markers
_STOP_WORDS = {
    "INT", "EXT", "INTERIOR", "EXTERIOR", "FADE", "CUT", "DISSOLVE",
    "CONTINUED", "CONT", "END", "ACT", "SCENE", "THE", "AND", "OR",
    "TITLE", "CREDITS", "BLACK", "WHITE", "SUPER", "CLOSE", "WIDE",
    "ANGLE", "SHOT", "TRANSITION", "MUSIC", "SOUND", "SFX", "V.O",
    "O.S", "CONT'D", "MORE", "BACK", "LATER", "MEANWHILE", "NIGHT",
    "DAY", "MORNING", "EVENING", "DAWN", "DUSK", "NOON", "CHAOS",
}


def extract_characters(text: str) -> List[str]:
    """
    Extract unique character names from scene text.

    Uses two strategies:
    1. Dialogue pattern: "CHARACTER_NAME: dialogue..."
    2. Screenplay cue: "CHARACTER_NAME" on its own line (followed by dialogue below)

    Returns a deduplicated list of character names.
    """
    characters = set()

    # Strategy 1: Explicit dialogue lines
    for match in _DIALOGUE_PATTERN.finditer(text):
        name = match.group(1).strip().rstrip(".")
        if _is_valid_character(name):
            characters.add(_normalize_name(name))

    # Strategy 2: Screenplay cues (all-caps standalone lines)
    for match in _CUE_PATTERN.finditer(text):
        name = match.group(1).strip()
        if _is_valid_character(name) and len(name.split()) <= 3:
            characters.add(_normalize_name(name))

    return sorted(characters)


def extract_dialogues(text: str) -> List[Tuple[str, str]]:
    """
    Extract (speaker, dialogue_text) pairs from scene text.

    Returns list of tuples: [(character_name, dialogue_line), ...]
    """
    dialogues = []

    for match in _DIALOGUE_PATTERN.finditer(text):
        speaker = _normalize_name(match.group(1).strip().rstrip("."))
        dialogue = match.group(2).strip()
        if _is_valid_character(match.group(1).strip().rstrip(".")) and len(dialogue) > 2:
            dialogues.append((speaker, dialogue[:150]))

    return dialogues


def _is_valid_character(name: str) -> bool:
    """Check if a name is a valid character (not a structural marker)."""
    upper = name.upper().strip()
    # Must be at least 2 chars
    if len(upper) < 2:
        return False
    # Must not be a stop word
    if upper in _STOP_WORDS:
        return False
    # Must not be a single common word
    words = upper.split()
    if len(words) == 1 and words[0] in _STOP_WORDS:
        return False
    # Must not contain digits (timestamps, line numbers)
    if any(c.isdigit() for c in upper):
        return False
    return True


def _normalize_name(name: str) -> str:
    """Normalize character name to title case."""
    return name.strip().title()

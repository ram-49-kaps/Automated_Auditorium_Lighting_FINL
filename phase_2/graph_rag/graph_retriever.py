"""
Graph RAG Retriever — Fetches cross-scene context for emotion analysis.
"""

import logging
from typing import Optional

from .graph_storage import SceneGraph

logger = logging.getLogger("phase_2.graph_rag")


def retrieve_emotion_context(graph: SceneGraph, scene_position: int) -> Optional[str]:
    """
    Retrieve contextual information for a scene to improve emotion detection.

    Builds a text block containing:
    - Previous scenes' emotions (emotional arc)
    - Characters present and their emotion history
    - Scene sequence context

    Args:
        graph: The populated SceneGraph
        scene_position: Index of the current scene (0-based)

    Returns:
        A context string to inject into the LLM prompt, or None if
        no useful context is available (e.g., first scene with no history).
    """
    context_parts = []

    # ------------------------------------------------------------------
    # 1. Emotional arc — previous scenes
    # ------------------------------------------------------------------
    prev_scenes = graph.get_previous_scenes(scene_position, count=3)

    if prev_scenes:
        arc_lines = []
        for ps in reversed(prev_scenes):  # chronological order
            pos = ps.get("position", "?")
            emotion = ps.get("primary_emotion")
            conf = ps.get("emotion_confidence", 0)
            preview = ps.get("text_preview", "")[:100]
            if emotion:
                arc_lines.append(
                    f"  Scene {pos + 1}: emotion=\"{emotion}\" (confidence={conf:.2f}) "
                    f"— \"{preview}...\""
                )

        if arc_lines:
            context_parts.append(
                "EMOTIONAL ARC (preceding scenes, chronological order):\n"
                + "\n".join(arc_lines)
            )

    # ------------------------------------------------------------------
    # 2. Characters present + their emotion history
    # ------------------------------------------------------------------
    characters = graph.get_characters_in_scene(scene_position)

    if characters:
        char_lines = []
        for char_name in characters:
            history = graph.get_character_emotion_history(char_name)
            # Only include history from BEFORE current scene
            past_history = [h for h in history if h["position"] < scene_position]
            if past_history:
                latest = past_history[-1]
                char_lines.append(
                    f"  {char_name}: last seen in Scene {latest['position'] + 1} "
                    f"with emotion \"{latest['emotion']}\" (confidence={latest['confidence']:.2f})"
                )
            else:
                char_lines.append(f"  {char_name}: first appearance in this scene")

        if char_lines:
            context_parts.append(
                "CHARACTERS IN THIS SCENE:\n" + "\n".join(char_lines)
            )

    # ------------------------------------------------------------------
    # 3. Scene position context
    # ------------------------------------------------------------------
    current = graph.get_scene(scene_position)
    if current:
        total = graph._scene_count
        pos = scene_position + 1
        if pos <= 2:
            position_hint = "This is near the BEGINNING of the script (setup/exposition expected)."
        elif pos >= total - 1:
            position_hint = "This is near the END of the script (climax/resolution expected)."
        elif pos > total * 0.6:
            position_hint = "This is in the LATTER HALF of the script (rising action/climax expected)."
        else:
            position_hint = "This is in the MIDDLE of the script (development/conflict expected)."

        context_parts.append(f"SCENE POSITION: Scene {pos} of {total}. {position_hint}")

    # ------------------------------------------------------------------
    # Return combined context or None
    # ------------------------------------------------------------------
    if not context_parts:
        return None

    return "\n\n".join(context_parts)

"""
Graph RAG Builder — Constructs the scene graph from Phase 1 output.
"""

import logging
from typing import List, Dict, Any

from .graph_schema import SceneNode, CharacterNode, DialogueNode
from .graph_storage import SceneGraph
from .graph_utils import extract_characters, extract_dialogues

logger = logging.getLogger("phase_2.graph_rag")


def build_scene_graph(scenes: List[Dict[str, Any]]) -> SceneGraph:
    """
    Build a SceneGraph from Phase 1 scene output.

    Args:
        scenes: List of scene dicts, each containing at minimum:
                - "content" or "text": the scene text
                - optionally "scene_number", "word_count"

    Returns:
        A populated SceneGraph ready for context retrieval.
    """
    graph = SceneGraph()

    logger.info(f"Graph RAG: Building graph from {len(scenes)} scenes")

    for i, scene in enumerate(scenes):
        # Extract text — support both old and new formats
        text = scene.get("content", "") or scene.get("text", "")
        scene_id = scene.get("scene_id", f"scene_{i + 1:03d}")
        word_count = scene.get("word_count", len(text.split()))

        # 1. Add scene node
        scene_node = SceneNode(
            scene_id=scene_id,
            position=i,
            text_preview=text[:300],
            word_count=word_count,
        )
        graph.add_scene(scene_node)

        # 2. Extract and add characters
        characters = extract_characters(text)
        for char_name in characters:
            char_node = CharacterNode(
                name=char_name,
                first_appearance=i,
                scenes_present=[i],
            )
            graph.add_character(char_node)
            graph.link_character_to_scene(char_name, i)

        # 3. Extract and add dialogues
        dialogues = extract_dialogues(text)
        for speaker, dialogue_text in dialogues:
            dlg_node = DialogueNode(
                speaker=speaker,
                text_preview=dialogue_text,
                scene_position=i,
            )
            graph.add_dialogue(dlg_node)

    stats = graph.summary()
    logger.info(
        f"Graph RAG: Built graph with {stats['total_nodes']} nodes, "
        f"{stats['total_edges']} edges "
        f"({stats['scenes']} scenes, {stats['characters']} characters, "
        f"{stats['dialogues']} dialogues)"
    )

    return graph

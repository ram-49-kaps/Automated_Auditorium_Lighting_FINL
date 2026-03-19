"""
Graph RAG Storage — In-memory NetworkX graph for scene relationships.
"""

import logging
from typing import Dict, Any, List, Optional

try:
    import networkx as nx
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False

from .graph_schema import (
    SceneNode, CharacterNode, DialogueNode,
    SCENE_FOLLOWS_SCENE, SCENE_HAS_CHARACTER,
    CHARACTER_SPEAKS, SCENE_HAS_EMOTION, DIALOGUE_IN_SCENE,
)

logger = logging.getLogger("phase_2.graph_rag")


class SceneGraph:
    """
    In-memory graph storing scene, character, and emotion relationships.
    Uses NetworkX DiGraph under the hood.
    """

    def __init__(self):
        if not NX_AVAILABLE:
            raise ImportError(
                "NetworkX is required for Graph RAG. Install with: pip install networkx"
            )
        self.graph = nx.DiGraph()
        self._scene_count = 0
        self._character_index: Dict[str, str] = {}  # name -> node_id

    # ------------------------------------------------------------------
    # Scene operations
    # ------------------------------------------------------------------

    def add_scene(self, scene: SceneNode) -> str:
        """Add a scene node to the graph. Returns the node ID."""
        node_id = f"scene_{scene.position}"
        self.graph.add_node(
            node_id,
            node_type="scene",
            scene_id=scene.scene_id,
            position=scene.position,
            text_preview=scene.text_preview,
            word_count=scene.word_count,
            primary_emotion=scene.primary_emotion,
            emotion_confidence=scene.emotion_confidence,
            secondary_emotion=scene.secondary_emotion,
            accent_emotion=scene.accent_emotion,
        )

        # Link to previous scene
        if scene.position > 0:
            prev_id = f"scene_{scene.position - 1}"
            if self.graph.has_node(prev_id):
                self.graph.add_edge(prev_id, node_id, edge_type=SCENE_FOLLOWS_SCENE)

        self._scene_count = max(self._scene_count, scene.position + 1)
        return node_id

    # ------------------------------------------------------------------
    # Character operations
    # ------------------------------------------------------------------

    def add_character(self, char: CharacterNode) -> str:
        """Add a character node. Returns the node ID."""
        node_id = f"char_{char.name.lower().replace(' ', '_')}"
        if self.graph.has_node(node_id):
            return node_id  # already exists

        self.graph.add_node(
            node_id,
            node_type="character",
            name=char.name,
            first_appearance=char.first_appearance,
        )
        self._character_index[char.name.lower()] = node_id
        return node_id

    def link_character_to_scene(self, char_name: str, scene_position: int):
        """Create SCENE_HAS_CHARACTER edge."""
        char_id = self._character_index.get(char_name.lower())
        scene_id = f"scene_{scene_position}"
        if char_id and self.graph.has_node(scene_id):
            self.graph.add_edge(scene_id, char_id, edge_type=SCENE_HAS_CHARACTER)

    # ------------------------------------------------------------------
    # Dialogue operations
    # ------------------------------------------------------------------

    def add_dialogue(self, dlg: DialogueNode) -> str:
        """Add a dialogue node and link to scene + character."""
        dlg_id = f"dlg_{dlg.scene_position}_{hash(dlg.text_preview) % 10000}"
        self.graph.add_node(
            dlg_id,
            node_type="dialogue",
            speaker=dlg.speaker,
            text_preview=dlg.text_preview,
            scene_position=dlg.scene_position,
        )

        # Link dialogue → scene
        scene_id = f"scene_{dlg.scene_position}"
        if self.graph.has_node(scene_id):
            self.graph.add_edge(dlg_id, scene_id, edge_type=DIALOGUE_IN_SCENE)

        # Link character → dialogue
        char_id = self._character_index.get(dlg.speaker.lower())
        if char_id:
            self.graph.add_edge(char_id, dlg_id, edge_type=CHARACTER_SPEAKS)

        return dlg_id

    # ------------------------------------------------------------------
    # Emotion operations
    # ------------------------------------------------------------------

    def update_scene_emotion(
        self, scene_position: int, primary: str, confidence: float,
        secondary: Optional[str] = None, accent: Optional[str] = None
    ):
        """Store detected emotion back into the scene node."""
        node_id = f"scene_{scene_position}"
        if self.graph.has_node(node_id):
            self.graph.nodes[node_id]["primary_emotion"] = primary
            self.graph.nodes[node_id]["emotion_confidence"] = confidence
            self.graph.nodes[node_id]["secondary_emotion"] = secondary
            self.graph.nodes[node_id]["accent_emotion"] = accent

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def get_scene(self, position: int) -> Optional[Dict[str, Any]]:
        """Get scene node data by position."""
        node_id = f"scene_{position}"
        if self.graph.has_node(node_id):
            return dict(self.graph.nodes[node_id])
        return None

    def get_previous_scenes(self, position: int, count: int = 3) -> List[Dict[str, Any]]:
        """Get the N preceding scene nodes (most recent first)."""
        results = []
        for i in range(position - 1, max(position - 1 - count, -1), -1):
            scene = self.get_scene(i)
            if scene:
                results.append(scene)
        return results

    def get_characters_in_scene(self, scene_position: int) -> List[str]:
        """Get character names linked to a scene."""
        scene_id = f"scene_{scene_position}"
        if not self.graph.has_node(scene_id):
            return []

        chars = []
        for _, target, data in self.graph.edges(scene_id, data=True):
            if data.get("edge_type") == SCENE_HAS_CHARACTER:
                node_data = self.graph.nodes.get(target, {})
                if node_data.get("node_type") == "character":
                    chars.append(node_data.get("name", ""))
        return chars

    def get_character_emotion_history(self, char_name: str) -> List[Dict[str, Any]]:
        """Get all scenes where a character appeared, with their emotions."""
        char_id = self._character_index.get(char_name.lower())
        if not char_id:
            return []

        history = []
        # Find all scenes linked to this character
        for source, _, data in self.graph.in_edges(char_id, data=True):
            if data.get("edge_type") == SCENE_HAS_CHARACTER:
                scene_data = self.graph.nodes.get(source, {})
                if scene_data.get("node_type") == "scene" and scene_data.get("primary_emotion"):
                    history.append({
                        "position": scene_data.get("position"),
                        "emotion": scene_data.get("primary_emotion"),
                        "confidence": scene_data.get("emotion_confidence", 0),
                    })

        return sorted(history, key=lambda x: x.get("position", 0))

    def summary(self) -> Dict[str, int]:
        """Return graph statistics."""
        nodes_by_type = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("node_type", "unknown")
            nodes_by_type[t] = nodes_by_type.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "scenes": nodes_by_type.get("scene", 0),
            "characters": nodes_by_type.get("character", 0),
            "dialogues": nodes_by_type.get("dialogue", 0),
        }

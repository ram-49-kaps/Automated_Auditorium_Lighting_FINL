"""
Phase 2 Graph RAG — Cross-scene context for emotion analysis.

Usage:
    from phase_2.graph_rag import build_scene_graph, retrieve_emotion_context

    graph = build_scene_graph(scenes)
    context = retrieve_emotion_context(graph, scene_position=2)
"""

from .graph_builder import build_scene_graph
from .graph_retriever import retrieve_emotion_context
from .graph_storage import SceneGraph

__all__ = [
    "build_scene_graph",
    "retrieve_emotion_context",
    "SceneGraph",
]

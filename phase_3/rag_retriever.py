"""
Phase 3 RAG Retriever (LangChain + FAISS)
Exposes the Auditorium and Semantics knowledge bases to the rest of the system.
"""

import os
from typing import Dict, List, Any
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Define paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.join(BASE_DIR, "rag")
AUDITORIUM_INDEX = os.path.join(RAG_DIR, "auditorium")
SEMANTICS_INDEX = os.path.join(RAG_DIR, "lighting_semantics")

class Phase3Retriever:
    """
    The official interface for Phase 3.
    Use this class to query physical hardware or design rules.
    """
    
    def __init__(self):
        print("📥 Initializing Phase 3 RAG Engine...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.auditorium_db = self._load_index(AUDITORIUM_INDEX)
        self.semantics_db = self._load_index(SEMANTICS_INDEX)
        
    def _load_index(self, path: str):
        try:
            if os.path.exists(path):
                return FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
            else:
                print(f"⚠️ Warning: Index not found at {path}")
                return None
        except Exception as e:
            print(f"❌ Error loading index {path}: {e}")
            return None

    def retrieve_auditorium_context(self, query: str, k: int = 5) -> List[Dict]:
        """
        Query the physical hardware available.
        Args:
            query: Natural language description (e.g. "spotlight for podium")
            k: Number of fixtures to trigger
        Returns:
            List of fixture metadata files
        """
        if not self.auditorium_db:
            return []
            
        docs = self.auditorium_db.similarity_search(query, k=k)
        return [doc.metadata for doc in docs]

    def retrieve_semantics_context(self, emotion: str, script_type: str, k: int = 3) -> List[Dict]:
        """
        Query the design rules.
        Args:
            emotion: "fear", "joy", etc.
            script_type: "drama", "formal", etc.
        Returns:
            List of design rule metadata files
        """
        if not self.semantics_db:
            return []
            
        query = f"{emotion} {script_type}"
        docs = self.semantics_db.similarity_search(query, k=k)
        return [doc.metadata for doc in docs]

    def retrieve_palette(self, emotion: str) -> Dict[str, Any]:
        """
        Adapter method for Phase 4: Retrieve a formatted palette for rule-based generation.
        Uses RAG FAISS index. Falls back to SimpleRetriever defaults if no valid match found.
        """
        emotion_lower = emotion.lower().strip()
        
        # === FAISS RETRIEVAL ===
        # Search for the matching emotion rule (k=3 to allow validation)
        results = self.retrieve_semantics_context(emotion_lower, "general", k=3)
        
        # Find the result that actually matches this emotion
        rule = None
        semantics = {}
        
        for r in results:
            if r.get("context_type") == "emotion" and r.get("context_value", "").lower() == emotion_lower:
                rule = r
                semantics = r.get("rules", {})
                break
        
        # If no exact match found, try the first emotion-type result anyway
        if rule is None:
            for r in results:
                if r.get("context_type") == "emotion":
                    rule = r
                    semantics = r.get("rules", {})
                    print(f"⚠️  No exact RAG match for '{emotion_lower}', using closest: '{r.get('context_value')}'")
                    break
        
        # If still nothing, return empty (Phase 4 SimpleRetriever handles fallback)
        if not semantics:
            print(f"No RAG rule found for '{emotion}', falling back to defaults")
            return {}
        
        # Convert Phase 3 Schema → Phase 4 Palette Format
        palette = {}
        
        # Color
        if "color" in semantics:
            colors = semantics["color"].get("palettes", [])
            palette["primary_colors"] = [{"name": c} for c in colors]
            palette["color_temperature"] = semantics["color"].get("temperature", "neutral")
            
        # Intensity
        if "intensity" in semantics:
            r = semantics["intensity"].get("preferred_range", [0.5, 0.5])
            avg_int = sum(r) / len(r)
            palette["intensity"] = {"default": int(avg_int * 100)}
            
        # Transitions
        if "transitions" in semantics:
            speed = semantics["transitions"].get("speed", "medium")
            speed_map = {"instant": 0.1, "fast": 0.5, "medium": 2.0, "slow": 4.0}
            duration = speed_map.get(speed, 2.0)
            
            pref_types = semantics["transitions"].get("preferred_types", ["fade"])
            trans_type = pref_types[0] if pref_types else "fade"
            
            palette["transition"] = {"type": trans_type, "duration": duration}
            
        return palette

    def build_context_for_llm(self, emotion: str, scene_text: str) -> str:
        """
        Adapter method for Phase 4: Build a text blob for the LLM prompt.
        """
        # 1. Get Semantic Rules
        rules = self.retrieve_semantics_context(emotion, "general", k=3)
        
        # 2. Get Hardware Context (maybe search for keywords in scene text?)
        fixtures = self.retrieve_auditorium_context(scene_text, k=2)
        
        context_lines = []
        context_lines.append(f"--- DESIGN RULES FOR EMOTION: {emotion.upper()} ---")
        for r in rules:
            src = r.get('source', 'Unknown')
            ctx = r.get('context_value', '')
            # Flatten the rule dict for the LLM
            context_lines.append(f"Rule ({src}): When {ctx}, use {r.get('rules', {})}")
            
        context_lines.append(f"\n--- AVAILABLE HARDWARE RELEVANT TO SCENE ---")
        for f in fixtures:
            context_lines.append(f"Fixture: {f.get('fixture_type')} at {f.get('position', 'unknown')}")
            
        return "\n".join(context_lines)

# Singleton
_instance = None

def get_retriever():
    global _instance
    if _instance is None:
        _instance = Phase3Retriever()
    return _instance
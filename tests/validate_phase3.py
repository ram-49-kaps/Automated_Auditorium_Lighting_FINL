"""
Phase 3 Validation Script
Verifies that the RAG system correctly retrieves:
1. Physical fixtures (from Auditorium Index)
2. Design rules (from Semantics Index)
Without making any decisions (as per strict rules).
"""

import os
import json
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Paths
RAG_DIR = "rag"
AUDITORIUM_INDEX = os.path.join(RAG_DIR, "auditorium")
SEMANTICS_INDEX = os.path.join(RAG_DIR, "lighting_semantics")

def load_vector_stores():
    print("📥 Loading Vector Stores...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    try:
        auditorium_db = FAISS.load_local(AUDITORIUM_INDEX, embeddings, allow_dangerous_deserialization=True)
        semantics_db = FAISS.load_local(SEMANTICS_INDEX, embeddings, allow_dangerous_deserialization=True)
        return auditorium_db, semantics_db
    except Exception as e:
        print(f"❌ Error loading indexes: {e}")
        return None, None

def print_result(title, docs):
    print(f"\n   --- {title} ---")
    if not docs:
        print("   (No results found)")
        return
        
    for i, doc in enumerate(docs):
        # We only print the metadata to prove we have the structured data
        meta = doc.metadata
        if "fixture_id" in meta:
            # It's a fixture
            print(f"   {i+1}. [{meta['group_id']}] {meta['fixture_id']} ({meta['fixture_type']})")
        elif "context_type" in meta:
            # It's a rule
            print(f"   {i+1}. [Rule] {meta['context_type']}={meta['context_value']} (Priority: {meta['priority']})")
            print(f"      -> Suggests: {meta.get('_comment', '')}")

def run_test_query(name, scene_desc, emotion, script_type, auditorium_db, semantics_db):
    print(f"\n🧪 TEST QUERY: {name}")
    print(f"   Input: '{scene_desc}' | Emotion: {emotion} | Type: {script_type}")
    
    # 1. Query Auditorium (Physical possibilities)
    # We search for fixtures relevant to the description
    fixture_results = auditorium_db.similarity_search(scene_desc, k=5)
    
    # 2. Query Semantics (Design biases)
    # We search for rules relevant to the emotion AND script type
    # Construct a query string for the semantics RAG
    semantics_query = f"{emotion} {script_type}"
    rule_results = semantics_db.similarity_search(semantics_query, k=3)
    
    print_result("Retrieved Fixtures (Physical)", fixture_results)
    print_result("Retrieved Semantics (Design Rules)", rule_results)
    print("-" * 60)

def main():
    auditorium_db, semantics_db = load_vector_stores()
    if not auditorium_db:
        return

    # TEST 1: The Scary Scene (Emotion driven)
    run_test_query(
        name="Horror Scene",
        scene_desc="A dark, creepy ghost appears in the fog. Sudden flashes.",
        emotion="fear",
        script_type="drama",
        auditorium_db=auditorium_db,
        semantics_db=semantics_db
    )

    # TEST 2: The Formal Speech (Neutral/Formal driven)
    run_test_query(
        name="Dean's Speech",
        scene_desc="The Dean stands at the podium for a formal address. Bright and clear.",
        emotion="neutral",
        script_type="formal_event",
        auditorium_db=auditorium_db,
        semantics_db=semantics_db
    )

    # TEST 3: The Party/Concert (Color/Action driven)
    run_test_query(
        name="Celebration Dance",
        scene_desc="A high energy dance number with colorful moving lights hitting the floor.",
        emotion="joy",
        script_type="musical",
        auditorium_db=auditorium_db,
        semantics_db=semantics_db
    )

if __name__ == "__main__":
    main()

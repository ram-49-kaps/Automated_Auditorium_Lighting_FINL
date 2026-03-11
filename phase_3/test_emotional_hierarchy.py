
import sys
import os

# Ensure we can import modules
sys.path.append(os.getcwd())

from phase_3.rag_retriever import get_retriever

def test_hierarchy():
    print("🧠 Testing Phase 3 Emotional Hierarchy Retrieval...")
    retriever = get_retriever()
    
    # query for "Nostalgia" (Primary)
    print("\n🔍 Query 1: 'Nostalgia' (Expected: Warm, Sepia, Additive Blend)")
    docs = retriever.retrieve_semantics_context(emotion="nostalgia", script_type="drama")
    
    for d in docs:
        meta = d  # The retriever returns metadata dicts directly
        print(f"   - Found Rule: {meta.get('context_value')} (Source: {meta.get('source')})")
        print(f"     Blending: {meta.get('blending_mode')} | Layers: {meta.get('layer_compatibility')}")
        print(f"     Color Rules: {meta.get('rules', {}).get('color', {}).get('temperature')}")

    # query for "Hope" (Secondary)
    print("\n🔍 Query 2: 'Hope' (Expected: Cyan/Gold, Secondary Layer)")
    docs = retriever.retrieve_semantics_context(emotion="hope", script_type="drama")
    
    for d in docs:
        meta = d  # The retriever returns metadata dicts directly
        print(f"   - Found Rule: {meta.get('context_value')} (Source: {meta.get('source')})")
        print(f"     Blending: {meta.get('blending_mode')} | Layers: {meta.get('layer_compatibility')}")

if __name__ == "__main__":
    test_hierarchy()

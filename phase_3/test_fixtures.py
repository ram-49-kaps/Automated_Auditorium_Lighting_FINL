
import sys
import os
sys.path.append(os.getcwd())
from phase_3.rag_retriever import get_retriever

def test_fixtures():
    print("💡 Testing Phase 3 Fixture Retrieval...")
    retriever = get_retriever()
    
    # query for "spotlight"
    print("\n🔍 Query: 'spotlight'")
    docs = retriever.retrieve_auditorium_context(query="spotlight", k=3)
    
    if not docs:
        print("❌ FAILED: No fixtures found for 'spotlight'")
        sys.exit(1)
        
    for d in docs:
        print(f"   - Found Fixture: {d.get('fixture_id')} ({d.get('fixture_type')})")
        
    # query for "wash"
    print("\n🔍 Query: 'wash'")
    docs = retriever.retrieve_auditorium_context(query="wash", k=3)
    if not docs:
        print("❌ FAILED: No fixtures found for 'wash'")
        sys.exit(1)

    for d in docs:
        print(f"   - Found Fixture: {d.get('fixture_id')} ({d.get('fixture_type')})")
        
    print("\n✅ SUCCESS: Fixture retrieval working.")

if __name__ == "__main__":
    test_fixtures()

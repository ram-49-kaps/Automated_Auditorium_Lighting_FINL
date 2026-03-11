import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from backend.pipeline_runner import run_pipeline

async def mock_callback(data):
    print(f"Phase {data.get('phase')}: {data.get('detail', data.get('status'))}")

if __name__ == "__main__":
    asyncio.run(run_pipeline("test1", "data/raw_scripts/Event-Schedule-Test.txt", mock_callback))

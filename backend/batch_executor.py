"""
Phase 6 — Batch Executor
Processes multiple scripts sequentially through the pipeline.
"""

import os
import glob
from typing import List, Dict
from pathlib import Path


class BatchExecutor:
    """Execute the pipeline on multiple scripts in a directory."""
    
    def __init__(self, input_dir: str = "data/raw_scripts", output_dir: str = "data/jobs"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
    
    def discover_scripts(self, extensions: List[str] = None) -> List[Path]:
        """Find all script files in the input directory."""
        if extensions is None:
            extensions = [".txt", ".pdf", ".docx"]
        
        scripts = []
        for ext in extensions:
            scripts.extend(self.input_dir.glob(f"*{ext}"))
        
        return sorted(scripts)
    
    def execute_batch(self, scripts: List[Path] = None) -> Dict:
        """
        Run the pipeline on each script sequentially.
        
        Returns:
            Dict with per-script results summary.
        """
        if scripts is None:
            scripts = self.discover_scripts()
        
        results = {
            "total": len(scripts),
            "succeeded": 0,
            "failed": 0,
            "results": [],
        }
        
        for script_path in scripts:
            print(f"\n{'='*50}")
            print(f"Processing: {script_path.name}")
            print(f"{'='*50}")
            
            try:
                # Import here to avoid circular imports
                from backend.pipeline_runner import run_pipeline
                import uuid
                
                job_id = str(uuid.uuid4())
                job_dir = self.output_dir / job_id
                job_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy script to job dir
                import shutil
                shutil.copy(script_path, job_dir / script_path.name)
                
                # Run pipeline
                result = run_pipeline(str(job_dir / script_path.name), str(job_dir))
                
                results["succeeded"] += 1
                results["results"].append({
                    "filename": script_path.name,
                    "job_id": job_id,
                    "status": "success",
                })
                
            except Exception as e:
                results["failed"] += 1
                results["results"].append({
                    "filename": script_path.name,
                    "status": "failed",
                    "error": str(e),
                })
        
        print(f"\n{'='*50}")
        print(f"Batch complete: {results['succeeded']}/{results['total']} succeeded")
        print(f"{'='*50}")
        
        return results

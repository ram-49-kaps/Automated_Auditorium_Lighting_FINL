"""
Phase 6: Batch Executor

Handles batch execution of multiple scripts.
Batch logic lives ONLY in this file.
"""

import logging
from typing import List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config_models import PipelineConfig, PipelineResult, PhaseStatus
from .pipeline_runner import PipelineRunner

logger = logging.getLogger("phase_6.batch")


class BatchExecutor:
    """
    Execute pipeline on multiple scripts.
    
    Supports:
    - Single script execution
    - Multi-script batch execution
    - Sequential or parallel execution
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize batch executor.
        
        Args:
            config: Pipeline configuration applied to all scripts
        """
        self.config = config or PipelineConfig()
    
    def run_single(self, script_path: str) -> PipelineResult:
        """
        Execute pipeline on a single script.
        
        Args:
            script_path: Path to script file
            
        Returns:
            PipelineResult for the script
        """
        runner = PipelineRunner(self.config)
        return runner.run(script_path)
    
    def run_batch(
        self, 
        script_paths: List[str],
        parallel: bool = False,
        max_workers: int = 4
    ) -> List[PipelineResult]:
        """
        Execute pipeline on multiple scripts.
        
        Args:
            script_paths: List of script file paths
            parallel: If True, execute scripts in parallel
            max_workers: Max parallel workers (if parallel=True)
            
        Returns:
            List of PipelineResult, one per script
        """
        logger.info(f"Batch execution started: {len(script_paths)} scripts")
        
        if parallel:
            return self._run_parallel(script_paths, max_workers)
        else:
            return self._run_sequential(script_paths)
    
    def _run_sequential(self, script_paths: List[str]) -> List[PipelineResult]:
        """Execute scripts sequentially"""
        results = []
        
        for i, script_path in enumerate(script_paths):
            logger.info(f"Processing script {i+1}/{len(script_paths)}: {script_path}")
            
            result = self.run_single(script_path)
            results.append(result)
            
            logger.info(
                f"Script {i+1} completed: {result.final_status.value} "
                f"in {result.total_duration_seconds:.2f}s"
            )
        
        return results
    
    def _run_parallel(
        self, 
        script_paths: List[str], 
        max_workers: int
    ) -> List[PipelineResult]:
        """Execute scripts in parallel"""
        results = [None] * len(script_paths)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.run_single, path): idx 
                for idx, path in enumerate(script_paths)
            }
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                    logger.info(
                        f"Script {idx+1} completed: "
                        f"{results[idx].final_status.value}"
                    )
                except Exception as e:
                    logger.error(f"Script {idx+1} failed: {e}")
                    results[idx] = PipelineResult(
                        script_path=script_paths[idx],
                        final_status=PhaseStatus.FAILED
                    )
        
        return results
    
    def run_directory(
        self, 
        directory: str,
        pattern: str = "*.txt",
        parallel: bool = False
    ) -> List[PipelineResult]:
        """
        Execute pipeline on all matching scripts in a directory.
        
        Args:
            directory: Directory containing script files
            pattern: Glob pattern for script files
            parallel: If True, execute in parallel
            
        Returns:
            List of PipelineResult
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        script_paths = sorted(str(p) for p in dir_path.glob(pattern))
        
        if not script_paths:
            logger.warning(f"No scripts matching '{pattern}' in {directory}")
            return []
        
        logger.info(f"Found {len(script_paths)} scripts in {directory}")
        return self.run_batch(script_paths, parallel=parallel)
    
    @staticmethod
    def summarize_results(results: List[PipelineResult]) -> dict:
        """
        Summarize batch execution results.
        
        Args:
            results: List of PipelineResult
            
        Returns:
            Summary dictionary
        """
        total = len(results)
        success = sum(1 for r in results if r.final_status == PhaseStatus.SUCCESS)
        failed = sum(1 for r in results if r.final_status == PhaseStatus.FAILED)
        total_duration = sum(r.total_duration_seconds for r in results)
        
        return {
            "total_scripts": total,
            "successful": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": total_duration / total if total > 0 else 0
        }

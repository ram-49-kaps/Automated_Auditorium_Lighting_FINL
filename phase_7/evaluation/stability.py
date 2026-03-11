"""
Phase 7 — Stability Metrics
Measures cross-run consistency for reproducibility analysis.
"""

import json
import os
import glob
from typing import Dict, List


def compute_cross_run_stability(trace_dir: str = "data/traces") -> float:
    """
    Compare multiple trace files to measure cross-run stability.
    
    Stability is the average determinism score across all pairs of runs.
    A fully deterministic system (rule-based) should score 1.0.
    
    Args:
        trace_dir: Directory containing trace JSON files
        
    Returns:
        float: Stability score 0.0 to 1.0
    """
    trace_files = sorted(glob.glob(os.path.join(trace_dir, "trace_*.json")))
    
    if len(trace_files) < 2:
        return 1.0  # Cannot measure with fewer than 2 runs
    
    # Load all traces
    traces = []
    for tf in trace_files:
        try:
            with open(tf) as f:
                traces.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    
    if len(traces) < 2:
        return 1.0
    
    # Compare output hashes across runs
    similarities = []
    for i in range(len(traces)):
        for j in range(i + 1, len(traces)):
            sim = _compare_traces(traces[i], traces[j])
            similarities.append(sim)
    
    return sum(similarities) / len(similarities) if similarities else 1.0


def _compare_traces(trace_a: Dict, trace_b: Dict) -> float:
    """Compare two traces and return similarity score."""
    entries_a = trace_a.get("entries", [])
    entries_b = trace_b.get("entries", [])
    
    if not entries_a or not entries_b:
        return 0.0
    
    # Match by scene_id
    map_a = {e["scene_id"]: e for e in entries_a}
    map_b = {e["scene_id"]: e for e in entries_b}
    
    common = set(map_a.keys()) & set(map_b.keys())
    if not common:
        return 0.0
    
    matches = 0
    for sid in common:
        if map_a[sid].get("output_hash") == map_b[sid].get("output_hash"):
            matches += 1
    
    return matches / len(common)

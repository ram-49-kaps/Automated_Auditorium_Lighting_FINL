"""
Phase 7 — Consistency Metrics
Measures Jaccard similarity, determinism, and drift between consecutive scenes.
"""

from typing import Dict, List, Set


def extract_group_ids(instruction: Dict) -> Set[str]:
    """Extract group IDs from a lighting instruction."""
    return {g.get("group_id", "") for g in instruction.get("groups", [])}


def compute_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """
    Compute Jaccard similarity between two sets.
    
    Returns:
        float: 0.0 (no overlap) to 1.0 (identical)
    """
    if not set_a and not set_b:
        return 1.0
    
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    
    return intersection / union if union > 0 else 0.0


def compute_determinism_score(instructions_a: List[Dict], instructions_b: List[Dict]) -> float:
    """
    Compute determinism: how structurally identical two runs are.
    Compares group IDs, intensities (within epsilon), and transition types.
    
    Returns:
        float: 1.0 = fully deterministic, 0.0 = completely different
    """
    if len(instructions_a) != len(instructions_b):
        return 0.0
    
    epsilon = 0.01  # Intensity tolerance
    matches = 0
    total = 0
    
    for a, b in zip(instructions_a, instructions_b):
        groups_a = {g.get("group_id"): g for g in a.get("groups", [])}
        groups_b = {g.get("group_id"): g for g in b.get("groups", [])}
        
        all_groups = set(groups_a.keys()) | set(groups_b.keys())
        
        for gid in all_groups:
            total += 1
            ga = groups_a.get(gid, {})
            gb = groups_b.get(gid, {})
            
            if not ga or not gb:
                continue
            
            # Check intensity
            ia = ga.get("parameters", {}).get("intensity", 0)
            ib = gb.get("parameters", {}).get("intensity", 0)
            
            # Check transition type
            ta = ga.get("transition", {}).get("type", "")
            tb = gb.get("transition", {}).get("type", "")
            
            if abs(ia - ib) <= epsilon and ta == tb:
                matches += 1
    
    return matches / total if total > 0 else 1.0


def compute_drift_score(instructions: List[Dict]) -> float:
    """
    Compute drift: average change in global intensity between consecutive scenes.
    
    0 = stable (intensity is exactly the same)
    1 = chaotic (intensity swings by 100% every scene)
    
    Returns:
        float: Drift score 0.0 to 1.0
    """
    if len(instructions) < 2:
        return 0.0
    
    drifts = []
    for i in range(len(instructions) - 1):
        groups_a = instructions[i].get("groups", [])
        avg_a = sum(g.get("parameters", {}).get("intensity", 0) for g in groups_a) / max(len(groups_a), 1)
        
        groups_b = instructions[i+1].get("groups", [])
        avg_b = sum(g.get("parameters", {}).get("intensity", 0) for g in groups_b) / max(len(groups_b), 1)
        
        # Absolute difference in intensity (0-100), divided by 100 to get 0.0-1.0 scale
        drifts.append(abs(avg_a - avg_b) / 100.0)
    
    return sum(drifts) / len(drifts)

"""
Phase 7 — Coverage Metrics
Measures group utilization and parameter diversity.
"""

from typing import Dict, List, Set


def compute_group_coverage(instructions: List[Dict], available_groups: Set[str]) -> float:
    """
    Compute group coverage ratio: |groups_used| / |available_groups|
    
    Args:
        instructions: List of lighting instructions
        available_groups: Set of all possible group IDs
        
    Returns:
        float: Coverage ratio 0.0 to 1.0
    """
    used_groups = set()
    for instr in instructions:
        for g in instr.get("groups", []):
            used_groups.add(g.get("group_id", ""))
    
    if not available_groups:
        return 0.0
    
    return len(used_groups & available_groups) / len(available_groups)


def compute_parameter_diversity(instructions: List[Dict]) -> float:
    """
    Compute parameter diversity: how much intensity varies across instructions.
    
    Returns:
        float: Standard deviation of intensities (higher = more diverse)
    """
    intensities = []
    for instr in instructions:
        scene_intensities = []
        for g in instr.get("groups", []):
            val = g.get("parameters", {}).get("intensity")
            if val is not None:
                scene_intensities.append(val)
        if scene_intensities:
            intensities.append(sum(scene_intensities) / len(scene_intensities))
    
    if len(intensities) < 2:
        return 0.0
    
    mean = sum(intensities) / len(intensities)
    variance = sum((x - mean) ** 2 for x in intensities) / len(intensities)
    return variance ** 0.5

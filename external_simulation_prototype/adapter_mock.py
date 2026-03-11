"""
Stateless Adapter Mock
Demonstrates how to control the High-Fidelity Simulation.
Rules:
1. No internal state.
2. No timelines / orchestration.
3. Instantaneous Application.

Usage:
    This file would typically send the instruction to the visualization 
    via WebSocket or API. For this prototype, it prints the specific 
    Physical UIDs and Values needed.
"""

from typing import Dict, Any, List
from .world.layout import get_fixtures_for_group

def apply_instruction_instant(instruction: Dict[str, Any]):
    """
    Takes a LightingInstruction (Group Level) 
    and IMMEDIATELY resolves it to Physical Fixtures.
    """
    
    print(f"\n[ADAPTER] Processing Snapshot for Scene: {instruction.get('scene_id')}")
    
    updates = []
    
    # Iterate groups in the instruction
    for group_cmd in instruction.get("groups", []):
        group_id = group_cmd["group_id"]
        params = group_cmd["parameters"]
        
        # 1. Resolve Logical -> Physical (One Way)
        physical_fixtures = get_fixtures_for_group(group_id)
        
        if not physical_fixtures:
            print(f"  Warning: No hardware found for group '{group_id}'")
            continue
            
        print(f"  Group '{group_id}' maps to {len(physical_fixtures)} units:")
        
        # 2. Derive Physical Parameters
        # Note: We do NOT handle transitions here. We just take the target value.
        intensity = params.get("intensity", 0.0)
        color = params.get("color", "#ffffff") # Assuming pre-resolved hex for this mock
        
        # 3. Generate Hardware Commands
        for fix in physical_fixtures:
            cmd = {
                "uid": fix.uid,
                "intensity": intensity,
                "color": color,
                "fixture_type": fix.profile.model_name
            }
            updates.append(cmd)
            print(f"    -> {fix.uid} [{fix.profile.model_name}] = {intensity*100}% @ {color}")

    return updates

# --- Test Case (Does NOT run a loop/timeline) ---
if __name__ == "__main__":
    # Mock Phase 4 Output
    mock_instruction = {
        "scene_id": "TEST_SCENE_001",
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {"intensity": 0.8, "color": "#ffb347"} 
            },
            {
                "group_id": "specials",
                "parameters": {"intensity": 1.0, "color": "#0000ff"}
            }
        ]
    }
    
    apply_instruction_instant(mock_instruction)
    print("\n[ADAPTER] Done. In a real system, 'updates' list is sent to Visualizer/DMX.")

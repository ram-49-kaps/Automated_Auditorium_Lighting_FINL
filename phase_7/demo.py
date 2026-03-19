"""
Phase 7 Demo Script — Example Usage

Run this from the project root:
    python phase_7/demo.py
"""
import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase_7 import TraceLogger, MetricsEngine


def demo_trace_logging():
    """Demonstrate trace logging functionality."""
    print("\n" + "="*50)
    print("[DEMO 1] Trace Logging")
    print("="*50)
    
    output_dir = project_root / "data" / "traces"
    logger = TraceLogger(output_dir=output_dir, seed=42)
    
    scene = {
        "scene_id": "scene_001",
        "text": "Romeo enters dramatically",
        "emotion": {"primary": "anticipation"}
    }
    
    instruction = {
        "scene_id": "scene_001",
        "groups": [
            {"group_id": "FRONT_WASH", "parameters": {"intensity": 0.8, "color": "warm_amber"}},
            {"group_id": "BACK_LIGHT", "parameters": {"intensity": 0.4, "color": "cool_blue"}}
        ]
    }
    
    entry = logger.log_decision(scene, instruction)
    print(f"[OK] Logged decision for scene: {entry.scene_id}")
    print(f"     Run ID: {entry.run_id}")
    print(f"     Input hash: {entry.input_hash}")
    print(f"     Output hash: {entry.output_hash}")
    
    trace_file = logger.save()
    print(f"[SAVED] Trace saved to: {trace_file}")


def demo_metrics():
    """Demonstrate metrics computation."""
    print("\n" + "="*50)
    print("[DEMO 2] Metrics Computation")
    print("="*50)
    
    available_groups = {"FRONT_WASH", "BACK_LIGHT", "SIDE_FILL", "SPOT_1", "SPOT_2"}
    engine = MetricsEngine(available_groups=available_groups)
    
    instruction = {
        "scene_id": "scene_001",
        "groups": [
            {"group_id": "FRONT_WASH", "parameters": {"intensity": 0.8}, "transition": {"type": "fade"}},
            {"group_id": "BACK_LIGHT", "parameters": {"intensity": 0.4}, "transition": {"type": "fade"}},
            {"group_id": "SIDE_FILL", "parameters": {"intensity": 0.6}, "transition": {"type": "cut"}}
        ]
    }
    
    result = engine.evaluate_instruction(instruction)
    print(f"[METRICS] Coverage: {result['coverage']:.1%} of groups used")
    print(f"   Diversity:")
    print(f"     - Intensity range: {result['diversity']['intensity_range']:.2f}")
    print(f"     - Transition types: {result['diversity']['transition_types']}")
    print(f"     - Groups used: {result['diversity']['groups_used']}")


def demo_consistency():
    """Demonstrate consistency comparison."""
    print("\n" + "="*50)
    print("[DEMO 3] Consistency Check")
    print("="*50)
    
    engine = MetricsEngine()
    
    instruction_a = {
        "groups": [
            {"group_id": "FRONT_WASH", "parameters": {"intensity": 0.80}, "transition": {"type": "fade"}}
        ]
    }
    
    instruction_b = {
        "groups": [
            {"group_id": "FRONT_WASH", "parameters": {"intensity": 0.82}, "transition": {"type": "fade"}}
        ]
    }
    
    comparison = engine.evaluate_pair(instruction_a, instruction_b)
    print(f"[SCORE] Determinism Score: {comparison['determinism_score']:.2f}")
    print(f"   (1.0 = identical, 0.0 = completely different)")
    print(f"   Breakdown:")
    print(f"     - Group match: {comparison['breakdown']['group_match']:.2f}")
    print(f"     - Intensity epsilon: +/-{comparison['breakdown']['intensity_epsilon']}")


def demo_with_real_files():
    """Load and analyze real fixture files."""
    print("\n" + "="*50)
    print("[DEMO 4] Loading Real Files")
    print("="*50)
    
    fixture_dir = project_root / "tests" / "fixtures" / "phase_7"
    scene_file = fixture_dir / "sample_scene.json"
    instr_file = fixture_dir / "sample_instruction.json"
    
    if scene_file.exists() and instr_file.exists():
        with open(scene_file) as f:
            scene = json.load(f)
        with open(instr_file) as f:
            instruction = json.load(f)
        
        print(f"[OK] Loaded scene: {scene['scene_id']}")
        print(f"[OK] Loaded instruction with {len(instruction['groups'])} groups")
        
        engine = MetricsEngine(available_groups={"FRONT_WASH", "BACK_LIGHT", "SIDE_FILL"})
        result = engine.evaluate_instruction(instruction)
        print(f"[METRICS] Coverage: {result['coverage']:.1%}")
    else:
        print("[WARNING] Fixture files not found.")


if __name__ == "__main__":
    print("Phase 7 - Evaluation & Metrics Demo")
    print("="*50)
    
    demo_trace_logging()
    demo_metrics()
    demo_consistency()
    demo_with_real_files()
    
    print("\n" + "="*50)
    print("[COMPLETE] Demo finished!")
    print("="*50)

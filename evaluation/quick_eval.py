import sys
import json
import argparse
from pathlib import Path

# Add root to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase_7.metrics import MetricsEngine

def main():
    parser = argparse.ArgumentParser(description="Run surface-level evaluation metrics on a processed JSON script.")
    parser.add_argument("filepath", type=str, help="Path to the processed JSON (e.g., data/standardized_output/Script-5_processed.json)")
    args = parser.parse_args()
    
    filepath = Path(args.filepath)
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
        
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        sys.exit(1)
        
    scenes = data.get("scenes", [])
    if not scenes:
        print("No scenes found in the JSON file.")
        sys.exit(1)
        
    # Extract only the lighting instructions for the Metrics Engine
    instructions = data.get("lighting_instructions", [])
    emotions = []
    
    for scene in scenes:
            
        # Tally emotions for diversity
        emotion_data = scene.get("emotion", "neutral")
        if isinstance(emotion_data, dict):
            primary_emotion = emotion_data.get("primary_emotion", "neutral")
        else:
            primary_emotion = str(emotion_data)
        emotions.append(primary_emotion)
        
    # Display Surface-Level Metrics
    print(f"\n==================================================")
    print(f"📊 QUICK EVALUATION REPORT: {filepath.name}")
    print(f"==================================================")
    
    # 1. Pipeline Success
    print(f"Total Scenes Processed: {len(scenes)}")
    print(f"Total Lighting Cues Generated: {len(instructions)}")
    
    # 2. Emotion Diversity
    unique_emotions = set(emotions)
    non_neutral = len([e for e in emotions if e != "neutral"])
    diversity_score = (non_neutral / len(emotions)) * 100 if emotions else 0
    print(f"\n🎭 Emotion Analysis")
    print(f"Unique Emotions Detected: {len(unique_emotions)}")
    print(f"Non-Neutral Diversity Score: {diversity_score:.1f}%")
    if unique_emotions:
        print(f"Emotions present: {', '.join(unique_emotions)}")
        
    # 3. Lighting Metrics (Phase 7)
    print(f"\n💡 Lighting Phase Metrics")
    try:
        engine = MetricsEngine()
        report = engine.generate_report(instructions)
        print(f"Coverage Score (Fixtures used vs total): {report.get('coverage', 0)}")
        print(f"Parameter Diversity: {report.get('parameter_diversity', 0)}")
        print(f"Drift Score (Between Scenes): {report.get('drift_score', 0)}")
        print(f"Intensity Range: {report.get('intensity_range', (0,0))}")
        print(f"Transition Types Used: {', '.join(report.get('transition_types', []))}")
        print(f"Determinism Score: {report.get('determinism', 1.0)}")
    except Exception as e:
        print(f"Phase 7 Metrics evaluation failed: {e}")
        
    print(f"==================================================\n")

if __name__ == "__main__":
    main()

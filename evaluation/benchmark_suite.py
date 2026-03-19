import os
import sys
import glob
import json
from pathlib import Path

# Add root to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase_7.metrics import MetricsEngine

def main():
    print("==================================================")
    print("🚀 PIPELINE BENCHMARK SUITE")
    print("==================================================\n")
    
    output_dir = Path("data/standardized_output")
    json_files = glob.glob(str(output_dir / "*_processed.json"))
    
    if not json_files:
        print(f"No processed JSON files found in {output_dir}")
        sys.exit(1)
        
    engine = MetricsEngine()
    total_scenes = 0
    total_cues = 0
    aggregate_drift = []
    aggregate_diversity = []
    
    print(f"Found {len(json_files)} processed scripts to benchmark.\n")
    
    for fp in json_files:
        path = Path(fp)
        try:
            with open(path, "r") as f:
                data = json.load(f)
                
            scenes = data.get("scenes", [])
            instructions = data.get("lighting_instructions", [])
            metadata = data.get("metadata", {})
            
            num_scenes = len(scenes)
            num_cues = len(instructions)
            
            total_scenes += num_scenes
            total_cues += num_cues
            
            report = engine.generate_report(instructions)
            drift = report.get("drift_score", 0)
            diversity = report.get("parameter_diversity", 0)
            
            aggregate_drift.append(drift)
            aggregate_diversity.append(diversity)
            
            print(f"📄 {metadata.get('source_file', path.name)} ({metadata.get('genre', 'unknown')})")
            print(f"   Scenes: {num_scenes:03d} | Cues: {num_cues:03d}")
            print(f"   Dominant Emotion: {metadata.get('dominant_emotion', 'neutral')}")
            print(f"   Drift Score: {drift:.3f} | Diversity: {diversity:.3f}")
            print("-" * 50)
            
        except Exception as e:
            print(f"Failed to process {path.name}: {e}")
            
    # Print Aggregates
    print("\n==================================================")
    print("📈 AGGREGATE BENCHMARK RESULTS")
    print("==================================================")
    print(f"Scripts Evaluated: {len(json_files)}")
    print(f"Total Scenes:      {total_scenes}")
    print(f"Total Cues:        {total_cues}")
    
    avg_drift = sum(aggregate_drift) / len(aggregate_drift) if aggregate_drift else 0
    avg_div = sum(aggregate_diversity) / len(aggregate_diversity) if aggregate_diversity else 0
    
    print(f"Average Drift:     {avg_drift:.3f} (Lower = smoother transitions)")
    print(f"Average Diversity: {avg_div:.3f} (Higher = richer emotional lighting)")
    print("==================================================\n")

if __name__ == "__main__":
    main()

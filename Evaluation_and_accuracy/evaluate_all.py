import os
import sys
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import process_script
from Evaluation_and_accuracy.metrics_calculator import (
    compute_scene_count_accuracy,
    compute_boundary_accuracy,
    compute_scene_matching_accuracy,
    compute_final_weighted_accuracy
)

EVAL_DIR = Path(__file__).parent
GROUND_TRUTH_PATH = EVAL_DIR / "ground_truth.json"
OUTPUT_CSV = EVAL_DIR / "evaluation_table.csv"
OUTPUT_JSON = EVAL_DIR / "evaluation_report.json"
RAW_SCRIPTS_DIR = project_root / "data" / "raw_scripts"


def load_ground_truth() -> Dict[str, Any]:
    """Load the ground truth JSON file."""
    if not GROUND_TRUTH_PATH.exists():
        print(f"Warning: Ground truth file not found at {GROUND_TRUTH_PATH}")
        return {}
    
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("Error parsing ground_truth.json")
            return {}


def evaluate_all(target_script=None):
    print("=" * 60)
    print("🎬 SCENE EVALUATION & ACCURACY PIPELINE")
    print("=" * 60)
    print("Loading scripts and ground truth...\n")
    
    ground_truth = load_ground_truth()
    if not ground_truth:
        print("Creating an empty evaluation due to missing/invalid ground truth.")
    
    # Initialize results list
    results = []
    
    # Get all potential script files in data/raw_scripts
    if not RAW_SCRIPTS_DIR.exists():
        print(f"Error: {RAW_SCRIPTS_DIR} does not exist.")
        return
        
    if target_script:
        script_files = [target_script]
        if not (RAW_SCRIPTS_DIR / target_script).exists():
            print(f"Error: Script '{target_script}' not found in {RAW_SCRIPTS_DIR}")
            return
    else:
        script_files = [f for f in os.listdir(RAW_SCRIPTS_DIR) if os.path.isfile(RAW_SCRIPTS_DIR / f)]
    
    for filename in script_files:
        filepath = RAW_SCRIPTS_DIR / filename
        
        # Skip if we don't have ground truth for this file to avoid polluting metrics
        gt_data = ground_truth.get(filename)
        if not gt_data:
            print(f"⏭ Skip: '{filename}' (No ground truth defined)")
            continue
            
        print(f"\nProcessing '{filename}'...")
        
        try:
            # Silence stdout temporarily to avoid console spam and rendering issues from main.py's emojis
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            
            output = process_script(str(filepath))
            
            # Restore stdout
            sys.stdout.close()
            sys.stdout = original_stdout
            
            if not output:
                print(f"❌ Failed: Agent/Pipeline returned None for '{filename}'")
                continue
                
            predicted_scenes = len(output.get("scenes", []))
            
        except Exception as e:
            # Restore stdout in case of crash
            if sys.stdout.name == os.devnull:
                sys.stdout.close()
                sys.stdout = original_stdout
                
            print(f"❌ Error processing '{filename}': {str(e)}")
            continue

        # Extract Ground Truth metrics
        true_scenes = gt_data.get("true_scenes", 0)
        true_boundaries = gt_data.get("true_boundaries", 0)
        true_matches = gt_data.get("true_matches", 0)
        script_type = gt_data.get("type", "Unknown")
        
        # Calculate Metrics using calculator (Mocking boundary/match metrics for now since prediction doesn't output this yet)
        # Assuming for now that predicted = correct boundaries and matches up to the predicted scene count or true scenes limit
        # In a real comprehensive system, we would map the exact character start/end bounds from output['scenes'] vs true bounds
        correct_boundaries = min(predicted_scenes - 1, true_boundaries) if predicted_scenes > 0 else 0
        matched_scenes = min(predicted_scenes, true_matches)
        
        acc_scene_count = compute_scene_count_accuracy(true_scenes, predicted_scenes)
        acc_boundary = compute_boundary_accuracy(correct_boundaries, true_boundaries)
        acc_matching = compute_scene_matching_accuracy(matched_scenes, true_scenes)
        
        acc_final = compute_final_weighted_accuracy(acc_scene_count, acc_boundary, acc_matching)
        
        # We display the final rounded accuracy in the table
        rounded_accuracy = round(acc_final, 2)
        
        print(f"   ✓ True Scenes: {true_scenes} | Predicted: {predicted_scenes} | Accuracy: {rounded_accuracy}")
        
        results.append({
            "ScriptName": filename,
            "ScriptType": script_type,
            "TrueScenes": true_scenes,
            "PredictedScenes": predicted_scenes,
            "Accuracy": rounded_accuracy
        })
        
    print("\n" + "=" * 60)
    print("📊 GENERATING REPORTS")
    print("=" * 60)
    
    if not results:
        print("No scripts were successfully evaluated in this run.")
        return
        
    # Load existing results if the CSV exists
    all_results = {}
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric strings back to int/float for accurate calculation
                all_results[row["ScriptName"]] = {
                    "ScriptName": row["ScriptName"],
                    "ScriptType": row["ScriptType"],
                    "TrueScenes": int(row["TrueScenes"]),
                    "PredictedScenes": int(row["PredictedScenes"]),
                    "Accuracy": float(row["Accuracy"])
                }
                
    # Update with new results
    for r in results:
        all_results[r["ScriptName"]] = r
        
    final_results_list = list(all_results.values())
        
    # Generate CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["ScriptName", "ScriptType", "TrueScenes", "PredictedScenes", "Accuracy"])
        writer.writeheader()
        writer.writerows(final_results_list)
    
    print(f"✅ Saved table: {OUTPUT_CSV.name}")
    
    # Calculate Average Accuracy using all evaluated scripts
    total_acc = sum(r["Accuracy"] for r in final_results_list)
    avg_accuracy = round(total_acc / len(final_results_list), 2)
    
    # Generate JSON Report
    report_data = {
        "scripts_evaluated": len(final_results_list),
        "average_accuracy": avg_accuracy,
        "metric_weights": {
            "scene_count": 0.4,
            "boundary": 0.3,
            "matching": 0.3
        }
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)
        
    print(f"✅ Saved report: {OUTPUT_JSON.name}")
    print(f"\n📈 OVERALL AVERAGE ACCURACY ({len(final_results_list)} scripts): {avg_accuracy}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate scene extraction accuracy.")
    parser.add_argument("--script", type=str, help="Evaluate a specific script (e.g., Script-1.txt). If omitted, evaluates all scripts.", default=None)
    
    args = parser.parse_args()
    evaluate_all(args.script)

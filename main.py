"""
Main pipeline orchestration script (CLI)
Supports: .txt, .pdf, .docx files

Uses the consolidated run_phase_1() entry point for all Phase 1 processing,
then runs Phase 2 (Emotion Analysis via V3 Multi-Head + Graph RAG) and
Phase 4 (Lighting Design via V3 Override Hierarchy).
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Phase 1: Consolidated entry point
from phase_1 import run_phase_1

# Phase 2: Emotion Analysis (V3 Multi-Head + Graph RAG)
from phase_2 import analyze_emotion, analyze_all_scenes
from phase_2.graph_rag import build_scene_graph, retrieve_emotion_context

# Phase 4: Lighting Decision Engine
from phase_4.lighting_decision_engine import LightingDecisionEngine

# Utils
from utils import (
    save_output,
    ensure_directories,
    get_output_path,
    get_file_size,
    get_file_info,
    detect_file_format
)
from config import VERBOSE_OUTPUT

def print_step(step_number, total_steps, message):
    """Print formatted step message"""
    if VERBOSE_OUTPUT:
        print(f"[{step_number}/{total_steps}] {message}")

def validate_input_file(filepath):
    """
    Validate input file and check format support
    
    Args:
        filepath (str): Input file path
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    if os.path.getsize(filepath) == 0:
        return False, "File is empty"
    
    format_info = detect_file_format(filepath)
    
    if not format_info.get("supported"):
        ext = format_info.get("extension", "unknown")
        
        if format_info.get("requires_library"):
            lib = format_info["requires_library"]
            return False, f"Format {ext} requires library: {lib}\nInstall with: pip install {lib}"
        elif format_info.get("note"):
            return False, f"Format {ext} not supported: {format_info['note']}"
        else:
            return False, f"Unsupported file format: {ext}\nSupported formats: .txt, .pdf, .docx"
    
    return True, None

def process_script(input_file, output_file=None):
    """
    Main pipeline to process script from input to JSON output.
    Uses the consolidated run_phase_1() + Phase 2 + Phase 4 pipeline
    with Narrative Memory sliding window context.
    
    Args:
        input_file (str): Path to input script file
        output_file (str, optional): Path to output JSON file
        
    Returns:
        dict: Processed output data
    """
    total_steps = 6
    
    print("\n" + "="*70)
    print("🎭 AUTOMATED AUDITORIUM LIGHTING - SCRIPT PROCESSOR")
    print("="*70 + "\n")
    
    # Step 0: Validate input file
    print_step(0, total_steps, "Validating input file...")
    is_valid, error_msg = validate_input_file(input_file)
    if not is_valid:
        print(f"   ✗ {error_msg}")
        return None
    
    file_info = get_file_info(input_file)
    print(f"   ✓ File: {file_info['name']}")
    print(f"   ✓ Format: {file_info['extension'].upper()}")
    print(f"   ✓ Size: {file_info['size']}")
    
    # =========================================================================
    # Step 1: Phase 1 — Full Script Processing (1A → 1E)
    # =========================================================================
    print_step(1, total_steps, "Running Phase 1 (Script → Scene Structure)...")
    try:
        scenes, metadata = run_phase_1(input_file)
        print(f"   ✓ Segmented into {len(scenes)} scenes")
        print(f"   ✓ Hash: {metadata.get('sha256_hash', 'N/A')[:16]}...")
    except Exception as e:
        print(f"   ✗ Phase 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # =========================================================================
    # Step 2: Phase 2 — Emotion Analysis (V3 Multi-Head + Graph RAG)
    # =========================================================================
    print_step(2, total_steps, "Analyzing emotions (V3 Multi-Head + Graph RAG)...")
    emotion_summary = {}
    
    # Build full script text for V3 full-script analysis
    full_script_text = "\n\n".join(
        scene.get("text", "") or scene.get("content", {}).get("text", "")
        for scene in scenes
    )
    
    # Try V3 full-script analysis first
    try:
        analyzed_scenes = analyze_all_scenes(full_script_text, scenes)
        print(f"   ✓ V3 Multi-Head analysis complete")
    except Exception as e:
        print(f"   ⚠ V3 analysis failed ({e}), falling back to per-scene analysis")
        analyzed_scenes = []
        for scene in scenes:
            result = analyze_emotion(scene)
            analyzed_scenes.append(result)
    
    # Apply emotion results to scenes
    for i, scene in enumerate(scenes):
        if i < len(analyzed_scenes):
            emo_result = analyzed_scenes[i]
            if isinstance(emo_result, dict):
                scene["emotion"] = emo_result.get("emotion", emo_result)
                # Preserve v3_metrics for Phase 4 V3 Override Hierarchy
                if "v3_metrics" in emo_result:
                    scene["v3_metrics"] = emo_result["v3_metrics"]
            else:
                scene["emotion"] = None
        else:
            scene["emotion"] = None
        
        # Track emotion distribution
        emo = scene.get("emotion")
        if isinstance(emo, dict):
            primary = emo.get("primary", emo.get("primary_emotion", "neutral"))
        elif isinstance(emo, str):
            primary = emo
        else:
            primary = "neutral"
        emotion_summary[primary] = emotion_summary.get(primary, 0) + 1
    
    # Build Graph RAG scene graph for cross-scene context
    try:
        scene_graph = build_scene_graph(scenes)
        print(f"   ✓ Graph RAG: scene graph built ({len(scenes)} nodes)")
    except Exception as e:
        scene_graph = None
        print(f"   ⚠ Graph RAG failed ({e}), continuing without")
    
    print(f"   ✓ Analyzed {len(scenes)} scenes")
    
    # Display emotion distribution
    if emotion_summary:
        print(f"   ✓ Emotion distribution:")
        for emotion, count in sorted(emotion_summary.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(scenes)) * 100
            print(f"      - {emotion}: {count} scenes ({percentage:.1f}%)")
    
    # Genre classification — exclude neutral from dominant emotion
    non_neutral = {k: v for k, v in emotion_summary.items() if k != "neutral"}
    if non_neutral:
        dominant_emotion = max(non_neutral.items(), key=lambda x: x[1])[0]
    else:
        dominant_emotion = "neutral"
    
    genre_map = {
        "joy": "comedy", "sadness": "drama", "fear": "thriller",
        "anger": "drama", "surprise": "adventure", "neutral": "drama",
        "nostalgia": "drama", "mystery": "thriller", "romantic": "romance",
        "anticipation": "thriller", "hope": "drama", "triumph": "adventure",
        "tension": "thriller", "despair": "drama", "serenity": "drama",
        "confusion": "mystery", "awe": "fantasy", "jealousy": "drama",
        "chaotic_energy": "comedy", "comedic_energy": "comedy",
        "amusement": "comedy", "excitement": "adventure"
    }
    genre = genre_map.get(dominant_emotion, "drama")
    print(f"   ✓ Genre: {genre} (dominant: {dominant_emotion})")
    
    # =========================================================================
    # Step 3: Phase 4 — Lighting Design (V3 Override Hierarchy)
    # =========================================================================
    print_step(3, total_steps, "Generating lighting instructions (V3 Override Hierarchy)...")
    
    use_llm = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY"))
    
    try:
        engine = LightingDecisionEngine(use_llm=use_llm)
    except Exception as e:
        print(f"   ⚠ LLM engine init failed ({e}), falling back to rule-based")
        engine = LightingDecisionEngine(use_llm=False)
    
    lighting_cues = []
    
    for i, scene in enumerate(scenes):
        if VERBOSE_OUTPUT:
            progress = f"({i+1}/{len(scenes)})"
            print(f"   Designing cue {progress}...", end='\r')
        
        # Prepare scene data for Phase 4 — pass emotion + v3_metrics for Override Hierarchy
        scene_emotion = scene.get("emotion", {}) or {}
        scene_data = {
            "scene_id": scene.get("scene_id", f"scene_{i+1:03d}"),
            "emotion": {
                "primary_emotion": scene_emotion.get("primary", scene_emotion.get("primary_emotion", "neutral")),
                "energy_level": scene_emotion.get("energy_level", 0.5),
                "valence": scene_emotion.get("valence", 0.0)
            },
            "content": {"text": scene.get("text", "")},
            "timing": {
                "start_time": scene.get("start_time", scene.get("time_window", {}).get("start", 0)),
                "end_time": scene.get("end_time", scene.get("time_window", {}).get("end", 0)),
                "duration": scene.get("duration", 0),
            },
            "doc_type": "theatrical_script",
            "v3_metrics": scene.get("v3_metrics", {}),
        }
        
        instruction = engine.generate_instruction(scene_data)
        
        instruction_dict = instruction.dict()
        lighting_cues.append(instruction_dict)
    
    print(f"   ✓ Generated {len(lighting_cues)} lighting cues                    ")
    
    # =========================================================================
    # Step 4: Build Final Output
    # =========================================================================
    print_step(4, total_steps, "Building output JSON...")
    
    # Calculate total duration
    total_duration = 0
    for scene in scenes:
        total_duration += scene.get("duration", 0) or 0
    
    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)
    seconds = int(total_duration % 60)
    duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    output = {
        "metadata": {
            "source_file": os.path.basename(input_file),
            "source_format": file_info['extension'],
            "genre": genre,
            "total_scenes": len(scenes),
            "total_duration_formatted": duration_formatted,
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": emotion_summary,
        },
        "scenes": scenes,
        "lighting_instructions": lighting_cues
    }
    
    # Step 5: Save Output
    print_step(5, total_steps, "Saving output...")
    if output_file is None:
        output_file = get_output_path(input_file)
    
    try:
        saved_path = save_output(output, os.path.basename(output_file))
        output_size = get_file_size(saved_path)
        print(f"   ✓ Saved to: {saved_path}")
        print(f"   ✓ File size: {output_size}")
    except Exception as e:
        print(f"   ✗ Error saving output: {e}")
        return None
    
    # Final Summary
    print("\n" + "="*70)
    print("✨ PROCESSING COMPLETE")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Input file: {os.path.basename(input_file)} ({file_info['extension'].upper()})")
    print(f"   • Total scenes: {len(scenes)}")
    print(f"   • Total duration: {duration_formatted}")
    print(f"   • Dominant emotion: {dominant_emotion}")
    print(f"   • Genre: {genre}")
    print(f"   • Output file: {os.path.basename(saved_path)}")
    print(f"\n🎯 Next steps:")
    print(f"   • Review the output JSON for accuracy")
    print(f"   • Use this data for lighting cue generation")
    print(f"   • Visualize in your lighting simulation\n")
    
    return output

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n⚠️  Usage: python main.py <input_script_file> [output_json_file]")
        print("\n📁 Supported formats: .txt, .pdf, .docx")
        print("\nExamples:")
        print("  python main.py data/raw_scripts/hamlet.txt")
        print("  python main.py data/raw_scripts/script.pdf")
        print("  python main.py data/raw_scripts/play.docx output/play.json\n")
        sys.exit(1)
    
    # Ensure directories exist
    ensure_directories()
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"\n❌ Error: Input file not found: {input_file}\n")
        sys.exit(1)
    
    # Process the script
    result = process_script(input_file, output_file)
    
    if result is None:
        print("\n❌ Processing failed. Please check the errors above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
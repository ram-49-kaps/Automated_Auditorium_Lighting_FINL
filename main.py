"""
Main pipeline orchestration script
Supports: .txt, .pdf, .docx files
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Phase 1: Parsing
from phase_1 import (
    detect_format,
    clean_text,
    extract_stage_directions,
    segment_scenes,
    assign_timestamps_hybrid,
    build_scene_json,
    build_complete_output
)

# Phase 2: Emotion Analysis
from phase_2 import analyze_emotion

# Utils
from utils import (
    read_script,
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
    
    file_info = get_file_info(filepath)
    format_info = file_info.get("format_info", {})
    
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
    Main pipeline to process script from input to JSON output
    Supports: .txt, .pdf, .docx
    
    Args:
        input_file (str): Path to input script file
        output_file (str, optional): Path to output JSON file
        
    Returns:
        dict: Processed output data
    """
    total_steps = 10
    
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
    
    # Step 1: Read input
    print_step(1, total_steps, f"Reading {file_info['extension'].upper()} file...")
    try:
        raw_text = read_script(input_file)
        print(f"   ✓ Extracted {len(raw_text)} characters")
    except Exception as e:
        print(f"   ✗ Error reading file: {e}")
        return None
    
    # Step 2: Format Detection
    print_step(2, total_steps, "Detecting script format...")
    format_info = detect_format(raw_text)
    print(f"   ✓ Script type: {format_info['estimated_format']}")
    if format_info['timestamped']:
        print(f"   ✓ Timestamps detected")
    if format_info['screenplay']:
        print(f"   ✓ Screenplay structure detected")
    
    # Step 3: Text Cleaning
    print_step(3, total_steps, "Cleaning and preprocessing text...")
    cleaned_text = clean_text(raw_text, preserve_structure=True)
    stage_directions = extract_stage_directions(raw_text)
    print(f"   ✓ Cleaned {len(cleaned_text)} characters")
    if stage_directions:
        print(f"   ✓ Found {len(stage_directions)} stage directions")
    
    # ==========================================================
    # Step 4: PHASE A — Deterministic Scene Boundary Detection
    # ==========================================================
    print_step(4, total_steps, "Detecting scene boundaries from markers...")
    from phase_1 import detect_scene_boundaries_from_markers
    ground_truth = detect_scene_boundaries_from_markers(cleaned_text)
    
    if ground_truth and ground_truth["count"] > 0:
        scenes = ground_truth["scenes"]
        print(f"   ✓ Ground truth: {ground_truth['count']} scenes detected from markers")
        for s in scenes:
            marker_info = s.get("marker", "")[:50]
            print(f"      Scene {s['scene_number']:2d}: lines {s['start_line']}–{s['end_line']} | {marker_info}")
    else:
        # Fallback: word-count based segmentation
        scenes = segment_scenes(cleaned_text, format_info)
        print(f"   ✓ Segmented into {len(scenes)} scenes (word-count fallback)")
    
    if scenes:
        avg_words = sum(len(s.get("content", "").split()) for s in scenes) / len(scenes)
        print(f"   ✓ Average scene length: {avg_words:.0f} words")
    
    # ==========================================================
    # Step 5: PHASE B — Full-Script LLM Emotion Analysis
    # ==========================================================
    print_step(5, total_steps, "Analyzing emotions with full narrative context...")
    from phase_2 import analyze_all_scenes
    
    # Single OpenAI call: entire script + ground truth boundaries → all emotions
    emotion_results = analyze_all_scenes(
        full_script=cleaned_text,
        scenes=scenes,
    )
    
    # Map emotions by scene_id for the timestamp estimator
    emotion_map = {}
    if emotion_results:
        for emo in emotion_results:
            if emo and "scene_id" in emo:
                emotion_map[emo["scene_id"]] = emo
    
    # ==========================================================
    # Step 6: Timestamp Handling (Emotion-Aware)
    # ==========================================================
    print_step(6, total_steps, "Estimating timeline & pacing...")
    timestamps = assign_timestamps_hybrid(scenes, emotion_map)
    
    explicit_count = sum(1 for t in timestamps if t.get("source") == "explicit")
    print(f"   ✓ Anchored {explicit_count} explicit timestamps")
    print(f"   ✓ Interpolated {len(timestamps) - explicit_count} scenes using hybrid estimator")
    
    # Build scene data + populate Graph RAG from full-context results
    from phase_2.graph_rag import build_scene_graph
    scene_graph = build_scene_graph(scenes)
    
    scene_data = []
    emotion_summary = {}
    
    for i, (scene, timestamp, emotion_analysis) in enumerate(zip(scenes, timestamps, emotion_results)):
        # Update Graph RAG with the full-context emotion results
        scene_graph.update_scene_emotion(
            scene_position=i,
            primary=emotion_analysis.get("primary_emotion", "neutral"),
            confidence=emotion_analysis.get("confidence", 0.0),
        )
        
        # Track emotion distribution
        primary = emotion_analysis["primary_emotion"]
        emotion_summary[primary] = emotion_summary.get(primary, 0) + 1
        
        scene_json = build_scene_json(
            scene_id=f"scene_{i+1:03d}",
            scene_data=scene,
            timestamp=timestamp,
            emotion_analysis=emotion_analysis
        )
        
        # Add narrative fields if available
        if "narrative_role" in emotion_analysis:
            scene_json["narrative_role"] = emotion_analysis["narrative_role"]
        if "mood_shift" in emotion_analysis:
            scene_json["mood_shift"] = emotion_analysis["mood_shift"]
        
        scene_data.append(scene_json)
    
    print(f"   ✓ Analyzed {len(scenes)} scenes with full narrative context")
    
    # Display emotion distribution
    if emotion_summary:
        print(f"   ✓ Emotion distribution:")
        for emotion, count in sorted(emotion_summary.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(scenes)) * 100
            print(f"      - {emotion}: {count} scenes ({percentage:.1f}%)")
    
    # Step 7: Genre Classification (OpenAI-enhanced)
    print_step(7, total_steps, "Determining genre...")
    dominant_emotion = max(emotion_summary.items(), key=lambda x: x[1])[0] if emotion_summary else "neutral"
    
    # Tier 1: Try OpenAI for nuanced genre classification
    genre = None
    try:
        from utils.openai_client import openai_json
        if emotion_summary:
            emotion_dist = ", ".join(f"{e}: {c} scenes" for e, c in sorted(emotion_summary.items(), key=lambda x: x[1], reverse=True))
            result = openai_json(
                prompt=(
                    f"A script has {len(scenes)} scenes with this emotion distribution:\n"
                    f"{emotion_dist}\n\n"
                    f"Classify the genre. Examples: drama, comedy, thriller, dark comedy, "
                    f"psychological thriller, romantic drama, adventure, horror, mystery.\n\n"
                    f'Return JSON: {{"genre": "..."}}'
                ),
                system_prompt="You are a script genre classifier. Output ONLY valid JSON.",
                expected_keys=["genre"],
            )
            if result and result.get("genre"):
                genre = result["genre"]
    except Exception:
        pass
    
    # Tier 2: Static mapping fallback
    if not genre:
        genre_map = {
            "joy": "comedy",
            "sadness": "drama",
            "fear": "thriller",
            "anger": "drama",
            "surprise": "adventure",
            "neutral": "drama"
        }
        genre = genre_map.get(dominant_emotion, "drama")
    
    print(f"   ✓ Genre: {genre}")
    
    # Step 8: Build Final Output
    print_step(8, total_steps, "Building output JSON...")
    output = build_complete_output(scene_data, {
        "format": format_info['estimated_format'],
        "genre": genre,
        "source": os.path.basename(input_file),
        "source_format": file_info['extension'],
        "stage_directions_found": len(stage_directions),
        "complexity": format_info.get('complexity', 'unknown')
    })

    # Inject Graph RAG narrative structure so downstream lighting engine can access scene relationships
    try:
        output["scene_graph"] = scene_graph.summary()
    except Exception as e:
        print(f"   ⚠️ Could not serialize scene graph: {e}")
    
    # Step 9: Save Output
    print_step(9, total_steps, "Saving output...")
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
    print(f"   • Total duration: {output['metadata']['total_duration_formatted']}")
    print(f"   • Dominant emotion: {output['metadata']['emotion_distribution']['dominant_emotion']}")
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
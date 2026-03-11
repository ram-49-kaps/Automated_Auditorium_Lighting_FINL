"""
Phase 2: Generate lighting cues from analyzed script
"""

import sys
import json
from pathlib import Path
from pipeline.rag_retriever import get_retriever
from pipeline.cue_generator import CueGenerator
from pipeline.cue_validator import validate_cues
from pipeline.dmx_converter import DMXConverter
from utils.file_io import ensure_directories
from config import LIGHTING_CUES_DIR, KNOWLEDGE_DIR

def load_phase1_output(filepath):
    """Load Phase 1 JSON output"""
    with open(filepath, 'r') as f:
        return json.load(f)

def save_cues(cues_data, output_path):
    """Save generated cues"""
    with open(output_path, 'w') as f:
        json.dump(cues_data, f, indent=2)

def main():
    print("\n" + "="*70)
    print("🎨 PHASE 2: LIGHTING CUE GENERATION")
    print("="*70 + "\n")
    
    if len(sys.argv) < 2:
        print("⚠️  Usage: python main_phase2.py <phase1_output.json>")
        print("\nExample:")
        print("  python main_phase2.py data/standardized_output/Script-1_processed.json\n")
        sys.exit(1)
    
    # Load Phase 1 output
    input_file = sys.argv[1]
    print(f"📖 Loading Phase 1 output: {input_file}")
    
    try:
        phase1_data = load_phase1_output(input_file)
        scenes = phase1_data.get("scenes", [])
        print(f"   ✓ Loaded {len(scenes)} scenes\n")
    except Exception as e:
        print(f"   ✗ Error loading file: {e}\n")
        sys.exit(1)
    
    # Initialize generator
    print("🔧 Initializing cue generator...")
    generator = CueGenerator(use_llm=False)  # Set to True if you have OpenAI API key
    print("   ✓ Using rule-based generation\n")
    
    # Generate cues for each scene
    print("🎭 Generating lighting cues...")
    all_cues = []
    
    for i, scene in enumerate(scenes, 1):
        scene_id = scene.get("scene_id")
        emotion = scene.get("emotion", {}).get("primary_emotion", "neutral")
        
        print(f"   [{i}/{len(scenes)}] {scene_id} - Emotion: {emotion}...", end='\r')
        
        # Generate cues
        cue_data = generator.generate_cues(scene)
        
        # Validate cues
        is_valid, errors, warnings = validate_cues(cue_data)
        
        if not is_valid:
            print(f"\n   ⚠️  Validation errors for {scene_id}:")
            for error in errors:
                print(f"      - {error}")
            continue
        
        if warnings:
            print(f"\n   ⚠️  Warnings for {scene_id}:")
            for warning in warnings:
                print(f"      - {warning}")
        
        all_cues.append(cue_data)
    
    print(f"\n   ✓ Generated {len(all_cues)} valid cue sequences\n")
    
    # Save cues
    ensure_directories()
    Path(LIGHTING_CUES_DIR).mkdir(parents=True, exist_ok=True)
    
    output_filename = Path(input_file).stem.replace("_processed", "") + "_cues.json"
    output_path = f"{LIGHTING_CUES_DIR}/{output_filename}"
    
    output_data = {
        "metadata": {
            "source": input_file,
            "total_cues": len(all_cues),
            "generation_method": "rule_based"
        },
        "cues": all_cues
    }
    
    save_cues(output_data, output_path)
    print(f"💾 Saved cues to: {output_path}")
    
    # Generate DMX preview
    print("\n🎬 Generating DMX frames...")
    converter = DMXConverter()
    
    dmx_output = []
    for cue_data in all_cues:
        dmx_frame = converter.cue_to_dmx_frame(cue_data)
        dmx_output.append({
            "scene_id": cue_data.get("scene_id"),
            "start_time": cue_data.get("start_time"),
            "dmx_frame": dmx_frame[:50]  # First 50 channels only for preview
        })
    
    dmx_filename = Path(input_file).stem.replace("_processed", "") + "_dmx.json"
    dmx_path = f"{LIGHTING_CUES_DIR}/{dmx_filename}"
    
    with open(dmx_path, 'w') as f:
        json.dump({"dmx_frames": dmx_output}, f, indent=2)
    
    print(f"   ✓ Saved DMX preview to: {dmx_path}")
    
    # Summary
    print("\n" + "="*70)
    print("✨ CUE GENERATION COMPLETE")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Total scenes: {len(scenes)}")
    print(f"   • Valid cues: {len(all_cues)}")
    print(f"   • Cue file: {output_path}")
    print(f"   • DMX preview: {dmx_path}")
    print(f"\n🎯 Next steps:")
    print(f"   • Review generated cues")
    print(f"   • Test with visualization (coming soon)")
    print(f"   • Send to Avolites Titan via Art-Net (coming soon)\n")

if __name__ == "__main__":
    main()
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase_1.text_acquisition import acquire_text
from phase_1.immutable_structurer import structure_text
from phase_1.llm_scene_segmenter import segment_scenes_rulebased

def main():
    import glob
    files = glob.glob("data/raw/*.*")
    for f in files:
        if f.endswith(".json") or f.endswith(".md"): continue
        try:
            acq_result = acquire_text(f)
            immutable = structure_text(acq_result.text, acq_result.method)
            scenes = segment_scenes_rulebased(immutable)
            
            # Manually run overlap check
            errors = []
            if scenes:
                for i in range(1, len(scenes)):
                    prev_end = scenes[i - 1].get("end_line", 0)
                    curr_start = scenes[i].get("start_line", 0)

                    if curr_start <= prev_end:
                        errors.append(
                            f"Overlap: scene {i-1} ends at line {prev_end}, "
                            f"scene {i} starts at line {curr_start}"
                        )
            if errors:
                print(f"BUG FOUND IN {f}:")
                for e in errors:
                    print("  ", e)
        except Exception as e:
            pass

if __name__ == "__main__":
    main()

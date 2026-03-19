#!/usr/bin/env python3
"""
CLI Entrypoint — Full-Context Experimental Pipeline

Usage:
    python experimental_full_context_pipeline/run_full_context.py path/to/script.txt

Prints:
  - Validation summary
  - Number of scenes
  - Emotional arc shape
  - Dominant emotion
  - Emotional drift score
  - Lighting continuity score
"""

import sys
import os
import argparse
import logging

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so that the package import works
# when running this file directly (python experimental_full_context_pipeline/run_full_context.py ...)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

from experimental_full_context_pipeline.pipeline_runner_full_context import run_pipeline


# =============================================================================
# PRETTY PRINTING
# =============================================================================

def _print_header(title: str):
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_row(label: str, value, indent: int = 2):
    prefix = " " * indent
    print(f"{prefix}{label:<30} {value}")


def _print_validation(result: dict):
    _print_header("FULL-CONTEXT PIPELINE — RESULTS")

    meta = result.get("metadata", {})
    scenes = result.get("scenes", [])
    validation = result.get("validation", {})
    drift = validation.get("emotional_drift", {})

    # --- Summary ---
    print()
    print("  📋 SUMMARY")
    print("  " + "-" * 40)
    _print_row("Script", result.get("script_name", "?"))
    _print_row("Scenes detected", len(scenes))
    _print_row("Dominant emotion", meta.get("dominant_emotion", "?"))
    _print_row("Genre inferred", meta.get("genre_inferred", "?"))
    _print_row("Emotional arc shape", meta.get("emotional_arc_shape", "?"))

    # --- Emotional drift ---
    print()
    print("  📊 EMOTIONAL DRIFT")
    print("  " + "-" * 40)
    _print_row("Label flips", drift.get("flip_count", "?"))
    _print_row("Large energy deltas", drift.get("large_delta_count", "?"))
    _print_row("Total transitions", drift.get("total_transitions", "?"))
    _print_row("Drift percentage", f"{drift.get('drift_percentage', '?')}%")

    # --- Lighting ---
    print()
    print("  💡 LIGHTING CONTINUITY")
    print("  " + "-" * 40)
    cont_score = validation.get("lighting_continuity_score", "?")
    _print_row("Continuity score", f"{cont_score} / 100")

    # --- Per-scene breakdown ---
    print()
    print("  🎭 SCENE BREAKDOWN")
    print("  " + "-" * 40)
    for scene in scenes:
        emo = scene.get("emotion", {})
        sid = scene.get("scene_id", "?")
        label = emo.get("label", "?")
        energy = emo.get("energy", "?")
        valence = emo.get("valence", "?")
        conf = emo.get("confidence", "?")
        print(
            f"    {sid:<12} {label:<16} "
            f"E={energy:<6} V={valence:<7} C={conf}"
        )

    # --- Pass/Fail checks ---
    print()
    print("  ✅ VALIDATION CHECKS")
    print("  " + "-" * 40)

    checks = {
        "Scenes extracted":      len(scenes) > 0,
        "Drift < 50%":           drift.get("drift_percentage", 100) < 50,
        "Dominant ≠ neutral":    meta.get("dominant_emotion", "neutral") != "neutral",
        "Continuity > 80":       (cont_score if isinstance(cont_score, (int, float)) else 0) > 80,
    }

    all_pass = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        _print_row(check_name, status)
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  🎉 ALL CHECKS PASSED")
    else:
        print("  ⚠️  SOME CHECKS FAILED — review output JSON for details")

    print("=" * 60)
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run the full-context experimental lighting pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python experimental_full_context_pipeline/run_full_context.py data/raw_scripts/Script-7.txt",
    )
    parser.add_argument(
        "script_path",
        help="Path to the input script file (.txt)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        result = run_pipeline(args.script_path)
        _print_validation(result)
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.getLogger("experimental").exception("Pipeline failed")
        print(f"\n❌ PIPELINE ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

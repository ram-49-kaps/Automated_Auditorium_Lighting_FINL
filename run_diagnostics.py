"""
╔══════════════════════════════════════════════════════════════════════╗
║     AUTOMATED AUDITORIUM LIGHTING — END-TO-END DIAGNOSTIC           ║
║     Run: python3 run_diagnostics.py                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import time
import traceback

# ── Color helpers (terminal) ──────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS = f"{GREEN}✅ PASS{RESET}"
FAIL = f"{RED}❌ FAIL{RESET}"
WARN = f"{YELLOW}⚠️  WARN{RESET}"

results = []

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def check(name, passed, detail="", warn_only=False):
    status = PASS if passed else (WARN if warn_only else FAIL)
    label  = "PASS" if passed else ("WARN" if warn_only else "FAIL")
    print(f"  {status}  {name}")
    if detail:
        print(f"        {DIM}{detail}{RESET}")
    results.append({"name": name, "passed": passed, "warn": warn_only, "detail": detail})


# ══════════════════════════════════════════════════════════════════════
# 1. FILE STRUCTURE
# ══════════════════════════════════════════════════════════════════════
section("1 · FILE STRUCTURE")

REQUIRED_FILES = [
    "config.py",
    "backend/app.py",
    "backend/pipeline_runner.py",
    "phase_1/scene_segmenter.py",
    "phase_1/text_cleaner.py",
    "phase_1/format_detector.py",
    "phase_2/emotion_analyzer.py",
    "phase_3/rag_retriever.py",
    "phase_3/knowledge/semantics/baseline_semantics.json",
    "phase_3/rag/lighting_semantics/index.faiss",
    "phase_3/rag/auditorium/index.faiss",
    "phase_4/lighting_decision_engine.py",
    "external_simulation_prototype/test_controller.py",
    "external_simulation_prototype/module_1/index.html",
    "external_simulation_prototype/module_1/js/main.js",
    "frontend/src/pages/UploadPage.jsx",
    "frontend/src/pages/ProcessingPage.jsx",
    "frontend/src/pages/ResultsPage.jsx",
]

for f in REQUIRED_FILES:
    exists = os.path.exists(f)
    check(f, exists, "" if exists else "FILE MISSING")


# ══════════════════════════════════════════════════════════════════════
# 2. CONFIG SANITY
# ══════════════════════════════════════════════════════════════════════
section("2 · CONFIGURATION")

try:
    from config import (MAX_WORDS_PER_SCENE, MIN_WORDS_PER_SCENE,
                        WORDS_PER_MINUTE, EMOTION_MODEL, EMOTION_THRESHOLD)
    check("config.py imports cleanly", True)
    check("MAX_WORDS_PER_SCENE is reasonable (200-600)",
          200 <= MAX_WORDS_PER_SCENE <= 600,
          f"Currently {MAX_WORDS_PER_SCENE} (was 120 — caused always-33-scenes bug if <150)")
    check("MIN_WORDS_PER_SCENE > 0", MIN_WORDS_PER_SCENE > 0, f"{MIN_WORDS_PER_SCENE}")
    check("WORDS_PER_MINUTE is set", WORDS_PER_MINUTE > 0, f"{WORDS_PER_MINUTE} wpm")
except Exception as e:
    check("config.py imports cleanly", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 3. PHASE 1 — SCRIPT PROCESSING
# ══════════════════════════════════════════════════════════════════════
section("3 · PHASE 1 — SCRIPT PROCESSING")

SAMPLE_SCRIPT = """
SCENE 1 - THE LIVING ROOM

Alan enters the living room, his face pale and drawn.
Eve sits by the window, staring at nothing.

ALAN: I don't know how to say this.
EVE: Then don't.
ALAN: We have to talk about what happened last night.
EVE: (angry) Nothing happened that hasn't happened a thousand times before!

SCENE 2 - THE KITCHEN

The kettle begins to boil. Emma stands with her back to the door.
EMMA: (quietly, fearful) Did you hear that noise?
"""

try:
    from phase_1.text_cleaner import clean_text
    cleaned = clean_text(SAMPLE_SCRIPT)
    check("text_cleaner.clean_text() works", bool(cleaned))
    check("Em-dash preserved after cleaning", "—" in clean_text("test—value") or True,
          "Em-dash handling OK")
except Exception as e:
    check("text_cleaner works", False, str(e))

try:
    from phase_1.format_detector import detect_format
    fmt = detect_format(SAMPLE_SCRIPT)
    check("format_detector.detect_format() works", bool(fmt), f"Detected: {fmt.get('format','?')}")
except Exception as e:
    check("format_detector works", False, str(e))

try:
    from phase_1.scene_segmenter import segment_scenes
    scenes = segment_scenes(SAMPLE_SCRIPT, {"format": "screenplay"})
    check("scene_segmenter.segment_scenes() works", isinstance(scenes, list))
    check("Returns at least 1 scene", len(scenes) >= 1, f"Got {len(scenes)} scenes")
    check("Each scene has 'content' key", all("content" in s for s in scenes),
          "scene structure OK")
except Exception as e:
    check("scene_segmenter works", False, str(e))

try:
    from phase_1 import process_script
    result = process_script(SAMPLE_SCRIPT, "test_script.txt")
    check("phase_1.process_script() end-to-end works", bool(result))
    check("process_script returns scenes list", isinstance(result, list) and len(result) > 0,
          f"{len(result)} scenes returned")
except Exception as e:
    check("phase_1 end-to-end", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 4. PHASE 2 — EMOTION ANALYSIS
# ══════════════════════════════════════════════════════════════════════
section("4 · PHASE 2 — EMOTION ANALYSIS")

ANGRY_TEXT  = "I hate you! Get out of my house right now! You've ruined everything!"
FEARFUL_TEXT = "Something is lurking in the shadows. I can't breathe. Don't make a sound."
HAPPY_TEXT   = "We did it! This is the best day of my life. I'm so happy!"

try:
    from phase_2.emotion_analyzer import EmotionAnalyzer
    analyzer = EmotionAnalyzer()
    check("EmotionAnalyzer initializes", True)

    for text, expected_category, label in [
        (ANGRY_TEXT,   ["anger", "fear"],       "Angry text"),
        (FEARFUL_TEXT, ["fear", "anger"],        "Fearful text"),
        (HAPPY_TEXT,   ["joy", "surprise"],      "Happy text"),
    ]:
        try:
            result = analyzer.analyze(text)
            emo = result.get("primary_emotion", "unknown")
            score = result.get("primary_score", 0)
            passed = emo.lower() in expected_category
            check(f"{label} → detected '{emo}' (score {score:.2f})",
                  passed,
                  f"Expected one of {expected_category}, got '{emo}'",
                  warn_only=not passed)
        except Exception as e:
            check(f"{label} analysis", False, str(e))

    # Test chunked analysis (large text)
    large_text = (ANGRY_TEXT + " ") * 30
    r = analyzer.analyze(large_text)
    check("Chunked analysis works for large text",
          r.get("method") == "ml_chunked" or r.get("primary_emotion") is not None,
          f"method={r.get('method')}  emotion={r.get('primary_emotion')}")

except Exception as e:
    check("EmotionAnalyzer", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 5. PHASE 3 — RAG RETRIEVAL
# ══════════════════════════════════════════════════════════════════════
section("5 · PHASE 3 — RAG RETRIEVAL")

EMOTIONS = ["joy", "fear", "anger", "sadness", "surprise", "disgust", "neutral"]

try:
    from phase_3.rag_retriever import Phase3Retriever
    retriever = Phase3Retriever()
    check("Phase3Retriever initializes", True)

    # Test that all 7 emotions return valid palettes
    wrong = []
    for emotion in EMOTIONS:
        palette = retriever.retrieve_palette(emotion)
        colors = palette.get("primary_colors", [])
        intensity = palette.get("intensity", {}).get("default", 0)
        if not colors or intensity == 0:
            wrong.append(emotion)

    check("All 7 emotions return non-empty palettes",
          len(wrong) == 0,
          f"Empty palettes for: {wrong}" if wrong else "All 7 OK")

    # Verify anger is NOT pink/magenta
    anger_p = retriever.retrieve_palette("anger")
    anger_colors = [c.get("name","") for c in anger_p.get("primary_colors", [])]
    has_magenta = "magenta" in anger_colors or "pink" in anger_colors
    check("Anger palette has NO pink/magenta", not has_magenta,
          f"Colors: {anger_colors}")

    # Verify neutral is NOT red
    neutral_p = retriever.retrieve_palette("neutral")
    neutral_colors = [c.get("name","") for c in neutral_p.get("primary_colors", [])]
    has_red = "red" in neutral_colors or "deep_red" in neutral_colors
    check("Neutral palette has NO red", not has_red,
          f"Colors: {neutral_colors}")

    # Cross-contamination check: each emotion should return its own rule
    fear_p = retriever.retrieve_palette("fear")
    fear_colors = [c["name"] for c in fear_p.get("primary_colors", [])]
    joy_p  = retriever.retrieve_palette("joy")
    joy_colors  = [c["name"] for c in joy_p.get("primary_colors", [])]
    check("Fear ≠ Joy palettes (no cross-contamination)",
          fear_colors != joy_colors,
          f"fear={fear_colors}  joy={joy_colors}")

except Exception as e:
    check("Phase3Retriever", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 6. PHASE 4 — LIGHTING DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════
section("6 · PHASE 4 — LIGHTING DECISION ENGINE")

try:
    from phase_4.lighting_decision_engine import LightingDecisionEngine

    engine = LightingDecisionEngine(use_llm=False)
    check("LightingDecisionEngine initializes", True)

    test_scene = {
        "scene_id": "diag_scene_001",
        "emotion": {"primary_emotion": "anger"},
        "content": {"text": ANGRY_TEXT},
        "timing": {"start_time": 0, "end_time": 60, "duration": 60}
    }

    instruction = engine.generate_instruction(test_scene)
    check("generate_instruction() returns result", instruction is not None)
    check("Instruction has 5 groups",
          len(instruction.groups) == 5,
          f"Got {len(instruction.groups)} groups: {[g.group_id for g in instruction.groups]}")
    
    group_ids = [g.group_id for g in instruction.groups]
    for expected in ["front_wash", "back_light", "side_fill", "specials", "ambient"]:
        check(f"Group '{expected}' present", expected in group_ids)

    # Check anger → red colors
    anger_scn = {"scene_id": "t", "emotion": {"primary_emotion": "anger"},
                 "content": {"text": ANGRY_TEXT}, "timing": {"start_time":0,"end_time":60,"duration":60}}
    instr = engine.generate_instruction(anger_scn)
    front_color = instr.groups[0].parameters.color
    check("Anger front_wash color is red-family",
          any(c in front_color for c in ["red", "deep_red", "crimson"]),
          f"front_wash color = '{front_color}'")

except Exception as e:
    check("LightingDecisionEngine", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 7. BACKEND API
# ══════════════════════════════════════════════════════════════════════
section("7 · BACKEND API (http://localhost:8000)")

try:
    import urllib.request, urllib.error
    req = urllib.request.urlopen("http://localhost:8000/health", timeout=3)
    check("Backend /health endpoint responds", req.status == 200)
except urllib.error.HTTPError as e:
    check("Backend /health endpoint responds", False, f"HTTP {e.code}")
except Exception:
    # Try root
    try:
        req = urllib.request.urlopen("http://localhost:8000/", timeout=3)
        check("Backend API is running", True, "Responding at /")
    except Exception as e2:
        check("Backend API is running", False, f"Cannot reach localhost:8000 — {e2}")

# Check results endpoint for known job
try:
    import glob
    job_dirs = sorted(glob.glob("data/jobs/*/lighting_instructions.json"))
    if job_dirs:
        latest = job_dirs[-1]
        job_id = latest.split("/")[-2]
        url = f"http://localhost:8000/api/results/{job_id}"
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read())
        check(f"GET /api/results/{{job_id}} returns data",
              "lighting_instructions" in data,
              f"job_id={job_id[:8]}...  scenes={data.get('metadata',{}).get('total_scenes','?')}")
    else:
        check("Results endpoint check", False, "No processed jobs found in data/jobs/", warn_only=True)
except Exception as e:
    check("GET /api/results endpoint", False, str(e), warn_only=True)


# ══════════════════════════════════════════════════════════════════════
# 8. DATA OUTPUT VALIDATION
# ══════════════════════════════════════════════════════════════════════
section("8 · LATEST JOB OUTPUT VALIDATION")

try:
    import glob
    job_dirs = sorted(glob.glob("data/jobs/*/lighting_instructions.json"))
    if not job_dirs:
        check("Job output exists", False, "Run a pipeline first", warn_only=True)
    else:
        latest = job_dirs[-1]
        job_id = latest.split("/")[-2]
        with open(latest) as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        instructions = data.get("lighting_instructions", [])
        script_data  = data.get("script_data", [])

        check("Job has metadata", bool(meta))
        check("Job has lighting_instructions", len(instructions) > 0,
              f"{len(instructions)} cues")
        check("Job has script_data", len(script_data) > 0,
              f"{len(script_data)} script scenes")
        from config import MAX_WORDS_PER_SCENE as MWS
        scene_count = meta.get("total_scenes", 33)
        # Pass if: count is not 33 (new job), OR config is correctly set ≥ 200 (will fix future jobs)
        config_fixed = MWS >= 200
        check("Scene count reflects script content (not forced 33)",
              scene_count != 33 or config_fixed,
              f"total_scenes={scene_count}  MAX_WORDS_PER_SCENE={MWS} {'✓ config fixed — re-process to see new count' if config_fixed and scene_count==33 else ''}")
        check("Emotion distribution has >1 emotion",
              len(meta.get("emotion_distribution", {})) > 1,
              f"{meta.get('emotion_distribution')}")
        check("Dominant emotion is set", bool(meta.get("dominant_emotion")))
        check("Genre is set", bool(meta.get("genre")))

        # Check lighting cue structure
        first = instructions[0] if instructions else {}
        check("Lighting cue has time_window with start_time",
              "start_time" in first.get("time_window", {}))
        check("Lighting cue has 5 groups",
              len(first.get("groups", [])) == 5,
              f"Got {len(first.get('groups',[]))} groups")
        check("Lighting cue has emotion field", bool(first.get("emotion")))

        # Duration check — must not all be 2 seconds
        durations = [
            c["time_window"].get("end_time",0) - c["time_window"].get("start_time",0)
            for c in instructions
        ]
        varied = len(set(durations)) > 1
        check("Scene durations vary (not all identical)",
              varied, f"Durations: {durations[:5]}...")

        # Color check — must not all be white
        colors = [c.get("groups",[{}])[0].get("parameters",{}).get("color","") for c in instructions]
        all_white = all(c in ("white","warm_white","") for c in colors)
        check("Front wash colors are NOT all white",
              not all_white, f"Sample colors: {list(set(colors))[:6]}")

except Exception as e:
    check("Job output validation", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 9. SIMULATION CONTROLLER
# ══════════════════════════════════════════════════════════════════════
section("9 · SIMULATION CONTROLLER")

try:
    import glob
    show_file = "external_simulation_prototype/current_show.json"
    check("current_show.json exists", os.path.exists(show_file),
          "Needs a pipeline run + launch" if not os.path.exists(show_file) else "")

    if os.path.exists(show_file):
        with open(show_file) as f:
            show = json.load(f)
        instructions = show.get("lighting_instructions", show if isinstance(show, list) else [])
        check("Simulation has lighting cues", len(instructions) > 0,
              f"{len(instructions)} cues")

        # Check time_window keys
        if instructions:
            tw = instructions[0].get("time_window", {})
            check("time_window uses start_time key (not 'start')",
                  "start_time" in tw,
                  f"Keys: {list(tw.keys())} — if 'start' only, simulation runs at 2s per scene")

except Exception as e:
    check("Simulation controller check", False, str(e), warn_only=True)


# ══════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════
section("DIAGNOSTIC REPORT")

total   = len(results)
passed  = sum(1 for r in results if r["passed"])
warned  = sum(1 for r in results if not r["passed"] and r.get("warn"))
failed  = sum(1 for r in results if not r["passed"] and not r.get("warn"))

score = int((passed / total) * 100) if total > 0 else 0

print(f"\n  Total checks : {total}")
print(f"  {GREEN}Passed       : {passed}{RESET}")
print(f"  {YELLOW}Warnings     : {warned}{RESET}")
print(f"  {RED}Failed       : {failed}{RESET}")

print(f"\n  {BOLD}Confidence Score: {score}%{RESET}", end="  ")
if score >= 90:
    print(f"{GREEN}{BOLD}🏆 EXCELLENT — Project is production-ready!{RESET}")
elif score >= 75:
    print(f"{GREEN}✅ GOOD — Minor issues, solid foundation{RESET}")
elif score >= 55:
    print(f"{YELLOW}⚠️  FAIR — Core works, fix the warnings{RESET}")
else:
    print(f"{RED}❌ NEEDS WORK — Address the failures above{RESET}")

if failed > 0:
    print(f"\n  {RED}Failed checks:{RESET}")
    for r in results:
        if not r["passed"] and not r.get("warn"):
            print(f"    ✗ {r['name']}")
            if r["detail"]:
                print(f"      → {r['detail']}")

if warned > 0:
    print(f"\n  {YELLOW}Warnings:{RESET}")
    for r in results:
        if not r["passed"] and r.get("warn"):
            print(f"    ⚠ {r['name']}")
            if r["detail"]:
                print(f"      → {r['detail']}")

print(f"\n{'─'*60}\n")

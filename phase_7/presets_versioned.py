"""
Versioned Emotion Presets for Phase 7 Evaluation
==================================================
Contains exact copies of EMOTION_PRESETS for evaluation reference,
plus conflict detection rules.

IMPORTANT:
  - EMOTION_PRESETS_v1 is an EXACT copy of phase_4r/strategy_converter.py EMOTION_PRESETS.
  - DO NOT modify v1 — it is the ground truth baseline.
  - v2 is a placeholder populated by human feedback over time.
  - EMOTION_DEFAULTS_v1 mirrors phase_4r/strategy_generator.py EMOTION_DEFAULTS.
"""

# ──────────────────────────────────────────────────────────────
# v1: Exact copy from phase_4r/strategy_converter.py
# ──────────────────────────────────────────────────────────────
EMOTION_PRESETS_v1 = {
    "fear":         {"intensity": 0.25, "color": "steel_blue",   "transition": "fade",      "duration": 3.0},
    "sadness":      {"intensity": 0.30, "color": "cool_blue",    "transition": "fade",      "duration": 4.0},
    "joy":          {"intensity": 0.85, "color": "warm_amber",   "transition": "cut",       "duration": 1.0},
    "anger":        {"intensity": 0.70, "color": "deep_red",     "transition": "cut",       "duration": 0.5},
    "surprise":     {"intensity": 0.90, "color": "bright_white", "transition": "cut",       "duration": 0.3},
    "neutral":      {"intensity": 0.50, "color": "warm_white",   "transition": "fade",      "duration": 2.0},
    "tension":      {"intensity": 0.35, "color": "cold_cyan",    "transition": "crossfade", "duration": 3.5},
    "mystery":      {"intensity": 0.20, "color": "deep_purple",  "transition": "fade",      "duration": 4.0},
    "anticipation": {"intensity": 0.60, "color": "gold",         "transition": "fade",      "duration": 2.5},
    "trust":        {"intensity": 0.65, "color": "soft_blue",    "transition": "fade",      "duration": 2.0},
    "disgust":      {"intensity": 0.40, "color": "sickly_green", "transition": "fade",      "duration": 2.0},
    "romance":      {"intensity": 0.45, "color": "rose_pink",    "transition": "crossfade", "duration": 3.0},
}

# ──────────────────────────────────────────────────────────────
# v1: Exact copy from phase_4r/strategy_generator.py
# ──────────────────────────────────────────────────────────────
EMOTION_DEFAULTS_v1 = {
    "fear":     {"intensity": 0.25, "color": "steel_blue",   "contrast": "high",   "temperature": "cold"},
    "sadness":  {"intensity": 0.30, "color": "cool_blue",    "contrast": "low",    "temperature": "cold"},
    "joy":      {"intensity": 0.85, "color": "warm_amber",   "contrast": "low",    "temperature": "warm"},
    "anger":    {"intensity": 0.70, "color": "deep_red",     "contrast": "high",   "temperature": "warm"},
    "surprise": {"intensity": 0.90, "color": "bright_white", "contrast": "high",   "temperature": "neutral"},
    "neutral":  {"intensity": 0.50, "color": "warm_white",   "contrast": "medium", "temperature": "neutral"},
    "disgust":  {"intensity": 0.40, "color": "sickly_green", "contrast": "medium", "temperature": "cold"},
}

# ──────────────────────────────────────────────────────────────
# v2: Adaptive presets (populated by human feedback)
# Starts as a copy of v1 — modified by AdaptivePresetManager
# ──────────────────────────────────────────────────────────────
EMOTION_PRESETS_v2 = dict(EMOTION_PRESETS_v1)


# ──────────────────────────────────────────────────────────────
# Color Classification — for conflict detection
# ──────────────────────────────────────────────────────────────
WARM_COLORS = {"warm_amber", "deep_red", "gold", "warm_white", "rose_pink"}
COLD_COLORS = {"steel_blue", "cool_blue", "cold_cyan", "deep_purple", "soft_blue"}
NEUTRAL_COLORS = {"bright_white", "white", "sickly_green"}


def get_color_temperature(color: str) -> str:
    """
    Classify a color name as warm, cold, or neutral.

    Args:
        color: Semantic color name.

    Returns:
        'warm', 'cold', or 'neutral'.
    """
    if color in WARM_COLORS:
        return "warm"
    elif color in COLD_COLORS:
        return "cold"
    else:
        return "neutral"


# ──────────────────────────────────────────────────────────────
# Conflict Rule Definitions
# ──────────────────────────────────────────────────────────────

# Emotions that MUST have low intensity (< threshold)
LOW_INTENSITY_EMOTIONS = {"fear", "sadness", "mystery"}
LOW_INTENSITY_MAX = 0.5

# Emotions that MUST have high intensity (> threshold)
HIGH_INTENSITY_EMOTIONS = {"joy", "surprise"}
HIGH_INTENSITY_MIN = 0.6

# Transitions that don't fit certain emotions
TRANSITION_CONFLICTS = {
    "sadness":  {"cut"},           # Cut is too abrupt for sadness
    "anger":    {"crossfade"},     # Crossfade is too gentle for anger
    "surprise": {"crossfade"},     # Crossfade is too slow for surprise
    "fear":     {"cut"},           # Cut is too sudden for building fear
}

# Maximum allowed secondary weight for warm+cold color blending
MAX_SECONDARY_WEIGHT_FOR_TEMPERATURE_MIX = 0.3

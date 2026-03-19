"""
Deterministic Lighting Engine

Converts emotion vectors → lighting states.
Fully deterministic. NO LLM. NO RAG.

Rules:
  - intensity = BASE_INTENSITY + (energy × ENERGY_INTENSITY_SCALE)
  - warmth derived from valence
  - color palette selected by emotion label
  - 60% primary / 25% secondary / 15% neutral anchor
  - Consecutive scenes are blended via LIGHTING_BLEND_FACTOR
  - No full-stage single saturated color
"""

from .config_full_context import (
    LIGHTING_BLEND_FACTOR,
    BASE_INTENSITY,
    ENERGY_INTENSITY_SCALE,
    PRIMARY_COLOR_RATIO,
    SECONDARY_COLOR_RATIO,
    ANCHOR_COLOR_RATIO,
)


# =============================================================================
# EMOTION → COLOR PALETTE MAP
# =============================================================================
# Each palette has: primary (60%), secondary (25%), anchor (15%).
# Anchor is always a desaturated neutral to prevent full-stage saturation.
# Hex values chosen for theatrical lighting aesthetics.

EMOTION_PALETTES = {
    # --- Positive high-energy ---
    "joy": {
        "primary":   "#FFB347",  # warm amber
        "secondary": "#FFD700",  # gold
        "anchor":    "#FFF5E1",  # soft cream
    },
    "excitement": {
        "primary":   "#FF6F61",  # coral
        "secondary": "#FFA07A",  # light salmon
        "anchor":    "#FFF0E0",  # peach cream
    },
    "triumph": {
        "primary":   "#DAA520",  # goldenrod
        "secondary": "#FF8C00",  # dark orange
        "anchor":    "#FFFACD",  # lemon chiffon
    },
    "amusement": {
        "primary":   "#FFD166",  # sunflower
        "secondary": "#06D6A0",  # mint
        "anchor":    "#F0F0E8",  # warm white
    },
    "elation": {
        "primary":   "#FFDF00",  # golden yellow
        "secondary": "#FF69B4",  # hot pink
        "anchor":    "#FFFFF0",  # ivory
    },

    # --- Positive low-energy ---
    "tenderness": {
        "primary":   "#FFB6C1",  # light pink
        "secondary": "#DDA0DD",  # plum
        "anchor":    "#FFF0F5",  # lavender blush
    },
    "serenity": {
        "primary":   "#87CEEB",  # sky blue
        "secondary": "#B0E0E6",  # powder blue
        "anchor":    "#F0F8FF",  # alice blue
    },
    "hope": {
        "primary":   "#98FB98",  # pale green
        "secondary": "#FFD700",  # gold
        "anchor":    "#F5FFFA",  # mint cream
    },

    # --- Negative high-energy ---
    "anger": {
        "primary":   "#C0392B",  # dark crimson (NOT pure red)
        "secondary": "#E74C3C",  # softer red
        "anchor":    "#2C2C2C",  # charcoal (prevents full-red stage)
    },
    "fear": {
        "primary":   "#4A235A",  # deep purple
        "secondary": "#1A1A2E",  # midnight blue
        "anchor":    "#3D3D3D",  # dark grey
    },
    "rage": {
        "primary":   "#8B0000",  # dark red
        "secondary": "#DC143C",  # crimson
        "anchor":    "#333333",  # dark charcoal
    },
    "disgust": {
        "primary":   "#556B2F",  # dark olive green
        "secondary": "#6B8E23",  # olive drab
        "anchor":    "#3E3E3E",  # grey
    },

    # --- Negative low-energy ---
    "sadness": {
        "primary":   "#4169E1",  # royal blue
        "secondary": "#6A5ACD",  # slate blue
        "anchor":    "#2F2F3F",  # dark blue-grey
    },
    "melancholy": {
        "primary":   "#5F6A8A",  # muted blue-grey
        "secondary": "#7B68AE",  # muted purple
        "anchor":    "#383848",  # dark slate
    },
    "grief": {
        "primary":   "#2C3E50",  # dark slate blue
        "secondary": "#34495E",  # wet asphalt
        "anchor":    "#1C1C1C",  # near black
    },
    "despair": {
        "primary":   "#1A1A2E",  # midnight
        "secondary": "#2C2C54",  # dark indigo
        "anchor":    "#0D0D0D",  # almost black
    },

    # --- Mid-range / dramatic ---
    "tension": {
        "primary":   "#B8860B",  # dark goldenrod
        "secondary": "#8B4513",  # saddle brown
        "anchor":    "#3B3B3B",  # dark grey
    },
    "suspense": {
        "primary":   "#2E4053",  # dark blue-grey
        "secondary": "#5D6D7E",  # cool grey
        "anchor":    "#1C2833",  # very dark blue
    },
    "mystery": {
        "primary":   "#483D8B",  # dark slate blue
        "secondary": "#6A5ACD",  # slate blue
        "anchor":    "#2C2C38",  # deep grey
    },
    "surprise": {
        "primary":   "#E67E22",  # carrot orange
        "secondary": "#F1C40F",  # sunflower yellow
        "anchor":    "#ECF0F1",  # light grey
    },
    "confusion": {
        "primary":   "#7F8C8D",  # grey
        "secondary": "#95A5A6",  # silver
        "anchor":    "#BDC3C7",  # light silver
    },
    "determination": {
        "primary":   "#E67E22",  # orange
        "secondary": "#D35400",  # pumpkin
        "anchor":    "#F5F5DC",  # beige
    },
    "betrayal": {
        "primary":   "#800020",  # burgundy
        "secondary": "#4A0000",  # very dark red
        "anchor":    "#2C2C2C",  # charcoal
    },

    # --- Neutral / default ---
    "neutral": {
        "primary":   "#A0A0A0",  # medium grey
        "secondary": "#C0C0C0",  # silver
        "anchor":    "#E8E8E8",  # light grey
    },
}


# =============================================================================
# COLOR UTILITIES
# =============================================================================

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (R, G, B) ints."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) ints to '#RRGGBB'."""
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def _blend_hex(color_a: str, color_b: str, factor: float) -> str:
    """
    Linearly interpolate two hex colors.
    factor = 1.0 → pure color_b (target).
    factor = 0.0 → pure color_a (previous).
    """
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    r = ra + (rb - ra) * factor
    g = ga + (gb - ga) * factor
    b = ba + (bb - ba) * factor
    return _rgb_to_hex(r, g, b)


def _color_distance(hex_a: str, hex_b: str) -> float:
    """Euclidean distance in RGB space (0–441.67 max)."""
    ra, ga, ba = _hex_to_rgb(hex_a)
    rb, gb, bb = _hex_to_rgb(hex_b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


# =============================================================================
# PUBLIC API
# =============================================================================

def get_emotion_palette(label: str) -> dict:
    """
    Look up the color palette for an emotion label.
    Falls back to "neutral" for unknown labels.
    """
    return EMOTION_PALETTES.get(label, EMOTION_PALETTES["neutral"])


def compute_lighting_state(scene: dict, prev_state: dict = None) -> dict:
    """
    Compute a single lighting state from a scene's emotion vector.

    Args:
        scene:      Scene dict with "emotion" sub-dict (label, energy, valence).
        prev_state: Previous lighting state dict (for blending), or None.

    Returns:
        Lighting state dict with keys:
            scene_id, intensity, warmth, palette (primary/secondary/anchor),
            color_ratios, blended (bool).
    """
    emo = scene["emotion"]
    energy = emo["energy"]
    valence = emo["valence"]
    label = emo["label"]

    # --- Intensity ---
    intensity = round(BASE_INTENSITY + (energy * ENERGY_INTENSITY_SCALE), 2)
    intensity = min(100.0, max(0.0, intensity))

    # --- Warmth ---
    warmth = round(valence, 4)

    # --- Palette ---
    target_palette = get_emotion_palette(label)

    # --- Blend with previous state ---
    blended = False
    if prev_state is not None:
        blended = True
        prev_palette = prev_state["palette"]
        palette = {
            "primary":   _blend_hex(prev_palette["primary"],   target_palette["primary"],   LIGHTING_BLEND_FACTOR),
            "secondary": _blend_hex(prev_palette["secondary"], target_palette["secondary"], LIGHTING_BLEND_FACTOR),
            "anchor":    _blend_hex(prev_palette["anchor"],    target_palette["anchor"],    LIGHTING_BLEND_FACTOR),
        }
    else:
        palette = dict(target_palette)  # copy

    return {
        "scene_id": scene.get("scene_id", "unknown"),
        "intensity": intensity,
        "warmth": warmth,
        "palette": palette,
        "color_ratios": {
            "primary": PRIMARY_COLOR_RATIO,
            "secondary": SECONDARY_COLOR_RATIO,
            "anchor": ANCHOR_COLOR_RATIO,
        },
        "blended": blended,
    }


def generate_all_lighting(scenes: list) -> list:
    """
    Generate lighting states for all scenes with carry-forward blending.

    Args:
        scenes: List of scene dicts (post-smoothing).

    Returns:
        List of lighting state dicts, one per scene.
    """
    states = []
    prev_state = None
    for scene in scenes:
        state = compute_lighting_state(scene, prev_state)
        states.append(state)
        prev_state = state
    return states


def calculate_lighting_continuity_score(states: list) -> float:
    """
    Measure lighting continuity across the sequence.

    Computes average color distance (primary channel) between adjacent states.
    Lower distance = smoother transitions.

    Returns:
        Continuity score as a float (0–100).
        100 = perfectly smooth, 0 = maximally discontinuous.
    """
    if len(states) < 2:
        return 100.0

    MAX_RGB_DIST = 441.67  # sqrt(255² + 255² + 255²)
    total_dist = 0.0
    pairs = len(states) - 1

    for i in range(1, len(states)):
        dist = _color_distance(
            states[i - 1]["palette"]["primary"],
            states[i]["palette"]["primary"],
        )
        total_dist += dist

    avg_dist = total_dist / pairs
    # Normalise to 0-100 (100 = smooth)
    score = round((1.0 - avg_dist / MAX_RGB_DIST) * 100, 2)
    return max(0.0, score)

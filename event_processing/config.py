"""
Event Processing Configuration

All constants, keyword weights, structural patterns, segment types,
and segment-to-lighting mappings live here. Nothing is hardcoded
elsewhere in the module.

Lighting parameter values are drawn from contracts/lighting_instruction_schema.json:
  - group_id: front_wash, back_light, side_fill, specials, ambient
  - transition types: fade, snap, smooth, crossfade, cut, pulse
  - intensity: 0.0–1.0
  - color_temperature: warm, neutral, cool
  - focus_area: center_stage, full_stage, etc.
"""

import re


# ============================================================================
# DETECTION KEYWORDS (phrase → weight)
# ============================================================================
# Higher weight = stronger signal for college event classification.
# Weights are summed and normalized against total word count.

EVENT_KEYWORDS = {
    # Ceremony markers (strongest signals)
    "lighting the lamp": 3.0,
    "lamp lighting": 3.0,
    "inauguration ceremony": 3.0,

    # Formal event markers
    "welcome address": 2.5,
    "chief guest": 2.5,
    "guest of honour": 2.5,
    "guest of honor": 2.5,
    "vote of thanks": 2.5,
    "annual day": 2.5,
    "annual function": 2.5,

    # College-specific
    "inauguration": 2.0,
    "cultural fest": 2.0,
    "cultural performance": 2.0,
    "symposium": 2.0,
    "technical symposium": 2.0,
    "convocation": 2.0,
    "orientation program": 2.0,
    "orientation programme": 2.0,

    # Moderate signals
    "principal": 1.5,
    "vice principal": 1.5,
    "department of": 1.5,
    "panel discussion": 1.5,
    "club presentation": 1.5,
    "club event": 1.5,
    "technical session": 1.5,
    "paper presentation": 1.5,
    "anchoring": 1.5,
    "anchoring script": 1.5,
    "compere": 1.5,
    "felicitation": 1.5,
    "prize distribution": 1.5,
    "award ceremony": 1.5,
    "guest lecture": 1.5,
    "keynote address": 1.5,
    "valedictory": 1.5,
    "valedictory function": 1.5,
    "fresher": 1.5,
    "freshers day": 1.5,

    # Weaker but supportive
    "national anthem": 1.0,
    "invocation": 1.0,
    "college": 1.0,
    "university": 1.0,
    "students": 1.0,
    "faculty": 1.0,
    "dean": 1.0,
    "hod": 1.0,
    "head of department": 1.0,
    "debate": 1.0,
    "quiz": 1.0,
    "conference": 1.0,
    "seminar": 1.0,
    "workshop": 1.0,
}


# ============================================================================
# STRUCTURAL PATTERNS (compiled regexes for agenda detection)
# ============================================================================

STRUCTURAL_PATTERNS = [
    # Time blocks: "10:00 AM - 11:00 AM" or "10:00 - 11:00"
    re.compile(
        r"\b\d{1,2}[.:]\d{2}\s*(?:am|pm|AM|PM)?\s*[-–—to]+\s*\d{1,2}[.:]\d{2}\s*(?:am|pm|AM|PM)?\b"
    ),
    # Numbered agenda items: "1." or "1)" at start of line
    re.compile(r"^\s*\d{1,2}[.)]\s+\S", re.MULTILINE),
    # Speaker markers
    re.compile(r"(?:Speaker|Presented by|By|Chief Guest|Guest of Honour?)\s*[:–—-]", re.IGNORECASE),
    # Formal section headers in caps
    re.compile(r"^[A-Z][A-Z\s]{5,}$", re.MULTILINE),
    # Time-only markers: "10:00 AM" standalone-ish
    re.compile(r"^\s*\d{1,2}[.:]\d{2}\s*(?:am|pm|AM|PM)\b", re.MULTILINE | re.IGNORECASE),
    # "Session 1", "Session 2", etc.
    re.compile(r"\bSession\s+\d+\b", re.IGNORECASE),
    # "Day 1", "Day 2", etc.
    re.compile(r"\bDay\s+\d+\b", re.IGNORECASE),
]


# ============================================================================
# SEGMENT TYPES
# ============================================================================

class SegmentTypes:
    """Enum-like constants for event segment classification."""
    SPEECH = "SPEECH"
    PERFORMANCE = "PERFORMANCE"
    AWARD = "AWARD"
    INTRODUCTION = "INTRODUCTION"
    TRANSITION = "TRANSITION"
    PANEL_DISCUSSION = "PANEL_DISCUSSION"
    TECHNICAL_PRESENTATION = "TECHNICAL_PRESENTATION"
    INAUGURATION = "INAUGURATION"


# ============================================================================
# SEGMENT CLASSIFIER RULES (ordered by priority — first match wins)
# ============================================================================
# Each rule: (keywords_list, segment_type)

SEGMENT_CLASSIFIER_RULES = [
    # Inauguration (highest priority — ceremonial)
    (
        ["inauguration", "lighting the lamp", "lamp lighting", "inaugural",
         "invocation", "national anthem"],
        SegmentTypes.INAUGURATION,
    ),
    # Performance
    (
        ["performance", "dance", "music", "skit", "cultural", "song",
         "drama", "play", "band", "choir", "orchestra", "act", "recital"],
        SegmentTypes.PERFORMANCE,
    ),
    # Award / Prize
    (
        ["award", "prize", "felicitation", "recognition", "trophy",
         "certificate", "medal", "honour", "honor", "appreciation"],
        SegmentTypes.AWARD,
    ),
    # Panel Discussion
    (
        ["panel discussion", "panel", "discussion", "debate", "forum",
         "roundtable", "round table"],
        SegmentTypes.PANEL_DISCUSSION,
    ),
    # Technical Presentation
    (
        ["technical", "paper presentation", "project", "demo", "demonstration",
         "presentation", "research", "poster", "hackathon", "coding",
         "workshop", "hands-on", "tutorial", "technical session"],
        SegmentTypes.TECHNICAL_PRESENTATION,
    ),
    # Speech (formal addresses)
    (
        ["speech", "address", "chief guest", "guest of honour", "guest of honor",
         "keynote", "principal", "vice principal", "dean", "hod",
         "welcome address", "presidential address", "guest lecture",
         "valedictory", "convocation address"],
        SegmentTypes.SPEECH,
    ),
    # Transition (closing, breaks)
    (
        ["vote of thanks", "closing", "break", "lunch", "tea break",
         "refreshment", "intermission", "interval", "thank you",
         "concluding", "farewell"],
        SegmentTypes.TRANSITION,
    ),
    # Introduction (default-ish, but explicit markers)
    (
        ["introduction", "welcome", "about", "overview", "orientation",
         "briefing", "anchoring", "compere", "emcee", "mc"],
        SegmentTypes.INTRODUCTION,
    ),
]


# ============================================================================
# SEGMENT → LIGHTING PROFILE MAPPING
# ============================================================================
# Each profile defines the 5 fixture groups from lighting_instruction_schema.json.
# Values: intensity (0.0–1.0), color (semantic name), color_temperature,
#         focus_area, transition type + duration.

SEGMENT_LIGHTING_MAP = {
    SegmentTypes.SPEECH: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.8,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.4,
                    "color": "soft_gold",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.5,
                    "color": "warm_white",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.6,
                    "color": "warm_white",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.3,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": "audience",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
        ],
    },

    SegmentTypes.PERFORMANCE: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.7,
                    "color": "vibrant_blue",
                    "color_temperature": "cool",
                    "focus_area": "full_stage",
                },
                "transition": {"type": "crossfade", "duration_seconds": 1.5},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.6,
                    "color": "deep_magenta",
                    "color_temperature": "cool",
                    "focus_area": None,
                },
                "transition": {"type": "crossfade", "duration_seconds": 1.5},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.65,
                    "color": "electric_purple",
                    "color_temperature": "cool",
                    "focus_area": None,
                },
                "transition": {"type": "crossfade", "duration_seconds": 1.5},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.9,
                    "color": "dynamic_color",
                    "color_temperature": "cool",
                    "focus_area": "full_stage",
                },
                "transition": {"type": "crossfade", "duration_seconds": 1.5},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.5,
                    "color": "color_wash",
                    "color_temperature": "cool",
                    "focus_area": "audience",
                },
                "transition": {"type": "crossfade", "duration_seconds": 1.5},
            },
        ],
    },

    SegmentTypes.AWARD: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.6,
                    "color": "golden",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "smooth", "duration_seconds": 2.0},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.35,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "smooth", "duration_seconds": 2.0},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.3,
                    "color": "soft_gold",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "smooth", "duration_seconds": 2.0},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 1.0,
                    "color": "spotlight_white",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "smooth", "duration_seconds": 2.0},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.2,
                    "color": "dim_warm",
                    "color_temperature": "warm",
                    "focus_area": "audience",
                },
                "transition": {"type": "smooth", "duration_seconds": 2.0},
            },
        ],
    },

    SegmentTypes.INAUGURATION: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.85,
                    "color": "warm_gold",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 3.0},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.5,
                    "color": "soft_amber",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 3.0},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.55,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 3.0},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.7,
                    "color": "ceremonial_gold",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 3.0},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.4,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": "audience",
                },
                "transition": {"type": "fade", "duration_seconds": 3.0},
            },
        ],
    },

    SegmentTypes.PANEL_DISCUSSION: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.75,
                    "color": "neutral_white",
                    "color_temperature": "neutral",
                    "focus_area": "full_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 1.5},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.4,
                    "color": "cool_white",
                    "color_temperature": "neutral",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 1.5},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.5,
                    "color": "neutral_white",
                    "color_temperature": "neutral",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 1.5},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.3,
                    "color": "subtle_wash",
                    "color_temperature": "neutral",
                    "focus_area": "full_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 1.5},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.4,
                    "color": "neutral_white",
                    "color_temperature": "neutral",
                    "focus_area": "audience",
                },
                "transition": {"type": "fade", "duration_seconds": 1.5},
            },
        ],
    },

    SegmentTypes.TECHNICAL_PRESENTATION: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.8,
                    "color": "cool_white",
                    "color_temperature": "cool",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "snap", "duration_seconds": 0.5},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.3,
                    "color": "steel_blue",
                    "color_temperature": "cool",
                    "focus_area": None,
                },
                "transition": {"type": "snap", "duration_seconds": 0.5},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.45,
                    "color": "cool_white",
                    "color_temperature": "cool",
                    "focus_area": None,
                },
                "transition": {"type": "snap", "duration_seconds": 0.5},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.5,
                    "color": "focused_white",
                    "color_temperature": "cool",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "snap", "duration_seconds": 0.5},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.3,
                    "color": "neutral_dim",
                    "color_temperature": "neutral",
                    "focus_area": "audience",
                },
                "transition": {"type": "snap", "duration_seconds": 0.5},
            },
        ],
    },

    SegmentTypes.TRANSITION: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.4,
                    "color": "soft_blue",
                    "color_temperature": "neutral",
                    "focus_area": "full_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 2.5},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.2,
                    "color": "dim_blue",
                    "color_temperature": "neutral",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.5},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.25,
                    "color": "soft_blue",
                    "color_temperature": "neutral",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.5},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.1,
                    "color": "off",
                    "color_temperature": None,
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.5},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.5,
                    "color": "ambient_wash",
                    "color_temperature": "neutral",
                    "focus_area": "audience",
                },
                "transition": {"type": "fade", "duration_seconds": 2.5},
            },
        ],
    },

    SegmentTypes.INTRODUCTION: {
        "groups": [
            {
                "group_id": "front_wash",
                "parameters": {
                    "intensity": 0.7,
                    "color": "warm_white",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "back_light",
                "parameters": {
                    "intensity": 0.35,
                    "color": "soft_amber",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "side_fill",
                "parameters": {
                    "intensity": 0.4,
                    "color": "warm_white",
                    "color_temperature": "warm",
                    "focus_area": None,
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "specials",
                "parameters": {
                    "intensity": 0.5,
                    "color": "warm_white",
                    "color_temperature": "warm",
                    "focus_area": "center_stage",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
            {
                "group_id": "ambient",
                "parameters": {
                    "intensity": 0.35,
                    "color": "warm_amber",
                    "color_temperature": "warm",
                    "focus_area": "audience",
                },
                "transition": {"type": "fade", "duration_seconds": 2.0},
            },
        ],
    },
}


# ============================================================================
# ALLOWED COLOR PALETTE (for LLM refinement constraint)
# ============================================================================

ALLOWED_COLORS = [
    "warm_amber", "soft_gold", "warm_white", "warm_gold", "soft_amber",
    "ceremonial_gold", "golden", "dim_warm",
    "vibrant_blue", "deep_magenta", "electric_purple", "dynamic_color",
    "color_wash", "soft_blue", "dim_blue",
    "cool_white", "steel_blue", "focused_white", "neutral_dim",
    "neutral_white", "subtle_wash", "ambient_wash",
    "spotlight_white", "off",
]

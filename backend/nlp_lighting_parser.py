import re
import logging

logger = logging.getLogger(__name__)

INTENSITY_KEYWORDS = {
    "blackout": 0, "off": 0, "very dim": 10, "dim": 25, "low": 30,
    "medium": 50, "half": 50, "bright": 75, "high": 80, "full": 100,
    "blinding": 100, "subtle": 20, "gentle": 25, "dark": 5
}

COLOR_KEYWORDS = {
    "red": "#FF0000", "warm": "#FFB347", "amber": "#FFB347",
    "cold": "#4488FF", "blue": "#3366FF", "cool blue": "#4682B4",
    "green": "#00CC44", "purple": "#7B00FF", "white": "#FFFFFF",
    "pink": "#FF69B4", "golden": "#FFD700", "reddish": "#CC3333",
    "orange": "#FF8C00", "lavender": "#9370DB", "cyan": "#00FFFF",
    "yellow": "#FFFF00", "magenta": "#FF00FF", "teal": "#008080"
}

FOCUS_KEYWORDS = {
    "center": "center_stage", "left": "stage_left", "right": "stage_right",
    "full": "full_stage", "back": "upstage", "front": "downstage",
    "spotlight": "center_stage",
}

GROUP_KEYWORDS = {
    "wash": "FRONT_WASH", "front": "FRONT_WASH",
    "back": "BACK_LIGHT", "blinder": "BACK_LIGHT",
    "side": "SIDE_FILL", "color": "SIDE_FILL",
    "spot": "SPECIALS", "spotlight": "SPECIALS", "moving": "SPECIALS",
    "ambient": "AMBIENT", "fill": "AMBIENT",
    "smoke": "SMOKE", "haze": "SMOKE", "fog": "SMOKE",
}

def parse_lighting_command(text: str) -> dict:
    """
    Parses a natural language string into structured lighting parameters.
    e.g., 'make lights dim and reddish on front stage'
    """
    text_lower = text.lower()
    
    # Initialize empty result
    result = {}
    
    # 1. Parse Intensity
    # Prioritize longest matches first, or exact matches
    found_intensity = None
    for kw, val in sorted(INTENSITY_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            found_intensity = val
            break
    if found_intensity is not None:
        result["intensity"] = found_intensity

    # 2. Parse Color
    found_color = None
    for kw, hex_val in sorted(COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            found_color = hex_val
            break
    if found_color is not None:
        result["color"] = found_color

    # 3. Parse Focus Area
    found_focus = None
    for kw, focus_val in sorted(FOCUS_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            found_focus = focus_val
            break
    if found_focus is not None:
        result["focus_area"] = found_focus
        
    # 4. Parse Fixture Groups
    found_groups = set()
    for kw, group_val in sorted(GROUP_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            found_groups.add(group_val)
    if found_groups:
        result["groups"] = list(found_groups)
        
    # Explicit hex color parser for "hex #ff0000" or just "#ff0000"
    hex_match = re.search(r'#(?:[0-9a-fA-F]{3}){1,2}\b', text_lower)
    if hex_match:
        result["color"] = hex_match.group(0).upper()
        
    return result

if __name__ == "__main__":
    tests = [
        "dim warm amber spotlight center",
        "blackout",
        "make it very dim and reddish",
        "flood the stage with blue wash and 50 percent intensity",
        "use #FF5500 for the back lights"
    ]
    for t in tests:
        print(f"| '{t}' -> {parse_lighting_command(t)}")

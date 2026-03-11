"""
Color utility functions for visualization
"""

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB to hex color
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        Hex color string (e.g., "#FF0000")
    """
    return f"#{r:02x}{g:02x}{b:02x}"

def get_color_name(r: int, g: int, b: int) -> str:
    """
    Get human-readable color name from RGB
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        Color name string
    """
    # Brightness
    brightness = (r + g + b) / 3
    
    # Check for grayscale
    if abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
        if brightness < 50:
            return "Black"
        elif brightness < 120:
            return "Dark Gray"
        elif brightness < 180:
            return "Gray"
        elif brightness < 230:
            return "Light Gray"
        else:
            return "White"
    
    # Dominant color
    max_val = max(r, g, b)
    
    if max_val == r:
        if g > 100 and b < 50:
            return "Orange" if g < 200 else "Yellow"
        elif b > 100:
            return "Magenta" if b > g else "Pink"
        else:
            return "Red"
    elif max_val == g:
        if r > 100:
            return "Yellow" if r > 200 else "Lime"
        elif b > 100:
            return "Cyan" if b > r else "Teal"
        else:
            return "Green"
    else:  # max_val == b
        if r > 100:
            return "Magenta" if r > g else "Purple"
        elif g > 100:
            return "Cyan" if g > r else "Sky Blue"
        else:
            return "Blue"

def dmx_to_percent(dmx_value: int) -> int:
    """
    Convert DMX value (0-255) to percentage (0-100)
    
    Args:
        dmx_value: DMX value (0-255)
        
    Returns:
        Percentage (0-100)
    """
    return int((dmx_value / 255) * 100)

def get_intensity_label(percent: int) -> str:
    """
    Get human-readable intensity label
    
    Args:
        percent: Intensity percentage (0-100)
        
    Returns:
        Label string
    """
    if percent == 0:
        return "Off"
    elif percent < 20:
        return "Very Dim"
    elif percent < 40:
        return "Dim"
    elif percent < 60:
        return "Medium"
    elif percent < 80:
        return "Bright"
    else:
        return "Very Bright"

# Semantic Color Palette
SEMANTIC_COLORS = {
    # Whites / Ambers
    "warm_white": "#FFD1A3",
    "cool_white": "#E3F3FF",
    "neutral_white": "#FFFFFF",
    "warm_amber": "#FFB347",
    "amber": "#FFBF00",
    "candlelight": "#FF9329",
    
    # Primaries
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    
    # Secondary / Theatrical
    "cool_blue": "#4A90E2",
    "night_blue": "#141E30",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "purple": "#800080",
    "lavender": "#E6E6FA",
    "teal": "#008080",
    "orange": "#FFA500",
    "yellow": "#FFFF00",
    "lime": "#00FF00",
    "pink": "#FFC0CB",
    "uv": "#3D0C02",
    "black": "#000000",
    "off": "#000000"
}

def get_hex_from_semantic(color_name: str) -> str:
    """
    Translate semantic color name to hex color.
    Returns white (#FFFFFF) if unknown, to ensure visibility.
    
    Args:
        color_name: Semantic name (e.g. "warm_amber", "Red")
        
    Returns:
        Hex string (e.g. "#FFB347")
    """
    if not color_name:
        return "#FFFFFF"
        
    # Normalize
    key = color_name.lower().replace(" ", "_")
    
    # Direct lookup
    if key in SEMANTIC_COLORS:
        return SEMANTIC_COLORS[key]
    
    # Check if it's already a hex code (simple validation)
    if key.startswith("#") and len(key) in [4, 7]:
        return color_name
        
    # Fallback
    return "#FFFFFF"
"""
Fixture Models Library
Defines distinct equipment types by their PHYSICAL capabilities.
Does NOT define manufacturer DMX profiles.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional

@dataclass
class FixtureProfile:
    model_name: str
    beam_angle_range: Tuple[float, float]  # (min, max) degrees
    has_color_mixing: bool                 # RGB/CMY
    has_gobo: bool
    pan_limit: Tuple[float, float]         # e.g., (-270, 270)
    tilt_limit: Tuple[float, float]        # e.g., (-135, 135)
    luminous_flux_approx: float            # Lumens (ballpark)

# --- Standard Library ---

# 1. Ellipsoidal (Lecko / Source 4)
# Fixed beam, warm white only (usually filtered)
SOURCE_FOUR_36 = FixtureProfile(
    model_name="ETC Source Four 36deg",
    beam_angle_range=(36.0, 36.0),
    has_color_mixing=False, # Gel only
    has_gobo=True,
    pan_limit=(0, 0),       # Fixed focus
    tilt_limit=(0, 0),
    luminous_flux_approx=10000.0
)

# 2. LED PAR Can
# General wash, mixing color
LED_PAR_ZOOM = FixtureProfile(
    model_name="Generic LED PAR Zoom",
    beam_angle_range=(15.0, 50.0),
    has_color_mixing=True,
    has_gobo=False,
    pan_limit=(0, 0),
    tilt_limit=(0, 0),
    luminous_flux_approx=4000.0
)

# 3. Moving Spot (The "Fancy" Light)
# Hard edge, gobos, moving
MAVERICK_SPOT = FixtureProfile(
    model_name="Chauvet Maverick Mk2 Spot",
    beam_angle_range=(13.0, 37.0),
    has_color_mixing=True, # CMY
    has_gobo=True,
    pan_limit=(-270, 270),
    tilt_limit=(-135, 135),
    luminous_flux_approx=20000.0
)

# 4. Moving Wash
# Soft edge, big color
MAC_AURA = FixtureProfile(
    model_name="Martin MAC Aura",
    beam_angle_range=(11.0, 58.0),
    has_color_mixing=True,
    has_gobo=False,
    pan_limit=(-270, 270),
    tilt_limit=(-100, 100),
    luminous_flux_approx=6000.0
)

# 5. Effects / Haze
# Atmospheric Generator
HAZE_GENERATOR = FixtureProfile(
    model_name="Generic Hazer",
    beam_angle_range=(180.0, 180.0), # Omnidirectional dispersal
    has_color_mixing=False,
    has_gobo=False,
    pan_limit=(0, 0),
    tilt_limit=(0, 0),
    luminous_flux_approx=0.0 # Creates media, emits no light itself
)

"""
Auditorium Layout & Patch (Refined from Photo)
Defines where fixtures are physically located and how Logical Groups map to them.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from .geometry import TRUSSES, Truss
from ..fixtures.models import FixtureProfile, SOURCE_FOUR_36, LED_PAR_ZOOM, MAVERICK_SPOT, HAZE_GENERATOR

@dataclass
class PhysicalFixture:
    uid: str
    profile: FixtureProfile
    position: Dict[str, float]  # {x, y, z} in meters
    orientation: Dict[str, float] # {pan, tilt} initial degrees
    truss_ref: str # Name of the truss it's hung on

# --- The Patch (Scenegraph) ---
INSTALLED_FIXTURES: List[PhysicalFixture] = []

def _mount_fixture(uid_prefix: str, profile: FixtureProfile, truss: Truss, offset_x: float):
    """Helper to hang a light on a truss"""
    INSTALLED_FIXTURES.append(PhysicalFixture(
        uid=f"{truss.name}_{uid_prefix}",
        profile=profile,
        position={"x": truss.x + offset_x, "y": truss.y, "z": truss.z},
        orientation={"pan": 0, "tilt": 0},
        truss_ref=truss.name
    ))

# 1. Main Face Pipe (Visible in Photo)
# 10x LED PARs distributed across the width
# Layout: 5 Left | [Center Proj Space] | 5 Right
truss = next(t for t in TRUSSES if t.name == "LX_Face_Pipe")

# Left Side (Outboard -> Inboard)
_mount_fixture("Face_L5", LED_PAR_ZOOM, truss, -5.0)
_mount_fixture("Face_L4", LED_PAR_ZOOM, truss, -4.0)
_mount_fixture("Face_L3", LED_PAR_ZOOM, truss, -3.0)
_mount_fixture("Face_L2", LED_PAR_ZOOM, truss, -2.0)
_mount_fixture("Face_L1", LED_PAR_ZOOM, truss, -1.0) # Closest to center

# Right Side (Inboard -> Outboard)
_mount_fixture("Face_R1", LED_PAR_ZOOM, truss, 1.0) # Closest to center
_mount_fixture("Face_R2", LED_PAR_ZOOM, truss, 2.0)
_mount_fixture("Face_R3", LED_PAR_ZOOM, truss, 3.0)
_mount_fixture("Face_R4", LED_PAR_ZOOM, truss, 4.0)
_mount_fixture("Face_R5", LED_PAR_ZOOM, truss, 5.0)

# 2. Upstage Pipe (Inferred - for Backlight/Color)
# 6x Movers for effects
truss_us = next(t for t in TRUSSES if t.name == "LX_Upstage")
_mount_fixture("Mover_L3", MAVERICK_SPOT, truss_us, -4.5)
_mount_fixture("Mover_L2", MAVERICK_SPOT, truss_us, -3.0)
_mount_fixture("Mover_L1", MAVERICK_SPOT, truss_us, -1.5)
_mount_fixture("Mover_R1", MAVERICK_SPOT, truss_us, 1.5)
_mount_fixture("Mover_R2", MAVERICK_SPOT, truss_us, 3.0)
_mount_fixture("Mover_R3", MAVERICK_SPOT, truss_us, 4.5)

# 3. Haze (Ground)
_mount_fixture("Haze_1", HAZE_GENERATOR, next(t for t in TRUSSES if t.name == "Floor"), 5.0)


# --- The "One-Way" Map ---
# Logical Group ID -> List of Physical UIDs
LOGICAL_TO_PHYSICAL_MAP: Dict[str, List[str]] = {
    # Front Wash: The main face pipe
    "front_wash": [
        "LX_Face_Pipe_Face_L5", "LX_Face_Pipe_Face_L4", "LX_Face_Pipe_Face_L3", "LX_Face_Pipe_Face_L2", "LX_Face_Pipe_Face_L1",
        "LX_Face_Pipe_Face_R1", "LX_Face_Pipe_Face_R2", "LX_Face_Pipe_Face_R3", "LX_Face_Pipe_Face_R4", "LX_Face_Pipe_Face_R5"
    ],
    
    # Overhead/Back Wash: The upstage movers
    "overhead_wash": [
        "LX_Upstage_Mover_L3", "LX_Upstage_Mover_L2", "LX_Upstage_Mover_L1",
        "LX_Upstage_Mover_R1", "LX_Upstage_Mover_R2", "LX_Upstage_Mover_R3"
    ],
    
    # Specials: Just the center-most face lights
    "specials": ["LX_Face_Pipe_Face_L1", "LX_Face_Pipe_Face_R1"],
    
    # Haze
    "haze": ["Floor_Haze_1"]
}

def get_fixtures_for_group(group_id: str) -> List[PhysicalFixture]:
    """Retrieve physical fixtures for a logical group key"""
    uids = LOGICAL_TO_PHYSICAL_MAP.get(group_id, [])
    return [f for f in INSTALLED_FIXTURES if f.uid in uids]

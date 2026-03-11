"""
Auditorium Physical Geometry Definition
Unit System: Meters (m)
Orientation: 
  - Y is Up
  - Z is Depth (Negative = Upstage, Positive = Downstage/Audience)
  - X is Width (Negative = Stage Left, Positive = Stage Right)
"""

from dataclasses import dataclass
from typing import List

@dataclass
class StageDimensions:
    width: float  # Proscenium width
    depth: float  # Depth from plaster line to back wall
    height: float # Deck height (usually 0 if deck is origin, or relative to floor)
    apron_depth: float # Depth of apron (in front of plaster line)

@dataclass
class Truss:
    name: str
    x: float      # Center point X
    y: float      # Height from stage floor
    z: float      # Depth (Z position)
    width: float  # Length of the pipe
    
# --- The Physical World ---

# Standard Proscenium Stage (Approx 12m wide, 10m deep)
STAGE = StageDimensions(
    width=12.0,
    depth=10.0,
    height=1.0,  # 1m raised stage
    apron_depth=2.0
)

# Rigging Points / Pipes (Refined from User Photo)
# Z=0 is plaster line. Z>0 is House, Z<0 is Stage.

TRUSSES: List[Truss] = [
    # 1. Main Face Pipe (Visible in photo)
    # Just in front of the wooden proscenium arch. 
    # Spans full width.
    Truss(name="LX_Face_Pipe", x=0, y=5.5, z=2.0, width=14.0),
    
    # 2. Upstage Pipe (Implied/Hidden behind header for backlight/cyc)
    Truss(name="LX_Upstage", x=0, y=5.5, z=-4.0, width=12.0),
    
    # 3. Floor (For Hazer/Floor cans)
    Truss(name="Floor", x=0, y=0, z=-2.0, width=12.0)
]

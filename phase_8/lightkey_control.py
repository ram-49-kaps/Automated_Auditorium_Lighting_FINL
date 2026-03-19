"""
Main LightKey control script - Direct execution
"""

import json
import time
import sys
from pathlib import Path

from utils.osc_sender import get_osc_client
from config import LIGHTKEY_FIXTURE_MAPPING

class LightKeyPlayer:
    """Real-time LightKey playback"""
    
    def __init__(self, cues_file: str):
        """
        Initialize player
        
        Args:
            cues_file: Path to cues JSON file
        """
        self.osc = get_osc_client()
        self.cues_file = cues_file
        self.cues = self._load_cues()
        
        print(f"\n{'='*70}")
        print(f"🎭 LIGHTKEY PLAYBACK ENGINE")
        print(f"{'='*70}\n")
        print(f"📁 Cues file: {cues_file}")
        print(f"📊 Total cues: {len(self.cues)}")
        print(f"⏱️  Duration: {self._get_duration():.1f}s")
        print(f"🎛️  OSC: {self.osc.ip}:{self.osc.port}")
        print(f"{'='*70}\n")
    
    def _load_cues(self) -> list:
        """Load cues from JSON"""
        with open(self.cues_file, 'r') as f:
            data = json.load(f)
        return data.get("cues", [])
    
    def _get_duration(self) -> float:
        """Get total duration"""
        if not self.cues:
            return 0
        return max(cue.get("end_time", 0) for cue in self.cues)
    
    def play(self):
        """Play cues in real-time"""
        if not self.cues:
            print("❌ No cues to play")
            return
        
        print("▶️  Starting playback...\n")
        
        start_time = time.time()
        
        try:
            for i, cue in enumerate(self.cues):
                # Wait until cue time
                cue_time = cue.get("start_time", 0)
                
                while time.time() - start_time < cue_time:
                    time.sleep(0.01)  # 10ms precision
                
                # Execute cue
                self._execute_cue(cue, i + 1)
            
            print("\n✅ Playback complete!\n")
        
        except KeyboardInterrupt:
            print("\n\n⏸️  Playback stopped by user\n")
            self.osc.blackout()
    
    def _execute_cue(self, cue: dict, cue_num: int):
        """
        Execute a single cue
        
        Args:
            cue: Cue dictionary
            cue_num: Cue number for display
        """
        scene_id = cue.get("scene_id", "unknown")
        emotion = cue.get("emotion", "neutral")
        start_time = cue.get("start_time", 0)
        
        print(f"[{self._format_time(start_time)}] {scene_id} ({emotion})")
        
        # Send to LightKey
        for fixture_cue in cue.get("cues", []):
            fixture_id = fixture_cue.get("fixture_id")
            dmx_channels = fixture_cue.get("dmx_channels", {})
            
            # Map to LightKey fixture number
            lightkey_num = LIGHTKEY_FIXTURE_MAPPING.get(fixture_id)
            
            if lightkey_num:
                self.osc.set_fixture_dmx_channels(lightkey_num, dmx_channels)
                
                # Debug output
                r = int(dmx_channels.get('1', 0))
                g = int(dmx_channels.get('2', 0))
                b = int(dmx_channels.get('3', 0))
                intensity = int(dmx_channels.get('8', 0))
                
                print(f"  → {fixture_id} (LK#{lightkey_num}): RGB({r},{g},{b}) @ {intensity}/255")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n⚠️  Usage: python lightkey_control.py <cues_file>\n")
        print("Example:")
        print("  python lightkey_control.py data/lighting_cues/Script-1_cues.json\n")
        sys.exit(1)
    
    cues_file = sys.argv[1]
    
    if not Path(cues_file).exists():
        print(f"\n❌ File not found: {cues_file}\n")
        sys.exit(1)
    
    # Create player
    player = LightKeyPlayer(cues_file)
    
    # Confirm before starting
    input("Press ENTER to start playback (or Ctrl+C to cancel)...")
    
    # Play
    player.play()

if __name__ == "__main__":
    main()
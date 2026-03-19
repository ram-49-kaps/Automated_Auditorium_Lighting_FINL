"""
OSC sender for LightKey control
"""

from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder
import time
from typing import Dict, List
from config import LIGHTKEY_OSC_IP, LIGHTKEY_OSC_PORT, LIGHTKEY_ENABLED

class LightKeyOSC:
    """LightKey OSC controller"""
    
    def __init__(self, ip=LIGHTKEY_OSC_IP, port=LIGHTKEY_OSC_PORT):
        """
        Initialize OSC client
        
        Args:
            ip: LightKey IP address
            port: LightKey OSC port
        """
        self.enabled = LIGHTKEY_ENABLED
        self.ip = ip
        self.port = port
        self.client = None
        
        if self.enabled:
            try:
                self.client = udp_client.SimpleUDPClient(ip, port)
                print(f"✅ LightKey OSC connected: {ip}:{port}")
            except Exception as e:
                print(f"❌ LightKey OSC connection failed: {e}")
                self.enabled = False
    
    def set_fixture_intensity(self, fixture_num: int, intensity: float):
        """
        Set fixture intensity (0.0 - 1.0)
        
        Args:
            fixture_num: Fixture number in LightKey (1-based)
            intensity: Intensity 0.0-1.0
        """
        if not self.enabled or not self.client:
            return
        
        try:
            # LightKey OSC address: /lightkey/fixture/{num}/intensity
            address = f"/lightkey/fixture/{fixture_num}/intensity"
            self.client.send_message(address, intensity)
        except Exception as e:
            print(f"❌ OSC send error: {e}")
    
    def set_fixture_color_rgb(self, fixture_num: int, r: int, g: int, b: int):
        """
        Set fixture RGB color (0-255)
        
        Args:
            fixture_num: Fixture number in LightKey
            r, g, b: RGB values 0-255
        """
        if not self.enabled or not self.client:
            return
        
        try:
            # Normalize to 0.0-1.0
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0
            
            # LightKey OSC addresses
            self.client.send_message(f"/lightkey/fixture/{fixture_num}/red", r_norm)
            self.client.send_message(f"/lightkey/fixture/{fixture_num}/green", g_norm)
            self.client.send_message(f"/lightkey/fixture/{fixture_num}/blue", b_norm)
        except Exception as e:
            print(f"❌ OSC color send error: {e}")
    
    def set_fixture_dmx_channels(self, fixture_num: int, dmx_channels: Dict[str, int]):
        """
        Set multiple DMX channels for a fixture
        
        Args:
            fixture_num: Fixture number
            dmx_channels: Dict of {channel: value}
        """
        if not self.enabled or not self.client:
            return
        
        # Extract RGB and intensity from common channels
        r = int(dmx_channels.get('1', 0))
        g = int(dmx_channels.get('2', 0))
        b = int(dmx_channels.get('3', 0))
        intensity_dmx = int(dmx_channels.get('8', 255))
        
        # Set color
        self.set_fixture_color_rgb(fixture_num, r, g, b)
        
        # Set intensity
        intensity = intensity_dmx / 255.0
        self.set_fixture_intensity(fixture_num, intensity)
    
    def blackout(self):
        """Turn off all fixtures"""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.send_message("/lightkey/blackout", 1.0)
        except Exception as e:
            print(f"❌ Blackout error: {e}")
    
    def restore(self):
        """Restore from blackout"""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.send_message("/lightkey/blackout", 0.0)
        except Exception as e:
            print(f"❌ Restore error: {e}")
    
    def send_raw_osc(self, address: str, value):
        """
        Send raw OSC message
        
        Args:
            address: OSC address (e.g., "/lightkey/go")
            value: OSC value
        """
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.send_message(address, value)
        except Exception as e:
            print(f"❌ Raw OSC error: {e}")

# Global instance
_osc_client = None

def get_osc_client():
    """Get singleton OSC client"""
    global _osc_client
    if _osc_client is None:
        _osc_client = LightKeyOSC()
    return _osc_client
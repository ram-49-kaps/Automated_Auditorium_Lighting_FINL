"""
MIDI Setup Helper for macOS
"""

import subprocess
import mido

def check_iac_driver():
    """Check if IAC Driver is enabled"""
    print("\n" + "="*70)
    print("🎹 MIDI SETUP CHECKER")
    print("="*70 + "\n")
    
    print("📡 Available MIDI ports:")
    ports = mido.get_output_names()
    
    if not ports:
        print("   ❌ No MIDI ports found!\n")
        print("🔧 TO FIX:")
        print("   1. Open 'Audio MIDI Setup' app")
        print("   2. Go to: Window → Show MIDI Studio")
        print("   3. Double-click 'IAC Driver'")
        print("   4. Check 'Device is online'")
        print("   5. Make sure 'Bus 1' exists")
        print("   6. Click 'Apply'\n")
        return False
    
    for i, port in enumerate(ports, 1):
        print(f"   {i}. {port}")
    
    print("\n✅ MIDI ports detected!")
    
    # Check for IAC Driver
    iac_found = any("IAC" in port for port in ports)
    
    if iac_found:
        print("✅ IAC Driver found!")
        print("\n📋 Recommended port: IAC Driver Bus 1")
    else:
        print("⚠️  IAC Driver not found!")
        print("\n🔧 TO ENABLE IAC Driver:")
        print("   1. Open 'Audio MIDI Setup' (/Applications/Utilities/)")
        print("   2. Window → Show MIDI Studio")
        print("   3. Double-click 'IAC Driver'")
        print("   4. Check ☑ 'Device is online'")
        print("   5. Click 'Apply'")
    
    print("\n" + "="*70)
    
    return iac_found

def test_midi_output():
    """Test MIDI output"""
    print("\n🧪 Testing MIDI output...")
    
    ports = mido.get_output_names()
    
    if not ports:
        print("❌ No ports available to test\n")
        return
    
    test_port = ports[0]
    print(f"   Using port: {test_port}")
    
    try:
        output = mido.open_output(test_port)
        
        # Send test note
        msg = mido.Message('note_on', note=60, velocity=64)
        output.send(msg)
        
        print("   ✅ Test message sent!")
        print(f"   Sent: {msg}")
        
        output.close()
        print("\n✅ MIDI is working!\n")
    
    except Exception as e:
        print(f"   ❌ Test failed: {e}\n")

def main():
    """Main setup function"""
    check_iac_driver()
    test_midi_output()
    
    print("📝 NEXT STEPS:")
    print("   1. Configure LightKey to receive MIDI")
    print("   2. Update config.py with correct MIDI port")
    print("   3. Run: python lightkey_midi_control.py\n")

if __name__ == "__main__":
    main()
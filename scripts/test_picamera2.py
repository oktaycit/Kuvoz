#!/usr/bin/env python3
import sys
import os

print("--- Checking Python Environment for Picamera2 ---")

try:
    import libcamera
    print(f"✅ libcamera module found: {libcamera}")
except ImportError as e:
    print(f"❌ libcamera module NOT found: {e}")

try:
    from picamera2 import Picamera2
    print(f"✅ Picamera2 module found: {Picamera2}")
    
    print("\n--- Checking Available Cameras ---")
    try:
        cameras = Picamera2.global_camera_info()
        print(f"Detected cameras: {cameras}")
        
        if not cameras:
            print("❌ No cameras detected by libcamera!")
            print("\nTroubleshooting steps:")
            print("1. Check camera connection (ribbon cable)")
            print("2. Run: libcamera-hello --list-cameras")
            print("3. Check camera is enabled in raspi-config")
            print("4. Ensure you're on legacy camera stack or have proper libcamera support")
            sys.exit(1)
            
        print(f"✅ Found {len(cameras)} camera(s)")
        
    except Exception as e:
        print(f"❌ Error checking cameras: {e}")
        sys.exit(1)
    
    print("\n--- Attempting to Initialize Picamera2 ---")
    try:
        picam = Picamera2()
        print("Picamera2 object created.")
        
        config = picam.create_still_configuration(main={"size": (640, 480), "format": "BGR888"})
        print("Configuration created.")
        
        picam.configure(config)
        print("Camera configured.")
        
        picam.start()
        print("Camera started.")
        
        frame = picam.capture_array()
        print(f"✅ Frame captured! Shape: {frame.shape}")
        
        picam.stop()
        print("✅ Camera stopped successfully.")
        
    except Exception as e:
        print(f"❌ Error during Picamera2 execution: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError as e:
    print(f"❌ Picamera2 module NOT found: {e}")
    print("\nPossible solutions:")
    print("1. Install it via apt: sudo apt install python3-libcamera python3-kms++")
    print("2. If in a venv, you need to enable system-site-packages or install it manually (difficult).")

print("-" * 30)

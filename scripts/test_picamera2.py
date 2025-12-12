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
        print(f"Frame captured! Shape: {frame.shape}")
        
        picam.stop()
        print("Camera stopped.")
        
    except Exception as e:
        print(f"❌ Error during Picamera2 execution: {e}")
        
except ImportError as e:
    print(f"❌ Picamera2 module NOT found: {e}")
    print("\nPossible solutions:")
    print("1. Install it via apt: sudo apt install python3-libcamera python3-kms++")
    print("2. If in a venv, you need to enable system-site-packages or install it manually (difficult).")

print("-" * 30)

#!/usr/bin/env python3
import cv2
import os
import subprocess
import sys
import time

def check_devices():
    print("--- Checking /dev/video* devices ---")
    devices = [f for f in os.listdir('/dev') if f.startswith('video')]
    if devices:
        print(f"Found devices: {devices}")
    else:
        print("No /dev/video* devices found.")
    print("-" * 30)

def check_vcgencmd():
    print("--- Checking vcgencmd get_camera ---")
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], capture_output=True, text=True)
        print(f"Output: {result.stdout.strip()}")
    except FileNotFoundError:
        print("vcgencmd not found (might be non-Raspberry Pi OS or new stack)")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

def check_libcamera():
    print("--- Checking libcamera-hello ---")
    try:
        result = subprocess.run(['libcamera-hello', '--list-cameras'], capture_output=True, text=True)
        print(f"Output:\n{result.stdout.strip()}")
    except FileNotFoundError:
        print("libcamera-hello not found")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

def test_opencv_capture(index=0, backend=None):
    print(f"--- Testing OpenCV Capture (Index {index}, Backend {backend}) ---")
    try:
        if backend:
            cap = cv2.VideoCapture(index, backend)
        else:
            cap = cv2.VideoCapture(index)
            
        if not cap.isOpened():
            print(f"Failed to open camera at index {index}")
            return False
        
        print(f"Camera opened successfully at index {index}")
        
        # Try to force MJPEG
        print("Attempting to set FOURCC to MJPG...")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print("Frame captured successfully with MJPEG")
            filename = f"test_capture_{index}_mjpeg.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved frame to {filename}")
        else:
            print("Failed to read frame even with MJPEG")
            
        cap.release()
        return True
    except Exception as e:
        print(f"Exception during OpenCV capture: {e}")
        return False
    finally:
        print("-" * 30)

if __name__ == "__main__":
    print("Starting Camera Diagnosis...")
    check_devices()
    check_vcgencmd()
    check_libcamera()
    
    # Test default
    print("Testing default backend...")
    test_opencv_capture(0)
    
    # Test V4L2 explicitly
    print("Testing V4L2 backend...")
    test_opencv_capture(0, cv2.CAP_V4L2)
    
    print("Diagnosis complete.")

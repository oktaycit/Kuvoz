#!/usr/bin/env python3
import cv2
import time

def test_yuyv():
    print("--- Testing YUYV Capture on /dev/video0 ---")
    # Enforce V4L2 backend to avoid GStreamer auto-negotiation issues
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print("Failed to open camera!")
        return

    print("Camera opened. Setting format to YUYV 640x480...")
    
    # Set YUYV
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Warmup
    time.sleep(2)
    
    print("Attempting to capture frame...")
    ret, frame = cap.read()
    
    if ret:
        print("SUCCESS: Frame captured!")
        print(f"Shape: {frame.shape}")
        cv2.imwrite("test_yuyv.jpg", frame)
    else:
        print("FAILURE: Could not read frame.")
    
    cap.release()

if __name__ == "__main__":
    test_yuyv()

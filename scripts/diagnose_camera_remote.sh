#!/bin/bash
# Run camera diagnostics on Raspberry Pi via SSH

echo "=== Running Camera Diagnostics on Raspberry Pi ==="
echo ""

# SSH to the Pi and run diagnostics
ssh oktay@raspberrypi << 'ENDSSH'

echo "--- 1. Checking libcamera-hello ---"
libcamera-hello --list-cameras 2>&1

echo ""
echo "--- 2. Checking vcgencmd ---"
vcgencmd get_camera 2>&1

echo ""
echo "--- 3. Checking /dev/video* devices ---"
ls -l /dev/video* 2>&1 || echo "No /dev/video* devices found"

echo ""
echo "--- 4. Checking /boot/firmware/config.txt camera settings ---"
grep -i camera /boot/firmware/config.txt 2>/dev/null || grep -i camera /boot/config.txt 2>/dev/null || echo "No camera config found"

echo ""
echo "--- 5. Checking dmesg for camera errors ---"
sudo dmesg | grep -i camera | tail -20

echo ""
echo "--- 6. Running Picamera2 test ---"
cd ~/kuvoz
python3 scripts/test_picamera2.py

ENDSSH

echo ""
echo "=== Diagnostics Complete ==="

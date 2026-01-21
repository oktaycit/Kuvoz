#!/bin/bash
# Kiosk X Session - runs inside X server

# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Start Openbox window manager
openbox &
sleep 2

# Determine browser command
if command -v chromium-browser >/dev/null 2>&1; then
    CMD=chromium-browser
elif command -v chromium >/dev/null 2>&1; then
    CMD=chromium
else
    echo 'Browser bulunamadı!' && exit 1
fi

# Launch Chromium in kiosk mode
FLAGS="--kiosk --no-sandbox --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --ignore-certificate-errors --check-for-update-interval=31536000 --disable-pinch --no-first-run --disable-translate --disable-features=TranslateUI"

# Keep retrying if browser crashes
while true; do
    $CMD $FLAGS http://localhost:8000
    sleep 5
done

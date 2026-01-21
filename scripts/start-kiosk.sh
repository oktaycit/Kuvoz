#!/bin/bash
# Kuvoz Kiosk Başlatma Script'i - X Server ile

# Wait for system to be ready
sleep 10

# Start X server with Openbox window manager if not already running
if ! pidof X > /dev/null; then
    echo "Starting X server..."
    startx /home/vet/kuvoz/scripts/kiosk-session.sh -- :0 vt1 &
    sleep 5
else
    echo "X server already running"
    # Just launch browser directly
    export DISPLAY=:0
    
    # Determine browser command
    if command -v chromium-browser >/dev/null 2>&1; then
        CMD=chromium-browser
    elif command -v chromium >/dev/null 2>&1; then
        CMD=chromium
    else
        echo 'Browser bulunamadı! Chromium kurulumu gerekli.' && exit 1
    fi
    
    # Disable screen blanking
    xset s off 2>/dev/null || true
    xset -dpms 2>/dev/null || true
    xset s noblank 2>/dev/null || true
    
    # Kill existing chromium instances
    pkill -f chromium
    sleep 2
    
    # Launch browser with robust flags
    FLAGS="--kiosk --no-sandbox --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --ignore-certificate-errors --check-for-update-interval=31536000 --disable-pinch --no-first-run --disable-translate --disable-features=TranslateUI"
    $CMD $FLAGS http://localhost:8000
fi


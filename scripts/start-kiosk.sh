#!/bin/bash
# Kuvoz Kiosk Başlatma Script'i
sleep 5
export DISPLAY=:0
# Trixie/Wayland compatibility flags
FLAGS="--kiosk --no-sandbox --ozone-platform-hint=auto --enable-features=UseOzonePlatform --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --disable-dev-shm-usage --disable-gpu"
if command -v chromium-browser >/dev/null 2>&1; then
    CMD=chromium-browser
elif command -v chromium >/dev/null 2>&1; then
    CMD=chromium
else
    echo 'Browser bulunamadı! Chromium kurulumu gerekli.' && exit 1
fi
$CMD $FLAGS http://localhost:8000

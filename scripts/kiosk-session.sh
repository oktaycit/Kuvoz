#!/bin/bash
# Kiosk X Session - runs inside X server

# Ensure a DBus session exists to reduce Chromium DBus errors
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    if command -v dbus-run-session >/dev/null 2>&1; then
        exec dbus-run-session -- "$0" "$@"
    elif command -v dbus-launch >/dev/null 2>&1; then
        eval "$(dbus-launch --sh-syntax)"
    fi
fi

# Best-effort XDG runtime dir for DBus clients
if [ -z "$XDG_RUNTIME_DIR" ]; then
    RUNDIR="/run/user/$(id -u)"
    if [ -d "$RUNDIR" ]; then
        export XDG_RUNTIME_DIR="$RUNDIR"
    fi
fi

# Force a Turkish UTF-8 session so Chromium renders locale-sensitive text consistently.
export LANG="${LANG:-tr_TR.UTF-8}"
export LANGUAGE="${LANGUAGE:-tr_TR:tr}"
export LC_CTYPE="${LC_CTYPE:-tr_TR.UTF-8}"

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
FLAGS="--kiosk --no-sandbox --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --ignore-certificate-errors --check-for-update-interval=31536000 --disable-pinch --no-first-run --disable-translate --disable-features=TranslateUI --lang=tr-TR --accept-lang=tr-TR,tr,en-US,en"

# Keep retrying if browser crashes
while true; do
    $CMD $FLAGS http://localhost:8000
    sleep 5
done

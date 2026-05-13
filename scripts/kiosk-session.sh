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

wait_for_web_ui() {
    local url="http://localhost:8000/"
    local max_attempts=30
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
                return 0
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -q --spider --timeout=2 "$url"; then
                return 0
            fi
        else
            return 0
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    return 0
}

# Force a Turkish UTF-8 session so Chromium renders locale-sensitive text consistently.
export LANG="${LANG:-tr_TR.UTF-8}"
export LANGUAGE="${LANGUAGE:-tr_TR:tr}"
export LC_CTYPE="${LC_CTYPE:-tr_TR.UTF-8}"

disable_screen_blanking() {
    echo "Disabling screen blanking and display power management..."
    if command -v xset >/dev/null 2>&1; then
        xset s off || true
        xset -dpms || true
        xset s noblank || true
        xset q 2>/dev/null | sed -n '/Screen Saver:/,/DPMS/p' || true
    fi

    if command -v vcgencmd >/dev/null 2>&1; then
        vcgencmd display_power 1 >/dev/null 2>&1 || true
    fi
}

disable_screen_blanking

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
FLAGS="--kiosk --no-sandbox --touch-events=enabled --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --ignore-certificate-errors --check-for-update-interval=31536000 --disable-pinch --no-first-run --disable-translate --disable-features=TranslateUI --lang=tr-TR --accept-lang=tr-TR,tr,en-US,en"

# Keep retrying if browser crashes
while true; do
    wait_for_web_ui
    $CMD $FLAGS http://localhost:8000
    sleep 5
done

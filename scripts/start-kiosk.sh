#!/bin/bash
# Kuvoz Kiosk Başlatma Script'i - X Server ile

# Wait for system to be ready
sleep 10

wait_for_web_ui() {
    local url="http://localhost:8000/"
    local max_attempts=30
    local attempt=1

    echo "Waiting for web UI on $url ..."
    while [ "$attempt" -le "$max_attempts" ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
                echo "Web UI is ready"
                return 0
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -q --spider --timeout=2 "$url"; then
                echo "Web UI is ready"
                return 0
            fi
        else
            # If no HTTP probe tool exists, don't block kiosk startup forever.
            return 0
        fi

        echo "Web UI not ready yet ($attempt/$max_attempts)"
        attempt=$((attempt + 1))
        sleep 2
    done

    echo "Web UI probe timed out, continuing anyway"
    return 0
}

# Best-effort XDG runtime dir for DBus clients
if [ -z "$XDG_RUNTIME_DIR" ]; then
    RUNDIR="/run/user/$(id -u)"
    if [ -d "$RUNDIR" ]; then
        export XDG_RUNTIME_DIR="$RUNDIR"
    fi
fi

# Force a Turkish UTF-8 session so Chromium and font fallback resolve locale-sensitive glyphs correctly.
export LANG="${LANG:-tr_TR.UTF-8}"
export LANGUAGE="${LANGUAGE:-tr_TR:tr}"
export LC_CTYPE="${LC_CTYPE:-tr_TR.UTF-8}"

# Detect if X is already running (Xorg or X)
if pgrep -x Xorg >/dev/null || pgrep -x X >/dev/null; then
    X_ALREADY_RUNNING=1
else
    X_ALREADY_RUNNING=0
fi

if [ "$X_ALREADY_RUNNING" -eq 0 ]; then
    echo "Starting X server..."
    # Ensure session script exists or fallback
    if [ ! -f /home/vet/kuvoz/scripts/kiosk-session.sh ]; then
        echo "Warning: kiosk-session.sh missing, creating fallback..."
        mkdir -p /home/vet/kuvoz/scripts
        cat > /home/vet/kuvoz/scripts/kiosk-session.sh <<EOF
#!/bin/bash
openbox &
chromium-browser --kiosk --no-sandbox http://localhost:8000
EOF
        chmod +x /home/vet/kuvoz/scripts/kiosk-session.sh
    fi
    startx /home/vet/kuvoz/scripts/kiosk-session.sh -- :0 vt1 &
    sleep 5
else
    echo "X server already running"
    # Just launch browser directly
    export DISPLAY=:0
    export XAUTHORITY=/home/vet/.Xauthority
    wait_for_web_ui
    
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
    FLAGS="--user-data-dir=/home/vet/kuvoz/chromium-data --disk-cache-dir=/home/vet/kuvoz/chromium-data --kiosk --no-sandbox --ozone-platform-hint=auto --enable-features=UseOzonePlatform --touch-events=enabled --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --ignore-certificate-errors --check-for-update-interval=31536000 --disable-pinch --no-first-run --disable-translate --disable-features=TranslateUI --lang=tr-TR --accept-lang=tr-TR,tr,en-US,en"
    RUN_PREFIX=""
    if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
        if command -v dbus-run-session >/dev/null 2>&1; then
            RUN_PREFIX="dbus-run-session --"
        elif command -v dbus-launch >/dev/null 2>&1; then
            eval "$(dbus-launch --sh-syntax)"
        fi
    fi
    $RUN_PREFIX $CMD $FLAGS http://localhost:8000
fi

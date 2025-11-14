#!/bin/bash
# Kuvoz Kiosk Mode Startup Script
# Chromium browser kiosk mode for web interface

# Değişkenler
WEB_URL="http://localhost:8000"
PORT="8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/kiosk.log"

# Log klasörü oluştur
mkdir -p "$PROJECT_DIR/logs"

# Log fonksiyonu
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# IP adresini al
get_local_ip() {
    # Önce network IP'yi dene
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$LOCAL_IP" ]; then
        # Alternatif yöntem
        LOCAL_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}')
    fi
    if [ -z "$LOCAL_IP" ]; then
        LOCAL_IP="127.0.0.1"
    fi
    echo "$LOCAL_IP"
}

log "🖥️  Starting Kuvoz Kiosk Mode..."

# Web server'ın çalışıp çalışmadığını kontrol et
check_web_server() {
    for i in {1..30}; do
        if curl -s "$WEB_URL" > /dev/null 2>&1; then
            log "✅ Web server is responding"
            return 0
        fi
        log "⏳ Waiting for web server... (attempt $i/30)"
        sleep 2
    done
    log "❌ Web server not responding after 60 seconds"
    return 1
}

# Display ayarları
setup_display() {
    log "🔧 Setting up display..."
    
    # Screen saver ve power management kapatma
    xset -dpms
    xset s off
    xset s noblank
    
    # Hide cursor after inactivity
    unclutter -idle 1 -root &
    
    log "✅ Display setup completed"
}

# Chromium kiosk başlatma
start_chromium_kiosk() {
    log "🚀 Starting Chromium in kiosk mode..."
    
    # Chromium executable bulma (Trixie'de farklı isimler olabilir)
    CHROMIUM_CMD=""
    if command -v chromium >/dev/null 2>&1; then
        CHROMIUM_CMD="chromium"
    elif command -v chromium-browser >/dev/null 2>&1; then
        CHROMIUM_CMD="chromium-browser"
    elif command -v google-chrome >/dev/null 2>&1; then
        CHROMIUM_CMD="google-chrome"
    else
        log "❌ No Chromium/Chrome found!"
        return 1
    fi
    
    log "✅ Using: $CHROMIUM_CMD"
    
    # Chromium ayarları
    CHROMIUM_ARGS=(
        --kiosk
        --no-sandbox
        --disable-dev-shm-usage
        --disable-gpu
        --disable-software-rasterizer
        --disable-background-timer-throttling
        --disable-backgrounding-occluded-windows
        --disable-renderer-backgrounding
        --disable-features=VizDisplayCompositor,TranslateUI
        --disable-ipc-flooding-protection
        --disable-background-networking
        --disable-sync
        --disable-translate
        --disable-extensions
        --disable-plugins
        --disable-web-security
        --disable-popup-blocking
        --disable-prompt-on-repost
        --no-first-run
        --no-default-browser-check
        --no-crash-upload
        --start-fullscreen
        --window-position=0,0
        --touch-events=enabled
        --force-device-scale-factor=1
        --disk-cache-size=52428800
        --media-cache-size=52428800
        --aggressive-cache-discard
        --disable-application-cache
        --app="$WEB_URL"
        --user-data-dir="$PROJECT_DIR/chromium-data"
        --log-level=1
    )
    
    # Chromium başlat
    exec "$CHROMIUM_CMD" "${CHROMIUM_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up kiosk mode..."
    pkill -f chromium-browser || true
    pkill unclutter || true
    exit 0
}

# Signal handlers
trap cleanup SIGTERM SIGINT

# Ana işlem
main() {
    log "📍 Working directory: $PROJECT_DIR"

    # IP adresini al ve göster
    NETWORK_IP=$(get_local_ip)
    log "📱 Local access:   http://localhost:$PORT"
    log "🌐 Network access: http://$NETWORK_IP:$PORT"

    # Web server kontrolü
    if ! check_web_server; then
        log "❌ Cannot start kiosk mode - web server not available"
        exit 1
    fi
    
    # Display ayarları
    setup_display
    
    # Kısa bekleme
    sleep 3
    
    # Chromium başlat
    start_chromium_kiosk
}

# Script başlat
main "$@"
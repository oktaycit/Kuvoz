#!/bin/bash
# Kuvoz Firefox Kiosk Mode Startup Script
# Firefox browser kiosk mode for web interface

# Değişkenler
WEB_URL="http://localhost:8000"
PORT="8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/firefox-kiosk.log"

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

log "🖥️  Starting Kuvoz Firefox Kiosk Mode..."

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

# Firefox kiosk başlatma
start_firefox_kiosk() {
    log "🚀 Starting Firefox in kiosk mode..."
    
    # Firefox profil dizini
    FIREFOX_PROFILE_DIR="$PROJECT_DIR/firefox-profile"
    mkdir -p "$FIREFOX_PROFILE_DIR"
    
    # Firefox ayarları
    FIREFOX_ARGS=(
        -kiosk
        "$WEB_URL"
        -new-instance
        -profile "$FIREFOX_PROFILE_DIR"
    )
    
    # Firefox environment variables
    export MOZ_DISABLE_AUTO_UPDATE=1
    export MOZ_DISABLE_TELEMETRY=1
    
    # Firefox başlat
    exec firefox "${FIREFOX_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up Firefox kiosk mode..."
    pkill -f firefox || true
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
    
    # Firefox başlat
    start_firefox_kiosk
}

# Script başlat
main "$@"

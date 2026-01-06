#!/bin/bash
# Kuvoz Kiosk Mode - Lightweight Edition (Zero 2 W için)
# Midori veya Firefox ESR kullanır (Chromium yerine)

# Değişkenler
WEB_URL="http://localhost:8000"
PORT="8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/kiosk-lite.log"

# Log klasörü oluştur
mkdir -p "$PROJECT_DIR/logs"

# Log fonksiyonu
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "🖥️  Starting Kuvoz Kiosk Mode (Lite)..."
log "📍 Working directory: $PROJECT_DIR"

# IP adresini al
LOCAL_IP=$(hostname -I | awk '{print $1}' || echo "127.0.0.1")
log "📱 Local access:   http://localhost:$PORT"
log "🌐 Network access: http://$LOCAL_IP:$PORT"

# Web server'ın çalışıp çalışmadığını kontrol et
log "⏳ Checking web server..."
for i in {1..15}; do
    if curl -s "$WEB_URL" > /dev/null 2>&1; then
        log "✅ Web server is responding"
        break
    fi
    if [ $i -eq 15 ]; then
        log "❌ Web server not responding after 30 seconds"
        log "💡 Start web server: sudo systemctl start kuvoz-web"
        exit 1
    fi
    sleep 2
done

# DISPLAY değişkeni kontrolü ve ayarlama
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    log "🔧 DISPLAY set to :0"
fi

# X server çalışıyor mu kontrol et
if ! xset q &>/dev/null; then
    log "❌ X server not running!"
    log "💡 Lite OS kullanıyorsanız:"
    log "   1. X server kur: sudo apt install xserver-xorg-core xinit openbox"
    log "   2. X'i başlat: startx &"
    log "   3. Veya browser kiosk yerine uzaktan erişim kullanın"
    exit 1
fi

# Display ayarları (hata varsa görmezden gel)
xset s off &>/dev/null || true
xset -dpms &>/dev/null || true
xset s noblank &>/dev/null || true

# Unclutter (mouse cursor gizle)
if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle 0.1 -root &>/dev/null &
    log "✅ Mouse cursor hidden"
fi

sleep 3

# Hafif browser seçimi (Zero 2 W için optimize)
log "🚀 Starting lightweight browser..."

# 1. Midori (en hafif)
if command -v midori >/dev/null 2>&1; then
    log "✅ Using: midori (lightweight)"
    midori -e Fullscreen -a "$WEB_URL" &>/dev/null &
    log "✅ Midori started in kiosk mode"
    exit 0
fi

# 2. Firefox ESR (Chromium'dan hafif)
if command -v firefox-esr >/dev/null 2>&1; then
    log "✅ Using: firefox-esr"
    firefox-esr --kiosk "$WEB_URL" &>/dev/null &
    log "✅ Firefox ESR started in kiosk mode"
    exit 0
fi

# 3. Chromium (son çare - Zero 2 W'de NEON hatası verebilir)
if command -v chromium-browser >/dev/null 2>&1; then
    log "⚠️  Using: chromium-browser (may have NEON issues on Zero 2 W)"
    chromium-browser --kiosk --noerrdialogs --disable-infobars \
        --no-first-run --disable-session-crashed-bubble \
        --disable-features=TranslateUI --password-store=basic \
        --use-mock-keychain --disable-sync --disable-translate \
        --disable-gpu --disable-software-rasterizer \
        "$WEB_URL" &>/dev/null &
    log "✅ Chromium started (with GPU disabled)"
    exit 0
elif command -v chromium >/dev/null 2>&1; then
    log "⚠️  Using: chromium (may have NEON issues on Zero 2 W)"
    chromium --kiosk --noerrdialogs --disable-infobars \
        --no-first-run --disable-session-crashed-bubble \
        --disable-features=TranslateUI --password-store=basic \
        --use-mock-keychain --disable-sync --disable-translate \
        --disable-gpu --disable-software-rasterizer \
        "$WEB_URL" &>/dev/null &
    log "✅ Chromium started (with GPU disabled)"
    exit 0
fi

# Browser bulunamadı
log "❌ No browser found!"
log "💡 Install lightweight browser:"
log "   sudo apt install midori          # Recommended for Zero 2 W"
log "   sudo apt install firefox-esr     # Alternative"
log ""
log "💡 BETTER SOLUTION for Zero 2 W:"
log "   Don't use kiosk mode - just use web browser from another device:"
log "   📱 Phone/Tablet: http://$LOCAL_IP:$PORT"
log "   💻 Laptop: http://$LOCAL_IP:$PORT"
exit 1

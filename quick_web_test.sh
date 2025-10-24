#!/bin/bash
# Kuvoz Web Interface Hızlı Test
# Raspberry Pi OS Trixie için

echo "🚀 Kuvoz Web Interface - Hızlı Test"
echo "===================================="

# 1. Chromium kontrolü
echo "1️⃣  Chromium Durumu:"
if command -v chromium >/dev/null 2>&1; then
    echo "✅ chromium: $(which chromium)"
elif command -v chromium-browser >/dev/null 2>&1; then
    echo "✅ chromium-browser: $(which chromium-browser)"
else
    echo "❌ Chromium bulunamadı - make web-install çalıştırın"
fi

# 2. Python packages kontrolü
echo ""
echo "2️⃣  Python Packages:"
if python3 -c "import flask" 2>/dev/null; then
    echo "✅ Flask (sistem): OK"
elif [ -f "web_venv/bin/python" ] && web_venv/bin/python -c "import flask" 2>/dev/null; then
    echo "✅ Flask (venv): OK"
else
    echo "❌ Flask bulunamadı - make web-deps-install çalıştırın"
fi

if python3 -c "import flask_socketio" 2>/dev/null; then
    echo "✅ Flask-SocketIO (sistem): OK"
elif [ -f "web_venv/bin/python" ] && web_venv/bin/python -c "import flask_socketio" 2>/dev/null; then
    echo "✅ Flask-SocketIO (venv): OK"
else
    echo "❌ Flask-SocketIO bulunamadı"
fi

# 3. Web dosyaları kontrolü
echo ""
echo "3️⃣  Web Dosyaları:"
if [ -f "web_server.py" ]; then
    echo "✅ web_server.py: Mevcut"
else
    echo "❌ web_server.py: Bulunamadı"
fi

if [ -d "web" ] && [ -f "web/index.html" ]; then
    echo "✅ web/index.html: Mevcut"
else
    echo "❌ web/ dizini eksik"
fi

# 4. Port kontrolü
echo ""
echo "4️⃣  Port Durumu:"
if netstat -tuln 2>/dev/null | grep ":5000" >/dev/null; then
    echo "⚠️  Port 5000 kullanımda - başka bir servis çalışıyor"
else
    echo "✅ Port 5000: Kullanılabilir"
fi

# 5. Hızlı çözüm önerileri
echo ""
echo "🎯 Hızlı Çözümler:"
echo "=================="

if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
    echo "🔧 Chromium kurulumu: make web-install"
fi

if ! python3 -c "import flask" 2>/dev/null && ! [ -f "web_venv/bin/python" ]; then
    echo "🔧 Python packages: make web-deps-install"
fi

echo "🚀 Web server başlat: make web-run"
echo "🌐 Browser açık: make auto-browser"
echo "📖 Detaylı rehber: cat TRIXIE_CHROMIUM_FIX.md"

echo ""
echo "💡 HIZLI BAŞLATMA:"
echo "make web-deps-install && make web-run"
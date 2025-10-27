#!/bin/bash
# Kuvoz Otomatik Boot Kurulum Script'i
# Bu script sistemi boot'ta otomatik olarak Kuvoz'u çalıştıracak şekilde yapılandırır

set -e

echo "🚀 Kuvoz Otomatik Boot Kurulumu"
echo "==============================="

# Değişkenler
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER=$(whoami)

echo "📁 Proje dizini: $SCRIPT_DIR"
echo "👤 Kullanıcı: $USER"
echo ""

# 1. Web bağımlılıklarını kontrol et
echo "🔧 Web bağımlılıkları kontrol ediliyor..."
python3 -c "import flask, flask_socketio" 2>/dev/null || {
    echo "📦 Flask ve Flask-SocketIO kuruluyor..."
    pip3 install --break-system-packages flask flask-socketio 2>/dev/null || \
    sudo apt install -y python3-flask python3-flask-socketio
}
echo "✅ Web bağımlılıkları hazır"

# 2. Systemd servislerini kur
echo ""
echo "🔧 Web servisi kuruluyor..."
sudo tee /etc/systemd/system/kuvoz-web.service > /dev/null << EOF
[Unit]
Description=Kuvoz Incubator Web Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONPATH=$SCRIPT_DIR:$SCRIPT_DIR/lib
Environment=FLASK_ENV=production
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 $SCRIPT_DIR/web_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SupplementaryGroups=gpio i2c spi

[Install]
WantedBy=multi-user.target
EOF

# 3. Kiosk script'ini oluştur
echo "🖥️  Kiosk script'i oluşturuluyor..."
mkdir -p "$SCRIPT_DIR/scripts"
cat > "$SCRIPT_DIR/scripts/start-kiosk.sh" << 'EOF'
#!/bin/bash
# Kuvoz Kiosk Başlatma Script'i
sleep 10

export DISPLAY=:0
export HOME=/home/$(whoami)

echo "🖥️  Kiosk modu başlatılıyor..."

# Web sunucusunun hazır olmasını bekle
for i in {1..30}; do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo "✅ Web sunucusu hazır"
        break
    fi
    echo "⏳ Web sunucusu bekleniyor... ($i/30)"
    sleep 2
done

# Browser ile kiosk modu başlat
if command -v chromium >/dev/null 2>&1; then
    echo "🌐 Chromium ile kiosk başlatılıyor..."
    chromium --kiosk --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --no-first-run --disable-default-apps http://localhost:5000
elif command -v chromium-browser >/dev/null 2>&1; then
    echo "🌐 Chromium-browser ile kiosk başlatılıyor..."
    chromium-browser --kiosk --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --no-first-run --disable-default-apps http://localhost:5000
elif command -v firefox-esr >/dev/null 2>&1; then
    echo "🦊 Firefox ile kiosk başlatılıyor..."
    firefox-esr --kiosk http://localhost:5000
else
    echo "❌ Browser bulunamadı!"
    echo "Chromium kurulumu: sudo apt install chromium"
    echo "Firefox kurulumu: sudo apt install firefox-esr"
    exit 1
fi
EOF

chmod +x "$SCRIPT_DIR/scripts/start-kiosk.sh"

# 4. Kiosk servisini kur
echo "🔧 Kiosk servisi kuruluyor..."
sudo tee /etc/systemd/system/kuvoz-kiosk.service > /dev/null << EOF
[Unit]
Description=Kuvoz Incubator Kiosk Mode
After=graphical-session.target kuvoz-web.service
Wants=graphical-session.target
Requires=kuvoz-web.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR
Environment=DISPLAY=:0
Environment=HOME=/home/$USER
ExecStart=$SCRIPT_DIR/scripts/start-kiosk.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SupplementaryGroups=video audio

[Install]
WantedBy=graphical.target
EOF

# 5. Systemd'yi yenile ve servisleri etkinleştir
echo ""
echo "🔄 Systemd servisleri etkinleştiriliyor..."
sudo systemctl daemon-reload

# Web servisini etkinleştir ve başlat
sudo systemctl enable kuvoz-web.service
sudo systemctl start kuvoz-web.service

# Kiosk servisini etkinleştir (grafik oturumda başlayacak)
sudo systemctl enable kuvoz-kiosk.service

echo ""
echo "✅ Otomatik boot kurulumu tamamlandı!"
echo "======================================"
echo ""
echo "📊 Servis Durumları:"
echo "Web Server: $(sudo systemctl is-active kuvoz-web.service)"
echo "Kiosk Mode: $(sudo systemctl is-enabled kuvoz-kiosk.service) (grafik oturumda başlayacak)"
echo ""
echo "🌐 Web Arayüzü:"
echo "   Yerel: http://localhost:5000"
echo "   Ağ: http://$(hostname -I | cut -d' ' -f1):5000"
echo ""
echo "🔧 Yönetim Komutları:"
echo "   make status-all      # Servis durumları"
echo "   make restart-all     # Tüm servisleri yeniden başlat"
echo "   make logs-web        # Web sunucu logları"
echo "   make logs-kiosk      # Kiosk logları"
echo "   make uninstall-all   # Tüm servisleri kaldır"
echo ""
echo "🎉 Sistem hazır! Yeniden başlatma sonrası otomatik çalışacak."
echo "   sudo reboot"
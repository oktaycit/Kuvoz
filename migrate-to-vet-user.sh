#!/bin/bash
# Kuvoz Servislerini vet Kullanıcısına Taşıma Scripti
# Mevcut cihazda oktay kullanıcısından vet'e geçiş

set -e

echo "🔄 Kuvoz Servislerini vet Kullanıcısına Taşıma"
echo "============================================="
echo ""

# Root kontrolü
if [ "$EUID" -eq 0 ]; then
    echo "❌ Bu scripti root olarak çalıştırmayın"
    echo "   Normal kullanıcı ile çalıştırın"
    exit 1
fi

# vet kullanıcısı kontrolü
if ! id "vet" &>/dev/null; then
    echo "❌ vet kullanıcısı bulunamadı!"
    echo "   Önce: make setup-new-device"
    exit 1
fi

# Kuvoz klasörü kontrolü
if [ ! -d "/home/vet/kuvoz" ]; then
    echo "❌ /home/vet/kuvoz bulunamadı!"
    echo "   Kuvoz projesini vet kullanıcısına klonlayın:"
    echo "   ssh vet@kuvoz.local"
    echo "   cd /home/vet"
    echo "   git clone https://github.com/oktaycit/Kuvoz.git kuvoz"
    exit 1
fi

echo "✅ vet kullanıcısı ve Kuvoz projesi mevcut"
echo ""

# ======================
# 1. SERVİSLERİ DURDUR
# ======================
echo "🛑 1/4 - Mevcut servisleri durduruluyor..."
sudo systemctl stop kuvoz-web 2>/dev/null || true
sudo systemctl stop kuvoz-kiosk 2>/dev/null || true
echo "✅ Servisler durduruldu"
echo ""

# ======================
# 2. SERVİS DOSYALARINI GÜNCELLE
# ======================
echo "📝 2/4 - Servis dosyaları güncelleniyor..."

# Web servisi
sudo tee /etc/systemd/system/kuvoz-web.service > /dev/null << 'EOF'
[Unit]
Description=Kuvoz Incubator Web Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=vet
Group=vet
WorkingDirectory=/home/vet/kuvoz
Environment=PYTHONPATH=/home/vet/kuvoz:/home/vet/kuvoz/lib
Environment=FLASK_ENV=production
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/vet/kuvoz/web_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SupplementaryGroups=gpio i2c spi

[Install]
WantedBy=multi-user.target
EOF

echo "✅ kuvoz-web.service güncellendi"

# Kiosk servisi (varsa)
if [ -f /etc/systemd/system/kuvoz-kiosk.service ]; then
    sudo tee /etc/systemd/system/kuvoz-kiosk.service > /dev/null << 'EOF'
[Unit]
Description=Kuvoz Incubator Kiosk Mode
After=graphical-session.target kuvoz-web.service
Wants=graphical-session.target
Requires=kuvoz-web.service

[Service]
Type=simple
User=vet
Group=vet
WorkingDirectory=/home/vet/kuvoz
Environment=DISPLAY=:0
Environment=HOME=/home/vet
ExecStartPre=/bin/sleep 10
ExecStart=/home/vet/kuvoz/scripts/start-kiosk.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SupplementaryGroups=video audio

[Install]
WantedBy=graphical.target
EOF
    echo "✅ kuvoz-kiosk.service güncellendi"
fi

echo ""

# ======================
# 3. SERVİSLERİ YENİDEN BAŞLAT
# ======================
echo "🔄 3/4 - Servisler yeniden başlatılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable kuvoz-web
sudo systemctl start kuvoz-web
echo "✅ Web servisi başlatıldı (vet kullanıcısı ile)"
echo ""

# Servis durumunu göster
echo "📊 Servis durumu:"
sudo systemctl status kuvoz-web --no-pager -n 5
echo ""

# ======================
# 4. ESKİ KULLANICI HAKKINDA BİLGİ
# ======================
echo "🗑️  4/4 - Eski kullanıcı temizliği"
echo ""

CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" = "vet" ]; then
    echo "✅ Zaten vet kullanıcısı ile çalışıyorsunuz"
    echo ""
    read -p "oktay kullanıcısını şimdi silmek ister misiniz? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  oktay kullanıcısı siliniyor..."
        sudo pkill -u oktay 2>/dev/null || true
        sleep 2
        sudo userdel -r oktay 2>&1 || echo "⚠️ Bazı dosyalar kalmış olabilir (beklenen)"
        echo "✅ oktay kullanıcısı silindi"
    else
        echo "⏭️  Daha sonra silmek için:"
        echo "   sudo pkill -u oktay"
        echo "   sudo userdel -r oktay"
    fi
else
    echo "⚠️ Şu anda '$CURRENT_USER' kullanıcısı ile çalışıyorsunuz"
    echo ""
    echo "oktay kullanıcısını silmek için:"
    echo "  1. Cihazı yeniden başlatın: sudo reboot"
    echo "  2. vet kullanıcısı ile login olun"
    echo "  3. Aşağıdaki komutları çalıştırın:"
    echo ""
    echo "     sudo pkill -u oktay"
    echo "     sudo userdel -r oktay"
fi

echo ""
echo "✅ MİGRASYON TAMAMLANDI!"
echo "======================="
echo ""
echo "🌐 Web arayüzü: http://$(hostname -I | awk '{print $1}'):8000"
echo "📊 Log izleme: sudo journalctl -u kuvoz-web -f"
echo ""
echo "✨ Servisler artık vet kullanıcısı ile çalışıyor!"

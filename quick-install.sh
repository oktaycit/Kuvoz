#!/bin/bash
# Kuvoz Hızlı Kurulum Script'i
# Tek komutla tüm sistemi kurar ve çalıştırır

set -e

echo "⚡ Kuvoz Hızlı Kurulum"
echo "===================="

# Proje dizinini belirle
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Makefile var mı kontrol et
if [ ! -f "Makefile" ]; then
    echo "❌ Makefile bulunamadı! Proje dizininde çalıştırın."
    exit 1
fi

echo "📁 Proje: $SCRIPT_DIR"
echo "👤 Kullanıcı: $(whoami)"
echo ""

# 1. Web bağımlılıklarını kur
echo "🔧 1/4 - Web bağımlılıkları kuruluyor..."
make web-deps

# 2. Web servisini kur ve başlat
echo "🌐 2/4 - Web servisi kuruluyor..."
make web-service

# 3. Kiosk servisini kur
echo "🖥️  3/4 - Kiosk servisi kuruluyor..."
make kiosk-service

# 4. Durumu kontrol et
echo "📊 4/4 - Sistem durumu kontrol ediliyor..."
sleep 3
make status-all

echo ""
echo "🎉 KURULUM TAMAMLANDI!"
echo "====================="
echo ""
echo "🌐 Web Arayüzü Erişim:"
echo "   Yerel: http://localhost:8000"
echo "   Ağ: http://$(hostname -I | cut -d' ' -f1 2>/dev/null):8000"
echo ""
echo "🔧 Yönetim Komutları:"
echo "   make web-start       # Web sunucusu başlat"
echo "   make kiosk-start     # Kiosk modu başlat"
echo "   make status-all      # Durumları görüntüle"
echo "   make restart-all     # Tüm servisleri yeniden başlat"
echo "   make logs-web        # Web sunucu logları"
echo ""
echo "💡 İpucu: Kiosk modu grafik oturumda otomatik başlayacak"
echo "   X11 oturumu açıksa: make kiosk-start"
echo ""
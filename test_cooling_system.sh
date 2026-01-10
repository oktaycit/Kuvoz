#!/bin/bash
# Soğutma Sistemi Test Scripti
# Bu script soğutma sisteminin doğru çalıştığını test eder

echo "🧊 Soğutma Sistemi Test Başlatılıyor..."
echo ""

# 1. GPIO Pin 12 kontrolü
echo "1️⃣ GPIO Pin 12 kontrolü..."
if command -v gpio &> /dev/null; then
    gpio -g mode 12 out
    echo "   ✅ GPIO 12 output olarak ayarlandı"
    
    # Test 1: Pin 12'yi LOW yap (Soğutma AÇIK)
    echo "   🔵 Test: GPIO 12 -> LOW (Soğutma AÇIK)"
    gpio -g write 12 0
    sleep 2
    
    # Test 2: Pin 12'yi HIGH yap (Soğutma KAPALI)
    echo "   🔴 Test: GPIO 12 -> HIGH (Soğutma KAPALI)"
    gpio -g write 12 1
    sleep 1
    
    echo "   ✅ GPIO 12 testi tamamlandı"
else
    echo "   ⚠️  gpio komutu bulunamadı, GPIO testi atlandı"
fi

echo ""

# 2. Web server loglarını kontrol et
echo "2️⃣ Web server loglarında b9 (soğutma) kontrolü..."
if systemctl is-active --quiet kuvoz-web; then
    echo "   ✅ kuvoz-web servisi çalışıyor"
    echo "   📋 Son 10 log satırı:"
    journalctl -u kuvoz-web -n 10 --no-pager | grep -E "(b9|cooling|COOLING|GPIO 12)" || echo "   ℹ️  Henüz b9 ile ilgili log yok"
else
    echo "   ⚠️  kuvoz-web servisi çalışmıyor"
    echo "   💡 Başlatmak için: sudo systemctl start kuvoz-web"
fi

echo ""

# 3. Button states dosyasını kontrol et
echo "3️⃣ Ayarlar dosyasında b9 kontrolü..."
if [ -f "Failure.dat" ]; then
    echo "   📄 Failure.dat içeriği:"
    if grep -q "b9" Failure.dat; then
        echo "   ✅ b9 butonu ayarlarda mevcut:"
        grep "b9" Failure.dat
    else
        echo "   ⚠️  b9 butonu ayarlarda yok (ilk kez kullanılacak)"
    fi
else
    echo "   ℹ️  Failure.dat dosyası henüz oluşturulmamış"
fi

echo ""

# 4. Web arayüzünde buton kontrolü
echo "4️⃣ Web arayüzünde soğutma butonu kontrolü..."
if [ -f "web/index.html" ]; then
    if grep -q 'data-name="b9"' web/index.html; then
        echo "   ✅ HTML'de b9 butonu mevcut"
        grep -A2 'data-name="b9"' web/index.html | head -3
    else
        echo "   ❌ HTML'de b9 butonu bulunamadı!"
    fi
else
    echo "   ❌ web/index.html dosyası bulunamadı!"
fi

echo ""

# 5. Sorun giderme önerileri
echo "🔧 Sorun Giderme:"
echo ""
echo "   Eğer soğutma butonu çalışmıyorsa:"
echo ""
echo "   1. Web servisini yeniden başlat:"
echo "      sudo systemctl restart kuvoz-web"
echo ""
echo "   2. Browser cache'ini temizle:"
echo "      • Chromium: Ctrl+Shift+R veya F5"
echo "      • Tarayıcıyı tamamen kapat ve aç"
echo ""
echo "   3. Logları canlı izle:"
echo "      sudo journalctl -u kuvoz-web -f"
echo ""
echo "   4. GPIO donanım bağlantısını kontrol et:"
echo "      • GPIO 12 (Physical Pin 32) relay'e bağlı mı?"
echo "      • Relay çalışıyor mu?"
echo ""
echo "   5. Manuel GPIO test:"
echo "      gpio -g mode 12 out"
echo "      gpio -g write 12 0  # Soğutma AÇIK (relay ON)"
echo "      gpio -g write 12 1  # Soğutma KAPALI (relay OFF)"
echo ""

# 6. Debug bilgisi topla
echo "📊 Sistem Bilgileri:"
echo "   Raspberry Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Bilinmiyor')"
echo "   Python Version: $(python3 --version 2>/dev/null || echo 'Python3 bulunamadı')"
echo "   Kuvoz Web Status: $(systemctl is-active kuvoz-web 2>/dev/null || echo 'Servis yok')"
echo ""

echo "✅ Test tamamlandı!"
echo ""
echo "💡 Soğutma butonunu test etmek için:"
echo "   1. Web arayüzünü aç: http://$(hostname -I | awk '{print $1}'):5000"
echo "   2. Soğutma hedefini ayarla (sld12)"
echo "   3. Soğutma butonuna (b9) tıkla"
echo "   4. Logları izle: sudo journalctl -u kuvoz-web -f"
echo ""

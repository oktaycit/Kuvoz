#!/bin/bash
# Kuvoz SD Kart Temizleme Scripti
# Cihazda çalıştırın: ssh vet@kuvoz.local
# Kullanım: ./cleanup-for-image.sh

echo "🧹 Kuvoz İmaj Temizleme Scripti"
echo "================================"
echo ""
echo "Bu script SD kartı imaj oluşturma için hazırlar."
echo "Tüm kişisel veriler ve loglar silinecek!"
echo ""
read -p "Devam edilsin mi? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ İptal edildi"
    exit 1
fi

# 1. Logları temizle
echo ""
echo "📝 Loglar temizleniyor..."
sudo rm -rf /home/vet/Kuvoz/logs/*
sudo rm -rf /var/log/*.log
sudo journalctl --vacuum-time=1d
echo "✅ Loglar temizlendi"

# 2. Cache temizle
echo ""
echo "🗑️  Cache temizleniyor..."
sudo apt clean
sudo apt autoclean
rm -rf ~/.cache/*
rm -rf /tmp/*
echo "✅ Cache temizlendi"

# 3. Bash history temizle
echo ""
echo "📜 Bash history temizleniyor..."
rm -f ~/.bash_history
history -c
echo "✅ Bash history temizlendi"

# 4. SSH known_hosts temizle
echo ""
echo "🔑 SSH bilgileri temizleniyor..."
rm -f ~/.ssh/known_hosts
echo "✅ SSH bilgileri temizlendi"

# 5. Tailscale logout
echo ""
echo "🌐 Tailscale logout..."
if command -v tailscale &> /dev/null; then
    sudo tailscale logout
    echo "✅ Tailscale logout yapıldı"
else
    echo "⚠️  Tailscale bulunamadı (normal)"
fi

# 6. Wi-Fi şifrelerini temizle (opsiyonel)
echo ""
read -p "Wi-Fi şifreleri silinsin mi? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -f /etc/NetworkManager/system-connections/*
    echo "✅ Wi-Fi şifreleri temizlendi"
fi

# 7. Failure.dat yedekle (ayarlar)
echo ""
echo "💾 Ayarlar yedekleniyor..."
if [ -f /home/vet/Kuvoz/failure.dat ]; then
    cp /home/vet/Kuvoz/failure.dat /home/vet/Kuvoz/failure.dat.backup
    echo "✅ Ayarlar yedeklendi: failure.dat.backup"
fi

# 8. Varsayılan ayarlara dön
echo ""
read -p "Varsayılan ayarlara dönülsün mü? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > /home/vet/Kuvoz/failure.dat << 'EOF'
{
    "slider_values": {
        "sld1": 30,
        "sld2": 60,
        "sld3": 32.0,
        "sld4": 25.0,
        "sld5": 45,
        "sld6": 6,
        "sld7": 12.0,
        "sld12": 25.0
    },
    "button_states": {
        "b1": false,
        "b2": false,
        "b3": false,
        "b4": false,
        "b5": false,
        "b6": false,
        "b7": false,
        "b8": false,
        "b9": false
    }
}
EOF
    echo "✅ Varsayılan ayarlar yüklendi"
fi

# 9. Disk kullanımı göster
echo ""
echo "💿 Disk Kullanımı:"
df -h / | tail -1

# 10. Özet
echo ""
echo "✅ Temizlik tamamlandı!"
echo ""
echo "Sonraki adımlar:"
echo "1. Sistemi kapatın: sudo shutdown -h now"
echo "2. SD kartı çıkarın"
echo "3. Mac'e takın ve imaj oluşturun"
echo ""
read -p "Şimdi sistemi kapatmak ister misiniz? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "👋 Sistem kapatılıyor..."
    sudo shutdown -h now
fi

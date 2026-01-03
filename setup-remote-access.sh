#!/bin/bash
# Kuvoz Uzaktan Erişim Hızlı Kurulum Script'i
# Tailscale kurulumu için basitleştirilmiş script

set -e

echo "🌐 Kuvoz Uzaktan Erişim Kurulumu"
echo "================================="
echo ""

# Hangi yöntemi kullanmak istediğini sor
echo "Uzaktan erişim için hangi yöntemi kullanmak istersiniz?"
echo ""
echo "1) Tailscale (ÖNERİLEN - Kolay, hızlı, mobil uyumlu)"
echo "2) Cloudflare Tunnel (Public erişim)"
echo "3) İkisini de kur"
echo "4) Çık"
echo ""
read -p "Seçiminiz (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Tailscale kurulumu başlatılıyor..."
        echo ""
        
        # Tailscale kurulumu
        if ! command -v tailscale &> /dev/null; then
            echo "⬇️  Tailscale indiriliyor..."
            curl -fsSL https://tailscale.com/install.sh | sh
            echo "✅ Tailscale kuruldu"
        else
            echo "✅ Tailscale zaten kurulu"
        fi
        
        echo ""
        echo "🔐 Tailscale başlatılıyor..."
        echo "Açılan tarayıcı penceresinde Tailscale hesabınızla giriş yapın"
        echo ""
        sudo tailscale up
        
        echo ""
        echo "✅ Tailscale kurulumu tamamlandı!"
        echo ""
        echo "📱 Erişim bilgileri:"
        echo "   Tailscale IP: $(tailscale ip -4 2>/dev/null || echo 'IP alınamadı')"
        echo "   Erişim URL: http://$(tailscale ip -4 2>/dev/null || echo 'IP'):8000"
        echo ""
        echo "📲 Mobil cihazdan bağlanmak için:"
        echo "   1. iOS: App Store'dan Tailscale uygulamasını indirin"
        echo "   2. Android: Play Store'dan Tailscale uygulamasını indirin"
        echo "   3. Aynı hesapla giriş yapın"
        echo "   4. VPN'i açın"
        echo "   5. Safari/Chrome'da yukarıdaki URL'i açın"
        echo ""
        echo "💡 Daha fazla bilgi için: cat REMOTE_ACCESS_SETUP.md"
        ;;
        
    2)
        echo ""
        echo "☁️  Cloudflare Tunnel kurulumu başlatılıyor..."
        echo ""
        
        # Cloudflared kurulumu
        if ! command -v cloudflared &> /dev/null; then
            echo "⬇️  Cloudflared indiriliyor..."
            
            if uname -m | grep -q "aarch64"; then
                echo "ARM64 sistemde"
                wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
                sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
            else
                echo "ARM32 sistemde"
                wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
                sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared
            fi
            
            sudo chmod +x /usr/local/bin/cloudflared
            echo "✅ Cloudflared kuruldu"
        else
            echo "✅ Cloudflared zaten kurulu"
        fi
        
        echo ""
        echo "🔐 Cloudflare'e giriş yapılıyor..."
        echo "Açılan tarayıcı penceresinde Cloudflare hesabınızla giriş yapın"
        echo ""
        cloudflared tunnel login
        
        echo ""
        read -p "Tunnel adı girin (örn: kuvoz-tunnel): " tunnel_name
        
        echo ""
        echo "🔧 Tunnel oluşturuluyor: $tunnel_name"
        cloudflared tunnel create "$tunnel_name"
        
        echo ""
        echo "⚙️  Yapılandırma dosyası oluşturuluyor..."
        sudo mkdir -p /etc/cloudflared
        
        tunnel_id=$(cloudflared tunnel list | grep "$tunnel_name" | awk '{print $1}')
        
        cat << EOF | sudo tee /etc/cloudflared/config.yml
tunnel: $tunnel_id
credentials-file: /root/.cloudflared/$tunnel_id.json

ingress:
  - service: http://localhost:8000
EOF
        
        echo ""
        echo "🚀 Servisi başlatıyor..."
        sudo cloudflared service install
        sudo systemctl start cloudflared
        sudo systemctl enable cloudflared
        
        echo ""
        echo "✅ Cloudflare Tunnel kurulumu tamamlandı!"
        echo ""
        echo "🌐 Erişim URL'inizi almak için:"
        echo "   https://one.dash.cloudflare.com/networks/tunnels"
        echo ""
        echo "📊 Tunnel durumu:"
        cloudflared tunnel list
        echo ""
        echo "💡 Daha fazla bilgi için: cat REMOTE_ACCESS_SETUP.md"
        ;;
        
    3)
        echo ""
        echo "🎯 Her iki yöntem de kuruluyor..."
        echo ""
        
        # Tailscale
        if ! command -v tailscale &> /dev/null; then
            echo "⬇️  Tailscale indiriliyor..."
            curl -fsSL https://tailscale.com/install.sh | sh
        fi
        echo "✅ Tailscale kuruldu"
        
        # Cloudflared
        if ! command -v cloudflared &> /dev/null; then
            echo "⬇️  Cloudflared indiriliyor..."
            
            if uname -m | grep -q "aarch64"; then
                wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
                sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
            else
                wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
                sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared
            fi
            
            sudo chmod +x /usr/local/bin/cloudflared
        fi
        echo "✅ Cloudflared kuruldu"
        
        echo ""
        echo "✅ Her iki araç da kuruldu!"
        echo ""
        echo "🔧 Ayarlamak için:"
        echo "   Tailscale: make tailscale-start"
        echo "   Cloudflare: make cloudflare-setup"
        echo ""
        echo "💡 Daha fazla bilgi için: cat REMOTE_ACCESS_SETUP.md"
        ;;
        
    4)
        echo "Çıkılıyor..."
        exit 0
        ;;
        
    *)
        echo "❌ Geçersiz seçim!"
        exit 1
        ;;
esac

echo ""
echo "🎉 Kurulum tamamlandı!"
echo ""
echo "📖 Komut satırı kısayolları:"
echo "   make remote-help          # Tüm uzaktan erişim komutları"
echo "   make tailscale-status     # Tailscale durumu"
echo "   make cloudflare-status    # Cloudflare durumu"
echo ""

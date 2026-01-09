#!/bin/bash
# Kuvoz Boot Splash Kurulum Script'i
# VetMarketi logolu Plymouth teması

set -e

THEME_NAME="kuvoz"
THEME_DIR="/usr/share/plymouth/themes/$THEME_NAME"
LOGO_SOURCE="$HOME/kuvoz/resim/VetMarketi logosu.png"
LOGO_TARGET="$THEME_DIR/logo.png"

echo "🎨 Kuvoz Boot Splash kuruluyor..."

# Plymouth kurulu mu kontrol et
if ! command -v plymouth &> /dev/null; then
    echo "📦 Plymouth kuruluyor..."
    sudo apt update
    sudo apt install -y plymouth plymouth-themes
fi

# Tema dizini oluştur
echo "📁 Tema dizini oluşturuluyor: $THEME_DIR"
sudo mkdir -p "$THEME_DIR"

# Logo dosyasını kopyala ve optimize et
echo "🖼️  Logo kopyalanıyor..."
if [ -f "$LOGO_SOURCE" ]; then
    # ImageMagick varsa resize yap
    if command -v convert &> /dev/null; then
        echo "   Resim optimize ediliyor (800x200)..."
        convert "$LOGO_SOURCE" -resize 800x200 -background none -gravity center -extent 800x200 /tmp/logo-optimized.png
        sudo cp /tmp/logo-optimized.png "$LOGO_TARGET"
        rm /tmp/logo-optimized.png
    else
        sudo cp "$LOGO_SOURCE" "$LOGO_TARGET"
    fi
else
    echo "❌ Logo dosyası bulunamadı: $LOGO_SOURCE"
    exit 1
fi

# Plymouth tema dosyası oluştur
echo "📝 Tema dosyası oluşturuluyor..."
sudo tee "$THEME_DIR/$THEME_NAME.plymouth" > /dev/null <<EOF
[Plymouth Theme]
Name=Kuvoz VetMarketi
Description=Kuvoz Incubator - VetMarketi Boot Splash
ModuleName=script

[script]
ImageDir=$THEME_DIR
ScriptFile=$THEME_DIR/$THEME_NAME.script
EOF

# Plymouth script dosyası oluştur
echo "📝 Script dosyası oluşturuluyor..."
sudo tee "$THEME_DIR/$THEME_NAME.script" > /dev/null <<'EOF'
# Kuvoz Plymouth Theme Script

# Ekran boyutlarını al
screen_width = Window.GetWidth();
screen_height = Window.GetHeight();

# Logo'yu yükle
logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);

# Logo boyutları
logo.width = logo.image.GetWidth();
logo.height = logo.image.GetHeight();

# Logo'yu merkeze yerleştir
logo.x = (screen_width - logo.width) / 2;
logo.y = (screen_height - logo.height) / 2 - 50;
logo.sprite.SetPosition(logo.x, logo.y, 0);

# Arka plan rengi (koyu gri)
Window.SetBackgroundTopColor(0.17, 0.24, 0.31);
Window.SetBackgroundBottomColor(0.20, 0.29, 0.37);

# Loading spinner
spinner_image = Image("spinner.png");
if (spinner_image) {
    spinner.sprite = Sprite(spinner_image);
    spinner.x = screen_width / 2 - spinner_image.GetWidth() / 2;
    spinner.y = logo.y + logo.height + 40;
    spinner.sprite.SetPosition(spinner.x, spinner.y, 1);
}

# Yükleme metni
message_sprite = Sprite();
message_sprite.SetPosition(screen_width / 2, screen_height - 100, 2);

fun refresh_callback() {
    # Spinner animasyonu (varsa)
    if (spinner.sprite) {
        spinner.angle += 0.1;
        if (spinner.angle >= 6.28) spinner.angle = 0;
        spinner.sprite.SetRotation(spinner.angle);
    }
}

Plymouth.SetRefreshFunction(refresh_callback);

fun message_callback(text) {
    message_image = Image.Text(text, 1, 1, 1);
    message_sprite.SetImage(message_image);
    message_sprite.SetX(screen_width / 2 - message_image.GetWidth() / 2);
}

Plymouth.SetMessageFunction(message_callback);
EOF

# Basit spinner oluştur (ImageMagick varsa)
if command -v convert &> /dev/null; then
    echo "🔄 Spinner oluşturuluyor..."
    convert -size 60x60 xc:none -fill white -draw "circle 30,30 30,10" -draw "circle 30,30 30,50" -draw "circle 30,30 10,30" -draw "circle 30,30 50,30" /tmp/spinner.png
    sudo cp /tmp/spinner.png "$THEME_DIR/spinner.png"
    rm /tmp/spinner.png
fi

# Temayı varsayılan yap
echo "🎯 Tema etkinleştiriliyor..."
sudo plymouth-set-default-theme -R "$THEME_NAME"

# initramfs güncelle
echo "🔄 initramfs güncelleniyor..."
sudo update-initramfs -u

# Cmdline'da splash ekle (yoksa)
CMDLINE_FILE="/boot/cmdline.txt"
if [ -f /boot/firmware/cmdline.txt ]; then
    CMDLINE_FILE="/boot/firmware/cmdline.txt"
fi

if ! grep -q "splash" "$CMDLINE_FILE"; then
    echo "📝 Kernel cmdline'a splash ekleniyor..."
    sudo sed -i 's/$/ splash quiet plymouth.ignore-serial-consoles/' "$CMDLINE_FILE"
fi

echo "✅ Kuvoz Boot Splash kurulumu tamamlandı!"
echo ""
echo "📊 Aktif tema:"
plymouth-set-default-theme
echo ""
echo "🔄 Değişikliklerin etkili olması için yeniden başlatın:"
echo "   sudo reboot"

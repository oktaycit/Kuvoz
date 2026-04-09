#!/bin/bash
# Kuvoz Raspberry Pi Setup via GitHub
# Router port forwarding sorununu bypass eder

echo "🚀 Kuvoz Raspberry Pi Setup - GitHub Method"
echo "============================================"

# Check if we're on Raspberry Pi
if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  This script is designed for Raspberry Pi"
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install git if not present
if ! command -v git &> /dev/null; then
    echo "📥 Installing git..."
    sudo apt install -y git
fi

# Ensure Turkish UTF-8 locale exists for kiosk/browser rendering.
echo "🌍 Ensuring Turkish UTF-8 locale..."
if command -v locale-gen >/dev/null 2>&1; then
    if ! locale -a 2>/dev/null | grep -qi '^tr_TR\.utf8$'; then
        sudo apt install -y locales
        if ! grep -q '^tr_TR.UTF-8 UTF-8$' /etc/locale.gen 2>/dev/null; then
            echo 'tr_TR.UTF-8 UTF-8' | sudo tee -a /etc/locale.gen >/dev/null
        fi
        sudo locale-gen tr_TR.UTF-8
    fi
    sudo update-locale LANG=tr_TR.UTF-8 LANGUAGE=tr_TR:tr LC_CTYPE=tr_TR.UTF-8
else
    echo "⚠️  locale-gen bulunamadı, Türkçe locale kurulumu atlandı"
fi

# Clone or update repository
if [ -d "kuvoz" ]; then
    echo "📁 Updating existing repository..."
    cd kuvoz
    git pull origin main
else
    echo "📥 Cloning Kuvoz repository..."
    git clone https://github.com/oktaycit/Kuvoz.git kuvoz
    cd kuvoz
fi

# Make scripts executable
echo "🔐 Setting permissions..."
chmod +x *.sh *.py

# Install dependencies
echo "📦 Installing dependencies..."
if [ -f "Makefile" ]; then
    make web-install
else
    echo "⚠️  Makefile not found, installing manually..."
    sudo apt install -y python3-flask python3-flask-socketio python3-eventlet
    # Install firebase-admin via pip as it's likely not in apt or outdated
    pip3 install firebase-admin --break-system-packages
    sudo apt install -y chromium xorg xinit openbox unclutter
fi

# Check Python imports
echo "🧪 Testing Python imports..."
python3 -c "
try:
    import flask, flask_socketio, eventlet, firebase_admin
    print('✅ Web dependencies: OK')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')

try:
    import RPi.GPIO
    print('✅ RPi.GPIO: OK')
except ImportError:
    print('⚠️  RPi.GPIO not available (simulation mode)')
"

# Disable Raspberry Pi Connect services (WayVNC loop fix)
echo "🚫 Disabling Raspberry Pi Connect services..."
systemctl --user stop rpi-connect-wayvnc.service 2>/dev/null || true
systemctl --user disable rpi-connect-wayvnc.service 2>/dev/null || true
systemctl --user mask rpi-connect-wayvnc.service 2>/dev/null || true
systemctl --user stop rpi-connect.service 2>/dev/null || true
systemctl --user disable rpi-connect.service 2>/dev/null || true
systemctl --user mask rpi-connect.service 2>/dev/null || true
# Also disable the signin service
systemctl --user stop rpi-connect-signin.service 2>/dev/null || true
systemctl --user disable rpi-connect-signin.service 2>/dev/null || true
systemctl --user mask rpi-connect-signin.service 2>/dev/null || true
echo "✅ Raspberry Pi Connect services disabled"

# Show setup status
echo ""
echo "📊 Setup Status:"
echo "================"
echo "📁 Project directory: $(pwd)"
echo "🐍 Python: $(python3 --version)"
echo "🌐 Flask: $(python3 -c 'import flask; print(flask.__version__)' 2>/dev/null || echo 'Not found')"
echo "🔧 GPIO: $(python3 -c 'import RPi.GPIO; print(\"Available\")' 2>/dev/null || echo 'Simulation mode')"

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "🌡️  Test DHT11 sensor:"
echo "   make dht11-test"
echo ""
echo "🚀 Start web server:"
echo "   make web-run"
echo ""
echo "🌐 Start kiosk mode:"
echo "   make auto-browser"
echo ""
echo "📱 Web interface: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "✅ Kuvoz setup completed via GitHub!"
echo "Router port forwarding not needed for this method! 🎉"

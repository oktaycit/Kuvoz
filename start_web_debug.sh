#!/bin/bash
# Kuvoz Web Server Startup Script
# GPIO sorunları için verbose debug

echo "🚀 Kuvoz Web Server - Debug Startup"
echo "===================================="

# GPIO gruplarını kontrol et
echo "1️⃣  User groups:"
groups | grep -E "(gpio|i2c|spi)" || echo "⚠️  No GPIO groups found"

# GPIO cihazlarını kontrol et
echo ""
echo "2️⃣  GPIO devices:"
ls -la /dev/gpio* 2>/dev/null || echo "⚠️  No GPIO devices found"
ls -la /dev/gpiomem 2>/dev/null || echo "⚠️  No gpiomem device found"

# Python GPIO test
echo ""
echo "3️⃣  Python GPIO test:"
python3 -c "
try:
    import RPi.GPIO as GPIO
    print('✅ RPi.GPIO import: OK')
    print(f'GPIO version: {GPIO.VERSION}')
    
    # Quick mode test
    GPIO.setmode(GPIO.BCM)
    print(f'✅ GPIO mode set: {GPIO.getmode()}')
    
    # Test pin setup
    GPIO.setup(18, GPIO.OUT)
    print('✅ GPIO pin setup: OK')
    
    GPIO.cleanup()
    print('✅ GPIO cleanup: OK')
    
except Exception as e:
    print(f'❌ GPIO test failed: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

# Check için bekleme
echo ""
echo "4️⃣  Starting web server in 3 seconds..."
echo "Press Ctrl+C to cancel"
sleep 3

# Web server'ı başlat
echo ""
echo "🌐 Starting Kuvoz Web Server..."
echo "================================"

# Virtual env kontrolü
if [ -f "web_venv/bin/python" ]; then
    echo "Using virtual environment Python"
    PYTHON_CMD="web_venv/bin/python"
elif python3 -c "import flask" 2>/dev/null; then
    echo "Using system Python"
    PYTHON_CMD="python3"
else
    echo "❌ Flask not found! Run: make web-deps-install"
    exit 1
fi

# Web server başlat
echo "Python command: $PYTHON_CMD"
echo "Arguments: $@"
echo ""

# Verbose logging ile başlat
export PYTHONUNBUFFERED=1
$PYTHON_CMD web_server.py "$@"
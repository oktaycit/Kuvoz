#!/bin/bash
# Adafruit_DHT Platform Fix Script
# "Unknown platform" hatasını çözmek için

echo "🔧 Adafruit_DHT Platform Fix"
echo "============================"

# 1. Platform environment variables
export FORCE_PI=1
export ADAFRUIT_FORCE_PI=1

# 2. Platform bilgilerini kontrol et
echo "1️⃣  System Information:"
echo "Hardware: $(cat /proc/cpuinfo | grep Hardware | head -1)"
echo "Model: $(cat /proc/cpuinfo | grep Model | head -1)"
echo "Machine: $(uname -m)"
echo "Platform: $(python3 -c 'import platform; print(platform.machine())')"

# 3. Adafruit_DHT test
echo ""
echo "2️⃣  Testing Adafruit_DHT with platform fix:"
python3 -c "
import os
os.environ['FORCE_PI'] = '1'
os.environ['ADAFRUIT_FORCE_PI'] = '1'

try:
    import Adafruit_DHT
    print('✅ Adafruit_DHT import: OK')
    
    # Force platform detection
    import Adafruit_DHT.common as common
    if hasattr(common, '_platform_detect'):
        print('🔧 Forcing platform detection...')
        # Override platform detection
        original_detect = common._platform_detect
        def force_pi_detect():
            return 1  # Force Raspberry Pi
        common._platform_detect = force_pi_detect
    
    # Test read
    print('🧪 Testing DHT11 read with platform fix...')
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 15)
    if hum is not None and temp is not None:
        print(f'✅ Success: {temp:.1f}°C, {hum:.0f}%rH')
    else:
        print('⚠️  Read returned None - sensor connection issue?')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"

# 4. DHT_Native fallback test
echo ""
echo "3️⃣  Testing DHT_Native fallback:"
python3 -c "
import sys
sys.path.append('lib/')
try:
    from DHT_Native import read_retry
    print('✅ DHT_Native import: OK')
    
    # Test read
    print('🧪 Testing DHT11 with DHT_Native...')
    hum, temp = read_retry(11, 15)
    if hum is not None and temp is not None:
        print(f'✅ Success: {temp:.1f}°C, {hum:.0f}%rH')
    else:
        print('⚠️  Read returned None')
        
except Exception as e:
    print(f'❌ Error: {e}')
"

echo ""
echo "4️⃣  Starting web server with fixes..."
echo "Environment variables set:"
echo "FORCE_PI=1"
echo "ADAFRUIT_FORCE_PI=1"
echo ""

# Web server'ı environment ile başlat
export FORCE_PI=1
export ADAFRUIT_FORCE_PI=1

if [ -f "web_venv/bin/python" ]; then
    echo "Using virtual environment Python"
    web_venv/bin/python web_server.py "$@"
elif python3 -c "import flask" 2>/dev/null; then
    echo "Using system Python"
    python3 web_server.py "$@"
else
    echo "❌ Flask not found! Run: make web-deps-install"
    exit 1
fi
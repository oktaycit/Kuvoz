#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adafruit_DHT Platform Fix
Raspberry Pi platform detection sorununu çözmek için
"""

import os
import sys

def fix_adafruit_dht_platform():
    """Adafruit_DHT için platform fix"""
    print("🔧 Fixing Adafruit_DHT platform detection...")
    
    # Platform bilgilerini zorla Raspberry Pi olarak ayarla
    try:
        # Environment variable set et
        os.environ['FORCE_PI'] = '1'
        
        # /proc/cpuinfo dosyasını kontrol et
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'Hardware' in cpuinfo and 'BCM' in cpuinfo:
                    print("✅ Raspberry Pi hardware detected")
                    return True
                else:
                    print("⚠️  Non-standard Raspberry Pi hardware")
        
        # Platform override için mock modül oluştur
        import platform
        original_machine = platform.machine
        original_processor = platform.processor
        
        def mock_machine():
            return 'armv7l'
        
        def mock_processor():
            return 'arm'
        
        platform.machine = mock_machine
        platform.processor = mock_processor
        
        print("✅ Platform override applied")
        return True
        
    except Exception as e:
        print(f"❌ Platform fix failed: {e}")
        return False

if __name__ == "__main__":
    fix_adafruit_dht_platform()
    
    # Test Adafruit_DHT
    try:
        import Adafruit_DHT
        print("✅ Adafruit_DHT import successful")
        
        # Test read
        print("🧪 Testing DHT11 read...")
        hum, temp = Adafruit_DHT.read(Adafruit_DHT.DHT11, 15)
        if hum is not None and temp is not None:
            print(f"✅ Success: {temp:.1f}°C, {hum:.0f}%rH")
        else:
            print("⚠️  Read returned None values")
            
    except Exception as e:
        print(f"❌ Adafruit_DHT test failed: {e}")
        import traceback
        traceback.print_exc()
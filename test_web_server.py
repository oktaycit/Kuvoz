#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Server Test - GPIO olmadan çalışma testi
"""

import sys
import os

# Test için mock modüller
class MockGPIO:
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0
    
    @staticmethod
    def setmode(mode):
        print(f"Mock GPIO: setmode({mode})")
    
    @staticmethod
    def setwarnings(enable):
        print(f"Mock GPIO: setwarnings({enable})")
    
    @staticmethod
    def setup(pin, mode):
        print(f"Mock GPIO: setup(pin={pin}, mode={mode})")
    
    @staticmethod
    def output(pin, state):
        print(f"Mock GPIO: output(pin={pin}, state={state})")
    
    @staticmethod
    def cleanup():
        print("Mock GPIO: cleanup()")

def test_web_server():
    """Web server basic test"""
    print("🧪 Web Server Test başlatılıyor...")
    
    # Mock GPIO için
    if 'RPi.GPIO' not in sys.modules:
        sys.modules['RPi.GPIO'] = type(sys)('RPi.GPIO')
        sys.modules['RPi.GPIO'].GPIO = MockGPIO()
    
    try:
        # Web server import test
        print("1. Web server import testi...")
        import web_server
        print("✅ Import başarılı")
        
        # Flask app test
        print("2. Flask app testi...")
        app = web_server.app
        print(f"✅ Flask app: {app}")
        
        # Basic routes test
        print("3. Routes testi...")
        with app.test_client() as client:
            response = client.get('/')
            print(f"✅ Ana sayfa response: {response.status_code}")
            
            response = client.get('/api/status')
            print(f"✅ API status response: {response.status_code}")
        
        print("✅ Tüm testler başarılı!")
        return True
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_web_server()
    sys.exit(0 if success else 1)
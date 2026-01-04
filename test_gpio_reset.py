#!/usr/bin/env python3
"""
GPIO Reset Test - DHT11 sorunları için
"""

import RPi.GPIO as GPIO
import time

DHT_PIN = 15

print("🔧 GPIO Reset ve Test")
print("=" * 50)

# GPIO'yu tamamen temizle
try:
    GPIO.cleanup()
    print("✅ GPIO cleanup yapıldı")
except:
    print("⚠️  GPIO cleanup atlandı")

time.sleep(0.5)

# GPIO'yu yeniden başlat
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin durumunu test et
print(f"\n📍 GPIO {DHT_PIN} pin test ediliyor...")

# 1. OUTPUT olarak test
GPIO.setup(DHT_PIN, GPIO.OUT)
GPIO.output(DHT_PIN, GPIO.HIGH)
print("   HIGH gönderildi (1 saniye)")
time.sleep(1)

GPIO.output(DHT_PIN, GPIO.LOW)
print("   LOW gönderildi (1 saniye)")
time.sleep(1)

GPIO.output(DHT_PIN, GPIO.HIGH)
print("   HIGH gönderildi (1 saniye)")
time.sleep(1)

# 2. INPUT olarak test (pull-up ile)
print(f"\n📍 GPIO {DHT_PIN} INPUT modu test ediliyor...")
GPIO.setup(DHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
state = GPIO.input(DHT_PIN)
print(f"   Pull-up ile INPUT: {'HIGH' if state else 'LOW'}")

time.sleep(0.5)

# 3. INPUT without pull-up
GPIO.setup(DHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
state = GPIO.input(DHT_PIN)
print(f"   Pull-up YOK INPUT: {'HIGH' if state else 'LOW'}")
print(f"   → Eğer HIGH ise: Harici pull-up direnci VAR ✓")
print(f"   → Eğer floating/unstable ise: Pull-up direnci gerekiyor!")

time.sleep(0.5)

# 4. INPUT with pull-down
GPIO.setup(DHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
state = GPIO.input(DHT_PIN)
print(f"   Pull-down ile INPUT: {'HIGH' if state else 'LOW'}")

print("\n" + "=" * 50)
print("✅ GPIO test tamamlandı")
print("\nSONRAKİ ADIM:")
print("  python3 test_dht11_debug.py")

GPIO.cleanup()

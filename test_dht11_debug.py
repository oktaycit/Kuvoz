#!/usr/bin/env python3
"""
DHT11 Debug Test - 2x değer sorunu için
Raspberry Pi 192.168.1.196 için test scripti
"""

import sys
import time
from lib.DHT_Native import read_retry, DHT11

def test_dht11_continuous():
    """DHT11'i sürekli oku ve 2x değer sorununu yakala"""
    
    pin = 15  # GPIO 15
    print(f"DHT11 Debug Test - GPIO {pin}")
    print("=" * 60)
    print("Her 3 saniyede bir okuma yapılıyor...")
    print("Ctrl+C ile durdurun")
    print("=" * 60)
    
    last_temp = None
    read_count = 0
    doubled_count = 0
    
    try:
        while True:
            read_count += 1
            print(f"\n--- Okuma #{read_count} ---")
            
            hum, temp = read_retry(sensor_type=DHT11, pin=pin, retries=3, delay=2.5)
            
            if hum is not None and temp is not None:
                print(f"✅ SONUÇ: {temp}°C, {hum}%rH")
                
                # 2x değer kontrolü
                if last_temp is not None:
                    ratio = temp / last_temp if last_temp > 0 else 0
                    if 1.9 < ratio < 2.1:  # ~2x
                        doubled_count += 1
                        print(f"⚠️  UYARI: Sıcaklık 2 katına çıktı! {last_temp}°C -> {temp}°C (oran: {ratio:.2f}x)")
                        print(f"   2x hata oranı: {doubled_count}/{read_count} = {100*doubled_count/read_count:.1f}%")
                    elif ratio > 2.5 or ratio < 0.4:  # Anormal değişim
                        print(f"⚠️  Anormal sıcaklık değişimi: {last_temp}°C -> {temp}°C (oran: {ratio:.2f}x)")
                
                last_temp = temp
            else:
                print(f"❌ Okuma başarısız")
            
            print(f"Başarı oranı: {(read_count-doubled_count)}/{read_count} = {100*(read_count-doubled_count)/read_count:.1f}%")
            
            time.sleep(3)  # DHT11 için minimum 2 saniye gerekli
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(f"Test tamamlandı: {read_count} okuma")
        print(f"2x hata sayısı: {doubled_count} ({100*doubled_count/read_count:.1f}% hata oranı)")
        print("=" * 60)

if __name__ == "__main__":
    test_dht11_continuous()

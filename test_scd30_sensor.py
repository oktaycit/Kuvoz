#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCD30 CO2 Sensörü Test Script'i
Bu script SCD30'un çalışıp çalışmadığını test eder
"""

import time

print("🧪 SCD30 CO2 Sensörü Test Ediliyor...")
print("=" * 40)

# 1. Kütüphane import testi
try:
    from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider
    from sensirion_i2c_scd30 import Scd30Device
    print("✅ SCD30 kütüphaneleri import edildi")
    library_available = True
except ImportError as e:
    print(f"❌ SCD30 kütüphaneleri import edilemedi: {e}")
    print("   ↳ make deps-scd30 (veya: pip3 install sensirion-driver-adapters sensirion-i2c-scd30 smbus2)")
    library_available = False

sensor_initialized = False
if library_available:
    try:
        # Linux I2C channel provider oluştur (bus 1)
        with LinuxI2cChannelProvider('/dev/i2c-1') as provider:
            channel = provider.get_channel()
            scd30 = Scd30Device(channel)
            # Periyodik ölçüm başlat (0 = otomatik kalibrasyon)
            scd30.start_periodic_measurement(0)
            sensor_initialized = True
            print("✅ SCD30 sensörü başlatıldı")
    except Exception as e:
        print(f"❌ SCD30 initialization hatası: {e}")
        import traceback
        traceback.print_exc()
        sensor_initialized = False

# 3. Ölçüm
if sensor_initialized:
    try:
        # İlk ölçüm için kısa bir bekleme (sensör 2s çevrimle çalışır)
        time.sleep(2.5)
        
        # Aynı provider ve channel ile okuma
        with LinuxI2cChannelProvider('/dev/i2c-1') as provider:
            channel = provider.get_channel()
            scd30 = Scd30Device(channel)
        
        # Veri hazır mı kontrol et
        ready = scd30.get_data_ready()
        if ready:
            # Ölçüm verilerini oku (CO2, sıcaklık, nem)
            co2, temp, humidity = scd30.read_measurement_data()
            
            print(f"🔍 Ölçüm:")
            print(f"   CO2: {co2:.0f} ppm")
            print(f"   Sıcaklık: {temp:.1f} °C")
            print(f"   Nem: {humidity:.1f} %")
            print("🎉 SONUÇ: SCD30 ÇALIŞIYOR")
        else:
            print("⚠️  Veri henüz hazır değil, birkaç saniye sonra tekrar deneyin")
    except Exception as e:
        print(f"❌ Ölçüm hatası: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  SCD30 başlatılamadığı için ölçüm yapılmadı")

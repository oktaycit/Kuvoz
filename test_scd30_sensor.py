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
    from smbus2 import SMBus
    from sensirion_i2c_driver import I2cConnection
    from sensirion_i2c_scd import Scd30I2cDevice
    print("✅ SCD30 kütüphaneleri import edildi")
    library_available = True
except ImportError as e:
    print(f"❌ SCD30 kütüphaneleri import edilemedi: {e}")
    print("   ↳ pip3 install sensirion-i2c-driver sensirion-i2c-scd smbus2")
    library_available = False

sensor_initialized = False
if library_available:
    try:
        bus = SMBus(1)
        scd30 = Scd30I2cDevice(I2cConnection(bus))
        # Ölçümü başlat (metod adı sürüme göre değişebilir)
        try:
            if hasattr(scd30, 'start_periodic_measurement'):
                scd30.start_periodic_measurement()
            elif hasattr(scd30, 'start_continuous_measurement'):
                scd30.start_continuous_measurement()
        except Exception as e:
            print(f"⚠️  Başlatma metodunda uyarı: {e}")
        sensor_initialized = True
        print("✅ SCD30 sensörü başlatıldı")
    except Exception as e:
        print(f"❌ SCD30 initialization hatası: {e}")
        sensor_initialized = False

# 3. Ölçüm
if sensor_initialized:
    try:
        # İlk ölçüm için kısa bir bekleme (sensör 2s çevrimle çalışır)
        time.sleep(2.5)
        measurement = scd30.read_measurement()

        co2_ppm = None
        temp_c = None
        rh = None

        try:
            if isinstance(measurement, (tuple, list)):
                co2_ppm = float(measurement[0])
                if len(measurement) > 1:
                    temp_c = float(measurement[1])
                if len(measurement) > 2:
                    rh = float(measurement[2])
            elif hasattr(measurement, 'co2'):
                co2_ppm = float(measurement.co2)
                temp_c = float(getattr(measurement, 'temperature', 'nan'))
                rh = float(getattr(measurement, 'humidity', 'nan'))
        except Exception:
            pass

        if co2_ppm is not None:
            print(f"🔍 Ölçüm: CO2= {co2_ppm:.0f} ppm, T= {temp_c if temp_c is not None else '--'} °C, RH= {rh if rh is not None else '--'} %")
            print("🎉 SONUÇ: SCD30 ÇALIŞIYOR")
        else:
            print(f"⚠️  Geçersiz ölçüm: {measurement}")
            print("❌ SONUÇ: SCD30 okuma başarısız")
    except Exception as e:
        print(f"❌ Ölçüm hatası: {e}")
else:
    print("⚠️  SCD30 başlatılamadığı için ölçüm yapılmadı")

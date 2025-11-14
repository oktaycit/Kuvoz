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
    library_available = True
    print("✅ smbus2 import edildi")
    
    # Yeni API denemesi (sensirion-i2c-scd >= 1.0)
    try:
        from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
        from sensirion_i2c_scd.scd30 import Scd30Sensor
        SCD_API = "new"
        print("✅ SCD30 kütüphaneleri import edildi (yeni API)")
    except ImportError:
        # Eski API denemesi (sensirion-i2c-scd < 1.0)
        try:
            from sensirion_i2c_driver import I2cConnection
            from sensirion_i2c_scd import Scd30I2cDevice
            SCD_API = "old"
            print("✅ SCD30 kütüphaneleri import edildi (eski API)")
        except ImportError as e:
            print(f"❌ SCD30 kütüphaneleri import edilemedi: {e}")
            print("   ↳ pip3 install sensirion-i2c-driver sensirion-i2c-scd smbus2")
            library_available = False
except ImportError as e:
    print(f"❌ smbus2 import edilemedi: {e}")
    print("   ↳ pip3 install smbus2")
    library_available = False

sensor_initialized = False
if library_available:
    try:
        bus = SMBus(1)
        
        if SCD_API == "new":
            # Yeni API (>= 1.0)
            with LinuxI2cTransceiver('/dev/i2c-1') as i2c_transceiver:
                scd30 = Scd30Sensor(i2c_transceiver)
                # Periyodik ölçüm başlat
                scd30.start_periodic_measurement()
                sensor_initialized = True
                print("✅ SCD30 sensörü başlatıldı (yeni API)")
        else:
            # Eski API (< 1.0)
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
            print("✅ SCD30 sensörü başlatıldı (eski API)")
    except Exception as e:
        print(f"❌ SCD30 initialization hatası: {e}")
        sensor_initialized = False

# 3. Ölçüm
if sensor_initialized:
    try:
        # İlk ölçüm için kısa bir bekleme (sensör 2s çevrimle çalışır)
        time.sleep(2.5)
        
        if SCD_API == "new":
            # Yeni API ile okuma
            with LinuxI2cTransceiver('/dev/i2c-1') as i2c_transceiver:
                scd30 = Scd30Sensor(i2c_transceiver)
                # Veri hazır mı kontrol et
                ready = scd30.get_data_ready()
                if ready:
                    co2, temp_c, rh = scd30.read_measurement_data()
                    co2_ppm = co2.ticks if hasattr(co2, 'ticks') else float(co2)
                    temp_c = temp_c.ticks if hasattr(temp_c, 'ticks') else float(temp_c)
                    rh = rh.ticks if hasattr(rh, 'ticks') else float(rh)
                    print(f"🔍 Ölçüm: CO2= {co2_ppm:.0f} ppm, T= {temp_c:.1f} °C, RH= {rh:.1f} %")
                    print("🎉 SONUÇ: SCD30 ÇALIŞIYOR")
                else:
                    print("⚠️  Veri henüz hazır değil, birkaç saniye bekleyin")
        else:
            # Eski API ile okuma
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

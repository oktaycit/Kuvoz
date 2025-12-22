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
provider = None
channel = None
scd30 = None

if library_available:
    try:
        # Linux I2C channel provider oluştur (bus 1)
        # SCD30 I2C adresi: 0x61, CRC yok (None)
        provider = LinuxI2cChannelProvider('/dev/i2c-1')
        provider.__enter__()  # Context manager'i başlat
        channel = provider.get_channel(slave_address=0x61, crc_parameters=None)
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
        if provider:
            try:
                provider.__exit__(None, None, None)
            except Exception:
                pass

# 3. Ölçüm (Birden fazla deneme)
if sensor_initialized and scd30:
    print("\n⏳ Sensör ısınıyor ve ilk 2 okumayı atlıyoruz...")
    
    # İlk 2 okumayı atla (genelde geçersiz)
    for warmup in range(2):
        time.sleep(3)
        try:
            if scd30.get_data_ready():
                co2, temp, hum = scd30.read_measurement_data()
                print(f"   Warmup {warmup+1}: CO2={co2:.0f}, T={temp:.1f}°C, H={hum:.1f}% (atlandı)")
        except:
            pass
    
    print("\n✅ Şimdi gerçek ölçümler başlıyor...\n")
    
    valid_readings = 0
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            # Veri hazır mı kontrol et
            ready = scd30.get_data_ready()
            if ready:
                # Ölçüm verilerini oku
                co2, temp, humidity = scd30.read_measurement_data()
                
                # Değerlerin makul aralıkta olup olmadığını kontrol et
                co2_valid = 0 <= co2 <= 10000
                temp_valid = -40 <= temp <= 85 and abs(temp) < 100  # Aşırı büyük değerleri reddet
                hum_valid = 0 <= humidity <= 100 and humidity >= 0  # Negatif olmayan
                
                print(f"🔍 Ölçüm {attempt + 1}/{max_attempts}:")
                print(f"   CO2: {co2:.0f} ppm {'✅' if co2_valid else '❌'}")
                print(f"   Sıcaklık: {temp:.1f} °C {'✅' if temp_valid else '❌'}")
                print(f"   Nem: {humidity:.1f} % {'✅' if hum_valid else '❌'}")
                
                if co2_valid and temp_valid and hum_valid:
                    valid_readings += 1
                    if valid_readings >= 2:
                        print("\n🎉 SONUÇ: SCD30 ÇALIŞIYOR VE GEÇERLİ DEĞERLER VERİYOR")
                        break
                else:
                    print("   ⚠️  Bazı değerler geçersiz, yeniden deneniyor...")
            else:
                print(f"\n⏳ Ölçüm {attempt + 1}: Veri henüz hazır değil...")
            
            if attempt < max_attempts - 1:
                time.sleep(2.5)  # Sonraki ölçüm için bekle
                
        except Exception as e:
            print(f"\n❌ Ölçüm {attempt + 1} hatası: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
    
    if valid_readings < 2:
        print("\n⚠️  UYARI: Geçerli ölçüm sayısı yetersiz")
        print("   → Sensör kalibrasyonu gerekebilir")
        print("   → I2C bağlantısını kontrol edin")
        print("   → Sensörü yeniden başlatın (güç kes/ver)")
else:
    print("⚠️  SCD30 başlatılamadığı için ölçüm yapılmadı")

# Temizlik
if provider:
    try:
        provider.__exit__(None, None, None)
    except Exception:
        pass

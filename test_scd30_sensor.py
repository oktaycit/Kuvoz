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
        
        # Soft reset (yeni sensör versiyonu için)
        try:
            scd30.soft_reset()
            time.sleep(0.5)
            print("✅ Soft reset yapıldı")
        except:
            pass  # Eski versiyonlarda bu komut olmayabilir
        
        # Measurement interval ayarla (5 saniye - sensör için daha uygun)
        try:
            scd30.set_measurement_interval(5)
            time.sleep(0.2)
            print("✅ Measurement interval: 5 saniye")
        except Exception as e:
            print(f"⚠️  Measurement interval ayarlanamadı: {e}")
        
        # Otomatik kalibrasyon kapat (hatalı okumaları önler)
        try:
            scd30.deactivate_automatic_self_calibration()
            time.sleep(0.2)
            print("✅ Auto-calibration kapatıldı")
        except AttributeError:
            print("ℹ️  Auto-calibration: API'de mevcut değil (normal)")
        except Exception as e:
            print(f"⚠️  Auto-calibration kapatılamadı: {e}")
        
        # Periyodik ölçüm başlat (0 = ambient basınç)
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
    print("\n⏳ Sensör ısınıyor (measurement interval: 5s)...")
    
    # İlk ölçüm için uzun bekle (yeni sensör versiyonu 30+ saniye gerektirebilir)
    warmup_time = 30  # 5s interval * 6 = 30 saniye
    print(f"   → {warmup_time} saniye bekleniyor...")
    time.sleep(warmup_time)
    
    print("   → Sensör durumu kontrol ediliyor...")
    try:
        ready = scd30.get_data_ready()
        print(f"   → get_data_ready() = {ready}")
    except Exception as e:
        print(f"   ⚠️  get_data_ready() hatası: {e}")
    
    # İlk okumayı atla (genelde geçersiz) - SADECE ready ise
    try:
        ready_check = scd30.get_data_ready()
        print(f"   Warmup ready check: {ready_check}")
        if ready_check:
            co2, temp, hum = scd30.read_measurement_data()
            print(f"   Warmup: CO2={co2:.0f}, T={temp:.1f}°C, H={hum:.1f}% (atlandı)")
        else:
            print(f"   Warmup: Veri henüz yok, doğrudan ölçümlere geçiliyor")
    except Exception as e:
        print(f"   Warmup hatası: {e}")
    
    print("\n✅ Şimdi gerçek ölçümler başlıyor (blocking_read kullanılıyor)...\n")
    print("ℹ️  Not: blocking_read_measurement_data() metodu otomatik polling yapar")
    print("      Veri gelene kadar bekler - bu 5-15 saniye sürebilir\n")
    
    valid_readings = 0
    max_attempts = 10
    
    for attempt in range(max_attempts):
        try:
            print(f"⏳ Ölçüm {attempt + 1}/{max_attempts}: Veri bekleniyor...")
            
            # SENSIRION RESMİ METOD: Veri gelene kadar otomatik bekler
            co2, temp, humidity = scd30.blocking_read_measurement_data()
            
            # nan kontrolü
            import math
            is_nan = math.isnan(co2) or math.isnan(temp) or math.isnan(humidity)
            
            if is_nan:
                print(f"   ⚠️  nan algılandı (sensör henüz hazır değil)")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                continue
            
            # Değerlerin makul aralıkta olup olmadığını kontrol et
            co2_valid = 0 <= co2 <= 10000
            temp_valid = -40 <= temp <= 85 and abs(temp) < 100
            hum_valid = 0 <= humidity <= 100 and humidity >= 0
            
            print(f"\n✅ Ölçüm {attempt + 1}/{max_attempts}:")
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
            
            if attempt < max_attempts - 1:
                time.sleep(2)
                
        except Exception as e:
            print(f"\n❌ Ölçüm {attempt + 1} hatası: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
    
    if valid_readings < 2:
        print("\n⚠️  UYARI: Geçerli ölçüm sayısı yetersiz")
        print("   → Sensörü fiziksel olarak resetleyin (güç kes/ver)")
        print("   → Veya Raspberry Pi'yi yeniden başlatın: sudo reboot")
else:
    print("⚠️  SCD30 başlatılamadığı için ölçüm yapılmadı")

# Temizlik
if provider:
    try:
        provider.__exit__(None, None, None)
    except Exception:
        pass

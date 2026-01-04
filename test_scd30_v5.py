#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCD30 v5 Özel Test - v5 firmware için optimize edilmiş
"""

import time
import math

print("🧪 SCD30 v5 Özel Test")
print("=" * 50)

try:
    from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider
    from sensirion_i2c_scd30 import Scd30Device
    print("✅ Kütüphaneler yüklendi")
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    exit(1)

try:
    provider = LinuxI2cChannelProvider('/dev/i2c-1')
    provider.__enter__()
    channel = provider.get_channel(slave_address=0x61, crc_parameters=None)
    scd30 = Scd30Device(channel)
    
    print("\n⚙️  SCD30 v5 İçin Özel Konfigürasyon...")
    print("-" * 50)
    
    # 1. Stop measurement (eğer çalışıyorsa)
    try:
        scd30.stop_periodic_measurement()
        time.sleep(0.5)
        print("✅ Periodic measurement durduruldu")
    except:
        pass
    
    # 2. Soft reset - v5 için kritik
    try:
        scd30.soft_reset()
        time.sleep(2.0)  # v5 için daha uzun bekleme
        print("✅ Soft reset (2s bekleme)")
    except Exception as e:
        print(f"⚠️  Soft reset: {e}")
    
    # 3. Auto-calibration KAPAT (v5'te sorun çıkarıyor)
    try:
        scd30.activate_auto_calibration(0)  # 0 = kapat
        time.sleep(0.5)
        print("✅ Auto-calibration kapatıldı")
    except Exception as e:
        print(f"ℹ️  Auto-calibration: {e}")
    
    # 4. Measurement interval: 10 saniye (v5 için daha uzun)
    try:
        scd30.set_measurement_interval(10)
        time.sleep(0.5)
        print("✅ Measurement interval: 10 saniye")
    except Exception as e:
        print(f"⚠️  Measurement interval: {e}")
    
    # 5. Altitude compensation (deniz seviyesi)
    try:
        scd30.set_altitude_compensation(0)
        time.sleep(0.2)
        print("✅ Altitude: 0m (deniz seviyesi)")
    except:
        pass
    
    # 6. Periyodik ölçüm başlat
    scd30.start_periodic_measurement(0)  # 0 = ambient pressure
    print("✅ Periyodik ölçüm başlatıldı")
    
    # 7. UZUN warm-up (v5 için 30-45 saniye gerekli)
    warmup_time = 45
    print(f"\n⏳ v5 warm-up: {warmup_time} saniye bekleniyor...")
    print("   (v5 sensörler daha uzun ısınma süresi gerektirir)")
    time.sleep(warmup_time)
    
    print("\n✅ Şimdi ölçümler başlıyor...\n")
    
    # 8. İlk 2 okumayı atla
    for i in range(2):
        try:
            co2, temp, hum = scd30.read_measurement_data()
            print(f"   Warmup {i+1}/2: CO2={co2:.0f} (atlandı)")
            time.sleep(10)  # Measurement interval kadar bekle
        except:
            time.sleep(10)
    
    # 9. Gerçek ölçümler
    print("\n📊 Gerçek Ölçümler:\n")
    valid_count = 0
    
    for attempt in range(10):
        try:
            # blocking_read kullan
            co2, temp, humidity = scd30.blocking_read_measurement_data()
            
            # nan kontrolü
            is_nan = math.isnan(co2) or math.isnan(temp) or math.isnan(humidity)
            
            if not is_nan:
                co2_valid = 400 <= co2 <= 10000
                temp_valid = -40 <= temp <= 85
                hum_valid = 0 <= humidity <= 100
                
                if co2_valid and temp_valid and hum_valid:
                    valid_count += 1
                    print(f"✅ Ölçüm {attempt+1}: CO2={co2:.0f}ppm  T={temp:.1f}°C  H={humidity:.1f}%")
                    
                    if valid_count >= 3:
                        print(f"\n🎉 BAŞARI! v5 sensör çalışıyor")
                        print(f"   → {valid_count} geçerli ölçüm alındı")
                        break
                else:
                    print(f"⚠️  Ölçüm {attempt+1}: Değerler şüpheli - CO2={co2:.0f} T={temp:.1f} H={humidity:.1f}")
            else:
                print(f"❌ Ölçüm {attempt+1}: nan değerler")
                
        except Exception as e:
            print(f"❌ Ölçüm {attempt+1} hatası: {e}")
    
    if valid_count < 3:
        print(f"\n⚠️  Sadece {valid_count} geçerli ölçüm - sensör arızalı olabilir")
        print("   → Fiziksel reset deneyin (güç kes/ver 30 saniye)")
        print("   → Factory reset gerekebilir")
    
    provider.__exit__(None, None, None)
    
except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()

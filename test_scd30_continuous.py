#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCD30 CO2 Sensörü Sürekli Test - Ne Zaman Veri Gelir?
Bu script sensörü sürekli okur ve ilk geçerli veri gelene kadar bekler
"""

import time
import math

print("🧪 SCD30 Sürekli Okuma Testi")
print("=" * 50)

# Kütüphane import
try:
    from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider
    from sensirion_i2c_scd30 import Scd30Device
    print("✅ Kütüphaneler yüklendi")
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    exit(1)

# Sensör başlat
try:
    provider = LinuxI2cChannelProvider('/dev/i2c-1')
    provider.__enter__()
    channel = provider.get_channel(slave_address=0x61, crc_parameters=None)
    scd30 = Scd30Device(channel)
    
    # Soft reset
    try:
        scd30.soft_reset()
        time.sleep(0.5)
        print("✅ Soft reset OK")
    except:
        print("ℹ️  Soft reset yok (eski API)")
    
    # Measurement interval
    try:
        scd30.set_measurement_interval(5)
        time.sleep(0.2)
        print("✅ Measurement interval: 5s")
    except Exception as e:
        print(f"⚠️  Measurement interval ayarlanamadı: {e}")
    
    # Periyodik ölçüm başlat
    scd30.start_periodic_measurement(0)
    print("✅ Sensör başlatıldı")
    
except Exception as e:
    print(f"❌ Sensör başlatma hatası: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Sürekli okuma
print("\n🔄 Sürekli okuma başlıyor...")
print("   (Ctrl+C ile durdurun)\n")

start_time = time.time()
attempt = 0
first_valid = False

try:
    while attempt < 30:  # Maksimum 30 deneme (150 saniye)
        attempt += 1
        elapsed = time.time() - start_time
        
        # get_data_ready kontrol
        try:
            ready = scd30.get_data_ready()
        except:
            ready = "error"
        
        # Her 5 saniyede bir oku
        if attempt > 1:
            time.sleep(5)
        
        # Okumayı dene
        try:
            co2, temp, humidity = scd30.read_measurement_data()
            
            # nan kontrolü
            is_nan = math.isnan(co2) or math.isnan(temp) or math.isnan(humidity)
            
            if is_nan:
                print(f"⏳ {elapsed:5.1f}s | Deneme {attempt:2d} | ready={ready} | nan (henüz hazır değil)")
            else:
                # Geçerli değerler
                co2_valid = 0 <= co2 <= 10000
                temp_valid = -40 <= temp <= 85
                hum_valid = 0 <= humidity <= 100
                
                if co2_valid and temp_valid and hum_valid:
                    print(f"✅ {elapsed:5.1f}s | Deneme {attempt:2d} | CO2={co2:.0f}ppm T={temp:.1f}°C H={humidity:.1f}%")
                    if not first_valid:
                        print(f"\n🎉 İLK GEÇERLİ VERİ! (Süre: {elapsed:.1f} saniye)")
                        first_valid = True
                        # 2 geçerli okuma daha al
                        continue
                    
                    # first_valid = True ve birkaç okuma daha yaptıysak
                    if first_valid:
                        valid_count = attempt - 1  # İlk valid'den sonraki okuma sayısı
                        if valid_count >= 2:  # İlk valid + 2 okuma daha
                            print(f"\n✅ BAŞARI: Sensör {elapsed:.1f} saniye sonra çalışmaya başladı")
                            print(f"   Toplam deneme: {attempt}")
                            break
                else:
                    print(f"⚠️  {elapsed:5.1f}s | Deneme {attempt:2d} | Geçersiz: CO2={co2:.0f} T={temp:.1f} H={humidity:.1f}")
        
        except Exception as e:
            print(f"❌ {elapsed:5.1f}s | Deneme {attempt:2d} | Okuma hatası: {e}")

except KeyboardInterrupt:
    print("\n\n⏹️  Test kullanıcı tarafından durduruldu")

# Temizlik
try:
    provider.__exit__(None, None, None)
except:
    pass

if not first_valid:
    print(f"\n⚠️  {attempt} denemede geçerli veri gelmedi")
    print("   → Sensörü resetleyin (güç kes/ver)")
    print("   → I2C bağlantısını kontrol edin")
    print("   → sudo i2cdetect -y 1 (0x61 görünmeli)")

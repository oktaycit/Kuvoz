#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oksijen Sensörü Test Script'i
Bu script oksijen sensörünün çalışıp çalışmadığını test eder
"""

import sys
sys.path.append("lib/")

print("🧪 Oksijen Sensörü Test Ediliyor...")
print("=" * 40)

# 1. Kütüphane import testi
try:
    from DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3, COLLECT_NUMBER
    print("✅ DFRobot_Oxygen kütüphanesi import edildi")
    library_available = True
except ImportError as e:
    print(f"❌ DFRobot_Oxygen kütüphanesi import edilemedi: {e}")
    library_available = False

# 2. Sensör initialization testi
if library_available:
    try:
        oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
        print("✅ Oksijen sensörü initialized")
        sensor_initialized = True
    except Exception as e:
        print(f"❌ Oksijen sensörü initialization hatası: {e}")
        sensor_initialized = False
else:
    sensor_initialized = False

# 3. Sensör okuma testi
if sensor_initialized:
    try:
        print("🔍 Oksijen sensörü test okuması yapılıyor...")
        oxygen_reading = oxygen_sensor.get_oxygen_data(5)  # 5 sample
        
        if oxygen_reading is not None:
            if 0 <= oxygen_reading <= 100:
                print(f"✅ Oksijen sensörü okuması başarılı: {oxygen_reading:.1f}%")
                sensor_working = True
            else:
                print(f"⚠️  Oksijen sensörü geçersiz değer: {oxygen_reading}")
                sensor_working = False
        else:
            print("❌ Oksijen sensörü None değer döndürdü")
            sensor_working = False
            
    except Exception as e:
        print(f"❌ Oksijen sensörü okuma hatası: {e}")
        sensor_working = False
else:
    sensor_working = False

# 4. Sonuç raporu
print("\n📊 TEST SONUÇLARI:")
print("=" * 40)
print(f"Kütüphane:     {'✅ OK' if library_available else '❌ HATA'}")
print(f"Initialization: {'✅ OK' if sensor_initialized else '❌ HATA'}")
print(f"Okuma:         {'✅ OK' if sensor_working else '❌ HATA'}")

if sensor_working:
    print("\n🎉 SONUÇ: Oksijen sensörü ÇALIŞIYOR")
    print("   ✅ Web dashboard'da görünecek")
    print("   ✅ Gerçek zamanlı okumalar yapılacak")
else:
    print("\n⚠️  SONUÇ: Oksijen sensörü ÇALIŞMIYOR")
    print("   ❌ Web dashboard'da görünmeyecek")
    print("   ❌ Oksijen okumaları yapılmayacak")
    print("   ℹ️  Sistem oksijen sensörü olmadan çalışmaya devam edecek")

print("\n💡 NOT: Web sunucusu başlatıldığında aynı test otomatik yapılır")
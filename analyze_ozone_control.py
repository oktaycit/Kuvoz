#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oksijen Sensörü ve Ozon Kontrolü Analiz Script'i
Bu script oksijen sensörü varlığına göre ozon kontrol stratejilerini analiz eder
"""

import sys
import time
sys.path.append("lib/")

def analyze_ozone_strategy():
    print("🔬 OKSIJEN SENSÖRÜ VE OZON KONTROLÜ ANALİZİ")
    print("=" * 60)
    
    # 1. Oksijen sensörü testi
    print("\n1️⃣  OKSİJEN SENSÖRÜ DURUMU:")
    print("-" * 40)
    
    try:
        from DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3
        oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
        
        # Test okuma
        oxygen_reading = oxygen_sensor.get_oxygen_data(5)
        
        if oxygen_reading is not None and 0 <= oxygen_reading <= 100:
            oxygen_available = True
            print(f"✅ Oksijen sensörü ÇALIŞIYOR: {oxygen_reading:.1f}%")
        else:
            oxygen_available = False
            print(f"❌ Oksijen sensörü geçersiz değer: {oxygen_reading}")
            
    except Exception as e:
        oxygen_available = False
        print(f"❌ Oksijen sensörü ÇALIŞMIYOR: {e}")
    
    print(f"\n📊 Sonuç: Oksijen sensörü {'MEVCUT' if oxygen_available else 'YOK'}")
    
    # 2. Ozon kontrol stratejisi analizi
    print("\n2️⃣  OZON KONTROL STRATEJİSİ:")
    print("-" * 40)
    
    if oxygen_available:
        print("🌟 AKILLI OZON KONTROLÜ (Oksijen Bazlı)")
        print("   ├── Yüksek O₂ (>24%):  Hemen ozon + tam süre")
        print("   ├── Normal+ O₂ (22-24%): Standart ozon döngüsü")
        print("   ├── Normal O₂ (18-22%):  Kısa süreli ozon (yarı süre)")
        print("   └── Düşük O₂ (<18%):    Ozon DEVREBEŞİ (güvenlik)")
        print("")
        print("📈 AVANTAJLARI:")
        print("   ✅ Gerçek zamanlı oksijen seviyesi kontrolü")
        print("   ✅ Otomatik güvenlik koruması")
        print("   ✅ Enerji tasarrufu (gereksiz ozon yok)")
        print("   ✅ Optimum hava kalitesi")
        
        # Test senaryoları
        test_scenarios = [
            (25.5, "Yüksek", "Hemen ozon + tam süre"),
            (23.2, "Normal+", "Standart ozon döngüsü"),
            (20.1, "Normal", "Kısa süreli ozon"),
            (16.8, "Düşük", "Ozon devre dışı")
        ]
        
        print("\n🧪 TEST SENARYOLARİ:")
        for oxygen_level, category, action in test_scenarios:
            print(f"   O₂ {oxygen_level:5.1f}% → {category:8s} → {action}")
            
    else:
        print("⏰ ZAMANLI OZON KONTROLÜ (Sabit Aralık)")
        print("   ├── Sabit aralıklar: Her X saatte bir")
        print("   ├── Sabit süre: Y dakika çalışma")
        print("   └── Manuel kontrol: Buton ile açma/kapama")
        print("")
        print("📊 ÖZELLİKLERİ:")
        print("   ⚠️  Oksijen seviyesi bilinmiyor")
        print("   ⚠️  Güvenlik kontrolü yok")
        print("   ✅ Basit ve güvenilir")
        print("   ✅ Öngörülebilir çalışma")
    
    # 3. Güvenlik analizi
    print("\n3️⃣  GÜVENLİK ANALİZİ:")
    print("-" * 40)
    
    if oxygen_available:
        print("🛡️  YÜKSEK GÜVENLİK:")
        print("   ✅ Düşük oksijen durumunda ozon otomatik durur")
        print("   ✅ Gerçek zamanlı izleme")
        print("   ✅ Adaptif kontrol")
        print("   ✅ Aşırı ozon üretimi önlenir")
    else:
        print("⚠️  ORTA GÜVENLİK:")
        print("   ⚠️  Oksijen seviyesi bilinmiyor")
        print("   ⚠️  Manuel müdahale gerekebilir")
        print("   ✅ Sabit aralık güvenli")
        print("   ✅ Manuel kontrol mevcut")
    
    # 4. Öneriler
    print("\n4️⃣  ÖNERİLER:")
    print("-" * 40)
    
    if oxygen_available:
        print("🎯 Mevcut durumunuz OPTIMAL:")
        print("   ➤ Oksijen sensörü çalışıyor")
        print("   ➤ Akıllı ozon kontrolü aktif")
        print("   ➤ Sistem otomatik optimize ediliyor")
        print("   ➤ Ek ayar gerekmez")
    else:
        print("🔧 İyileştirme önerileri:")
        print("   ➤ Oksijen sensörü bağlantısını kontrol edin")
        print("   ➤ I2C bağlantı pinlerini kontrol edin")
        print("   ➤ Sensör kalibrasyonu yapın")
        print("   ➤ Şimdilik zamanlı kontrol güvenli")
    
    # 5. Web arayüzü bilgileri
    print("\n5️⃣  WEB ARAYÜZÜ:")
    print("-" * 40)
    
    if oxygen_available:
        print("🌐 Dashboard'da görünecek:")
        print("   ✅ Oksijen sensörü kartı")
        print("   ✅ Ozon butonu: 'O2-SMART' modu")
        print("   ✅ Gerçek zamanlı O₂ değerleri")
        print("   ✅ Dinamik ozon durumu")
    else:
        print("🌐 Dashboard'da görünecek:")
        print("   ❌ Oksijen sensörü kartı gizli")
        print("   ✅ Ozon butonu: 'TIMED' modu")
        print("   ✅ Sadece sıcaklık/nem kartları")
        print("   ✅ Manuel ozon kontrolü")
    
    return oxygen_available

def simulate_ozone_logic(oxygen_available, oxygen_level=None):
    """Ozon kontrol mantığını simüle et"""
    print(f"\n🎮 OZON KONTROL SİMÜLASYONU:")
    print("-" * 40)
    
    if oxygen_available and oxygen_level is not None:
        print(f"📊 Oksijen seviyesi: {oxygen_level:.1f}%")
        
        if oxygen_level > 24.0:
            print("💨 Ozon Kararı: HEMEN BAŞLAT (yüksek oksijen)")
            duration = 30  # dakika
        elif oxygen_level > 22.0:
            print("💨 Ozon Kararı: STANDART ÇALIŞMA (normal+ oksijen)") 
            duration = 30  # dakika
        elif oxygen_level >= 18.0:
            print("💨 Ozon Kararı: KISA SÜRELİ (normal oksijen)")
            duration = 15  # dakika
        else:
            print("🚫 Ozon Kararı: DEVRE DIŞI (güvenlik)")
            duration = 0
            
        if duration > 0:
            print(f"⏱️  Çalışma süresi: {duration} dakika")
            print(f"🔄 Bir sonraki kontrol: 8 saat sonra (veya yüksek O₂ tespit)")
        else:
            print("⏱️  Çalışma süresi: 0 dakika (güvenlik)")
            print("🔄 Bir sonraki kontrol: Normal aralıkta kontrol edilir")
    else:
        print("📊 Oksijen seviyesi: Bilinmiyor")
        print("💨 Ozon Kararı: ZAMANLI ÇALIŞMA")
        print("⏱️  Çalışma süresi: 30 dakika")
        print("🔄 Bir sonraki kontrol: 8 saat sonra (sabit)")

if __name__ == "__main__":
    # Ana analiz
    oxygen_available = analyze_ozone_strategy()
    
    # Simülasyon örnekleri
    if oxygen_available:
        # Farklı oksijen seviyeleri ile test
        test_levels = [26.2, 23.5, 19.8, 16.5]
        for level in test_levels:
            simulate_ozone_logic(oxygen_available, level)
    else:
        simulate_ozone_logic(oxygen_available)
    
    print(f"\n{'='*60}")
    print("✅ ANALİZ TAMAMLANDI")
    print("🚀 Web sunucusunu başlat: python3 web_server.py")
    print("🌐 Tarayıcıda aç: http://localhost:5000")
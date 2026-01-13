#!/usr/bin/env python3
"""
GPIO Test Tool - Hızlı port açma/kapama test aracı
Kullanım: sudo python3 gpio_test.py -test <PIN> <on|off>
"""

import RPi.GPIO as GPIO
import sys
import time
from datetime import datetime

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin tanımları (referans için)
PIN_NAMES = {
    5: "Terapötik Aydınlatma (b1)",
    6: "Nebulizer (b2)",
    13: "Nemlendirici (b3)",
    16: "Karbon Isıtıcı (b4)",
    19: "IR Isıtıcı (b5)",
    20: "Fan (b6)",
    21: "UV Sterilizasyon (b7)",
    26: "Ozon (b8)",
    12: "Soğutma (b9)"
}

def timestamp():
    """Zaman damgası döndür"""
    return datetime.now().strftime("%H:%M:%S")

def set_gpio_state(pin, state):
    """
    GPIO pinini belirtilen duruma getir
    
    Args:
        pin: GPIO pin numarası (BCM)
        state: 'on' veya 'off'
    """
    try:
        pin_name = PIN_NAMES.get(pin, f"Pin {pin}")
        
        # Pin'i output olarak ayarla
        GPIO.setup(pin, GPIO.OUT)
        
        # Durum belirleme (Relay logic: LOW=ON, HIGH=OFF)
        if state.lower() == 'on':
            GPIO.output(pin, GPIO.LOW)
            gpio_state = "LOW"
            relay_state = "AÇIK ✅"
        elif state.lower() == 'off':
            GPIO.output(pin, GPIO.HIGH)
            gpio_state = "HIGH"
            relay_state = "KAPALI ❌"
        else:
            print(f"❌ HATA: Geçersiz durum '{state}'. 'on' veya 'off' kullanın.")
            return False
        
        # Kısa bekleme
        time.sleep(0.1)
        
        # Okuma ile doğrula
        read_value = GPIO.input(pin)
        expected = 0 if state.lower() == 'on' else 1
        
        print(f"[{timestamp()}] 🔌 GPIO{pin} ({pin_name})")
        print(f"[{timestamp()}] ➡️  Komut: {state.upper()} → GPIO = {gpio_state}")
        print(f"[{timestamp()}] ⬅️  Okuma: {read_value} {'✅' if read_value == expected else '❌ HATA!'}")
        print(f"[{timestamp()}] 📊 Röle durumu: {relay_state}")
        
        if read_value == expected:
            print(f"[{timestamp()}] ✅ İşlem başarılı!\n")
            return True
        else:
            print(f"[{timestamp()}] ⚠️  UYARI: Okuma değeri beklenen ile uyuşmuyor!\n")
            return False
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_usage():
    """Kullanım bilgisi"""
    print("\n" + "="*60)
    print("🔧 GPIO TEST ARACI")
    print("="*60)
    print("\n📖 KULLANIM:")
    print("  sudo python3 gpio_test.py -test <PIN> <on|off>")
    print("\n📝 ÖRNEKLER:")
    print("  sudo python3 gpio_test.py -test 12 on   # GPIO12'yi aç")
    print("  sudo python3 gpio_test.py -test 12 off  # GPIO12'yi kapat")
    print("  sudo python3 gpio_test.py -test 5 on    # GPIO5'i aç")
    print("  sudo python3 gpio_test.py -test 20 off  # GPIO20'yi kapat")
    print("\n🔌 MEVCUT PİNLER:")
    for pin, name in sorted(PIN_NAMES.items()):
        print(f"  GPIO{pin:2d} - {name}")
    print("\n💡 NOT:")
    print("  - Röle mantığı: LOW = AÇIK, HIGH = KAPALI")
    print("  - 'on' komutu → GPIO LOW → Röle AÇIK")
    print("  - 'off' komutu → GPIO HIGH → Röle KAPALI")
    print("="*60 + "\n")

def main():
    """Ana fonksiyon"""
    # Argüman kontrolü
    if len(sys.argv) < 4:
        print_usage()
        sys.exit(0)
    
    # -test argümanı kontrolü
    if sys.argv[1] != '-test':
        print(f"\n❌ HATA: İlk argüman '-test' olmalı!")
        print_usage()
        sys.exit(1)
    
    try:
        # Argümanları parse et
        pin = int(sys.argv[2])
        state = sys.argv[3]
        
        # Pin numarası kontrolü
        if pin < 0 or pin > 27:
            print(f"\n❌ HATA: Geçersiz pin numarası: {pin}")
            print("   Pin numarası 0-27 arası olmalı!")
            sys.exit(1)
        
        # Durum kontrolü
        if state.lower() not in ['on', 'off']:
            print(f"\n❌ HATA: Geçersiz durum: '{state}'")
            print("   Durum 'on' veya 'off' olmalı!")
            sys.exit(1)
        
        # Test başlat
        print(f"\n{'='*60}")
        print(f"🚀 GPIO TEST BAŞLIYOR")
        print(f"{'='*60}\n")
        
        success = set_gpio_state(pin, state)
        
        # Sonuç
        if success:
            print(f"{'='*60}")
            print(f"✅ TEST TAMAMLANDI")
            print(f"{'='*60}\n")
            sys.exit(0)
        else:
            print(f"{'='*60}")
            print(f"⚠️  TEST TAMAMLANDI (UYARILAR VAR)")
            print(f"{'='*60}\n")
            sys.exit(1)
        
    except ValueError:
        print(f"\n❌ HATA: Pin numarası sayı olmalı!")
        print_usage()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test iptal edildi (Ctrl+C)")
        sys.exit(130)
    finally:
        # GPIO temizleme yapma - durumu korumak için
        pass

if __name__ == "__main__":
    main()

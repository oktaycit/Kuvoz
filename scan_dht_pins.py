#!/usr/bin/env python3
"""
DHT Sensör Port Tarama
Tüm GPIO pinlerini tarar ve DHT sensörünü bulur
"""

import RPi.GPIO as GPIO
import time
import sys

# Pi Zero 2'de kullanılabilir GPIO pinleri (BCM numarası)
TESTABLE_PINS = [
    2, 3, 4, 14, 15, 17, 18, 27, 22, 23, 24, 10, 9, 25, 11, 8, 7, 5, 6, 12, 13, 19, 16, 26, 20, 21
]

def test_dht_on_pin(pin):
    """Belirtilen pin'de DHT sensörü var mı test et"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # DHT başlatma sinyali gönder
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.02)  # DHT11: 18-20ms LOW
        
        # INPUT'a geç ve sensörden cevap bekle
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.00004)
        
        # DHT sensörü cevap verirse pin LOW'a düşer
        timeout = time.time() + 0.1
        unchanged_count = 0
        last_state = GPIO.input(pin)
        
        while time.time() < timeout:
            current_state = GPIO.input(pin)
            if current_state != last_state:
                unchanged_count = 0
                last_state = current_state
            else:
                unchanged_count += 1
            
            # Eğer pin değişirse (sensör cevap veriyor)
            if unchanged_count == 0 and last_state == 0:
                # LOW algılandı - muhtemelen DHT var
                time.sleep(0.001)
                # Birkaç state değişimi daha bekle
                changes = 0
                check_timeout = time.time() + 0.05
                while time.time() < check_timeout and changes < 10:
                    new_state = GPIO.input(pin)
                    if new_state != last_state:
                        changes += 1
                        last_state = new_state
                
                if changes >= 5:  # En az 5 değişim = DHT protokolü
                    return True, changes
        
        return False, 0
        
    except Exception as e:
        return False, 0
    finally:
        try:
            GPIO.cleanup(pin)
        except:
            pass

def main():
    print("🔍 DHT Sensör Port Tarama")
    print("=" * 50)
    print("Pi Zero 2'de DHT sensörü aranıyor...")
    print("")
    
    found_pins = []
    
    for pin in TESTABLE_PINS:
        sys.stdout.write(f"\rPin {pin:2d} kontrol ediliyor...  ")
        sys.stdout.flush()
        
        has_dht, changes = test_dht_on_pin(pin)
        
        if has_dht:
            found_pins.append((pin, changes))
            print(f"\r✅ GPIO {pin:2d} → DHT sensörü BULUNDU! ({changes} sinyal değişimi)")
        
        time.sleep(0.1)  # Sensörü dinlendirmek için
    
    print("\r" + " " * 50)  # Clear progress line
    print("")
    print("=" * 50)
    
    if found_pins:
        print("🎯 SONUÇ: DHT sensörü bulundu!")
        print("")
        for pin, changes in found_pins:
            physical_pin = get_physical_pin(pin)
            print(f"  📍 GPIO {pin} (Physical Pin {physical_pin})")
            print(f"     Sinyal kalitesi: {changes} değişim")
            print("")
        print("Kullanım:")
        for pin, _ in found_pins:
            print(f"  python3 test_dht11_debug.py {pin}")
    else:
        print("❌ Hiçbir GPIO pin'de DHT sensörü bulunamadı")
        print("")
        print("Kontrol edilecekler:")
        print("  • DHT sensörü güç alıyor mu? (VCC → 3.3V, GND → GND)")
        print("  • Data pini doğru bağlı mı?")
        print("  • Pull-up rezistans var mı? (4.7kΩ - 10kΩ)")
        print("  • Sensör çalışıyor mu? (başka bir cihazda test et)")

def get_physical_pin(bcm_pin):
    """BCM numarasından Physical pin numarasını döndür"""
    bcm_to_physical = {
        2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13,
        22: 15, 23: 16, 24: 18, 10: 19, 9: 21, 25: 22, 11: 23,
        8: 24, 7: 26, 5: 29, 6: 31, 12: 32, 13: 33, 19: 35,
        16: 36, 26: 37, 20: 38, 21: 40
    }
    return bcm_to_physical.get(bcm_pin, "?")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tarama iptal edildi")
        GPIO.cleanup()
    except Exception as e:
        print(f"\n\n❌ Hata: {e}")
        GPIO.cleanup()

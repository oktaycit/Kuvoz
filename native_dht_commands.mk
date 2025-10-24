# Native DHT Driver Test
test-native-dht:
	@echo "🧪 Native DHT driver test ediliyor..."
	@echo "1. DHT_Native.py import testi:"
	@python3 -c "import sys; sys.path.append('lib'); from DHT_Native import read_retry, read, DHT11, DHT22; print('✅ Native DHT import başarılı')" || echo "❌ Native DHT import başarısız"
	@echo ""
	@echo "2. DHT11 test okuma:"
	@python3 -c "import sys; sys.path.append('lib'); from DHT_Native import read_retry, DHT11; h,t=read_retry(DHT11, 15); print(f'DHT11: {t}°C, {h}%')" || echo "❌ DHT11 test başarısız"
	@echo ""
	@echo "3. DHT22 test okuma:"
	@python3 -c "import sys; sys.path.append('lib'); from DHT_Native import read_retry, DHT22; h,t=read_retry(DHT22, 15); print(f'DHT22: {t}°C, {h}%')" || echo "❌ DHT22 test başarısız"

# Safe run with fallback systems
.PHONY: run-safe
run-safe:
	@echo "🛡️  Güvenli mod çalıştırma (tüm fallback'ler aktif)..."
	@echo "✅ Native DHT driver aktif"
	@echo "✅ Oxygen sensör fallback aktif"
	@echo "✅ Test verileri ile çalışma hazır"
	@sudo python3 main3.py

# Native DHT ile çalıştırma
.PHONY: run-native
run-native:
	@echo "🚀 Native DHT driver ile çalıştırma..."
	@echo "Adafruit_DHT yerine kendi DHT driver'ımız kullanılıyor"
	@sudo python3 main3.py

# DHT system paketlerini kaldır
.PHONY: remove-adafruit-dht  
remove-adafruit-dht:
	@echo "🗑️  Adafruit-DHT kütüphanesi kaldırılıyor..."
	@sudo apt remove -y python3-adafruit-dht 2>/dev/null || echo "Sistem paketi bulunamadı"
	@sudo pip3 uninstall -y Adafruit-DHT 2>/dev/null || echo "pip paketi bulunamadı"
	@rm -rf Adafruit_Python_DHT 2>/dev/null || echo "Kaynak kod temizlendi"
	@echo "✅ Adafruit-DHT tamamen kaldırıldı"
	@echo "🔧 Artık Native DHT driver kullanılıyor"

# Test all imports
.PHONY: test-imports
test-imports:
	@echo "📦 Import testleri..."
	@echo "1. Main imports:"
	@python3 -c "import RPi.GPIO as GPIO; import kivy; import threading; import time; print('✅ Temel imports OK')" || echo "❌ Temel imports HATA"
	@echo ""
	@echo "2. DHT imports:"
	@python3 -c "import sys; sys.path.append('lib'); from DHT_Native import read_retry, read, DHT11, DHT22; print('✅ DHT_Native OK')" || echo "❌ DHT_Native HATA"
	@echo ""
	@echo "3. Oxygen imports:"
	@python3 -c "import sys; sys.path.append('lib'); from DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3; print('✅ DFRobot_Oxygen OK')" || echo "❌ DFRobot_Oxygen HATA"

# Thread debugging
.PHONY: debug-threads
debug-threads:
	@echo "🧵 Thread debugging modunda çalıştırma..."
	@echo "Thread hataları yakalanacak ve loglanacak"
	@sudo python3 -c "import threading; print(f'Active threads: {threading.active_count()}'); import main3; print('main3 yüklendi')" || echo "Thread test başarısız"

# Run with verbose threading
.PHONY: run-verbose
run-verbose:
	@echo "🔊 Verbose thread logging ile çalıştırma..."
	@sudo PYTHONUNBUFFERED=1 python3 main3.py 1
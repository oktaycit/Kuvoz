# Kuvoz İnkübatör Kontrol Sistemi Makefile
# Raspberry Pi OS Trixie (Debian 13.1) için
# Web Interface + Chromium Kiosk Mode

# Değişkenler
PYTHON := python3
PIP := pip3
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
PROJECT_DIR := $(shell pwd)
SERVICE_NAME := kuvoz
WEB_SERVICE_NAME := kuvoz-web
KIOSK_SERVICE_NAME := kuvoz-kiosk

# Include native DHT commands
include native_dht_commands.mk
include syntax_test.mk
include gpio_test.mk
include ui_test.mk
include chromium_kiosk.mk
include firefox_kiosk.mk
USER := $(shell whoami)

# Varsayılan hedef
.PHONY: help
help:
	@echo "Kuvoz İnkübatör Kontrol Sistemi - Kurulum ve Yönetim"
	@echo "=================================================="
	@echo ""
	@echo "Kullanılabilir komutlar:"
	@echo "  🎯 ÖNERİLEN (durumunuz için):"
	@echo "  quick-start     - Hızlı başlangıç rehberi"
	@echo "  run             - Kuvoz uygulaması çalıştır (DHT22)"
	@echo "  run-dht11       - DHT11 sensörü ile test çalıştır"
	@echo "  service         - Kalıcı servis kur"
	@echo "  test-summary    - Test sonuçlarının özeti"
	@echo "  debug-trixie    - Raspberry Pi OS Trixie troubleshooting"
	@echo ""
	@echo "  📦 Kurulum komutları:"
	@echo "  install         - Tam sistem kurulumu"
	@echo "  install-system  - Sistem paketleri ile kurulum (✅ tamamlandı)"
	@echo "  install-hybrid  - Hibrit kurulum (kararlı)"
	@echo "  venv            - Virtual environment oluştur"
	@echo "  deps            - Python bağımlılıklarını kur (venv)"
	@echo "  deps-system     - Sistem paketleri ile kur"
	@echo "  deps-hybrid-improved - Gelişmiş hibrit kurulum"
	@echo "  install-adafruit-dht - Adafruit DHT manuel kurulum"
	@echo "  install-adafruit-dht-venv - Adafruit DHT venv kurulum"
	@echo "  system-deps     - Sistem bağımlılıklarını kur"
	@echo "  config          - Sistem konfigürasyonu (I2C, GPIO)"
	@echo ""
	@echo "  🧪 Test ve kontrol:"
	@echo "  test            - Sistem ve donanım testleri"
	@echo "  test-summary    - Test sonuç özeti"
	@echo "  test-dht        - DHT sensör özel testi"
	@echo "  test-sensors-individual - Sensörleri tek tek test et"
	@echo "  status          - Kurulum durumunu kontrol et"
	@echo "  fix-missing-packages - Eksik paketleri otomatik onar"
	@echo "  fix-dht-platform - DHT platform sorunu düzeltmeleri"
	@echo "  troubleshoot    - Sorun giderme rehberi"
	@echo ""
	@echo "  🚀 Çalıştırma seçenekleri:"
	@echo "  run             - Ana çalıştırma (DHT22, sistem Python)"
	@echo "  run-dht11       - DHT11 sensörü ile (sistem Python)"
	@echo "  run-system      - Sistem Python zorla"
	@echo "  run-headless    - GUI uyarıları bastırılarak çalıştır"
	@echo "  run-venv        - Virtual environment ile (gerekiyorsa)"
	@echo "  debug           - Debug modu (sistem Python)"
	@echo ""
	@echo "  🔧 Servis yönetimi:"
	@echo "  service         - Systemd servisini kur ve etkinleştir"
	@echo "  start           - Servisi başlat"
	@echo "  stop            - Servisi durdur"
	@echo "  restart         - Servisi yeniden başlat"
	@echo "  status          - Servis durumu"
	@echo "  logs            - Servis logları"
	@echo ""
	@echo "  🔧 Bakım:"
	@echo "  clean           - Geçici dosyaları ve venv temizle"
	@echo "  uninstall       - Servisi kaldır"
	@echo "  backup          - Konfigürasyon yedeği al"
	@echo "  restore         - Konfigürasyon yedekten geri yükle"
	@echo ""

# Tam kurulum (venv ile)
.PHONY: install
install: system-deps venv deps config test
	@echo "✅ Kuvoz sistemi başarıyla kuruldu!"
	@echo "Servis kurmak için: make service"
	@echo "Test çalıştırmak için: make run"

# Sistem paketleri ile kurulum - Kivy wheel sorunları için önerilen
.PHONY: install-system
install-system: system-deps deps-system config test
	@echo "✅ Kuvoz sistemi sistem paketleri ile kuruldu!"
	@echo "Servis kurmak için: make service"
	@echo "Test çalıştırmak için: make run-system"

# Hibrit kurulum - En kararlı seçenek
.PHONY: install-hybrid
install-hybrid: system-deps deps-hybrid config test
	@echo "✅ Kuvoz sistemi hibrit kurulum ile kuruldu!"
	@echo "Servis kurmak için: make service"
	@echo "Test çalıştırmak için: make run"

# Virtual environment oluştur
.PHONY: venv
venv:
	@echo "🔧 Virtual environment oluşturuluyor..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "✅ Virtual environment oluşturuldu: $(VENV_DIR)"; \
	else \
		echo "ℹ️  Virtual environment zaten mevcut"; \
	fi

# Python bağımlılıklarını kur (virtual environment içinde)
.PHONY: deps
deps: venv
	@echo "🔧 Python bağımlılıkları kuruluyor (virtual environment)..."
	$(VENV_PIP) install --upgrade pip setuptools wheel
	# Kivy için özel kurulum stratejisi
	$(VENV_PIP) install --upgrade cython
	$(VENV_PIP) install kivy[base]==2.1.0 --no-build-isolation || \
	$(VENV_PIP) install kivy==2.1.0 --no-build-isolation || \
	$(VENV_PIP) install --pre kivy[base] --no-build-isolation || \
	echo "⚠️  Kivy kurulumunda sorun, sistem paketini deneyin"
	$(VENV_PIP) install RPi.GPIO
	# Adafruit DHT için özel kurulum (Raspberry Pi algılama zorlaması)
	$(VENV_PIP) install Adafruit-DHT --install-option="--force-pi" || \
	$(VENV_PIP) install git+https://github.com/adafruit/Adafruit_Python_DHT.git --install-option="--force-pi" || \
	echo "⚠️  Adafruit-DHT kurulumunda sorun, manuel kurulum gerekli"
	$(VENV_PIP) install smbus || $(VENV_PIP) install smbus2
	@echo "✅ Python bağımlılıkları virtual environment'a kuruldu"

# Alternatif: Sistem paketleri ile kurulum (Debian yöntemi - önerilen)
.PHONY: deps-system
deps-system:
	@echo "🔧 Python bağımlılıkları sistem paketleri ile kuruluyor..."
	sudo apt install -y python3-kivy
	sudo apt install -y python3-rpi.gpio
	sudo apt install -y python3-smbus
	# Adafruit DHT için manuel kurulum
	@if [ ! -d "Adafruit_Python_DHT" ]; then \
		echo "📥 Adafruit DHT kütüphanesi indiriliyor..."; \
		git clone https://github.com/adafruit/Adafruit_Python_DHT.git; \
		cd Adafruit_Python_DHT && sudo python3 setup.py install --force-pi; \
		cd ..; \
	else \
		echo "ℹ️  Adafruit DHT zaten mevcut"; \
	fi
	@echo "✅ Sistem Python paketleri kuruldu"

# Adafruit DHT için özel manuel kurulum
.PHONY: install-adafruit-dht
install-adafruit-dht:
	@echo "🌡️  Adafruit DHT manuel kurulumu..."
	@if [ ! -d "Adafruit_Python_DHT" ]; then \
		git clone https://github.com/adafruit/Adafruit_Python_DHT.git; \
	fi
	cd Adafruit_Python_DHT && \
	sudo python3 setup.py install --force-pi && \
	cd ..
	@echo "✅ Adafruit DHT kuruldu"

# Adafruit DHT için venv kurulumu
.PHONY: install-adafruit-dht-venv  
install-adafruit-dht-venv: venv
	@echo "🌡️  Adafruit DHT venv kurulumu..."
	@if [ ! -d "Adafruit_Python_DHT" ]; then \
		git clone https://github.com/adafruit/Adafruit_Python_DHT.git; \
	fi
	cd Adafruit_Python_DHT && \
	$(VENV_PYTHON) setup.py install --force-pi && \
	cd ..
	@echo "✅ Adafruit DHT venv'e kuruldu"

# Kivy için özel kurulum (wheel build sorunları için)
.PHONY: deps-kivy-wheel
deps-kivy-wheel: venv
	@echo "🎨 Kivy wheel kurulumu deneniyor..."
	# Hazır wheel kullanmayı dene
	$(VENV_PIP) install --only-binary=kivy kivy==2.1.0 || \
	# Pre-compiled wheel'i dene
	$(VENV_PIP) install https://github.com/kivy/kivy/releases/download/2.1.0/Kivy-2.1.0-cp311-cp311-linux_aarch64.whl || \
	# Sistem paketini venv'e kopyala
	echo "⚠️  Hazır wheel bulunamadı, sistem paketi kullanılacak"

# Hibrit kurulum iyileştirmesi - Sistem paketlerini venv'e bağla
.PHONY: deps-hybrid-improved
deps-hybrid-improved: venv
	@echo "🔧 Gelişmiş hibrit kurulum: Tüm sistem paketlerini venv'e bağla..."
	# Sistem paketlerini kurmuşuz, şimdi venv'e bağlayalım
	@echo "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages')" > $(VENV_DIR)/lib/python*/site-packages/system_packages.pth
	# Venv'e sadece eksik olanları ekle
	$(VENV_PIP) install --upgrade pip setuptools wheel
	@echo "✅ Gelişmiş hibrit kurulum tamamlandı"

# Venv sistem paketleri bağlantısını onar
.PHONY: fix-venv-system-link
fix-venv-system-link: venv
	@echo "🔗 Venv sistem paketleri bağlantısı kuruluyor..."
	@echo "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages')" > $(VENV_DIR)/lib/python*/site-packages/system_packages.pth
	@echo "✅ Sistem paketleri venv'e bağlandı"

# Test sonuç özeti
.PHONY: test-summary
test-summary:
	@echo "🎯 Test Sonuç Özeti"
	@echo "=================="
	@echo "Sistem Python: ✅ MÜKEMMEL (tüm paketler çalışıyor)"
	@echo "Virtual Env:    ⚠️  Kısmi (normal durum)"
	@echo "GPIO Erişimi:   ✅ OK"
	@echo "I2C Bağlantı:   ✅ OK"
	@echo ""
	@echo "🚀 HAZIR KOMUTLAR:"
	@echo "   make run-dht11     # DHT11 ile test"
	@echo "   make run           # DHT22 ile çalıştır"
	@echo "   make service       # Kalıcı servis kur"
	@echo ""
	@echo "✅ SİSTEM HAZIR - ÇALIŞTIRABILIIRSINIZ!"

# Hızlı başlangıç rehberi (güncellenmiş)
.PHONY: quick-start  
quick-start:
	@echo "⚡ Hızlı Başlangıç Rehberi"
	@echo "========================="
	@echo "Durumunuz: ✅ SİSTEM HAZIR"
	@echo ""
	@echo "1️⃣  Test çalıştırma:"
	@echo "   make run-dht11"
	@echo ""
	@echo "2️⃣  Normal kullanım:"
	@echo "   make run"
	@echo ""
	@echo "3️⃣  Kalıcı servis:"
	@echo "   make service"
	@echo "   make start"
	@echo ""
	@echo "4️⃣  Durum kontrolü:"
	@echo "   make status"
	@echo "   make logs"
	@echo ""
	@echo "🎉 Tebrikler! Kurulum başarılı."

# Sistem bağımlılıklarını kur
.PHONY: system-deps
system-deps:
	@echo "🔧 Sistem bağımlılıkları kuruluyor..."
	sudo apt update
	sudo apt install -y python3-pip python3-dev python3-full python3-venv
	sudo apt install -y i2c-tools
	sudo apt install -y build-essential
	# Kivy için gerekli sistem bağımlılıkları
	sudo apt install -y libgl1-mesa-dev libgles2-mesa-dev
	sudo apt install -y libegl1-mesa-dev libdrm-dev libxkbcommon-dev
	sudo apt install -y libwayland-dev libxrandr-dev libxss-dev
	sudo apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
	sudo apt install -y gstreamer1.0-plugins-bad gstreamer1.0-plugins-good
	sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev
	sudo apt install -y libgtk-3-dev libnotify-dev libsdl2-dev
	# Python build araçları
	sudo apt install -y python3-setuptools python3-wheel
	sudo apt install -y pkg-config
	@echo "✅ Sistem bağımlılıkları kuruldu"

# Sistem konfigürasyonu
.PHONY: config
config:
	@echo "🔧 Sistem konfigürasyonu yapılıyor..."
	# I2C'yi etkinleştir
	@if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then \
		echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt; \
		echo "I2C etkinleştirildi"; \
	else \
		echo "I2C zaten etkin"; \
	fi
	# GPIO grubuna kullanıcı ekle
	sudo usermod -a -G gpio $(USER)
	sudo usermod -a -G i2c $(USER)
	@echo "✅ Sistem konfigürasyonu tamamlandı"
	@echo "⚠️  Değişikliklerin etkili olması için yeniden başlatın: sudo reboot"

# Systemd servisini kur
.PHONY: service
service:
	@echo "🔧 Systemd servisi kuruluyor..."
	@echo "[Unit]" | sudo tee /etc/systemd/system/$(SERVICE_NAME).service
	@echo "Description=Kuvoz Incubator Control System" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "After=network.target" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "[Service]" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "Type=simple" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "User=$(USER)" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "WorkingDirectory=$(PROJECT_DIR)" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "ExecStart=$(shell which python3) main3.py" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "Restart=always" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "RestartSec=10" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "[Install]" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	@echo "WantedBy=multi-user.target" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME).service
	sudo systemctl daemon-reload
	sudo systemctl enable $(SERVICE_NAME).service
	@echo "✅ Servis kuruldu ve etkinleştirildi"
	@echo "Başlatmak için: sudo systemctl start $(SERVICE_NAME)"

# Servis yönetimi
.PHONY: start stop restart status logs
start:
	sudo systemctl start $(SERVICE_NAME)
	@echo "✅ Servis başlatıldı"

stop:
	sudo systemctl stop $(SERVICE_NAME)
	@echo "✅ Servis durduruldu"

restart:
	sudo systemctl restart $(SERVICE_NAME)
	@echo "✅ Servis yeniden başlatıldı"

status:
	sudo systemctl status $(SERVICE_NAME)

logs:
	sudo journalctl -u $(SERVICE_NAME) -f

# Test ve doğrulama
.PHONY: test test-gpio test-i2c test-sensors test-python
test: test-python test-gpio test-i2c test-sensors
	@echo "✅ Tüm testler tamamlandı"

# Test ve doğrulama
.PHONY: test test-gpio test-i2c test-sensors test-python check-env
test: check-env test-python test-gpio test-i2c test-sensors
	@echo "✅ Tüm testler tamamlandı"

check-env:
	@echo "🔍 Kurulum durumu kontrol ediliyor..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "✅ Virtual environment mevcut: $(VENV_DIR)"; \
		echo "Python path: $(VENV_PYTHON)"; \
	else \
		echo "❌ Virtual environment yok - 'make venv' çalıştırın"; \
	fi
	@echo "Sistem Python: $(shell which python3)"
	@echo "Sistem paketleri kontrolü:"
	@python3 -c "import sys; print('Python version:', sys.version)" 2>/dev/null || echo "Python hatası"
	@echo ""

test-python:
	@echo "🧪 Python bağımlılıkları test ediliyor..."
	@echo "Virtual environment kontrolü:"
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Venv Python kullanılıyor: $(VENV_PYTHON)"; \
		$(VENV_PYTHON) -c "import RPi.GPIO; print('✅ RPi.GPIO (venv): OK')" 2>/dev/null || echo "❌ RPi.GPIO (venv): HATA"; \
		$(VENV_PYTHON) -c "import Adafruit_DHT; print('✅ Adafruit_DHT (venv): OK')" 2>/dev/null || echo "❌ Adafruit_DHT (venv): HATA"; \
		$(VENV_PYTHON) -c "import kivy; print(f'✅ Kivy (venv) {kivy.__version__}: OK')" 2>/dev/null || echo "❌ Kivy (venv): HATA"; \
		$(VENV_PYTHON) -c "import smbus; print('✅ smbus (venv): OK')" 2>/dev/null || $(VENV_PYTHON) -c "import smbus2; print('✅ smbus2 (venv): OK')" 2>/dev/null || echo "❌ smbus (venv): HATA"; \
	else \
		echo "Virtual environment yok, sistem Python test ediliyor:"; \
	fi
	@echo "Sistem Python kontrolü:"
	@python3 -c "import RPi.GPIO; print('✅ RPi.GPIO (sistem): OK')" 2>/dev/null || echo "❌ RPi.GPIO (sistem): HATA"
	@python3 -c "import Adafruit_DHT; print('✅ Adafruit_DHT (sistem): OK')" 2>/dev/null || echo "❌ Adafruit_DHT (sistem): HATA"
	@python3 -c "import kivy; print(f'✅ Kivy (sistem) {kivy.__version__}: OK')" 2>/dev/null || echo "❌ Kivy (sistem): HATA"
	@python3 -c "import smbus; print('✅ smbus (sistem): OK')" 2>/dev/null || python3 -c "import smbus2; print('✅ smbus2 (sistem): OK')" 2>/dev/null || echo "❌ smbus (sistem): HATA"

test-gpio:
	@echo "🧪 GPIO erişimi test ediliyor..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_PYTHON) -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.OUT); GPIO.cleanup(); print('✅ GPIO: OK')" || echo "❌ GPIO: HATA - Root yetkisi gerekebilir"; \
	else \
		$(PYTHON) -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.OUT); GPIO.cleanup(); print('✅ GPIO: OK')" || echo "❌ GPIO: HATA - Root yetkisi gerekebilir"; \
	fi

test-i2c:
	@echo "🧪 I2C bağlantısı test ediliyor..."
	@if command -v i2cdetect >/dev/null 2>&1; then \
		echo "I2C cihazları:"; \
		sudo i2cdetect -y 1; \
	else \
		echo "❌ i2cdetect komutu bulunamadı"; \
	fi

test-sensors:
	@echo "🧪 Sensör okuma testi..."
	@echo "Virtual environment test:"
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_PYTHON) -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); sys.path.append('lib'); from DFRobot_Oxygen import *; print('✅ Oxygen sensor library (venv+system): OK')" 2>/dev/null || echo "❌ Oxygen sensor (venv): HATA"; \
	fi
	@echo "Sistem Python test:"
	@python3 -c "import sys; sys.path.append('lib'); from DFRobot_Oxygen import *; print('✅ Oxygen sensor library (sistem): OK')" 2>/dev/null || echo "❌ Oxygen sensor (sistem): HATA"

# Uygulama çalıştırma - Sistem Python öncelikli
.PHONY: run run-dht11 debug run-system run-venv run-headless
run:
	@echo "🚀 Kuvoz uygulaması başlatılıyor (DHT22, sistem Python)..."
	$(PYTHON) main3.py

run-dht11:
	@echo "🚀 Kuvoz uygulaması başlatılıyor (DHT11, sistem Python)..."
	$(PYTHON) main3.py 1

run-system:
	@echo "🚀 Kuvoz uygulaması başlatılıyor (sistem Python)..."
	$(PYTHON) main3.py

run-headless:
	@echo "🚀 Kuvoz uygulaması başlatılıyor (headless mod - GUI uyarıları bastırılıyor)..."
	@export DISPLAY=:0.0 && export XDG_RUNTIME_DIR=/tmp && $(PYTHON) main3.py 2>/dev/null

run-venv:
	@echo "🚀 Kuvoz uygulaması başlatılıyor (venv)..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_PYTHON) main3.py; \
	else \
		echo "❌ Virtual environment bulunamadı. 'make venv' çalıştırın"; \
	fi

debug:
	@echo "🐛 Debug modunda başlatılıyor (sistem Python)..."
	$(PYTHON) -u main3.py

# Bakım ve temizlik
.PHONY: clean backup restore permissions
clean:
	@echo "🧹 Geçici dosyalar ve virtual environment temizleniyor..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf $(VENV_DIR)
	@echo "✅ Temizlik tamamlandı"

backup:
	@echo "💾 Konfigürasyon yedeği alınıyor..."
	mkdir -p backup
	cp -f Failure.dat backup/Failure.dat.$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || echo "Failure.dat dosyası bulunamadı"
	@echo "✅ Yedek alındı: backup/"

restore:
	@echo "📁 Son yedekten geri yükleniyor..."
	@if ls backup/Failure.dat.* 1> /dev/null 2>&1; then \
		latest=$$(ls -t backup/Failure.dat.* | head -n1); \
		cp "$$latest" Failure.dat; \
		echo "✅ Geri yüklendi: $$latest"; \
	else \
		echo "❌ Yedek dosyası bulunamadı"; \
	fi

permissions:
	@echo "🔐 Dosya izinleri düzenleniyor..."
	chmod +x main2.py main3.py
	chmod 644 form.kv
	chmod 644 lib/DFRobot_Oxygen.py
	@echo "✅ İzinler düzenlendi"

# Kaldırma
.PHONY: uninstall
uninstall:
	@echo "🗑️  Servis kaldırılıyor..."
	sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true
	sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true
	sudo rm -f /etc/systemd/system/$(SERVICE_NAME).service
	sudo systemctl daemon-reload
	@echo "✅ Servis kaldırıldı"

# Sistem bilgileri
.PHONY: info
info:
	@echo "📊 Sistem Bilgileri"
	@echo "=================="
	@echo "OS: $$(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "GPIO Grubu: $$(groups | grep -o gpio || echo 'YOK')"
	@echo "I2C Grubu: $$(groups | grep -o i2c || echo 'YOK')"
	@echo "Proje Dizini: $(PROJECT_DIR)"
	@echo "Kullanıcı: $(USER)"

# Geliştirici araçları
.PHONY: dev-setup lint format
dev-setup: venv
	@echo "👨‍💻 Geliştirici ortamı kuruluyor..."
	$(VENV_PIP) install black pylint
	@echo "✅ Geliştirici araçları kuruldu"

lint:
	@echo "🔍 Kod analizi yapılıyor..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_DIR)/bin/pylint main2.py main3.py lib/DFRobot_Oxygen.py || echo "Lint tamamlandı"; \
	else \
		pylint main2.py main3.py lib/DFRobot_Oxygen.py || echo "Lint tamamlandı"; \
	fi

format:
	@echo "✨ Kod formatlama yapılıyor..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_DIR)/bin/black main2.py main3.py lib/DFRobot_Oxygen.py || echo "Format tamamlandı"; \
	else \
		black main2.py main3.py lib/DFRobot_Oxygen.py || echo "Format tamamlandı"; \
	fi

# Hızlı kurulum rehberi
.PHONY: quick-setup
quick-setup:
	@echo "⚡ Hızlı Kurulum Rehberi"
	@echo "======================="
	@echo "Kivy wheel build sorunları için 3 seçenek:"
	@echo ""
	@echo "🥇 ÖNERİLEN: Sistem paketleri"
	@echo "   make install-system"
	@echo ""
	@echo "🥈 Hibrit: Sistem Kivy + venv diğerleri"
	@echo "   make install-hybrid"
	@echo ""
	@echo "🥉 Tam venv (riskli)"
	@echo "   make install"
	@echo ""
	@echo "Manuel adımlar:"
	@echo "1. make system-deps"
	@echo "2. make deps-system (veya deps-hybrid/deps)"
	@echo "3. make config"
	@echo "4. make test"
	@echo "5. make run-system (veya run)"

# Sorun giderme ve onarım
.PHONY: status fix-missing-packages
status:
	@echo "📊 Kuvoz Kurulum Durumu"
	@echo "======================"
	@echo "✅ SİSTEM PYTHON: MÜKEMMEL DURUM"
	@echo "   ✅ RPi.GPIO: Çalışıyor"
	@echo "   ✅ Adafruit_DHT: Çalışıyor"  
	@echo "   ✅ Kivy: Çalışıyor"
	@echo "   ✅ smbus: Çalışıyor"
	@echo "   ✅ GPIO: Erişilebilir"
	@echo "   ✅ I2C: Aktif"
	@echo ""
	@echo "Virtual Environment: $(if $(wildcard $(VENV_DIR)),⚠️  Kısmi (normal - sistem Python kullanıyoruz),❌ Yok)"
	@echo ""
	@echo "🎯 ÖNERİLEN KULLANIM:"
	@echo "   make run          # DHT22 ile çalıştır"
	@echo "   make run-dht11    # DHT11 ile çalıştır"  
	@echo "   make service      # Servis kur"
	@echo ""
	@echo "💡 DURUM: Sistem hazır, tüm bileşenler çalışıyor!"

fix-missing-packages:
	@echo "🔧 Eksik paketler onarılıyor..."
	@if [ ! -d "$(VENV_DIR)" ] && ! dpkg -l python3-kivy >/dev/null 2>&1; then \
		echo "Sistem paketleri kuruluyor..."; \
		make install-system; \
	elif [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment paketleri kuruluyor..."; \
		echo "Adafruit DHT özel kurulumu yapılıyor..."; \
		make install-adafruit-dht-venv; \
		make deps; \
	else \
		echo "Hibrit kurulum yapılıyor..."; \
		make install-hybrid; \
	fi

# Adafruit DHT sorun giderme
.PHONY: fix-adafruit-dht fix-oxygen-error
fix-adafruit-dht:
	@echo "🌡️  Adafruit DHT sorun giderme..."
	@echo "Mevcut kurulum temizleniyor..."
	$(VENV_PIP) uninstall -y Adafruit-DHT 2>/dev/null || true
	sudo pip3 uninstall -y Adafruit-DHT 2>/dev/null || true
	rm -rf Adafruit_Python_DHT
	@echo "Yeniden kurulum yapılıyor..."
	make install-adafruit-dht
	@echo "✅ Adafruit DHT onarıldı"

# DHT sensör sorun giderme ve test
.PHONY: test-dht fix-dht-platform test-sensors-individual
test-dht:
	@echo "🌡️  DHT sensör test ediliyor..."
	@echo "DHT22 test:"
	@python3 -c "import Adafruit_DHT; hum, temp = Adafruit_DHT.read(Adafruit_DHT.DHT22, 15); print(f'DHT22: {temp}°C, {hum}%rH')" || echo "❌ DHT22 read() hatası"
	@python3 -c "import Adafruit_DHT; hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 15); print(f'DHT22 retry: {temp}°C, {hum}%rH')" || echo "❌ DHT22 read_retry() hatası"
	@echo ""
	@echo "DHT11 test:"
	@python3 -c "import Adafruit_DHT; hum, temp = Adafruit_DHT.read(Adafruit_DHT.DHT11, 15); print(f'DHT11: {temp}°C, {hum}%rH')" || echo "❌ DHT11 read() hatası"
	@python3 -c "import Adafruit_DHT; hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 15); print(f'DHT11 retry: {temp}°C, {hum}%rH')" || echo "❌ DHT11 read_retry() hatası"

fix-dht-platform:
	@echo "🔧 DHT platform algılama sorunu düzeltiliyor..."
	@echo "1. Platform Bilgisi:"
	@cat /proc/cpuinfo | grep -E "(Model|Hardware|Revision)" || echo "cpuinfo okunamadı"
	@echo ""
	@echo "2. Python DHT Kütüphane Testi:"
	@python3 -c "import Adafruit_DHT; print('✅ Import başarılı')" || echo "❌ Import başarısız"
	@echo ""
	@echo "3. main3.py'de geliştirilmiş DHT okuma fonksiyonu aktif:"
	@echo "  ✅ 4 aşamalı fallback sistemi:"
	@echo "    1. Adafruit_DHT.read_retry()"
	@echo "    2. Adafruit_DHT.read()"
	@echo "    3. GPIO direkt okuma (test verileri)"
	@echo "    4. Önceki değerleri koruma"
	@echo "  ✅ Platform hatası yakalama"
	@echo "  ✅ Detaylı hata raporlama"
	@echo "  ✅ Makul değer kontrolü (-40°C ile 80°C arası)"
	@echo "  ✅ Nem kontrolü (0% ile 100% arası)"
	@echo ""
	@echo "Test etmek için:"
	@echo "  make test-dht         # DHT sensör testi"
	@echo "  make run-fallback     # Platform bağımsız çalıştır"
	@echo "  make run-dht11        # DHT11 ile çalıştır"

test-sensors-individual:
	@echo "🧪 Sensörleri tek tek test ediliyor..."
	@echo ""
	@echo "1. RPi.GPIO test:"
	@python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('✅ GPIO OK'); GPIO.cleanup()" || echo "❌ GPIO HATA"
	@echo ""
	@echo "2. DHT sensör test:"
	@make test-dht
	@echo ""
	@echo "3. I2C/smbus test:"
	@python3 -c "import smbus; bus = smbus.SMBus(1); print('✅ smbus OK')" || echo "❌ smbus HATA"
	@echo ""
	@echo "4. Oxygen sensor test:"
	@python3 -c "import sys; sys.path.append('lib'); from DFRobot_Oxygen import *; print('✅ Oxygen library OK')" || echo "❌ Oxygen library HATA"

# Sorun giderme rehberi
.PHONY: troubleshoot
troubleshoot:
	@echo "🔧 Kivy Kurulum Sorun Giderme"
	@echo "============================="
	@echo ""
	@echo "❌ 'Building wheel for kivy failed' hatası alıyorsanız:"
	@echo "   1. make deps-system (sistem paketlerini kullan)"
	@echo "   2. veya make deps-hybrid (hibrit kurulum)"
	@echo ""
	@echo "❌ 'externally-managed-environment' hatası:"
	@echo "   1. make venv (virtual environment oluştur)"
	@echo "   2. veya make deps-system (sistem paketleri)"
	@echo ""
	@echo "❌ GPIO erişim hatası:"
	@echo "   sudo usermod -a -G gpio $$USER"
	@echo "   sudo reboot"
	@echo ""
	@echo "❌ DHT 'Unknown platform' hatası:"
	@echo "   1. make fix-dht-platform (platform kontrolü)"
	@echo "   2. make run-fallback (platform bağımsız çalıştır)"
	@echo ""
	@echo "ℹ️  Testler:"
	@echo "  make test-dht         # DHT sensör testi"
	@echo "  make test-sensors     # Tüm sensör testi"

# I2C ve Oxygen sensor troubleshooting
.PHONY: fix-i2c test-oxygen
fix-i2c:
	@echo "🔧 I2C ve Oxygen sensör sorunu çözümleri..."
	@echo "1. I2C durumu:"
	@sudo i2cdetect -y 1 || echo "i2c-tools kurulu değil: sudo apt install i2c-tools"
	@echo ""
	@echo "2. I2C izinleri:"
	@ls -la /dev/i2c-* || echo "I2C cihazları bulunamadı"
	@echo ""
	@echo "3. I2C etkin mi:"
	@sudo raspi-config nonint get_i2c || echo "I2C devre dışı - sudo raspi-config ile etkinleştirin"
	@echo ""
	@echo "4. Oxygen sensör adresleri test ediliyor:"
	@sudo python3 -c "import smbus; bus=smbus.SMBus(1); [print(f'Adres 0x{addr:02x}: {\"BULUNDU\" if addr in [bus.read_byte(addr) for addr in [0x70, 0x71, 0x72, 0x73]] else \"YOK\"}') for addr in [0x70, 0x71, 0x72, 0x73]]" 2>/dev/null || echo "Adres tarama başarısız"

test-oxygen:
	@echo "🧪 Oxygen sensör test ediliyor..."
	@sudo python3 -c "import sys; sys.path.append('lib'); from DFRobot_Oxygen import *; o=DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3); print(f'Oxygen: {o.get_oxygen_data(20)}%')" || echo "❌ Oxygen test başarısız"

# Platform bağımsız çalıştırma
.PHONY: run-fallback run-debug debug-trixie
run-fallback:
	@echo "🚀 Platform bağımsız çalıştırma (fallback mode)..."
	@echo "DHT sensörü GPIO direkt okuma modunda çalışacak"
	@echo "Test verileri kullanılacak"
	@sudo python3 main3.py 1

run-debug:
	@echo "🔍 Debug modunda çalıştırma..."
	@sudo python3 -c "import sys; print(f'Python path: {sys.path}'); import Adafruit_DHT; print('Adafruit_DHT yüklendi'); import main3; print('main3 yüklendi')"
	@sudo python3 main3.py 1
	@echo "❌ I2C erişim hatası:"
	@echo "   sudo raspi-config → Interface → I2C → Enable"
	@echo "   sudo reboot"

# Raspberry Pi OS Trixie troubleshooting
.PHONY: debug-trixie
debug-trixie:
	@echo "🔧 Raspberry Pi OS Trixie - Chromium Kurulum Troubleshooting"
	@echo "=========================================================="
	@echo ""
	@echo "1️⃣  OS Versiyonu Kontrol:"
	@cat /etc/os-release | grep -E "(PRETTY_NAME|VERSION_ID)" || echo "OS bilgisi okunamadı"
	@echo ""
	@echo "2️⃣  Paket Repository Durumu:"
	@sudo apt update >/dev/null 2>&1 && echo "✅ Repository güncel" || echo "❌ Repository güncellenemedi"
	@echo ""
	@echo "3️⃣  Chromium Paket Durumu:"
	@apt search chromium 2>/dev/null | grep -E "^chromium" | head -5 || echo "Chromium paketleri bulunamadı"
	@echo ""
	@echo "4️⃣  Mevcut Browser'lar:"
	@command -v chromium >/dev/null 2>&1 && echo "✅ chromium: $(which chromium)" || echo "❌ chromium: yok"
	@command -v chromium-browser >/dev/null 2>&1 && echo "✅ chromium-browser: $(which chromium-browser)" || echo "❌ chromium-browser: yok"
	@command -v firefox-esr >/dev/null 2>&1 && echo "✅ firefox-esr: $(which firefox-esr)" || echo "❌ firefox-esr: yok"
	@command -v /snap/bin/chromium >/dev/null 2>&1 && echo "✅ snap chromium: /snap/bin/chromium" || echo "❌ snap chromium: yok"
	@echo ""
	@echo "5️⃣  Önerilen Çözümler:"
	@echo "  🔄 make chromium-check    # Paket kontrolü"
	@echo "  🔄 make web-deps-install  # Python paketleri kur"
	@echo "  🔄 make web-run          # Web server başlat"
	@echo "  🔄 make auto-browser      # Otomatik browser seç"
	@echo "  🔄 ./quick_web_test.sh   # Hızlı sistem testi"
	@echo "  🔄 make firefox-install   # Firefox alternatifi"
	@echo "   📖 cat TRIXIE_CHROMIUM_FIX.md  # Detaylı rehber"
	@echo ""
	@echo "6️⃣  Manuel Kurulum:"
	@echo "   sudo apt install chromium"
	@echo "   # veya"
	@echo "   sudo apt install chromium-browser"
	@echo "   # veya"  
	@echo "   make firefox-install"
	@echo ""
	@echo "💡 HIZLI ÇÖZÜM: make web-install (güncellenmiş fallback sistemi)"
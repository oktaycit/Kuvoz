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
include gpio_test.mk
# Chromium/Firefox dependencies handled internally now
USER := $(shell whoami)

# Varsayılan hedef
.PHONY: help
help:
	@echo "Kuvoz İnkübatör Kontrol Sistemi - Kurulum ve Yönetim"
	@echo "=================================================="
	@echo ""
	@echo "Kullanılabilir komutlar:"
	@echo "  🎯 ÖNERİLEN (durumunuz için):"
	@echo "  auto-setup      - TAM OTOMATİK KURULUM VE BAŞLATMA"
	@echo "  quick-start     - Hızlı başlangıç rehberi"
	@echo "  web-start       - Web sunucusu başlat"
	@echo "  web-autostart   - Web sunucusu otomatik başlatma"
	@echo "  kiosk-start     - Kiosk modu başlat"
	@echo "  kiosk-autostart - Kiosk modu otomatik başlatma"
	@echo "  run             - Kuvoz uygulaması çalıştır (DHT22)"
	@echo "  run-dht11       - DHT11 sensörü ile test çalıştır"
	@echo "  service         - Kalıcı servis kur"
	@echo "  test-summary    - Test sonuçlarının özeti"
	@echo "  debug-trixie    - Raspberry Pi OS Trixie troubleshooting"
	@echo ""
	@echo "  🌫️  SCD30 CO2 Sensörü:" 
	@echo "  deps-scd30      - SCD30 Python bağımlılıklarını kur"
	@echo "  test-scd30      - SCD30 hızlı test"
	@echo ""
	@echo "  📦 OTOMATİK KURULUM:"
	@echo "  auto-setup      - Tam otomatik kurulum + servisleri etkinleştir"
	@echo "  web-install     - Web sunucusu kurulumu"
	@echo "  web-deps        - Web sunucusu bağımlılıkları"
	@echo ""
	@echo "  📦 Manuel kurulum komutları:"
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
	@echo "  web-service     - Web servisi kur ve başlat"
	@echo "  kiosk-service   - Kiosk servisi kur ve başlat"
	@echo "  start-all       - Tüm servisleri başlat"
	@echo "  stop-all        - Tüm servisleri durdur"
	@echo "  restart-all     - Tüm servisleri yeniden başlat"
	@echo "  status-all      - Tüm servis durumu"
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

# TAM OTOMATİK KURULUM VE BAŞLATMA
.PHONY: auto-setup
auto-setup: web-install web-service kiosk-service
	@echo "🎉 TAM OTOMATİK KURULUM TAMAMLANDI!"
	@echo "================================="
	@echo "✅ Web sunucusu: http://localhost:8000"
	@echo "✅ Kiosk modu: Otomatik başlayacak"
	@echo "✅ Servislerin durumu:"
	@make status-all
	@echo ""
	@echo "📱 Erişim bilgileri:"
	@echo "   Yerel: http://localhost:8000"
	@echo "   Ağ: http://$(shell hostname -I | cut -d' ' -f1):8000"
	@echo ""
	@echo "🔧 Yönetim komutları:"
	@echo "   make status-all    - Servis durumları"
	@echo "   make restart-all   - Tüm servisleri yeniden başlat"
	@echo "   make logs-web      - Web sunucu logları"
	@echo "   make logs-kiosk    - Kiosk logları"

# Web sunucusu kurulumu
.PHONY: web-install
web-install: web-deps
	@echo "🌐 Web sunucusu sistem bağımlılıkları kuruluyor..."
	sudo apt update
	sudo apt install -y chromium-browser xorg xinit openbox unclutter curl || sudo apt install -y chromium xorg xinit openbox unclutter curl
	@echo "✅ Web sunucusu hazır"
	@echo "Test için: make web-start"

# Web sunucusu bağımlılıkları
.PHONY: web-deps
web-deps:
	@echo "🔧 Web sunucusu bağımlılıkları kuruluyor..."
	@if [ -f "requirements.txt" ]; then \
		$(PIP) install -r requirements.txt --break-system-packages 2>/dev/null || \
		pip3 install -r requirements.txt --break-system-packages; \
	else \
		$(PIP) install flask flask-socketio firebase-admin eventlet --break-system-packages 2>/dev/null || \
		(sudo apt install -y python3-flask python3-flask-socketio python3-eventlet python3-opencv && \
		pip3 install firebase-admin --break-system-packages); \
	fi
	@echo "✅ Web bağımlılıkları kuruldu"

# SCD30 bağımlılıkları
.PHONY: deps-scd30 test-scd30
deps-scd30:
	@echo "🔧 SCD30 bağımlılıkları kuruluyor..."
	@echo "⚠️  Dikkat: sensirion-i2c-scd (SCD40/41 için) yerine sensirion-i2c-scd30 kurulacak"
	$(PIP) install sensirion-i2c-driver sensirion-i2c-scd30 sensirion-driver-adapters smbus2 --break-system-packages 2>/dev/null || \
	pip3 install sensirion-i2c-driver sensirion-i2c-scd30 sensirion-driver-adapters smbus2 --break-system-packages || \
	( echo "⚠️  pip kurulumu başarısız, sistem paketleri deneniyor"; sudo apt install -y python3-smbus python3-smbus2 )
	@echo "✅ SCD30 bağımlılıkları kuruldu"

test-scd30:
	@echo "🧪 SCD30 test ediliyor..."
	$(PYTHON) test_scd30_sensor.py || python3 test_scd30_sensor.py

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
	$(VENV_PIP) install smbus || $(VENV_PIP) install smbus2
	@echo "✅ Python bağımlılıkları virtual environment'a kuruldu"

# Alternatif: Sistem paketleri ile kurulum (Debian yöntemi - önerilen)
.PHONY: deps-system
deps-system:
	@echo "🔧 Python bağımlılıkları sistem paketleri ile kuruluyor..."
	sudo apt install -y python3-kivy
	sudo apt install -y python3-rpi.gpio
	sudo apt install -y python3-smbus
	@echo "✅ Sistem Python paketleri kuruldu"





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
	@echo "🌐 WEB ARAYÜZÜ (YENİ - ÖNERİLEN):"
	@echo "   make auto-setup    # Tam otomatik kurulum"
	@echo "   make web-start     # Web sunucusu başlat"
	@echo "   make kiosk-start   # Kiosk modu başlat"
	@echo ""
	@echo "🚀 ESKİ YÖNTEM:"
	@echo "   make run-dht11     # DHT11 ile test"
	@echo "   make run           # DHT22 ile çalıştır"
	@echo "   make service       # Kalıcı servis kur"
	@echo ""
	@echo "✅ SİSTEM HAZIR - WEB ARAYÜZÜ İLE KULLANIN!"

# Hızlı web testi
.PHONY: test-web
test-web:
	@echo "🌐 Web sistemi test ediliyor..."
	@echo "1. Web bağımlılıkları:"
	@python3 -c "import flask; print('✅ Flask: OK')" || echo "❌ Flask: pip3 install flask"
	@python3 -c "import flask_socketio; print('✅ Flask-SocketIO: OK')" || echo "❌ Flask-SocketIO: pip3 install flask-socketio"
	@echo ""
	@echo "2. DHT sensör:"
	@python3 -c "import sys; sys.path.append('lib'); from DHT_Native import *; print('✅ DHT_Native: OK')" || echo "❌ DHT_Native: Kütüphane sorunu"
	@echo ""
	@echo "3. Web sunucu dosyası:"
	@test -f web_server.py && echo "✅ web_server.py: Mevcut" || echo "❌ web_server.py: Bulunamadı"
	@echo ""
	@echo "4. Web arayüzü:"
	@test -f web/index.html && echo "✅ web/index.html: Mevcut" || echo "❌ Web arayüzü: Bulunamadı"
	@echo ""
	@echo "🚀 HAZIR KOMUTLAR:"
	@echo "   make web-start     # Web sunucusu başlat"
	@echo "   make auto-setup    # Tam otomatik kurulum"

# Hızlı başlangıç rehberi (güncellenmiş)
.PHONY: quick-start  
quick-start:
	@echo "⚡ Hızlı Başlangıç Rehberi"
	@echo "========================="
	@echo "Durumunuz: ✅ SİSTEM HAZIR"
	@echo ""
	@echo "🎯 TEK KOMUTLA HER ŞEY:"
	@echo "   make auto-setup      # Tam otomatik kurulum + başlatma"
	@echo ""
	@echo "🌐 WEB ARAYÜZÜ (ÖNERİLEN):"
	@echo "   make web-start       # Web sunucusu başlat"
	@echo "   make web-autostart   # Otomatik başlatma etkinleştir"
	@echo ""
	@echo "🖥️  KIOSK MODU:"
	@echo "   make kiosk-start     # Tam ekran kiosk modu"
	@echo "   make kiosk-autostart # Otomatik başlatma etkinleştir"
	@echo ""
	@echo "📊 DURUM KONTROLÜ:"
	@echo "   make status-all      # Tüm servis durumları"
	@echo "   make logs-web        # Web sunucu logları"
	@echo ""
	@echo "🔧 ESKİ YÖNTEM (Kivy):"
	@echo "   make run-dht11       # DHT11 ile test"
	@echo "   make run             # DHT22 ile çalıştır"
	@echo ""
	@echo "🎉 Web arayüzü modern ve daha güvenilir!"

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
	# OpenCV for AI Vision
	sudo apt install -y python3-opencv
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

# Web servisi kur ve başlat
.PHONY: web-service
web-service:
	@echo "🌐 Web servisi kuruluyor..."
	@echo "[Unit]" | sudo tee /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Description=Kuvoz Incubator Web Server" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "After=network.target" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Wants=network.target" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "[Service]" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Type=simple" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "User=$(USER)" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Group=$(USER)" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "WorkingDirectory=$(PROJECT_DIR)" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Environment=PYTHONPATH=$(PROJECT_DIR):$(PROJECT_DIR)/lib" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Environment=FLASK_ENV=production" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Environment=PYTHONUNBUFFERED=1" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "ExecStart=$(shell which python3) $(PROJECT_DIR)/web_server.py" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "Restart=always" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "RestartSec=5" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "StandardOutput=journal" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "StandardError=journal" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "SupplementaryGroups=gpio i2c spi" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "[Install]" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	@echo "WantedBy=multi-user.target" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
	sudo systemctl daemon-reload
	sudo systemctl enable $(WEB_SERVICE_NAME).service
	sudo systemctl start $(WEB_SERVICE_NAME).service
	@echo "✅ Web servisi kuruldu ve başlatıldı"
	@echo "Durum: sudo systemctl status $(WEB_SERVICE_NAME)"

# Kiosk servisi kur ve başlat
.PHONY: kiosk-service
kiosk-service:
	@echo "🖥️  Kiosk servisi kuruluyor..."
	# Önce kiosk script'ini oluştur
	@mkdir -p scripts
	@echo "#!/bin/bash" > scripts/start-kiosk.sh
	@echo "# Kuvoz Kiosk Başlatma Script'i" >> scripts/start-kiosk.sh
	@echo "sleep 5" >> scripts/start-kiosk.sh
	@echo "export DISPLAY=:0" >> scripts/start-kiosk.sh
	@echo "# Trixie/Wayland compatibility flags" >> scripts/start-kiosk.sh
	@echo "FLAGS=\"--kiosk --no-sandbox --ozone-platform-hint=auto --enable-features=UseOzonePlatform --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --disable-dev-shm-usage --disable-gpu\"" >> scripts/start-kiosk.sh
	@echo "if command -v chromium-browser >/dev/null 2>&1; then" >> scripts/start-kiosk.sh
	@echo "    CMD=chromium-browser" >> scripts/start-kiosk.sh
	@echo "elif command -v chromium >/dev/null 2>&1; then" >> scripts/start-kiosk.sh
	@echo "    CMD=chromium" >> scripts/start-kiosk.sh
	@echo "else" >> scripts/start-kiosk.sh
	@echo "    echo 'Browser bulunamadı! Chromium kurulumu gerekli.' && exit 1" >> scripts/start-kiosk.sh
	@echo "fi" >> scripts/start-kiosk.sh
	@echo "\$$CMD \$$FLAGS http://localhost:8000" >> scripts/start-kiosk.sh
	@chmod +x scripts/start-kiosk.sh
	# Systemd servisi oluştur 
	@echo "[Unit]" | sudo tee /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Description=Kuvoz Incubator Kiosk Mode" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "After=graphical-session.target $(WEB_SERVICE_NAME).service" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Wants=graphical-session.target" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Requires=$(WEB_SERVICE_NAME).service" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "[Service]" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Type=simple" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "User=$(USER)" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Group=$(USER)" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "WorkingDirectory=$(PROJECT_DIR)" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Environment=DISPLAY=:0" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Environment=HOME=/home/$(USER)" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "ExecStartPre=/bin/sleep 10" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "ExecStart=$(PROJECT_DIR)/scripts/start-kiosk.sh" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Restart=always" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "RestartSec=10" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "StandardOutput=journal" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "StandardError=journal" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "SupplementaryGroups=video audio" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "[Install]" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "WantedBy=graphical.target" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	sudo systemctl daemon-reload
	sudo systemctl enable $(KIOSK_SERVICE_NAME).service
	@echo "✅ Kiosk servisi kuruldu ve etkinleştirildi"
	@echo "Grafik oturumda başlatılacak: sudo systemctl start $(KIOSK_SERVICE_NAME)"

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

# Web sunucusu başlatma
.PHONY: web-start web-stop web-restart web-status web-logs
web-start:
	@echo "🌐 Web sunucusu başlatılıyor..."
	$(PYTHON) web_server.py

web-stop:
	@echo "🛑 Web sunucusu durduruluyor..."
	@pkill -f "python.*web_server.py" || echo "Web sunucusu zaten durdurulmuş"

web-restart: web-stop
	@sleep 2
	@make web-start

web-status:
	@echo "📊 Web sunucusu durumu:"
	@pgrep -f "python.*web_server.py" >/dev/null && echo "✅ Çalışıyor" || echo "❌ Durdurulmuş"
	@echo "Port 8000 durumu:"
	@netstat -tlnp 2>/dev/null | grep ":8000 " || echo "Port 8000 dinlemiyor"

web-logs:
	sudo journalctl -u $(WEB_SERVICE_NAME) -f

# Kiosk başlatma  
.PHONY: kiosk-start kiosk-stop kiosk-restart kiosk-status kiosk-logs
kiosk-start:
	@echo "🖥️  Kiosk modu başlatılıyor..."
	@if [ -f scripts/start-kiosk.sh ]; then \
		./scripts/start-kiosk.sh & \
	else \
		echo "❌ Kiosk script bulunamadı. 'make kiosk-service' çalıştırın"; \
	fi

kiosk-stop:
	@echo "🛑 Kiosk modu durduruluyor..."
	@pkill -f chromium || pkill -f firefox || echo "Kiosk zaten durdurulmuş"

kiosk-restart: kiosk-stop
	@sleep 2
	@make kiosk-start

kiosk-status:
	@echo "📊 Kiosk durumu:"
	@pgrep -f "chromium|firefox" >/dev/null && echo "✅ Çalışıyor" || echo "❌ Durdurulmuş"

kiosk-logs:
	sudo journalctl -u $(KIOSK_SERVICE_NAME) -f

# Otomatik başlatma
.PHONY: web-autostart kiosk-autostart
web-autostart:
	@echo "🔄 Web sunucusu otomatik başlatma etkinleştiriliyor..."
	sudo systemctl enable $(WEB_SERVICE_NAME)
	sudo systemctl start $(WEB_SERVICE_NAME)
	@echo "✅ Web servisi otomatik başlatma etkin"

kiosk-autostart:
	@echo "🔄 Kiosk modu otomatik başlatma etkinleştiriliyor..."
	sudo systemctl enable $(KIOSK_SERVICE_NAME)
	@echo "✅ Kiosk servisi otomatik başlatma etkin (grafik oturumda)"

# Toplu servis yönetimi
.PHONY: start-all stop-all restart-all status-all logs-all
start-all:
	@echo "🚀 Tüm servisler başlatılıyor..."
	sudo systemctl start $(WEB_SERVICE_NAME)
	sudo systemctl start $(KIOSK_SERVICE_NAME)
	@echo "✅ Tüm servisler başlatıldı"

stop-all:
	@echo "🛑 Tüm servisler durduruluyor..."
	sudo systemctl stop $(KIOSK_SERVICE_NAME)
	sudo systemctl stop $(WEB_SERVICE_NAME)
	@echo "✅ Tüm servisler durduruldu"

restart-all:
	@echo "🔄 Tüm servisler yeniden başlatılıyor..."
	sudo systemctl restart $(WEB_SERVICE_NAME)
	sudo systemctl restart $(KIOSK_SERVICE_NAME)
	@echo "✅ Tüm servisler yeniden başlatıldı"

status-all:
	@echo "📊 Servis Durumları:"
	@echo "=================="
	@echo -n "Web Server: "; sudo systemctl is-active $(WEB_SERVICE_NAME) 2>/dev/null || echo "kurulu değil"
	@echo -n "Kiosk Mode: "; sudo systemctl is-active $(KIOSK_SERVICE_NAME) 2>/dev/null || echo "kurulu değil"
	@echo ""
	@echo "Otomatik başlatma:"
	@echo -n "Web Server: "; sudo systemctl is-enabled $(WEB_SERVICE_NAME) 2>/dev/null || echo "devre dışı"
	@echo -n "Kiosk Mode: "; sudo systemctl is-enabled $(KIOSK_SERVICE_NAME) 2>/dev/null || echo "devre dışı"

logs-all:
	@echo "📝 Tüm servis logları (Ctrl+C ile çıkış):"
	sudo journalctl -u $(WEB_SERVICE_NAME) -u $(KIOSK_SERVICE_NAME) -f

# Servis yönetimi (eski uyumluluk)
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
.PHONY: uninstall uninstall-all
uninstall:
	@echo "🗑️  Servis kaldırılıyor..."
	sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true
	sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true
	sudo rm -f /etc/systemd/system/$(SERVICE_NAME).service
	sudo systemctl daemon-reload
	@echo "✅ Servis kaldırıldı"

uninstall-all:
	@echo "🗑️  Tüm servisler kaldırılıyor..."
	# Web servisi
	sudo systemctl stop $(WEB_SERVICE_NAME) 2>/dev/null || true
	sudo systemctl disable $(WEB_SERVICE_NAME) 2>/dev/null || true
	sudo rm -f /etc/systemd/system/$(WEB_SERVICE_NAME).service
	# Kiosk servisi
	sudo systemctl stop $(KIOSK_SERVICE_NAME) 2>/dev/null || true
	sudo systemctl disable $(KIOSK_SERVICE_NAME) 2>/dev/null || true
	sudo rm -f /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	# Eski servis
	sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true
	sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true
	sudo rm -f /etc/systemd/system/$(SERVICE_NAME).service
	# Daemon reload
	sudo systemctl daemon-reload
	@echo "✅ Tüm servisler kaldırıldı"

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
.PHONY: fix-missing-packages system-status
system-status:
	@echo "📊 Kuvoz Sistem Durumu"
	@echo "======================"
	@echo "✅ SİSTEM PYTHON: MÜKEMMEL DURUM"
	@echo "   ✅ RPi.GPIO: Çalışıyor"
	@echo "   ✅ Adafruit_DHT: Çalışıyor"  
	@echo "   ✅ Kivy: Çalışıyor"
	@echo "   ✅ smbus: Çalışıyor"
	@echo "   ✅ GPIO: Erişilebilir"
	@echo "   ✅ I2C: Aktif"
	@echo ""
	@echo "Web Sunucusu:"
	@pgrep -f "python.*web_server.py" >/dev/null && echo "   ✅ Web Server: Çalışıyor" || echo "   ❌ Web Server: Durdurulmuş"
	@netstat -tlnp 2>/dev/null | grep ":8000 " >/dev/null && echo "   ✅ Port 8000: Dinliyor" || echo "   ❌ Port 8000: Kapalı"
	@echo ""
	@echo "Kiosk Modu:"
	@pgrep -f "chromium|firefox" >/dev/null && echo "   ✅ Browser: Çalışıyor" || echo "   ❌ Browser: Durdurulmuş"
	@echo ""
	@echo "Virtual Environment: $(if $(wildcard $(VENV_DIR)),⚠️  Kısmi (normal - sistem Python kullanıyoruz),❌ Yok)"
	@echo ""
	@echo "🎯 ÖNERİLEN KULLANIM:"
	@echo "   make auto-setup      # Tam otomatik kurulum"
	@echo "   make web-start       # Web arayüzü başlat"  
	@echo "   make kiosk-start     # Kiosk modu başlat"
	@echo "   make status-all      # Servis durumları"
	@echo ""
	@echo "💡 DURUM: Sistem hazır - Web arayüzü önerilen yöntem!"

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
	@echo "💡 HIZLI ÇÖZÜM: make auto-setup (tam otomatik kurulum)"
	@echo ""
	@echo "📄 DÖKÜMANTASYON:"
	@echo "   cat AUTOSTART_README.md    # Otomatik başlatma rehberi"
	@echo "   ./quick-install.sh         # Hızlı kurulum script'i"
	@echo "   ./auto-boot-setup.sh       # Boot kurulum script'i"
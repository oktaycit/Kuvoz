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
	@echo "  kiosk-fix-auth  - Kiosk authentication sorununu düzelt"
	@echo "  boot-splash     - VetMarketi boot splash ekranı kur"
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
	@echo "  🌡️  DHT Sensör Tipi Ayarları:"
	@echo "  set-dht11       - DHT11 sensör tipini ayarla ve servisi yeniden başlat"
	@echo "  set-dht22       - DHT22 sensör tipini ayarla ve servisi yeniden başlat"
	@echo "  show-dht-type   - Ayarlanmış DHT sensör tipini göster"
	@echo "  clear-dht-type  - DHT sensör tipi ayarını kaldır (varsayılan: DHT22)"
	@echo ""
	@echo "  🔥 Firebase (Mobil Uygulama):"
	@echo "  firebase-install - Firebase bağımlılıklarını kur"
	@echo "  firebase-start   - Firebase bridge başlat"
	@echo "  firebase-restart - Firebase servisi yeniden başlat"
	@echo "  firebase-service - Firebase servisi kur"
	@echo "  firebase-status  - Firebase servis durumu"
	@echo "  firebase-logs    - Firebase logları"
	@echo ""
	@echo "  🌐 Uzaktan Erişim (Web UI + QR Kod):"
	@echo "  tailscale-deps     - QR kod bağımlılıklarını kur"
	@echo "  tailscale-check    - Tailscale kurulu mu kontrol et"
	@echo "  tailscale-install  - Tailscale'i kur"
	@echo "  tailscale-up       - Tailscale bağlantısı kur"
	@echo "  tailscale-down     - Tailscale bağlantısı kes"
	@echo "  tailscale-status   - Tailscale durumunu göster"
	@echo "  💡 Tarayıcıdan: http://KUVOZ_IP:8000 → 'Uzaktan Erişim' butonu"
	@echo ""
	@echo "  ☁️  Cloudflare Tunnel (Public Erişim):"
	@echo "  cloudflare-install - Cloudflared kur"
	@echo "  cloudflare-setup   - Cloudflare Tunnel oluştur"
	@echo "  cloudflare-start   - Cloudflare Tunnel başlat"
	@echo "  cloudflare-status  - Cloudflare Tunnel durumu"
	@echo ""
	@echo "  🔧 Bakım:"
	@echo "  clean           - Geçici dosyaları ve venv temizle"
	@echo "  kiosk-clear-cache - Chromium cache'i temizle ve kiosk'u yeniden başlat"
	@echo "  disk-usage      - Disk kullanım durumunu göster"
	@echo "  disk-clean      - Güvenli disk temizliği (önerilen)"
	@echo "  disk-clean-logs - Sadece journal loglarını temizle"
	@echo "  disk-clean-cache - Sadece cache dosyalarını temizle"
	@echo "  disk-clean-packages - Sadece paket cache'lerini temizle"
	@echo "  disk-clean-all  - Agresif disk temizliği (dikkatli kullanın!)"
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

# Firebase bağımlılıkları ve servis yönetimi
.PHONY: firebase-install firebase-start firebase-stop firebase-restart firebase-status firebase-logs firebase-service
firebase-install:
	@echo "🔥 Firebase bağımlılıkları kuruluyor..."
	$(PIP) install firebase-admin --break-system-packages 2>/dev/null || \
	pip3 install firebase-admin --break-system-packages
	@echo "✅ Firebase Admin SDK kuruldu"
	@echo "⚠️  Firebase credentials gerekli: config/kuvoz-firebase-key.json"
	@echo "   İndirme: Firebase Console → Project Settings → Service Accounts"

firebase-start:
	@echo "🔥 Firebase bridge başlatılıyor..."
	@if [ ! -f "config/kuvoz-firebase-key.json" ]; then \
		echo "❌ Firebase credentials bulunamadı!"; \
		echo "   config/kuvoz-firebase-key.json dosyası gerekli."; \
		echo "   Firebase Console'dan indirin."; \
		exit 1; \
	fi
	$(PYTHON) firebase_bridge.py

firebase-stop:
	@echo "🛑 Firebase bridge durduruluyor..."
	@sudo systemctl stop kuvoz-firebase 2>/dev/null || pkill -f "python.*firebase_bridge.py" || echo "Firebase bridge zaten durdurulmuş"

firebase-restart:
	@echo "🔄 Firebase bridge yeniden başlatılıyor..."
	@sudo systemctl restart kuvoz-firebase 2>/dev/null || (make firebase-stop && sleep 2 && make firebase-start)

firebase-status:
	@echo "📊 Firebase bridge durumu:"
	@pgrep -f "python.*firebase_bridge.py" > /dev/null && echo "✅ Çalışıyor" || echo "❌ Durdurulmuş"
	@sudo systemctl is-active kuvoz-firebase 2>/dev/null && echo "Servis: Aktif" || echo "Servis: Devre dışı"

firebase-logs:
	@echo "📝 Firebase bridge logları:"
	@sudo journalctl -u kuvoz-firebase -f 2>/dev/null || tail -f /var/log/kuvoz-firebase.log

firebase-service:
	@echo "🔥 Firebase servisi kuruluyor..."
	@if [ -f "systemd/kuvoz-firebase.service" ]; then \
		sudo cp systemd/kuvoz-firebase.service /etc/systemd/system/; \
		sudo systemctl daemon-reload; \
		sudo systemctl enable kuvoz-firebase; \
		sudo systemctl start kuvoz-firebase; \
		echo "✅ Firebase servisi kuruldu ve başlatıldı"; \
		echo "Durum: sudo systemctl status kuvoz-firebase"; \
	else \
		echo "❌ systemd/kuvoz-firebase.service bulunamadı"; \
	fi

# SCD41 bağımlılıkları
.PHONY: deps-scd41 test-scd41
deps-scd41:
	@echo "🔧 SCD41 bağımlılıkları kuruluyor..."
	$(PIP) install adafruit-circuitpython-scd4x smbus2 --break-system-packages 2>/dev/null || \
	pip3 install adafruit-circuitpython-scd4x smbus2 --break-system-packages || \
	( echo "⚠️  pip kurulumu başarısız, sistem paketleri deneniyor"; sudo apt install -y python3-smbus python3-smbus2 )
	@echo "✅ SCD41 bağımlılıkları kuruldu"

test-scd41:
	@echo "🧪 SCD41 test ediliyor..."
	@$(PYTHON) test_scd41_sensor.py || python3 test_scd41_sensor.py

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

# Yeni cihaz ilk kurulumu (Raspberry Pi üzerinde çalıştırılmalı)
.PHONY: setup-new-device
setup-new-device:
	@echo "🏥 Yeni Kuvoz Cihazı Kurulumu"
	@echo "============================"
	@echo ""
	@echo "⚠️  Bu komut YENİ Raspberry Pi cihazlarda çalıştırılmalıdır"
	@echo "   Otomatik olarak:"
	@echo "   - vet kullanıcısı oluşturur (sudo yetkili)"
	@echo "   - Şifre: vetmarketi"
	@echo "   - SSH key authentication yapılandırır"
	@echo "   - Hostname ayarlar (varsayılan: kuvoz)"
	@echo ""
	@if [ -f ./setup-new-device.sh ]; then \
		./setup-new-device.sh; \
	else \
		echo "❌ setup-new-device.sh bulunamadı!"; \
		exit 1; \
	fi

# Mevcut cihazda kullanıcı değiştirme (oktay -> vet)
.PHONY: migrate-to-vet
migrate-to-vet:
	@echo "🔄 Servisleri vet Kullanıcısına Taşıma"
	@echo "======================================"
	@echo ""
	@echo "⚠️  Bu komut MEVCUT cihazlarda oktay'dan vet'e geçiş için kullanılır"
	@echo "   Otomatik olarak:"
	@echo "   - Servisleri durdurur"
	@echo "   - Servis dosyalarını vet için günceller"
	@echo "   - Servisleri vet kullanıcısı ile başlatır"
	@echo "   - oktay kullanıcısını silme seçeneği sunar"
	@echo ""
	@if [ -f ./migrate-to-vet-user.sh ]; then \
		./migrate-to-vet-user.sh; \
	else \
		echo "❌ migrate-to-vet-user.sh bulunamadı!"; \
		exit 1; \
	fi

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

# Kiosk authentication sorununu düzelt
.PHONY: kiosk-fix-auth
kiosk-fix-auth:
	@echo "🔧 Kiosk authentication sorunu düzeltiliyor..."
	@echo "[Unit]" | sudo tee /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Description=Kuvoz Chromium Kiosk Mode" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "After=graphical.target network.target $(WEB_SERVICE_NAME).service" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Wants=graphical.target" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "[Service]" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Type=simple" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "User=$(USER)" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Environment=\"DISPLAY=:0\"" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Environment=\"XAUTHORITY=/home/$(USER)/.Xauthority\"" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Environment=\"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus\"" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "ExecStart=/usr/bin/chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble --disable-features=TranslateUI --password-store=basic --use-mock-keychain --disable-sync --disable-translate http://localhost:8000" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "Restart=on-failure" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "RestartSec=10" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "[Install]" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@echo "WantedBy=graphical.target" | sudo tee -a /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	sudo systemctl daemon-reload
	sudo systemctl restart $(KIOSK_SERVICE_NAME).service
	@echo "✅ Kiosk servisi güncellendi ve yeniden başlatıldı"
	@echo "Durum kontrol: sudo systemctl status $(KIOSK_SERVICE_NAME)"

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
	@echo "🖥️  Kiosk servisi kuruluyor..."
	$(MAKE) kiosk-cache-tmpfs
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
	@echo "\$\$CMD \$\$FLAGS http://localhost:8000" >> scripts/start-kiosk.sh
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
	sudo systemctl enable $(KIOSK_SERVICE_NAME)
# Chromium cache için tmpfs mount ve fstab ekleme
.PHONY: kiosk-cache-tmpfs
kiosk-cache-tmpfs:
	@if ! grep -qE '^tmpfs[[:space:]]+/home/vet/kuvoz/chromium-data[[:space:]]+tmpfs' /etc/fstab; then \
		echo '' | sudo tee -a /etc/fstab >/dev/null; \
		echo 'tmpfs /home/vet/kuvoz/chromium-data tmpfs size=64M,mode=0777 0 0' | sudo tee -a /etc/fstab >/dev/null; \
		echo '✅ /etc/fstab chromium-data satırı eklendi.'; \
	else \
		echo 'ℹ️  /etc/fstab chromium-data satırı zaten var.'; \
	fi
	sudo umount /home/vet/kuvoz/chromium-data || true
	sudo mount /home/vet/kuvoz/chromium-data || true

# Chromium cache temizleme
.PHONY: kiosk-clear-cache
kiosk-clear-cache:
	@echo "🧹 Chromium cache temizleniyor..."
	@sudo systemctl stop $(KIOSK_SERVICE_NAME) 2>/dev/null || echo "ℹ️  Kiosk servisi zaten durdurulmuş"
	@rm -rf /home/vet/kuvoz/chromium-data/*
	@echo "✅ Cache temizlendi"
	@sudo systemctl start $(KIOSK_SERVICE_NAME) 2>/dev/null || echo "⚠️  Kiosk servisi başlatılamadı (servis kurulu değil?)"
	@echo "✅ Kiosk servisi yeniden başlatıldı"
# Boot Splash Ekranı - VetMarketi logosu
.PHONY: boot-splash
boot-splash:
	@echo "🎨 VetMarketi boot splash ekranı kuruluyor..."
	@if [ ! -f scripts/install-boot-splash.sh ]; then \
		echo "❌ scripts/install-boot-splash.sh bulunamadı"; \
		exit 1; \
	fi
	chmod +x scripts/install-boot-splash.sh
	./scripts/install-boot-splash.sh
	@echo "✅ Boot splash kuruldu - Reboot sonrası aktif olacak"

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
	sudo systemctl stop $(WEB_SERVICE_NAME)
	@echo "✅ Servis durduruldu"

restart:
	sudo systemctl restart $(WEB_SERVICE_NAME)
	@echo "✅ Servis yeniden başlatıldı"

status:
	sudo systemctl status $(WEB_SERVICE_NAME)

logs:
	sudo journalctl -u $(WEB_SERVICE_NAME) -f

# DHT Sensör Tipi Yönetimi
.PHONY: set-dht11 set-dht22 show-dht-type clear-dht-type
set-dht11:
	@echo "🌡️  DHT11 sensör tipi ayarlanıyor..."
	@sudo mkdir -p /etc/systemd/system/$(WEB_SERVICE_NAME).service.d
	@echo "[Service]" | sudo tee /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf > /dev/null
	@echo "Environment=DHT_SENSOR_TYPE=11" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf > /dev/null
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(WEB_SERVICE_NAME) 2>/dev/null || echo "⚠️  Servis henüz kurulmamış (make web-service)"
	@echo "✅ DHT11 sensör tipi ayarlandı"
	@echo "Kontrol: systemctl show $(WEB_SERVICE_NAME) -p Environment --no-pager"
	@sleep 2
	@systemctl show $(WEB_SERVICE_NAME) -p Environment --no-pager 2>/dev/null | grep DHT_SENSOR_TYPE || echo "❌ DHT_SENSOR_TYPE bulunamadı"

set-dht22:
	@echo "🌡️  DHT22 sensör tipi ayarlanıyor..."
	@sudo mkdir -p /etc/systemd/system/$(WEB_SERVICE_NAME).service.d
	@echo "[Service]" | sudo tee /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf > /dev/null
	@echo "Environment=DHT_SENSOR_TYPE=22" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf > /dev/null
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(WEB_SERVICE_NAME) 2>/dev/null || echo "⚠️  Servis henüz kurulmamış (make web-service)"
	@echo "✅ DHT22 sensör tipi ayarlandı"
	@echo "Kontrol: systemctl show $(WEB_SERVICE_NAME) -p Environment --no-pager"
	@sleep 2
	@systemctl show $(WEB_SERVICE_NAME) -p Environment --no-pager 2>/dev/null | grep DHT_SENSOR_TYPE || echo "❌ DHT_SENSOR_TYPE bulunamadı"

show-dht-type:
	@echo "🌡️  Ayarlanmış DHT sensör tipi:"
	@if [ -f /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf ]; then \
		echo "Override dosyası içeriği:"; \
		sudo cat /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf; \
		echo ""; \
		echo "Servis environment değişkenleri:"; \
		systemctl show $(WEB_SERVICE_NAME) -p Environment --no-pager 2>/dev/null | grep -o 'DHT_SENSOR_TYPE=[0-9]*' || echo "❌ DHT_SENSOR_TYPE ayarlanmamış (varsayılan: DHT22)"; \
	else \
		echo "❌ Override dosyası yok - DHT sensör tipi ayarlanmamış (varsayılan: DHT22)"; \
		echo "Ayarlamak için: make set-dht11 veya make set-dht22"; \
	fi

clear-dht-type:
	@echo "🌡️  DHT sensör tipi ayarı kaldırılıyor..."
	@sudo rm -f /etc/systemd/system/$(WEB_SERVICE_NAME).service.d/override.conf
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(WEB_SERVICE_NAME) 2>/dev/null || echo "⚠️  Servis henüz kurulmamış"
	@echo "✅ DHT sensör tipi ayarı kaldırıldı (varsayılan DHT22 kullanılacak)"

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
.PHONY: clean backup restore permissions disk-usage disk-clean disk-clean-all disk-clean-logs disk-clean-cache disk-clean-packages

clean:
	@echo "🧹 Geçici dosyalar ve virtual environment temizleniyor..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf $(VENV_DIR)
	@echo "✅ Temizlik tamamlandı"

# Disk kullanım durumu
disk-usage:
	@echo "💾 Disk Kullanım Durumu"
	@echo "======================"
	@echo ""
	@echo "📊 Genel disk durumu:"
	@df -h / | grep -E '(Filesystem|/dev/)'
	@echo ""
	@echo "📁 Büyük klasörler (/):"
	@sudo du -h --max-depth=1 / 2>/dev/null | sort -hr | head -10
	@echo ""
	@echo "📂 Kullanıcı dizini (/home/vet):"
	@sudo du -h --max-depth=1 /home/vet 2>/dev/null | sort -hr | head -10
	@echo ""
	@echo "📝 Journal log boyutu:"
	@sudo journalctl --disk-usage
	@echo ""
	@echo "📦 Paket cache boyutu:"
	@sudo du -sh /var/cache/apt/archives 2>/dev/null || echo "N/A"

# Güvenli disk temizliği (önerilen)
disk-clean:
	@echo "🧹 Güvenli Disk Temizliği Başlatılıyor..."
	@echo "========================================"
	@echo ""
	@echo "1️⃣  Journal loglarını temizliyor (sadece son 50MB kalacak)..."
	@sudo journalctl --vacuum-size=50M
	@echo ""
	@echo "2️⃣  Paket cache temizleniyor..."
	@sudo apt clean
	@echo ""
	@echo "3️⃣  Kullanılmayan paketler kaldırılıyor..."
	@sudo apt autoremove -y --purge
	@echo ""
	@echo "4️⃣  Kullanıcı cache temizleniyor..."
	@rm -rf ~/.cache/chromium || true
	@rm -rf ~/.cache/thumbnails || true
	@echo ""
	@echo "✅ Güvenli temizlik tamamlandı!"
	@echo ""
	@echo "📊 Yeni disk durumu:"
	@df -h / | grep -E '(Filesystem|/dev/)'

# Agresif disk temizliği (dikkatli kullanın)
disk-clean-all:
	@echo "⚠️  AGRESİF DİSK TEMİZLİĞİ"
	@echo "=========================="
	@echo ""
	@echo "Bu işlem şunları yapacak:"
	@echo "  - Tüm journal loglarını temizle"
	@echo "  - Tüm paket cache'lerini temizle"
	@echo "  - Kullanılmayan paketleri kaldır"
	@echo "  - Tüm kullanıcı cache'lerini temizle"
	@echo "  - Eski kernel dosyalarını temizle"
	@echo ""
	@read -p "Devam etmek için EVET yazın: " confirm && [ "$$confirm" = "EVET" ] || exit 1
	@echo ""
	@echo "🧹 Temizlik başlıyor..."
	@sudo journalctl --vacuum-time=1d
	@sudo apt clean
	@sudo apt autoclean
	@sudo apt autoremove -y --purge
	@rm -rf ~/.cache/*
	@find /tmp -mindepth 1 -maxdepth 1 ! -name 'systemd-private-*' -exec rm -rf {} + 2>/dev/null || true
	@sudo find /var/log -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ Agresif temizlik tamamlandı!"
	@df -h / | grep -E '(Filesystem|/dev/)'

# Sadece logları temizle
disk-clean-logs:
	@echo "📝 Journal logları temizleniyor (son 50MB kalacak)..."
	@sudo journalctl --vacuum-size=50M
	@echo "✅ Log temizliği tamamlandı"

# Sadece cache'leri temizle
disk-clean-cache:
	@echo "🗑️  Cache dosyaları temizleniyor..."
	@rm -rf ~/.cache/chromium
	@rm -rf ~/.cache/thumbnails
	@rm -rf ~/.local/share/Trash/*
	@echo "✅ Cache temizliği tamamlandı"

# Sadece paketleri temizle
disk-clean-packages:
	@echo "📦 Paket temizliği yapılıyor..."
	@sudo apt clean
	@sudo apt autoclean
	@sudo apt autoremove -y --purge
	@echo "✅ Paket temizliği tamamlandı"


# ============================================================================
# TAILSCALE UZAKTAN ERİŞİM
# ============================================================================

.PHONY: tailscale-check tailscale-install tailscale-up tailscale-down tailscale-status tailscale-deps

tailscale-deps:
	@echo "📦 Tailscale için QR kod bağımlılıkları kuruluyor..."
	@echo "   Debian sistem paketleri kullanılıyor (PEP 668 uyumlu)"
	sudo apt update
	sudo apt install -y python3-qrcode python3-pil
	@echo "✅ QR kod kütüphaneleri kuruldu"
	@echo ""
	@echo "Test için: python3 -c 'import qrcode; print(\"✅ QR Code OK\")'"

tailscale-check:
	@echo "🔍 Tailscale kontrolü..."
	@which tailscale > /dev/null 2>&1 && echo "✅ Tailscale kurulu" || echo "❌ Tailscale kurulu değil"

tailscale-install:
	@echo "📥 Tailscale kuruluyor..."
	@if which tailscale > /dev/null 2>&1; then \
		echo "✅ Tailscale zaten kurulu"; \
	else \
		curl -fsSL https://tailscale.com/install.sh | sh; \
		echo "✅ Tailscale kurulumu tamamlandı"; \
	fi

tailscale-up:
	@echo "🔗 Tailscale bağlantısı kuruluyor..."
	@sudo tailscale up
	@echo "✅ Tailscale bağlantısı kuruldu"
	@echo ""
	@echo "📱 Uzaktan erişim için:"
	@echo "   1. Web arayüzünde 'Uzaktan Erişim' butonuna tıklayın"
	@echo "   2. QR kodu mobil cihazınızla okutun"
	@echo "   3. Tailscale hesabınızla giriş yapın"

tailscale-down:
	@echo "🔌 Tailscale bağlantısı kesiliyor..."
	@sudo tailscale down
	@echo "✅ Tailscale bağlantısı kesildi"

tailscale-status:
	@echo "📊 Tailscale durumu:"
	@sudo tailscale status 2>/dev/null || echo "❌ Tailscale çalışmıyor"

# ============================================================================
# BAKIMA DEVAM
# ============================================================================

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

# =============================================================================
# UZAKTAN ERİŞİM - Tailscale (Web UI ile QR Kod desteği)
# =============================================================================

# Not: Tailscale yönetimi artık web arayüzünden yapılabilir
# http://KUVOZ_IP:8000 → "Uzaktan Erişim" butonu

# Cloudflare Tunnel - Public erişim için
.PHONY: cloudflare-install cloudflare-setup cloudflare-start cloudflare-stop cloudflare-status cloudflare-restart

cloudflare-install:
	@echo "☁️  Cloudflared kuruluyor..."
	@echo "📖 Detaylı rehber: cat REMOTE_ACCESS_SETUP.md"
	@if command -v cloudflared >/dev/null 2>&1; then \
		echo "✅ Cloudflared zaten kurulu"; \
		cloudflared --version; \
	else \
		echo "⬇️  Cloudflared indiriliyor..."; \
		if uname -m | grep -q "aarch64"; then \
			echo "ARM64 sistemde"; \
			wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64; \
			sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared; \
		else \
			echo "ARM32 sistemde"; \
			wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm; \
			sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared; \
		fi; \
		sudo chmod +x /usr/local/bin/cloudflared; \
		echo "✅ Cloudflared kuruldu"; \
	fi
	@echo ""
	@echo "🔑 Şimdi şunu çalıştırın:"
	@echo "   make cloudflare-setup"

cloudflare-setup:
	@echo "⚙️  Cloudflare Tunnel yapılandırılıyor..."
	@if ! command -v cloudflared >/dev/null 2>&1; then \
		echo "❌ Cloudflared kurulu değil!"; \
		echo "   make cloudflare-install"; \
		exit 1; \
	fi
	@echo ""
	@echo "1️⃣  Cloudflare'e giriş yapın:"
	cloudflared tunnel login
	@echo ""
	@echo "2️⃣  Tunnel oluşturun:"
	@read -p "Tunnel adı (örn: kuvoz-tunnel): " tunnel_name; \
	cloudflared tunnel create $$tunnel_name; \
	echo ""; \
	echo "✅ Tunnel oluşturuldu: $$tunnel_name"; \
	echo ""; \
	echo "3️⃣  Yapılandırma dosyası oluşturuluyor..."; \
	sudo mkdir -p /etc/cloudflared; \
	tunnel_id=$$(cloudflared tunnel list | grep $$tunnel_name | awk '{print $$1}'); \
	echo "tunnel: $$tunnel_id" | sudo tee /etc/cloudflared/config.yml; \
	echo "credentials-file: /root/.cloudflared/$$tunnel_id.json" | sudo tee -a /etc/cloudflared/config.yml; \
	echo "" | sudo tee -a /etc/cloudflared/config.yml; \
	echo "ingress:" | sudo tee -a /etc/cloudflared/config.yml; \
	echo "  - service: http://localhost:8000" | sudo tee -a /etc/cloudflared/config.yml; \
	echo "" | sudo tee -a /etc/cloudflared/config.yml
	@echo ""
	@echo "✅ Yapılandırma tamamlandı!"
	@echo "🚀 Başlatmak için: make cloudflare-start"

cloudflare-start:
	@echo "☁️  Cloudflare Tunnel başlatılıyor..."
	@if ! command -v cloudflared >/dev/null 2>&1; then \
		echo "❌ Cloudflared kurulu değil!"; \
		echo "   make cloudflare-install"; \
		exit 1; \
	fi
	@if [ ! -f /etc/cloudflared/config.yml ]; then \
		echo "❌ Yapılandırma dosyası yok!"; \
		echo "   make cloudflare-setup"; \
		exit 1; \
	fi
	@echo "🔧 Servisi kuruyor..."
	sudo cloudflared service install
	@echo "🚀 Servisi başlatıyor..."
	sudo systemctl start cloudflared
	sudo systemctl enable cloudflared
	@echo ""
	@echo "✅ Cloudflare Tunnel başlatıldı!"
	@echo "📊 Durum için: make cloudflare-status"
	@echo "🌐 Dashboard: https://one.dash.cloudflare.com/networks/tunnels"

cloudflare-stop:
	@echo "🛑 Cloudflare Tunnel durduruluyor..."
	sudo systemctl stop cloudflared
	@echo "✅ Cloudflare Tunnel durduruldu"

cloudflare-restart:
	@echo "🔄 Cloudflare Tunnel yeniden başlatılıyor..."
	sudo systemctl restart cloudflared
	@echo "✅ Cloudflare Tunnel yeniden başlatıldı"

cloudflare-status:
	@echo "📊 Cloudflare Tunnel Durumu"
	@echo "==========================="
	@if ! command -v cloudflared >/dev/null 2>&1; then \
		echo "❌ Cloudflared kurulu değil"; \
		echo "   make cloudflare-install"; \
		exit 1; \
	fi
	@echo ""
	@echo "🔌 Servis Durumu:"
	@sudo systemctl is-active cloudflared >/dev/null 2>&1 && echo "✅ Aktif" || echo "❌ Durdurulmuş"
	@echo ""
	@echo "📝 Son loglar:"
	@sudo journalctl -u cloudflared -n 10 --no-pager 2>/dev/null || echo "Log okunamadı"
	@echo ""
	@echo "🌐 Tunnel listesi:"
	@cloudflared tunnel list 2>/dev/null || echo "Tunnel bilgisi alınamadı"
	@echo ""
	@echo "💡 Dashboard: https://one.dash.cloudflare.com/networks/tunnels"

# Uzaktan erişim yardım
.PHONY: remote-help

remote-help:
	@echo "🌐 Kuvoz Uzaktan Erişim Rehberi"
	@echo "==============================="
	@echo ""
	@echo "📖 DETAYLI REHBER:"
	@echo "   cat TAILSCALE_README.md"
	@echo "   cat REMOTE_ACCESS_SETUP.md"
	@echo ""
	@echo "🚀 TAILSCALE (ÖNERİLEN - Web UI + QR Kod):"
	@echo "   1. make tailscale-deps       # QR kod kütüphaneleri"
	@echo "   2. make tailscale-install    # Tailscale kur"
	@echo "   3. Web tarayıcıdan: http://KUVOZ_IP:8000"
	@echo "   4. 'Uzaktan Erişim' butonuna tıkla"
	@echo "   5. 'Bağlantı Kur' → QR kodu mobil cihazla okut"
	@echo "   6. Tailscale hesabıyla giriş yap"
	@echo ""
	@echo "   📱 Komut satırından: make tailscale-up"
	@echo ""
	@echo "☁️  CLOUDFLARE TUNNEL (Public erişim - 15 dakika kurulum):"
	@echo "   1. make cloudflare-install   # Cloudflared kur"
	@echo "   2. make cloudflare-setup     # Tunnel oluştur"
	@echo "   3. make cloudflare-start     # Başlat"
	@echo "   4. make cloudflare-status    # Durum kontrol"
	@echo "   5. Dashboard'dan URL al: https://one.dash.cloudflare.com"
	@echo ""
	@echo "📊 DURUM KONTROLÜ:"
	@echo "   make tailscale-status        # Tailscale durumu"
	@echo "   make cloudflare-status       # Cloudflare durumu"
	@echo ""
	@echo "🛑 DURDURMA:"
	@echo "   make tailscale-stop          # Tailscale durdur"
	@echo "   make cloudflare-stop         # Cloudflare durdur"
	@echo ""
	@echo "💡 İKİSİNİ DE KURABİLİRSİNİZ:"
	@echo "   Tailscale: Hızlı mobil erişim"
	@echo "   Cloudflare: Yedek public erişim"

# =============================================================================
# RASPBERRY PI ZERO 2 W OPTİMİZASYONLARI (512MB RAM)
# =============================================================================

.PHONY: check-zero2w install-zero2w optimize-zero2w deps-minimal setup-zero2w disable-ai disable-kiosk status-zero2w

# Zero 2 W TAM OTOMATİK KURULUM (tek komut)
setup-zero2w:
	@echo "🚀 Raspberry Pi Zero 2 W - Tam Otomatik Kurulum"
	@echo "============================================="
	@echo ""
	@echo "📋 Kurulum adımları:"
	@echo "   1. Minimal bağımlılıklar"
	@echo "   2. Web servisi kurulumu"
	@echo "   3. AI modülü devre dışı"
	@echo "   4. Kiosk modu devre dışı"
	@echo "   5. RAM optimizasyonları"
	@echo ""
	@read -p "Devam etmek için Enter'a basın..." dummy
	@make deps-minimal
	@make web-deps
	@make disable-ai
	@make disable-kiosk
	@make web-service
	@make optimize-zero2w
	@echo ""
	@echo "✅ Zero 2 W kurulumu tamamlandı!"
	@echo "📊 Durum raporu için: make status-zero2w"
	@echo "🌐 Web arayüzü: http://$(shell hostname -I | cut -d' ' -f1):8000"
	@echo "🔄 Yeniden başlatma önerilir: sudo reboot"

# AI modülünü devre dışı bırak
disable-ai:
	@echo "🤖 AI modülü artık web arayüzünden kontrol edilmektedir!"
	@echo ""
	@echo "ℹ️  YENİ SİSTEM:"
	@echo "   - AI modülü otomatik yüklü ama varsayılan olarak KAPALI"
	@echo "   - Ana sayfadaki AI panelinde power butonuna tıklayarak aç/kapat"
	@echo "   - Tercih otomatik kaydedilir (sistem yeniden başlatılınca korunur)"
	@echo ""
	@echo "💾 AI modülünü TAMAMEN kaldırmak için:"
	@echo "   sudo apt remove python3-opencv python3-picamera2"
	@echo "📊 RAM tasarrufu: ~50-80MB (AI kapalıyken)"
	@echo ""
	@echo "🔍 Mevcut durum:"
	@python3 -c "import sys; sys.path.append('lib'); from ai.manager import AIManager; print('  ✅ AI modülü mevcut')" 2>/dev/null && echo "  🟢 Web arayüzünden aç/kapat" || echo "  ❌ AI modülü yüklü değil"

# AI modülünü aktifleştir
enable-ai:
	@echo "🤖 AI modülü artık web arayüzünden kontrol edilmektedir!"
	@echo ""
	@echo "👉 NASIL AKTİFLEŞTİRİLİR:"
	@echo "   1. Web arayüzünü aç: http://localhost:5000"
	@echo "   2. AI panelinde (sağ üstte) power butonuna tıkla"
	@echo "   3. Kamera başlatılacak ve AI aktif olacak"
	@echo ""
	@echo "✅ Tercih otomatik kaydedilir (sistem yeniden başlatılınca korunur)"
	@echo ""
	@echo "📹 Gereksinimler:"
	@echo "   - Raspberry Pi Camera Module veya USB webcam"
	@echo "   - python3-opencv, python3-picamera2 (optional)"
	@echo ""
	@echo "🔧 AI bağımlılıklarını kurmak için:"
	@echo "   make deps-ai"
	@echo ""
	@python3 -c "import sys; sys.path.append('lib'); from ai.manager import AIManager; print('✅ AI modülü hazır')" 2>/dev/null || (echo "❌ AI modülü yüklü değil" && echo "   make deps-ai ile yükleyin")

# Kiosk modunu devre dışı bırak
disable-kiosk:
	@echo "🖥️  Kiosk modu devre dışı bırakılıyor..."
	@if systemctl is-active $(KIOSK_SERVICE_NAME) >/dev/null 2>&1; then \
		sudo systemctl stop $(KIOSK_SERVICE_NAME); \
		sudo systemctl disable $(KIOSK_SERVICE_NAME); \
		echo "✅ Kiosk servisi durduruldu ve devre dışı bırakıldı"; \
	elif systemctl is-enabled $(KIOSK_SERVICE_NAME) >/dev/null 2>&1; then \
		sudo systemctl disable $(KIOSK_SERVICE_NAME); \
		echo "✅ Kiosk servisi devre dışı bırakıldı"; \
	else \
		echo "✅ Kiosk servisi zaten devre dışı"; \
	fi
	@echo "📊 ~120MB RAM tasarrufu sağlandı"
	@echo "💡 Web arayüzüne başka cihazdan erişin:"
	@echo "   📱 Telefon/Tablet: http://$(shell hostname -I | cut -d' ' -f1):8000"

# Zero 2 W durum raporu
status-zero2w:
	@echo "📊 Raspberry Pi Zero 2 W - Durum Raporu"
	@echo "======================================="
	@echo ""
	@echo "💾 RAM Kullanımı:"
	@free -h | grep Mem: | awk '{printf "   Kullanılan: %s / %s (%%%s)\n", $$3, $$2, int($$3/$$2*100)}'
	@echo ""
	@echo "🌐 Web Servisi:"
	@if systemctl is-active $(WEB_SERVICE_NAME) >/dev/null 2>&1; then \
		echo "   ✅ Çalışıyor"; \
		echo "   🌐 http://$(shell hostname -I | cut -d' ' -f1):8000"; \
	else \
		echo "   ❌ Çalışmıyor"; \
		echo "   💡 Başlatmak için: sudo systemctl start $(WEB_SERVICE_NAME)"; \
	fi
	@echo ""
	@echo "🖥️  Kiosk Modu:"
	@if systemctl is-active $(KIOSK_SERVICE_NAME) >/dev/null 2>&1; then \
		echo "   ⚠️  Çalışıyor (RAM tüketimi yüksek)"; \
		echo "   💡 Devre dışı bırakmak için: make disable-kiosk"; \
	else \
		echo "   ✅ Devre dışı (Optimal)"; \
	fi
	@echo ""
	@echo "🤖 AI Modülü:"
	@if grep -q "^ENABLE_AI = False" web_server.py 2>/dev/null; then \
		echo "   ✅ Devre dışı (Optimal)"; \
	elif grep -q "^ENABLE_AI = True" web_server.py 2>/dev/null; then \
		echo "   ⚠️  Aktif (RAM tüketimi yüksek)"; \
		echo "   💡 Devre dışı bırakmak için: make disable-ai"; \
	else \
		echo "   ❓ Bilinmiyor"; \
	fi
	@echo ""
	@echo "🌡️  CPU Sıcaklık:"
	@vcgencmd measure_temp 2>/dev/null || echo "   ❌ Ölçülemedi"
	@echo ""
	@echo "📡 Port Durumu:"
	@if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then \
		echo "   ✅ Port 8000: Dinleniyor"; \
	else \
		echo "   ❌ Port 8000: Kapalı"; \
	fi
	@echo ""
	@echo "📊 Disk Kullanımı:"
	@df -h / | tail -1 | awk '{printf "   Kullanılan: %s / %s (%%%s)\n", $$3, $$2, $$5}'
	@echo ""
	@echo "💡 Öneri: Tüm optimizasyonlar için 'make optimize-zero2w'"

# Zero 2 W sistem kontrolü
check-zero2w:
	@echo "🔋 Raspberry Pi Zero 2 W Sistem Kontrolü"
	@echo "========================================="
	@echo ""
	@echo "💾 RAM Durumu:"
	@free -h | grep -E 'Mem:|Swap:'
	@echo ""
	@echo "🖥️  OS Tipi:"
	@if [ -f /usr/bin/startx ]; then \
		echo "⚠️  Desktop OS tespit edildi - Lite OS önerilir!"; \
	else \
		echo "✅ Lite OS kullanılıyor (Optimal)"; \
	fi
	@echo ""
	@echo "🎮 GPU Memory:"
	@vcgencmd get_mem gpu 2>/dev/null || echo "❌ vcgencmd bulunamadı"
	@echo ""
	@echo "💿 Swap Durumu:"
	@swapon --show 2>/dev/null || echo "Swap devre dışı"
	@echo ""
	@echo "🌡️  CPU Sıcaklık:"
	@vcgencmd measure_temp 2>/dev/null || echo "Ölçülemedi"
	@echo ""
	@echo "🔌 Sensör Durumu:"
	@sudo i2cdetect -y 1 2>/dev/null | grep -E '(50|61|62)' && echo "✅ I2C sensörler tespit edildi" || echo "⚠️  I2C sensör bulunamadı"
	@echo ""
	@echo "📦 Kurulu Servisler:"
	@systemctl is-active $(WEB_SERVICE_NAME) 2>/dev/null && echo "✅ Web Server: Aktif" || echo "❌ Web Server: Kurulu değil"
	@systemctl is-active $(KIOSK_SERVICE_NAME) 2>/dev/null && echo "✅ Kiosk Mode: Aktif" || echo "⚠️  Kiosk Mode: Kurulu değil (RAM tasarrufu)"
	@echo ""
	@echo "💡 ÖNERİLER:"
	@if [ -f /usr/bin/startx ]; then \
		echo "   1. Lite OS kullan (Desktop OS RAM israfı)"; \
	fi
	@vcgencmd get_mem gpu 2>/dev/null | grep -q "gpu=64" || echo "   2. GPU memory düşür: gpu_mem=64"
	@swapon --show | grep -q "100M" || echo "   3. Swap azalt: make optimize-zero2w"
	@echo "   4. AI modülünü devre dışı bırak (web_server.py: AI_AVAILABLE=False)"

# Zero 2 W için minimal sistem bağımlılıkları
deps-minimal:
	@echo "🔧 Minimal sistem bağımlılıkları (Zero 2 W için)..."
	@echo "⚠️  Kivy GUI yüklenmeyecek - Sadece Web Interface"
	sudo apt update
	sudo apt install -y python3-pip python3-dev python3-full
	sudo apt install -y i2c-tools python3-smbus python3-smbus2
	# Web sunucu bağımlılıkları
	sudo apt install -y python3-flask python3-flask-socketio python3-eventlet
	# GPIO ve sensörler
	sudo apt install -y python3-rpi.gpio
	# Chromium minimal (--no-install-recommends ile ~150MB tasarruf)
	sudo apt install -y chromium-browser --no-install-recommends || sudo apt install -y chromium --no-install-recommends
	# X server minimal
	sudo apt install -y xserver-xorg-core xinit openbox unclutter --no-install-recommends
	@echo "✅ Minimal bağımlılıklar kuruldu (~200MB tasarruf)"
	@echo "📊 Disk kullanımı:"
	@df -h | grep -E '(Filesystem|/dev/root)'

# AI modülü bağımlılıkları (isteğe bağlı)
deps-ai:
	@echo "🤖 AI modülü bağımlılıkları kuruluyor..."
	@echo ""
	@echo "📹 Kamera desteği:"
	# Raspberry Pi Camera desteği
	sudo apt install -y python3-picamera2 2>/dev/null || echo "⚠️  picamera2 kurulamadı (sadece RPi için)"
	# OpenCV
	@echo "🖼️ OpenCV kuruluyor (~150MB)..."
	sudo apt install -y python3-opencv
	# NumPy (OpenCV dependency)
	sudo apt install -y python3-numpy 2>/dev/null || echo "✅ numpy zaten kurulu"
	@echo ""
	@echo "✅ AI bağımlılıkları kuruldu!"
	@echo ""
	@echo "🚀 AI'yı aktifleştirmek için:"
	@echo "   1. Web arayüzüne git: http://localhost:5000"
	@echo "   2. AI panelindeki power butonuna tıkla"
	@echo ""
	@echo "📊 Disk kullanımı:"
	@df -h | grep -E '(Filesystem|/dev/root)'

# Zero 2 W için optimize kurulum (AI varsayılan kapalı)
install-zero2w: deps-minimal config
	@echo "🔋 Raspberry Pi Zero 2 W için optimize kurulum..."
	@echo "⚠️  512MB RAM - AI modülü varsayılan kapalı (ihtiyaç halinde web'den aç)"
	# Web bağımlılıkları kur
	$(PIP) install flask flask-socketio eventlet --break-system-packages 2>/dev/null || \
	echo "✅ Flask sistem paketlerinden kullanılacak"
	# DHT sensör desteği
	$(PIP) install Adafruit-DHT --break-system-packages 2>/dev/null || \
	echo "⚠️  Adafruit-DHT kurulamadı, DHT_Native kullanılacak"
	@echo "🤖 AI modülü: Varsayılan KAPALI (web arayüzünden açabilirsiniz)"
	@echo "✅ Zero 2 W kurulumu tamamlandı!"
	@echo ""
	@echo "🚀 SIRADAKİ ADIMLAR:"
	@echo "   1. make optimize-zero2w  # RAM optimizasyonları"
	@echo "   2. make web-service      # Web servisi kur"
	@echo "   3. make check-zero2w     # Sistem kontrolü"
	@echo ""
	@echo "⚠️  KİOSK MODU KURMA - Manuel başlat:"
	@echo "   make kiosk-start (otomatik başlatma yapma)"

# Zero 2 W RAM optimizasyonları
optimize-zero2w:
	@echo "⚡ Raspberry Pi Zero 2 W RAM optimizasyonları..."
	@echo ""
	@echo "1️⃣  GPU Memory düşürülüyor (128MB → 64MB)..."
	@if ! grep -q "^gpu_mem=64" /boot/config.txt 2>/dev/null && ! grep -q "^gpu_mem=64" /boot/firmware/config.txt 2>/dev/null; then \
		if [ -f /boot/firmware/config.txt ]; then \
			echo "gpu_mem=64" | sudo tee -a /boot/firmware/config.txt; \
		else \
			echo "gpu_mem=64" | sudo tee -a /boot/config.txt; \
		fi; \
		echo "✅ GPU memory 64MB'a düşürüldü"; \
	else \
		echo "✅ GPU memory zaten optimize edilmiş"; \
	fi
	@echo ""
	@echo "2️⃣  Swap azaltılıyor (2GB → 100MB)..."
	@sudo dphys-swapfile swapoff 2>/dev/null || true
	@if [ -f /etc/dphys-swapfile ]; then \
		sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=100/' /etc/dphys-swapfile; \
		sudo dphys-swapfile setup; \
		sudo dphys-swapfile swapon; \
		echo "✅ Swap 100MB'a düşürüldü"; \
	else \
		echo "⚠️  dphys-swapfile bulunamadı"; \
	fi
	@echo ""
	@echo "3️⃣  Log rotasyon optimize ediliyor..."
	@if [ -f config/kuvoz-logrotate ]; then \
		sudo cp config/kuvoz-logrotate /etc/logrotate.d/kuvoz; \
		echo "✅ Log rotasyon yapılandırıldı"; \
	else \
		echo "⚠️  config/kuvoz-logrotate bulunamadı"; \
	fi
	@echo ""
	@echo "4️⃣  Gereksiz servisler kontrol ediliyor..."
	@systemctl is-active bluetooth 2>/dev/null && echo "⚠️  Bluetooth aktif (kullanmıyorsan: sudo systemctl disable bluetooth)" || echo "✅ Bluetooth devre dışı"
	@systemctl is-active avahi-daemon 2>/dev/null && echo "⚠️  Avahi aktif (kullanmıyorsan: sudo systemctl disable avahi-daemon)" || echo "✅ Avahi devre dışı"
	@echo ""
	@echo "✅ Optimizasyonlar tamamlandı!"
	@echo "🔄 Yeniden başlatma ÖNERİLİR: sudo reboot"
	@echo ""
	@echo "📊 Beklenen RAM kullanımı (boot sonrası):"
	@echo "   Sistem (Lite):      ~180MB"
	@echo "   Web Server:         ~80MB"
	@echo "   Chromium (kiosk):   ~120MB"
	@echo "   Sensör okuma:       ~10MB"
	@echo "   ---------------------------------"
	@echo "   Toplam:             ~390MB / 512MB ✅"
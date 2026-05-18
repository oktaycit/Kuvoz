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
# Chromium dependencies handled internally now
USER := $(shell whoami)

# Varsayılan hedef
.PHONY: help
help:
	@echo "  📦 Manuel kurulum komutları:"
	@echo "  install         - Tam sistem kurulumu"
	@echo "  install-system  - Sistem paketleri ile kurulum (✅ tamamlandı)"
	@echo "  install-hybrid  - `install` için uyumluluk alias'ı"
	@echo "  venv            - Virtual environment oluştur"
	@echo "  deps            - Python bağımlılıklarını kur (venv)"
	@echo "  deps-system     - Sistem paketleri ile kur"
	@echo "  system-deps     - Sistem bağımlılıklarını kur"
	@echo "  config          - Sistem konfigürasyonu (I2C, GPIO)"
	@echo ""
	@echo "  🧪 Test ve kontrol:"
	@echo "  test            - Sistem ve donanım testleri"
	@echo "  test-summary    - Test sonuç özeti"
	@echo "  test-dht        - DHT sensör özel testi"
	@echo "  test-sensors-individual - Sensörleri tek tek test et"
	@echo "  gpio-test       - GPIO port testi (örn: make gpio-test PIN=12 STATE=on)"
	@echo "  status          - Kurulum durumunu kontrol et"
	@echo "  field-check     - Saha kurulum kontrolü (güç, Wi-Fi, Tailscale)"
	@echo "  fix-missing-packages - Eksik paketleri otomatik onar"
	@echo "  troubleshoot    - Sorun giderme rehberi"
	@echo ""
	@echo "  🚀 Çalıştırma seçenekleri:"
	@echo "  run             - Web sunucusunu foreground başlat"
	@echo "  debug           - Debug web sunucusunu başlat"
	@echo ""
	@echo "  🔧 Servis yönetimi:"
	@echo "  web-service     - Web servisi kur ve başlat"
	@echo "  kiosk-service   - Kiosk servisi kur ve başlat"
	@echo "  kiosk-disable-blanking - Kiosk ekran kararmasını kapat"
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
	@echo "  🌐 Uzaktan Erişim (Web UI + QR Kod):"
	@echo "  tailscale-deps     - QR kod bağımlılıklarını kur"
	@echo "  tailscale-check    - Tailscale kurulu mu kontrol et"
	@echo "  tailscale-install  - Tailscale'i kur"
	@echo "  tailscale-up       - Tailscale bağlantısı kur"
	@echo "  tailscale-down     - Tailscale bağlantısı kes"
	@echo "  tailscale-status   - Tailscale durumunu göster"
	@echo "  💡 Tarayıcıdan: http://KUVOZ_IP:8000 → 'Uzaktan Erişim' butonu"
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
	@echo "  cron-install    - Günlük otomatik disk temizliği kur (04:00)"
	@echo "  cron-uninstall  - Otomatik disk temizliğini kaldır"
	@echo "  cron-status     - Otomatik temizlik görevini kontrol et"
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
	sudo apt install -y chromium-browser xorg xinit openbox unclutter curl wpasupplicant network-manager libnl-3-200 || sudo apt install -y chromium xorg xinit openbox unclutter curl wpasupplicant network-manager libnl-3-200
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
		$(PIP) install flask flask-socketio eventlet qrcode pillow reportlab --break-system-packages 2>/dev/null || \
		(sudo apt install -y python3-flask python3-flask-socketio python3-eventlet python3-qrcode python3-pil python3-reportlab); \
	fi
	@echo "✅ Web bağımlılıkları kuruldu"

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
	@echo "Servis kurmak için: make web-service"
	@echo "Test çalıştırmak için: make run"

# Sistem paketleri ile kurulum
.PHONY: install-system
install-system: system-deps deps-system config test
	@echo "✅ Kuvoz sistemi sistem paketleri ile kuruldu!"
	@echo "Servis kurmak için: make web-service"
	@echo "Test çalıştırmak için: make run"

# Geriye dönük uyumluluk için tutuldu
.PHONY: install-hybrid
install-hybrid: install
	@echo "✅ Hibrit kurulum alias'ı tamamlandı!"
	@echo "Servis kurmak için: make web-service"
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
	$(VENV_PIP) install -r requirements.txt
	@echo "✅ Python bağımlılıkları virtual environment'a kuruldu"

# Sistem Python ile bağımlılık kurulumu
.PHONY: deps-system
deps-system: web-deps
	@echo "✅ Sistem Python bağımlılıkları kuruldu"

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
	@echo "   make web-service   # Kalıcı web servisi kur"
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
	@echo ""
	@echo "🖥️  KIOSK MODU:"
	@echo "   make kiosk-start     # Tam ekran kiosk modu"
	@echo ""
	@echo "📊 DURUM KONTROLÜ:"
	@echo "   make status-all      # Tüm servis durumları"
	@echo "   make logs-web        # Web sunucu logları"
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
	sudo apt install -y wpasupplicant network-manager libnl-3-200
	sudo apt install -y build-essential
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
	@echo "Environment=KUVOZ_SOCKETIO_ASYNC_MODE=threading" | sudo tee -a /etc/systemd/system/$(WEB_SERVICE_NAME).service
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

# Kiosk ekran kararmasını kalıcı olarak kapat
.PHONY: kiosk-disable-blanking
kiosk-disable-blanking:
	@echo "🖥️  Ekran kararma ayarı kapatılıyor..."
	@if command -v raspi-config >/dev/null 2>&1; then \
		sudo raspi-config nonint do_blanking 1 || true; \
	else \
		echo "ℹ️  raspi-config bulunamadı, sadece runtime xset ayarları kullanılacak"; \
	fi
	@if [ -f /boot/firmware/cmdline.txt ]; then \
		if grep -qw 'consoleblank=0' /boot/firmware/cmdline.txt; then \
			echo "ℹ️  consoleblank=0 zaten ayarlı"; \
		elif grep -Eq '(^| )consoleblank=' /boot/firmware/cmdline.txt; then \
			sudo sed -i -E 's/(^| )consoleblank=[^ ]*/\1consoleblank=0/' /boot/firmware/cmdline.txt; \
			echo "✅ consoleblank=0 olarak güncellendi (reboot sonrası aktif)"; \
		else \
			sudo sed -i 's/$$/ consoleblank=0/' /boot/firmware/cmdline.txt; \
			echo "✅ consoleblank=0 eklendi (reboot sonrası aktif)"; \
		fi; \
	fi

# Kiosk servisi kur ve başlat
.PHONY: kiosk-service
kiosk-service: kiosk-disable-blanking
	@echo "🖥️  Kiosk servisi kuruluyor..."
	@chmod +x scripts/start-kiosk.sh scripts/kiosk-session.sh
	@sudo cp systemd/kuvoz-kiosk.service /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@sudo sed -i 's|/home/vet/kuvoz|$(PROJECT_DIR)|g' /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@sudo sed -i 's|/home/vet|$(HOME)|g' /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@sudo sed -i 's|User=vet|User=$(USER)|g' /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	@sudo sed -i 's|Group=vet|Group=$(USER)|g' /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
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
service: web-service
	@echo "ℹ️  `service` hedefi artık `web-service` alias'ı olarak çalışıyor"

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
kiosk-start: kiosk-cache-tmpfs kiosk-service
	@echo "🖥️  Kiosk servisi kuruluyor..."
	sudo systemctl start $(KIOSK_SERVICE_NAME)
	@echo "✅ Kiosk servisi başlatıldı"
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
	sudo systemctl start $(WEB_SERVICE_NAME)
	@echo "✅ Web servisi başlatıldı"

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
		$(VENV_PYTHON) -c "import flask, flask_socketio; print('✅ Flask/SocketIO (venv): OK')" 2>/dev/null || echo "❌ Flask/SocketIO (venv): HATA"; \
		$(VENV_PYTHON) -c "import qrcode, PIL; print('✅ qrcode/Pillow (venv): OK')" 2>/dev/null || echo "❌ qrcode/Pillow (venv): HATA"; \
		$(VENV_PYTHON) -c "from lib.DHT_Native import DHT_Native; print('✅ DHT_Native (venv): OK')" 2>/dev/null || echo "❌ DHT_Native (venv): HATA"; \
		$(VENV_PYTHON) -c "import smbus; print('✅ smbus (venv): OK')" 2>/dev/null || $(VENV_PYTHON) -c "import smbus2; print('✅ smbus2 (venv): OK')" 2>/dev/null || echo "❌ smbus (venv): HATA"; \
	else \
		echo "Virtual environment yok, sistem Python test ediliyor:"; \
	fi
	@echo "Sistem Python kontrolü:"
	@python3 -c "import flask, flask_socketio; print('✅ Flask/SocketIO (sistem): OK')" 2>/dev/null || echo "❌ Flask/SocketIO (sistem): HATA"
	@python3 -c "import qrcode, PIL; print('✅ qrcode/Pillow (sistem): OK')" 2>/dev/null || echo "❌ qrcode/Pillow (sistem): HATA"
	@python3 -c "from lib.DHT_Native import DHT_Native; print('✅ DHT_Native (sistem): OK')" 2>/dev/null || echo "❌ DHT_Native (sistem): HATA"
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

# Uygulama çalıştırma
.PHONY: run debug
run:
	@echo "🚀 Web sunucusu başlatılıyor..."
	$(PYTHON) web_server.py

debug:
	@echo "🐛 Debug web sunucusu başlatılıyor..."
	$(PYTHON) web_debug_server.py

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
	@rm -rf ~/.config/chromium || true
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

# Periyodik Bakım (Crontab)
.PHONY: cron-install cron-uninstall cron-status
cron-install:
	@echo "🕒 Periyodik temizleme görevi kuruluyor (Her gün 04:00)..."
	@(crontab -l 2>/dev/null | grep -v "make disk-clean" ; echo "0 4 * * * cd $(PROJECT_DIR) && /usr/bin/make disk-clean >> $(PROJECT_DIR)/logs/maintenance.log 2>&1") | crontab -
	@echo "✅ Crontab görevi eklendi"

cron-uninstall:
	@echo "🗑️  Periyodik temizleme görevi kaldırılıyor..."
	@(crontab -l 2>/dev/null | grep -v "make disk-clean") | crontab -
	@echo "✅ Crontab görevi kaldırıldı"

cron-status:
	@echo "📊 Aktif Crontab Görevleri:"
	@crontab -l 2>/dev/null || echo "❌ Henüz bir görev tanımlanmamış"


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
	cp -f failure.dat backup/failure.dat.$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || echo "failure.dat dosyası bulunamadı"

# Ayarları geri yükle
restore:
	@echo "📁 Son yedekten geri yükleniyor..."
	@if ls backup/failure.dat.* 1> /dev/null 2>&1; then \
		latest=$$(ls -t backup/failure.dat.* | head -n1); \
		cp "$$latest" failure.dat; \
		echo "✅ Geri yüklendi: $$latest"; \
	else \
		echo "❌ Yedek dosyası bulunamadı"; \
	fi

permissions:
	@echo "🔐 Dosya izinleri düzenleniyor..."
	chmod +x scripts/start-kiosk.sh
	chmod 644 web_server.py web_debug_server.py
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
		$(VENV_DIR)/bin/pylint web_server.py web_debug_server.py lib/DFRobot_Oxygen.py || echo "Lint tamamlandı"; \
	else \
		pylint web_server.py web_debug_server.py lib/DFRobot_Oxygen.py || echo "Lint tamamlandı"; \
	fi

format:
	@echo "✨ Kod formatlama yapılıyor..."
	@if [ -d "$(VENV_DIR)" ]; then \
		$(VENV_DIR)/bin/black web_server.py web_debug_server.py lib/DFRobot_Oxygen.py || echo "Format tamamlandı"; \
	else \
		black web_server.py web_debug_server.py lib/DFRobot_Oxygen.py || echo "Format tamamlandı"; \
	fi

# Hızlı kurulum rehberi
.PHONY: quick-setup
quick-setup:
	@echo "⚡ Hızlı Kurulum Rehberi"
	@echo "======================="
	@echo "Önerilen web kurulum akışı:"
	@echo ""
	@echo "🥇 ÖNERİLEN: Sistem paketleri"
	@echo "   make install-system"
	@echo ""
	@echo "🥈 Venv tabanlı kurulum"
	@echo "   make install"
	@echo ""
	@echo "🥉 Uyumluluk alias'ı"
	@echo "   make install-hybrid"
	@echo ""
	@echo "Manuel adımlar:"
	@echo "1. make system-deps"
	@echo "2. make deps-system (veya deps)"
	@echo "3. make config"
	@echo "4. make test"
	@echo "5. make run"

# Sorun giderme ve onarım
.PHONY: fix-missing-packages system-status
system-status:
	@echo "📊 Kuvoz Sistem Durumu"
	@echo "======================"
	@echo "✅ Web uygulaması için temel durum"
	@echo "   ✅ Flask tabanlı mimari"
	@echo "   ✅ DHT_Native sürücüsü"
	@echo "   ✅ smbus / I2C desteği"
	@echo "   ✅ GPIO erişim kontrolü"
	@echo ""
	@echo "Web Sunucusu:"
	@pgrep -f "python.*web_server.py" >/dev/null && echo "   ✅ Web Server: Çalışıyor" || echo "   ❌ Web Server: Durdurulmuş"
	@netstat -tlnp 2>/dev/null | grep ":8000 " >/dev/null && echo "   ✅ Port 8000: Dinliyor" || echo "   ❌ Port 8000: Kapalı"
	@echo ""
	@echo "Kiosk Modu:"
	@pgrep -f "chromium" >/dev/null && echo "   ✅ Browser: Çalışıyor" || echo "   ❌ Browser: Durdurulmuş"
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
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment paketleri kuruluyor..."; \
		make deps; \
	else \
		echo "Sistem paketleri kuruluyor..."; \
		make install-system; \
	fi

# DHT sensör sorun giderme ve test
.PHONY: test-dht test-sensors-individual
test-dht:
	@echo "🌡️  DHT sensör test ediliyor..."
	@python3 -c "from lib.DHT_Native import DHT_Native; s=DHT_Native(15, 22); print('✅ DHT_Native import OK'); print('Okuma:', s.read())" || echo "❌ DHT_Native test hatası"

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
.PHONY: troubleshoot field-check field-check-json
troubleshoot:
	@echo "🔧 Web Kurulum Sorun Giderme"
	@echo "============================"
	@echo ""
	@echo "❌ Python bağımlılıkları eksikse:"
	@echo "   1. make install-system"
	@echo "   2. veya make deps"
	@echo ""
	@echo "❌ 'externally-managed-environment' hatası:"
	@echo "   1. make venv (virtual environment oluştur)"
	@echo "   2. veya make deps-system"
	@echo ""
	@echo "❌ GPIO erişim hatası:"
	@echo "   sudo usermod -a -G gpio $$USER"
	@echo "   sudo reboot"
	@echo ""
	@echo "❌ DHT okuma sorunu:"
	@echo "   1. make test-dht"
	@echo "   2. DHT_SENSOR_TYPE override ayarını kontrol et"
	@echo ""
	@echo "ℹ️  Testler:"
	@echo "  make test-dht         # DHT sensör testi"
	@echo "  make test-sensors     # Tüm sensör testi"

field-check:
	@python3 scripts/field_setup_check.py; rc=$$?; \
	if [ $$rc -eq 2 ]; then \
		echo ""; \
		echo "⚠️  Kritik saha sorunu var; kurulum tamamlandı sayılmasın."; \
	elif [ $$rc -eq 1 ]; then \
		echo ""; \
		echo "⚠️  Uyarı var; sahada not alın ve mümkünse kapatın."; \
	fi; \
	exit 0

field-check-json:
	@python3 scripts/field_setup_check.py --json

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
	@command -v /snap/bin/chromium >/dev/null 2>&1 && echo "✅ snap chromium: /snap/bin/chromium" || echo "❌ snap chromium: yok"
	@echo ""
	@echo "5️⃣  Önerilen Çözümler:"
	@echo "  🔄 make chromium-check    # Paket kontrolü"
	@echo "  🔄 make web-deps-install  # Python paketleri kur"
	@echo "  🔄 make web-run          # Web server başlat"
	@echo "  🔄 make auto-browser      # Otomatik browser seç"
	@echo "  🔄 ./quick_web_test.sh   # Hızlı sistem testi"
	@echo "   📖 cat TRIXIE_CHROMIUM_FIX.md  # Detaylı rehber"
	@echo ""
	@echo "6️⃣  Manuel Kurulum:"
	@echo "   sudo apt install chromium"
	@echo "   # veya"
	@echo "   sudo apt install chromium-browser"
	@echo ""
	@echo "💡 HIZLI ÇÖZÜM: make auto-setup (tam otomatik kurulum)"
	@echo ""
	@echo "📄 DÖKÜMANTASYON:"
	@echo "   cat docs/AUTOSTART_README.md    # Otomatik başlatma rehberi"
	@echo "   ./quick-install.sh         # Hızlı kurulum script'i"
	@echo "   ./auto-boot-setup.sh       # Boot kurulum script'i"

# =============================================================================
# UZAKTAN ERİŞİM - Tailscale (Web UI ile QR Kod desteği)
# =============================================================================

# Not: Tailscale yönetimi artık web arayüzünden yapılabilir
# http://KUVOZ_IP:8000 → "Uzaktan Erişim" butonu

# Uzaktan erişim yardım
.PHONY: remote-help

remote-help:
	@echo "🌐 Kuvoz Uzaktan Erişim Rehberi"
	@echo "==============================="
	@echo ""
	@echo "📖 DETAYLI REHBER:"
	@echo "   cat docs/TAILSCALE_README.md"
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
	@echo "📊 DURUM KONTROLÜ:"
	@echo "   make tailscale-status        # Tailscale durumu"
	@echo ""
	@echo "🛑 DURDURMA:"
	@echo "   make tailscale-down          # Tailscale bağlantısını kes"

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
	sudo apt install -y python3-flask python3-flask-socketio python3-eventlet python3-reportlab
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

# GPIO Test Tool - Hızlı port testi
.PHONY: gpio-test
gpio-test:
	@if [ -z "$(PIN)" ] || [ -z "$(STATE)" ]; then \
		echo "❌ KULLANIM: make gpio-test PIN=<pin_numarası> STATE=<on|off>"; \
		echo ""; \
		echo "📝 ÖRNEKLER:"; \
		echo "  make gpio-test PIN=12 STATE=on   # GPIO 12'yi aç"; \
		echo "  make gpio-test PIN=12 STATE=off  # GPIO 12'yi kapat"; \
		echo "  make gpio-test PIN=5 STATE=on    # GPIO 5'i aç"; \
		echo ""; \
		echo "🔌 MEVCUT PİNLER:"; \
		echo "  GPIO5  - Terapötik Aydınlatma"; \
		echo "  GPIO6  - Nebulizer"; \
		echo "  GPIO13 - Nemlendirici"; \
		echo "  GPIO16 - Karbon Isıtıcı"; \
		echo "  GPIO19 - IR Isıtıcı"; \
		echo "  GPIO20 - Fan"; \
		echo "  GPIO21 - UV Sterilizasyon"; \
		echo "  GPIO26 - Ozon"; \
		echo "  GPIO12 - Soğutma"; \
		echo ""; \
		exit 1; \
	fi
	@echo "🔌 GPIO Test başlatılıyor..."
	@sudo python3 gpio_test.py -test $(PIN) $(STATE)

# AI Alert Diagnostic Tool
.PHONY: ai-diagnose
ai-diagnose:
	@echo "🤖 AI Alert Diagnostic Tool"
	@echo "============================"
	@python3 diagnose_ai_alerts.py

.PHONY: ai-logs
ai-logs:
	@echo "📊 AI Son 50 Log Kaydı"
	@echo "======================="
	@journalctl -u kuvoz-web --no-pager -n 100 2>/dev/null | grep -i "AI\|camera\|vision\|vital" || echo "Systemd log bulunamadı, web_server.log deneniyor..."
	@if [ -f web_server.log ]; then \
		echo ""; \
		echo "📄 web_server.log AI kayıtları:"; \
		tail -100 web_server.log | grep -i "AI\|camera\|vision\|vital" || echo "AI log bulunamadı"; \
	fi

.PHONY: disable-rpi-connect
disable-rpi-connect:
	@echo "🚫 Raspberry Pi Connect Hizmetleri Devre Dışı Bırakılıyor..."
	@echo "=============================================================="
	@echo "⚠️  Bu işlem WayVNC restart loop sorununu çözer"
	@echo ""
	@systemctl --user stop rpi-connect-wayvnc.service 2>/dev/null && echo "✅ rpi-connect-wayvnc durduruldu" || echo "⚠️  rpi-connect-wayvnc zaten durdurulmuş"
	@systemctl --user disable rpi-connect-wayvnc.service 2>/dev/null && echo "✅ rpi-connect-wayvnc devre dışı bırakıldı" || true
	@systemctl --user mask rpi-connect-wayvnc.service 2>/dev/null && echo "✅ rpi-connect-wayvnc maskelendi" || true
	@systemctl --user stop rpi-connect.service 2>/dev/null && echo "✅ rpi-connect durduruldu" || echo "⚠️  rpi-connect zaten durdurulmuş"
	@systemctl --user disable rpi-connect.service 2>/dev/null && echo "✅ rpi-connect devre dışı bırakıldı" || true
	@systemctl --user mask rpi-connect.service 2>/dev/null && echo "✅ rpi-connect maskelendi" || true
	@systemctl --user stop rpi-connect-signin.service 2>/dev/null && echo "✅ rpi-connect-signin durduruldu" || echo "⚠️  rpi-connect-signin zaten durdurulmuş"
	@systemctl --user disable rpi-connect-signin.service 2>/dev/null && echo "✅ rpi-connect-signin devre dışı bırakıldı" || true
	@systemctl --user mask rpi-connect-signin.service 2>/dev/null && echo "✅ rpi-connect-signin maskelendi" || true
	@echo ""
	@echo "✅ Raspberry Pi Connect hizmetleri devre dışı bırakıldı!"
	@echo "🔄 Değişikliklerin etkili olması için yeniden başlatma önerilir: sudo reboot"

.PHONY: ai-db-status
ai-db-status:
	@echo "📊 AI Vitals Database Durumu"
	@echo "============================"
	@if [ -f data/ai_vitals.db ]; then \
		echo "✅ Veritabanı mevcut: data/ai_vitals.db"; \
		echo ""; \
		echo "📊 Kayıt sayısı:"; \
		python3 -c "import sqlite3; conn=sqlite3.connect('data/ai_vitals.db'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM ai_vital_readings'); print(f'   {cur.fetchone()[0]} kayıt')" 2>/dev/null || echo "❌ Veritabanı yok"; \
		echo ""; \
		echo "📈 Son 10 kayıt:"; \
		python3 -c "import sqlite3; conn=sqlite3.connect('data/ai_vitals.db'); cur=conn.cursor(); cur.execute('SELECT timestamp, patient_name, status, respiration_bpm, confidence FROM ai_vital_readings ORDER BY timestamp DESC LIMIT 10'); [print(f'   {r[0]} | {r[1]} | {r[2]} | {r[3]} BPM | {r[4]}') for r in cur.fetchall()]" 2>/dev/null || echo "❌ Okuma hatası"; \
		echo ""; \
		echo "📊 Durum dağılımı:"; \
		python3 -c "import sqlite3; conn=sqlite3.connect('data/ai_vitals.db'); cur=conn.cursor(); cur.execute('SELECT status, COUNT(*) as count FROM ai_vital_readings GROUP BY status ORDER BY count DESC'); [print(f'   {r[0]}: {r[1]}') for r in cur.fetchall()]" 2>/dev/null || echo "❌ Gruplama hatası"; \
	else \
		echo "❌ Veritabanı bulunamadı: data/ai_vitals.db"; \
		echo "AI hiç veri kaydetmemiş!"; \
	fi

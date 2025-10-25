# Chromium Kiosk Mode Setup
# Web tabanlı interface için

.PHONY: web-install web-setup kiosk-setup web-service kiosk-service web-start web-stop kiosk-start kiosk-stop web-status

# Web dependencies installation
web-install:
	@echo "📦 Installing web dependencies..."
	sudo apt update
	# Raspberry Pi OS Trixie için güncel paket adları
	sudo apt install -y chromium xorg xinit openbox unclutter curl
	# Alternative chromium packages için fallback
	sudo apt install -y chromium-browser || sudo apt install -y chromium || echo "Chromium package variation installed"
	# Python packages için externally-managed-environment çözümü
	sudo apt install -y python3-flask python3-flask-socketio python3-eventlet || \
	(python3 -m venv web_venv && \
	 web_venv/bin/pip install flask flask-socketio eventlet && \
	 echo "✅ Web packages installed in virtual environment") || \
	pip3 install --break-system-packages flask flask-socketio eventlet
	@echo "✅ Web dependencies installed"

# Full web setup
web-setup: web-install
	@echo "🔧 Setting up web interface..."
	# Create web server service
	sudo cp systemd/kuvoz-web.service /etc/systemd/system/
	sudo sed -i 's|/path/to/kuvoz|$(PROJECT_DIR)|g' /etc/systemd/system/kuvoz-web.service
	sudo sed -i 's|pi|$(USER)|g' /etc/systemd/system/kuvoz-web.service
	sudo systemctl daemon-reload
	sudo systemctl enable $(WEB_SERVICE_NAME)
	
	# Create kiosk service
	sudo cp systemd/kuvoz-kiosk.service /etc/systemd/system/
	sudo sed -i 's|/path/to/kuvoz|$(PROJECT_DIR)|g' /etc/systemd/system/kuvoz-kiosk.service
	sudo sed -i 's|pi|$(USER)|g' /etc/systemd/system/kuvoz-kiosk.service
	sudo systemctl daemon-reload
	sudo systemctl enable $(KIOSK_SERVICE_NAME)
	
	# Setup autostart
	mkdir -p ~/.config/openbox
	cp config/openbox-autostart ~/.config/openbox/autostart
	chmod +x ~/.config/openbox/autostart
	
	# Setup X11 auto login
	sudo raspi-config nonint do_boot_behaviour B4  # Desktop autologin
	@echo "✅ Web interface setup completed"

# Kiosk mode setup only
kiosk-setup:
	@echo "🖥️  Setting up Chromium kiosk mode..."
	sudo apt update
	# Raspberry Pi OS Trixie için chromium paket kontrolü
	sudo apt install -y chromium xorg xinit openbox unclutter || \
	sudo apt install -y chromium-browser xorg xinit openbox unclutter || \
	echo "❌ Chromium installation failed - check package availability"
	
	# Create kiosk start script
	mkdir -p $(PROJECT_DIR)/scripts
	cp scripts/start-kiosk.sh $(PROJECT_DIR)/scripts/
	chmod +x $(PROJECT_DIR)/scripts/start-kiosk.sh
	
	# Setup openbox autostart
	mkdir -p ~/.config/openbox
	echo "#!/bin/bash" > ~/.config/openbox/autostart
	echo "# Kuvoz Kiosk Autostart" >> ~/.config/openbox/autostart
	echo "$(PROJECT_DIR)/scripts/start-kiosk.sh &" >> ~/.config/openbox/autostart
	chmod +x ~/.config/openbox/autostart
	
	@echo "✅ Kiosk mode setup completed"

# Web server service operations
web-service:
	@echo "🔧 Setting up web server service..."
	sudo cp systemd/kuvoz-web.service /etc/systemd/system/
	sudo sed -i 's|/path/to/kuvoz|$(PROJECT_DIR)|g' /etc/systemd/system/kuvoz-web.service
	sudo sed -i 's|pi|$(USER)|g' /etc/systemd/system/kuvoz-web.service
	sudo systemctl daemon-reload
	sudo systemctl enable $(WEB_SERVICE_NAME)
	@echo "✅ Web service installed and enabled"

kiosk-service:
	@echo "🖥️  Setting up kiosk service..."
	sudo cp systemd/kuvoz-kiosk.service /etc/systemd/system/
	sudo sed -i 's|/path/to/kuvoz|$(PROJECT_DIR)|g' /etc/systemd/system/kuvoz-kiosk.service
	sudo sed -i 's|pi|$(USER)|g' /etc/systemd/system/kuvoz-kiosk.service
	sudo systemctl daemon-reload
	sudo systemctl enable $(KIOSK_SERVICE_NAME)
	@echo "✅ Kiosk service installed and enabled"

# Service management
web-start:
	@echo "🚀 Starting web server..."
	sudo systemctl start $(WEB_SERVICE_NAME)
	@echo "✅ Web server started"
	@echo "📱 Access: http://localhost:5000"

web-stop:
	@echo "⏹️  Stopping web server..."
	sudo systemctl stop $(WEB_SERVICE_NAME)
	@echo "✅ Web server stopped"

kiosk-start:
	@echo "🖥️  Starting kiosk mode..."
	sudo systemctl start $(KIOSK_SERVICE_NAME)
	@echo "✅ Kiosk mode started"

kiosk-stop:
	@echo "⏹️  Stopping kiosk mode..."
	sudo systemctl stop $(KIOSK_SERVICE_NAME)
	@echo "✅ Kiosk mode stopped"

web-status:
	@echo "📊 Web Services Status:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Web Server:"
	@sudo systemctl status $(WEB_SERVICE_NAME) --no-pager -l || echo "❌ Web service not found"
	@echo ""
	@echo "Kiosk Mode:"
	@sudo systemctl status $(KIOSK_SERVICE_NAME) --no-pager -l || echo "❌ Kiosk service not found"
	@echo ""
	@echo "Network Status:"
	@ip addr show | grep "inet " | head -3
	@echo ""
	@echo "Display Status:"
	@if [ -n "$$DISPLAY" ]; then echo "✅ Display available: $$DISPLAY"; else echo "❌ No display"; fi

# Development server
web-dev:
	@echo "🔧 Starting development web server..."
	cd $(PROJECT_DIR) && $(PYTHON) web_server.py

# Test web interface
web-test:
	@echo "🧪 Testing web interface..."
	curl -s http://localhost:5000/ > /dev/null && echo "✅ Web server responding" || echo "❌ Web server not responding"
	curl -s http://localhost:5000/api/status > /dev/null && echo "✅ API responding" || echo "❌ API not responding"

# Manual kiosk start (for testing)
kiosk-manual:
	@echo "🖥️  Starting manual kiosk mode..."
	@echo "Note: This will start fullscreen browser"
	@# Chromium executable bulma
	@if command -v chromium >/dev/null 2>&1; then \
		DISPLAY=:0 chromium \
			--kiosk \
			--no-sandbox \
			--disable-dev-shm-usage \
			--disable-gpu \
			--disable-features=VizDisplayCompositor \
			--start-fullscreen \
			--window-position=0,0 \
			--window-size=1920,1080 \
			--app=http://localhost:5000 & \
	elif command -v chromium-browser >/dev/null 2>&1; then \
		DISPLAY=:0 chromium-browser \
			--kiosk \
			--no-sandbox \
			--disable-dev-shm-usage \
			--disable-gpu \
			--disable-features=VizDisplayCompositor \
			--start-fullscreen \
			--window-position=0,0 \
			--window-size=1920,1080 \
			--app=http://localhost:5000 & \
	else \
		echo "❌ No Chromium found!"; \
	fi

# Clean web setup
web-clean:
	@echo "🧹 Cleaning web setup..."
	sudo systemctl stop $(WEB_SERVICE_NAME) || true
	sudo systemctl stop $(KIOSK_SERVICE_NAME) || true
	sudo systemctl disable $(WEB_SERVICE_NAME) || true
	sudo systemctl disable $(KIOSK_SERVICE_NAME) || true
	sudo rm -f /etc/systemd/system/$(WEB_SERVICE_NAME).service
	sudo rm -f /etc/systemd/system/$(KIOSK_SERVICE_NAME).service
	sudo systemctl daemon-reload
	rm -f ~/.config/openbox/autostart
	@echo "✅ Web setup cleaned"

# Help for web commands
web-help:
	@echo "🌐 Kuvoz Web Interface Commands:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Installation:"
	@echo "  make web-install      - Install web dependencies"
	@echo "  make web-deps-install - Install Python packages only"
	@echo "  make web-setup        - Full web + kiosk setup"
	@echo "  make kiosk-setup      - Kiosk mode only"
	@echo "  make chromium-check   - Check Chromium availability"
	@echo ""
	@echo "🔧 Services:"
	@echo "  make web-service      - Install web server service"
	@echo "  make kiosk-service    - Install kiosk service"
	@echo ""
	@echo "⚡ Operations:"
	@echo "  make web-run          - Start web server (auto-detect Python)"
	@echo "  make web-test-sim     - Test in simulation mode"
	@echo "  make web-sim          - Run in simulation mode"
	@echo "  make web-debug        - Debug web server"
	@echo "  make web-debug-gpio   - GPIO debug mode"
	@echo "  make web-dht-debug    - DHT sensor debug mode"
	@echo "  make dht11-test       - Test DHT11 sensor (pin 15)"
	@echo "  make dht11-native-test - Test DHT11 with DHT_Native only"
	@echo "  make fix-adafruit-platform - Fix Adafruit_DHT platform issue"
	@echo "  make web-platform-fix-full - Web server with platform fix"
	@echo "  make web-start        - Start web server service"
	@echo "  make web-stop         - Stop web server service"
	@echo "  make kiosk-start      - Start kiosk mode"
	@echo "  make kiosk-stop       - Stop kiosk mode"
	@echo "  make web-status       - Show services status"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make web-dev          - Start development server"
	@echo "  make kiosk-manual     - Manual kiosk start"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make web-clean        - Clean web setup"
	@echo "  make web-help         - Show this help"

# Chromium paket kontrol
chromium-check:
	@echo "🔍 Checking Chromium availability..."
	@echo "Available Chromium packages:"
	@apt list --installed | grep -i chromium || echo "❌ No Chromium packages installed"
	@echo ""
	@echo "Available executables:"
	@if command -v chromium >/dev/null 2>&1; then echo "✅ chromium found"; else echo "❌ chromium not found"; fi
	@if command -v chromium-browser >/dev/null 2>&1; then echo "✅ chromium-browser found"; else echo "❌ chromium-browser not found"; fi
	@if command -v google-chrome >/dev/null 2>&1; then echo "✅ google-chrome found"; else echo "❌ google-chrome not found"; fi
	@echo ""
	@echo "Searchable packages:"
	# Searchable packages:"
	@apt search chromium 2>/dev/null | grep "^chromium" | head -5

# Web bağımlılıkları ayrı kurulum
web-deps-install:
	@echo "📦 Web Python packages kuruluyor..."
	@echo "Trying system packages first..."
	sudo apt install -y python3-flask python3-flask-socketio python3-eventlet || \
	(echo "System packages failed, trying virtual environment..." && \
	 python3 -m venv web_venv && \
	 web_venv/bin/pip install flask flask-socketio eventlet && \
	 echo "✅ Web packages kuruldu: web_venv/bin/python") || \
	(echo "Virtual env failed, using --break-system-packages..." && \
	 pip3 install --break-system-packages flask flask-socketio eventlet)
	@echo "✅ Web dependencies kuruldu"

# Web server'ı uygun Python ile çalıştır
web-run:
	@echo "🚀 Web server başlatılıyor..."
	@if [ -f "web_venv/bin/python" ]; then \
		echo "Using virtual environment Python"; \
		web_venv/bin/python web_server.py; \
	elif python3 -c "import flask" 2>/dev/null; then \
		echo "Using system Python"; \
		python3 web_server.py; \
	else \
		echo "❌ Flask not found! Run: make web-deps-install"; \
		exit 1; \
	fi

# Web server test (simulation mode)
web-test-sim:
	@echo "🧪 Web server test (simulation mode)..."
	@if [ -f "web_venv/bin/python" ]; then \
		echo "Testing with virtual environment Python"; \
		web_venv/bin/python web_server.py --sim; \
	elif python3 -c "import flask" 2>/dev/null; then \
		echo "Testing with system Python"; \
		python3 web_server.py --sim; \
	else \
		echo "❌ Flask not found! Run: make web-deps-install"; \
		exit 1; \
	fi

# Debug web server
web-debug:
	@echo "🔍 Web server debug mode..."
	python3 test_web_server.py

# Web server with GPIO debug
web-debug-gpio:
	@echo "🔍 Web server GPIO debug mode..."
	./start_web_debug.sh

# Web server with simulation
web-sim:
	@echo "🔧 Web server simulation mode..."
	@if [ -f "web_venv/bin/python" ]; then \
		web_venv/bin/python web_server.py --sim; \
	elif python3 -c "import flask" 2>/dev/null; then \
		python3 web_server.py --sim; \
	else \
		echo "❌ Flask not found! Run: make web-deps-install"; \
		exit 1; \
	fi

# DHT11 sensor test
dht11-test:
	@echo "🌡️  Testing DHT11 sensor on pin 15..."
	python3 test_dht11.py

# GPIO basic test
gpio-basic-test:
	@echo "🔧 Testing basic GPIO functionality..."
	@python3 test_gpio_basic.py 22

# Simple DHT11 connection test
dht11-simple-test:
	@echo "🔍 Simple DHT11 connection test..."
	@python3 test_dht_simple.py

# DHT Native only test  
dht11-native-test:
	@echo "🌡️  Testing DHT11 with DHT_Native only..."
	@python3 test_dht_native.py

# Fix Adafruit_DHT platform issue
fix-adafruit-platform:
	@echo "🔧 Fixing Adafruit_DHT platform detection..."
	python3 fix_adafruit_platform.py

# Web server with platform fix
web-platform-fix:
	@echo "🔧 Starting web server with platform fix..."
	@python3 fix_adafruit_platform.py && make web-run

# Web server with platform fix script
web-platform-fix-full:
	@echo "🔧 Starting web server with full platform fix..."
	./start_web_platform_fix.sh

# Web server with verbose DHT logging
web-dht-debug:
	@echo "🌡️  Web server with DHT debug..."
	@export PYTHONUNBUFFERED=1 && \
	if [ -f "web_venv/bin/python" ]; then \
		web_venv/bin/python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('web_server.py').read())"; \
	elif python3 -c "import flask" 2>/dev/null; then \
		python3 -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('web_server.py').read())"; \
	else \
		echo "❌ Flask not found! Run: make web-deps-install"; \
		exit 1; \
	fi
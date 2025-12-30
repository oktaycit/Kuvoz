# Firefox Kiosk Alternative
# Chromium bulunamazsa Firefox kullan

.PHONY: firefox-install firefox-kiosk firefox-manual

# Firefox installation
firefox-install:
	@echo "🦊 Installing Firefox as Chromium alternative..."
	sudo apt update
	sudo apt install -y firefox-esr xorg xinit openbox unclutter
	@echo "✅ Firefox installed"

# Firefox kiosk mode
firefox-kiosk:
	@echo "🦊 Starting Firefox in kiosk mode..."
	@if command -v firefox-esr >/dev/null 2>&1; then \
		DISPLAY=:0 firefox-esr \
			--kiosk \
			--private-window \
			http://localhost:8000 & \
	elif command -v firefox >/dev/null 2>&1; then \
		DISPLAY=:0 firefox \
			--kiosk \
			--private-window \
			http://localhost:8000 & \
	else \
		echo "❌ Firefox not found!"; \
	fi

# Manual Firefox kiosk
firefox-manual:
	@echo "🦊 Starting manual Firefox kiosk..."
	@if command -v firefox-esr >/dev/null 2>&1; then \
		firefox-esr --kiosk --private-window http://localhost:8000 & \
	elif command -v firefox >/dev/null 2>&1; then \
		firefox --kiosk --private-window http://localhost:8000 & \
	else \
		echo "❌ Firefox not found!"; \
	fi

# Browser detection and automatic selection
auto-browser:
	@echo "🔍 Auto-detecting available browser..."
	@if command -v chromium >/dev/null 2>&1; then \
		echo "✅ Using Chromium"; \
		make kiosk-manual; \
	elif command -v chromium-browser >/dev/null 2>&1; then \
		echo "✅ Using Chromium Browser"; \
		make kiosk-manual; \
	elif command -v firefox-esr >/dev/null 2>&1; then \
		echo "✅ Using Firefox ESR"; \
		make firefox-kiosk; \
	elif command -v firefox >/dev/null 2>&1; then \
		echo "✅ Using Firefox"; \
		make firefox-kiosk; \
	else \
		echo "❌ No suitable browser found!"; \
		echo "Install with: make web-install or make firefox-install"; \
	fi

# Browser help
browser-help:
	@echo "🌐 Available Browser Options:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Primary (Chromium):"
	@echo "  make kiosk-manual   - Chromium kiosk"
	@echo "  make web-install    - Install Chromium"
	@echo ""
	@echo "Alternative (Firefox):"
	@echo "  make firefox-manual - Firefox kiosk"
	@echo "  make firefox-install- Install Firefox"
	@echo ""
	@echo "Auto-detection:"
	@echo "  make auto-browser   - Use any available browser"
	@echo "  make chromium-check - Check what's installed"
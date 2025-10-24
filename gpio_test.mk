# GPIO test and debug commands
.PHONY: test-gpio debug-gpio
test-gpio:
	@echo "🔌 GPIO test ediliyor..."
	@sudo python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setwarnings(False); outChannels=[5,6,13,16,19,20,21,26]; GPIO.setup(outChannels, GPIO.OUT); GPIO.output(outChannels, GPIO.HIGH); print('✅ GPIO setup OK'); GPIO.cleanup()" || echo "❌ GPIO test HATA"

debug-gpio:
	@echo "🔍 GPIO debug bilgileri..."
	@echo "1. GPIO cihaz durumu:"
	@ls -la /dev/gpiomem /dev/mem 2>/dev/null || echo "GPIO cihazları bulunamadı"
	@echo ""
	@echo "2. GPIO izinleri:"
	@groups | grep gpio && echo "✅ GPIO grup üyeliği OK" || echo "❌ GPIO grup üyeliği yok - sudo usermod -a -G gpio $$USER"
	@echo ""
	@echo "3. GPIO test:"
	@make test-gpio

# Quick GPIO test run
.PHONY: run-gpio-test
run-gpio-test:
	@echo "⚡ GPIO ile hızlı test çalıştırma..."
	@sudo timeout 10 python3 main3.py 1 && echo "✅ 10 saniye başarılı" || echo "⚠️  10 saniye timeout veya hata"

# Nebulizer test
.PHONY: test-nebulizer
test-nebulizer:
	@echo "🌊 Nebulizatör test modu..."
	@echo "Bu test otomatik nebulizatör fonksiyonunu gösterir:"
	@echo "- Oxygen sensör algılanamadığında"
	@echo "- 1 dakika çalışma, 10 dakika bekleme döngüsü"
	@echo "- b1 butonunda AUTO modu görünür"
	@echo ""
	@echo "Test için: make run-dht11"
	@echo "Oxygen sensör bağlı olmadığında nebulizatör otomatik başlar"

# Manual nebulizer control info
.PHONY: nebulizer-info
nebulizer-info:
	@echo "🌊 Nebulizatör Kontrol Sistemi"
	@echo "==============================="
	@echo ""
	@echo "📋 Otomatik Mod:"
	@echo "  • Oxygen sensör algılanamadığında otomatik başlar"
	@echo "  • 3 ardışık sensor hatası sonrası devreye girer"
	@echo "  • 1 dakika çalışma + 10 dakika bekleme döngüsü"
	@echo "  • b1 butonunda 'AUTO' modu görünür"
	@echo ""
	@echo "📋 Manuel Mod:"
	@echo "  • Oxygen sensör çalıştığında otomatik durur"
	@echo "  • b1 butonu normal toggle davranışı gösterir"
	@echo ""
	@echo "📋 Durum Göstergeleri:"
	@echo "  • Yeşil: Nebulizatör aktif (çalışıyor)"
	@echo "  • Sarı: Nebulizatör bekleme modunda"
	@echo "  • Beyaz: Manuel mod (kapalı)"
	@echo "  • Oxygen label'da 'AUTO' yazısı görünür"
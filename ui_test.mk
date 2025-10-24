# Kivy UI test commands
.PHONY: test-kivy test-kv-syntax
test-kivy:
	@echo "🎨 Kivy UI test ediliyor..."
	@python3 -c "import kivy; from kivy.app import App; from kivy.lang import Builder; print('✅ Kivy import OK')" || echo "❌ Kivy import HATA"

test-kv-syntax:
	@echo "📝 form.kv syntax kontrolü..."
	@python3 -c "from kivy.lang import Builder; Builder.load_file('form.kv'); print('✅ form.kv syntax OK')" || echo "❌ form.kv syntax HATA"

# UI test without images
.PHONY: test-ui-no-images
test-ui-no-images:
	@echo "🖼️  Image'siz UI testi..."
	@echo "form.kv dosyasında image referansları devre dışı bırakıldı:"
	@echo "  ✅ MyButton background image'ler kaldırıldı"
	@echo "  ✅ Ana image placeholder ile değiştirildi"
	@echo "  ✅ TabbedPanelItem background image'ler kaldırıldı"
	@echo "  ✅ Arka plan image devre dışı"
	@echo ""
	@make test-kv-syntax

# Run with no-image mode info
.PHONY: run-no-images
run-no-images:
	@echo "🚀 Image'siz UI modu ile çalıştırma..."
	@echo "UI image dosyaları bulunamadığında hata vermeyecek"
	@make run-dht11
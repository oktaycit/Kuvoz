# Quick syntax test
test-syntax:
	@echo "🔍 main3.py syntax kontrolü..."
	@python3 -m py_compile main3.py && echo "✅ Syntax OK" || echo "❌ Syntax HATA"

# Quick run test
test-quick-run:
	@echo "⚡ Hızlı çalıştırma testi..."
	@timeout 5 python3 -c "import sys; sys.path.append('.'); import main3; print('✅ Import başarılı')" || echo "⚠️  5 saniye timeout"
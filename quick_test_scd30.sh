#!/bin/bash
# SCD30 Hızlı Test Script'i - Raspberry Pi'de çalıştırın

echo "🧪 SCD30 CO2 Sensör Hızlı Test"
echo "======================================"
echo ""

# 1. I2C Kontrolü
echo "📡 1. I2C Bağlantı Kontrolü..."
if command -v i2cdetect &> /dev/null; then
    echo "   Beklenen: 0x61 adresi görünmeli"
    sudo i2cdetect -y 1 | grep -E "^60:"
    echo ""
else
    echo "   ⚠️  i2c-tools kurulu değil: sudo apt install i2c-tools"
    echo ""
fi

# 2. Python Paket Kontrolü
echo "📦 2. Python Paketleri Kontrolü..."
python3 -c "from sensirion_i2c_scd30 import Scd30Device; print('   ✅ sensirion-i2c-scd30: OK')" 2>/dev/null || echo "   ❌ sensirion-i2c-scd30: Eksik (pip3 install sensirion-i2c-scd30)"
python3 -c "from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider; print('   ✅ sensirion-driver-adapters: OK')" 2>/dev/null || echo "   ❌ sensirion-driver-adapters: Eksik"
echo ""

# 3. Test Script Çalıştır
echo "🔬 3. SCD30 Test Script'i Çalıştırılıyor..."
echo "   (İlk ölçüm 8-10 saniye sürer, sabırlı olun)"
echo ""
python3 test_scd30_sensor.py

echo ""
echo "======================================"
echo "✅ Test tamamlandı!"
echo ""
echo "📚 Sorun mu yaşıyorsunuz?"
echo "   → Troubleshooting: cat SCD30_TROUBLESHOOTING.md"
echo "   → Detaylı docs: cat README_SCD30.md"

#!/bin/bash
# Check SCD41 sensor status after restart

echo "🔍 SCD41 Sensor Status Check"
echo "=============================="
echo ""

# 1. Check I2C devices
echo "1. I2C Device Scan:"
echo "   SCD41 should be at address 0x62"
echo "   SCD30 would be at address 0x61"
echo ""
i2cdetect -y 1
echo ""

# 2. Check web server logs for CO2 sensor detection
echo "2. Web Server Logs (CO2 Sensor Detection):"
echo ""
sudo journalctl -u kuvoz-web -n 100 --no-pager | grep -E "CO2|SCD41|SCD30|sensor library" | tail -20
echo ""

# 3. Check if web server is running
echo "3. Service Status:"
systemctl is-active kuvoz-web && echo "   ✅ kuvoz-web: Running" || echo "   ❌ kuvoz-web: Stopped"
systemctl is-active kuvoz-kiosk && echo "   ✅ kuvoz-kiosk: Running" || echo "   ❌ kuvoz-kiosk: Stopped"
echo ""

# 4. Check port 8000
echo "4. Web Server Port:"
if sudo lsof -i:8000 > /dev/null 2>&1; then
    echo "   ✅ Port 8000 is in use"
    sudo lsof -i:8000 | grep -v COMMAND | awk '{print "   Process:", $1, "PID:", $2}'
else
    echo "   ❌ Port 8000 is not in use"
fi
echo ""

# 5. Show last errors
echo "5. Recent Errors (last 10):"
sudo journalctl -u kuvoz-web -p err -n 10 --no-pager | tail -15
echo ""

echo "=============================="
echo "✅ Status check complete!"
echo ""
echo "To view live logs: sudo journalctl -u kuvoz-web -f"

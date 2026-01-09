#!/bin/bash
# Quick debug for stuck web server

echo "🔍 Web Server Debug"
echo "==================="
echo ""

# 1. Stop service
echo "1. Stopping service..."
sudo systemctl stop kuvoz-web
sleep 2

# 2. Kill any remaining processes
echo "2. Cleaning up processes..."
sudo pkill -9 -f "python.*web_server"
sudo pkill -9 -f "eventlet"

# 3. Show last errors
echo ""
echo "3. Last service errors:"
sudo journalctl -u kuvoz-web -n 30 --no-pager | tail -20
echo ""

# 4. Try manual start to see error
echo "4. Starting manually to see error..."
echo "   (Press Ctrl+C to stop)"
echo ""
cd /home/vetma/kuvoz
python3 web_server.py 2>&1 | head -100

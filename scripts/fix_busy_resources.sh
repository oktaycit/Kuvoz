#!/bin/bash
# Fix busy resources (camera, ports) on Raspberry Pi

echo "🔍 Kuvoz - Resource Cleanup Script"
echo "=================================="
echo ""

# 1. Check and kill processes using port 8000
echo "1. Checking port 8000..."
PORT_PID=$(sudo lsof -ti:8000)
if [ ! -z "$PORT_PID" ]; then
    echo "   ⚠️  Port 8000 is used by PID: $PORT_PID"
    ps -p $PORT_PID -o comm=,args=
    read -p "   Kill this process? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo kill -9 $PORT_PID
        echo "   ✅ Process killed"
    fi
else
    echo "   ✅ Port 8000 is free"
fi

# 2. Check camera usage
echo ""
echo "2. Checking camera usage..."
CAM_PROCS=$(sudo lsof /dev/video* 2>/dev/null | grep -v "COMMAND")
if [ ! -z "$CAM_PROCS" ]; then
    echo "   ⚠️  Camera is in use:"
    echo "$CAM_PROCS"
    echo ""
    CAM_PIDS=$(sudo lsof /dev/video* 2>/dev/null | grep -v "COMMAND" | awk '{print $2}' | sort -u)
    for PID in $CAM_PIDS; do
        ps -p $PID -o comm=,args=
    done
    read -p "   Kill these processes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for PID in $CAM_PIDS; do
            sudo kill -9 $PID
        done
        echo "   ✅ Camera processes killed"
    fi
else
    echo "   ✅ Camera is free"
fi

# 3. Stop systemd services
echo ""
echo "3. Checking systemd services..."
if systemctl is-active --quiet kuvoz-web; then
    echo "   ⚠️  kuvoz-web service is running"
    read -p "   Stop it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl stop kuvoz-web
        echo "   ✅ kuvoz-web stopped"
    fi
else
    echo "   ✅ kuvoz-web is not running"
fi

# 4. Check Python processes
echo ""
echo "4. Checking Python processes..."
PYTHON_PROCS=$(ps aux | grep "python.*web_server" | grep -v grep)
if [ ! -z "$PYTHON_PROCS" ]; then
    echo "   ⚠️  Found web_server.py processes:"
    echo "$PYTHON_PROCS"
    read -p "   Kill these processes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -9 -f "python.*web_server"
        echo "   ✅ Python processes killed"
    fi
else
    echo "   ✅ No web_server.py processes found"
fi

# 5. Final status
echo ""
echo "=================================="
echo "✅ Cleanup complete!"
echo ""
echo "Now you can:"
echo "  • Run SCD41 test:  python3 test_scd41_sensor.py"
echo "  • Start web server: python3 web_server.py"
echo "  • Or enable service: sudo systemctl start kuvoz-web"

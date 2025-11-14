#!/bin/bash
# Kuvoz günlük bakım scripti

LOG_DIR="/home/oktay/kuvoz/logs"
CACHE_DIR="/home/oktay/kuvoz/chromium-data"

# Eski cache'i temizle (7 günden eski)
find "$CACHE_DIR" -type f -mtime +7 -delete 2>/dev/null

# Kiosk'u yeniden başlat (memory temizliği için)
systemctl restart kuvoz-kiosk

# Log
echo "$(date): Kuvoz maintenance completed" >> "$LOG_DIR/maintenance.log"

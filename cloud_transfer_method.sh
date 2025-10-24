#!/bin/bash
# Cloud Transfer Method - Raspberry Pi File Transfer
# SSH port sorunu varsa cloud storage üzerinden transfer

echo "☁️ Cloud Transfer Method"
echo "======================="

PROJECT_DIR="$(pwd)"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
ARCHIVE_NAME="kuvoz_project_${TIMESTAMP}.tar.gz"

echo "📁 Project directory: $PROJECT_DIR"
echo "📦 Archive name: $ARCHIVE_NAME"

# 1. Create archive
echo ""
echo "1️⃣ Creating project archive..."
tar -czf "$ARCHIVE_NAME" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='web_venv' \
    --exclude='backup' \
    *.py *.kv *.mk *.md *.sh Makefile lib/ web/ systemd/ 2>/dev/null

if [ -f "$ARCHIVE_NAME" ]; then
    echo "✅ Archive created: $ARCHIVE_NAME"
    echo "📊 Archive size: $(du -h $ARCHIVE_NAME | cut -f1)"
else
    echo "❌ Failed to create archive"
    exit 1
fi

# 2. Upload methods
echo ""
echo "2️⃣ Upload Methods:"
echo "=================="

echo "Method 1 - Google Drive:"
echo "• Upload $ARCHIVE_NAME to Google Drive"
echo "• Share link publicly or with Raspberry Pi account"
echo "• On Pi: wget 'https://drive.google.com/uc?id=FILE_ID' -O $ARCHIVE_NAME"

echo ""
echo "Method 2 - OneDrive:"
echo "• Upload to OneDrive"
echo "• Get sharing link"
echo "• On Pi: wget 'ONEDRIVE_LINK' -O $ARCHIVE_NAME"

echo ""
echo "Method 3 - Dropbox:"
echo "• Upload to Dropbox"
echo "• Get direct link"
echo "• On Pi: wget 'DROPBOX_LINK' -O $ARCHIVE_NAME"

echo ""
echo "Method 4 - File.io (temporary):"
echo "• curl -F 'file=@$ARCHIVE_NAME' https://file.io"
echo "• Get temporary download link"
echo "• On Pi: wget 'FILE_IO_LINK' -O $ARCHIVE_NAME"

echo ""
echo "Method 5 - WeTransfer:"
echo "• Upload via web interface"
echo "• Send download link to yourself"
echo "• Download on Raspberry Pi"

# 3. Raspberry Pi commands
echo ""
echo "3️⃣ Raspberry Pi Commands:"
echo "========================="
echo "# After downloading archive on Raspberry Pi:"
echo "cd /home/oktay"
echo "tar -xzf $ARCHIVE_NAME"
echo "mv kuvoz_project_* kuvoz  # or rename appropriately"
echo "cd kuvoz"
echo "chmod +x *.sh *.py"
echo "make web-deps-install"
echo "make web-platform-fix-full"

# 4. Quick upload to file.io
echo ""
echo "4️⃣ Quick Upload (file.io):"
echo "=========================="
echo "Uploading to file.io for quick transfer..."

if command -v curl >/dev/null 2>&1; then
    echo "Uploading..."
    UPLOAD_RESULT=$(curl -s -F "file=@$ARCHIVE_NAME" https://file.io)
    
    if echo "$UPLOAD_RESULT" | grep -q "success"; then
        DOWNLOAD_LINK=$(echo "$UPLOAD_RESULT" | grep -o '"link":"[^"]*' | cut -d'"' -f4)
        echo "✅ Upload successful!"
        echo "📥 Download link: $DOWNLOAD_LINK"
        echo ""
        echo "🔗 On Raspberry Pi, run:"
        echo "wget '$DOWNLOAD_LINK' -O $ARCHIVE_NAME"
        echo "tar -xzf $ARCHIVE_NAME"
    else
        echo "❌ Upload failed"
    fi
else
    echo "⚠️ curl not available for automatic upload"
fi

echo ""
echo "💡 Next Steps:"
echo "1. Upload $ARCHIVE_NAME to your preferred cloud service"
echo "2. Get download link"
echo "3. Download on Raspberry Pi using wget/curl"
echo "4. Extract and setup project"
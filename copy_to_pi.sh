#!/bin/bash
# Kuvoz Raspberry Pi Copy Script
# SCP ile dosyaları kopyalama

echo "🚀 Kuvoz Files -> Raspberry Pi"
echo "================================"

REMOTE_HOST="oktay@88.235.245.254"
REMOTE_PATH="/home/oktay/kuvoz"

echo "📡 Target: $REMOTE_HOST:$REMOTE_PATH"
echo ""

# SSH key fingerprint kabul et
export SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# Klasör oluştur
echo "📁 Creating remote directory..."
ssh $SSH_OPTS $REMOTE_HOST "mkdir -p $REMOTE_PATH"

# Ana dosyalar
echo "📄 Copying main files..."
scp $SSH_OPTS *.py $REMOTE_HOST:$REMOTE_PATH/
scp $SSH_OPTS *.kv $REMOTE_HOST:$REMOTE_PATH/
scp $SSH_OPTS Makefile $REMOTE_HOST:$REMOTE_PATH/
scp $SSH_OPTS *.mk $REMOTE_HOST:$REMOTE_PATH/
scp $SSH_OPTS *.md $REMOTE_HOST:$REMOTE_PATH/
scp $SSH_OPTS *.sh $REMOTE_HOST:$REMOTE_PATH/

# Klasörler
echo "📚 Copying lib folder..."
scp -r $SSH_OPTS lib/ $REMOTE_HOST:$REMOTE_PATH/

echo "🌐 Copying web folder..."
scp -r $SSH_OPTS web/ $REMOTE_HOST:$REMOTE_PATH/

echo "⚙️ Copying systemd folder..."
scp -r $SSH_OPTS systemd/ $REMOTE_HOST:$REMOTE_PATH/

echo "📜 Copying scripts folder..."
scp -r $SSH_OPTS scripts/ $REMOTE_HOST:$REMOTE_PATH/

echo "🔧 Copying config folder..."
scp -r $SSH_OPTS config/ $REMOTE_HOST:$REMOTE_PATH/ 2>/dev/null || echo "Config folder not found, skipping..."

# Executable permissions
echo "🔐 Setting permissions..."
ssh $SSH_OPTS $REMOTE_HOST "cd $REMOTE_PATH && chmod +x *.sh *.py"

echo ""
echo "✅ Copy completed!"
echo "🔗 Connect: ssh $REMOTE_HOST"
echo "📁 Project: cd kuvoz"
echo "🚀 Setup: make web-deps-install"
echo "🌐 Run: make web-platform-fix-full"
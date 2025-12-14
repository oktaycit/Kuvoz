# Kuvoz Firebase Setup Guide

## Quick Start

```bash
# 1. Install Firebase dependencies
make firebase-install

# 2. Get Firebase credentials from console
# Download kuvoz-firebase-key.json and save to config/

# 3. Test Firebase bridge
make firebase-start

# 4. Install as service (auto-start on boot)
make firebase-service

# 5. Check status
make firebase-status
make firebase-logs
```

## Firebase Console Setup

### 1. Create Firebase Project

1. Go to https://console.firebase.google.com/
2. Click "Add project"
3. Project name: `kuvoz-vet-system`
4. Disable Google Analytics (optional)
5. Click "Create project"

### 2. Enable Realtime Database

1. In Firebase Console, go to **Build** → **Realtime Database**
2. Click "Create Database"
3. Choose location (europe-west1 recommended for Turkey)
4. Start in **test mode** (we'll configure security rules later)
5. Click "Enable"
6. Note the database URL: `https://kuvoz-vet-system-default-rtdb.firebaseio.com/`

### 3. Get Service Account Credentials

1. Go to **Project Settings** (⚙️ icon)
2. Click **Service Accounts** tab
3. Click "Generate new private key"
4. Save the downloaded JSON file
5. Copy to Raspberry Pi:

```bash
# From your Mac
scp ~/Downloads/kuvoz-vet-system-*.json oktay@192.168.1.132:/home/oktay/kuvoz/config/kuvoz-firebase-key.json

# On Raspberry Pi
chmod 600 /home/oktay/kuvoz/config/kuvoz-firebase-key.json
```

### 4. Configure Security Rules

In Realtime Database → Rules tab, paste:

```json
{
  "rules": {
    "devices": {
      "$deviceId": {
        ".read": "auth != null",
        ".write": "auth != null",
        "sensors": {
          ".write": true
        },
        "status": {
          ".write": true
        }
      }
    }
  }
}
```

⚠️ **Note**: This allows device writes without authentication. For production, implement proper authentication.

### 5. Enable Authentication (Optional)

1. Go to **Build** → **Authentication**
2. Click "Get started"
3. Enable **Email/Password**
4. Enable **Google** sign-in (optional)

## Configuration

### Environment Variables (Optional)

Edit `systemd/kuvoz-firebase.service` to customize:

```ini
Environment="KUVOZ_DEVICE_ID=kuvoz1"
Environment="KUVOZ_DEVICE_NAME=Kuvoz Cage A"
Environment="KUVOZ_FIREBASE_URL=https://your-project.firebaseio.com/"
```

### Device Configuration

For multiple devices, create `config/device.conf`:

```bash
KUVOZ_DEVICE_ID="kuvoz1"
KUVOZ_DEVICE_NAME="Kuvoz Cage A"
```

## Makefile Commands

```bash
# Installation
make firebase-install        # Install Firebase Admin SDK

# Running
make firebase-start          # Start bridge manually
make firebase-stop           # Stop bridge
make firebase-restart        # Restart bridge

# Service Management
make firebase-service        # Install systemd service
sudo systemctl start kuvoz-firebase
sudo systemctl stop kuvoz-firebase
sudo systemctl restart kuvoz-firebase

# Monitoring
make firebase-status         # Check if running
make firebase-logs           # View logs (live)
sudo journalctl -u kuvoz-firebase -n 100  # Last 100 lines
```

## Testing

### 1. Test Firebase Connection

```bash
# Start bridge manually
make firebase-start

# Expected output:
# ✅ Firebase connected to https://...
# ✅ Device registered: Kuvoz Cage A
# ✅ Listening to commands from Firebase
# 🌡️ Sensor reading thread started
```

### 2. Check Firebase Console

1. Go to Realtime Database in Firebase Console
2. You should see:
```
devices/
  kuvoz1/
    info/
      name: "Kuvoz Cage A"
      lastSeen: 1702468800000
    sensors/
      temperature/
        value: 25.5
    status/
      online: true
```

### 3. Send Test Command

In Firebase Console, manually add:

```
devices/kuvoz1/commands/pending/test_cmd_123
{
  "type": "toggle_button",
  "data": {
    "button": "b1",
    "state": true
  },
  "timestamp": 1702468800000,
  "processed": false
}
```

Check logs:
```bash
make firebase-logs
# Should see: "Processing command: toggle_button"
```

## Troubleshooting

### Error: "Firebase credentials not found"

```bash
# Check if file exists
ls -la config/kuvoz-firebase-key.json

# If missing, download from Firebase Console
```

### Error: "Permission denied"

```bash
# Fix permissions
chmod 600 config/kuvoz-firebase-key.json
chown oktay:oktay config/kuvoz-firebase-key.json
```

### Error: "Module 'firebase_admin' not found"

```bash
# Reinstall Firebase SDK
make firebase-install
```

### Service won't start

```bash
# Check service status
sudo systemctl status kuvoz-firebase

# Check logs
sudo journalctl -u kuvoz-firebase -n 50

# Common issues:
# - Wrong Firebase URL in service file
# - Missing credentials file
# - Python path issues
```

## Integration with Web Server

Both services can run simultaneously:

```bash
# Start both
sudo systemctl start kuvoz-web
sudo systemctl start kuvoz-firebase

# Check both
make status-all
```

The web server uses Socket.IO for local control, Firebase bridge provides remote access via mobile app.

## Next Steps

1. ✅ Complete Firebase setup
2. ✅ Test bridge connection
3. ✅ Install as service
4. 🔄 Develop React Native mobile app
5. 🔄 Implement authentication
6. 🔄 Add multiple device support

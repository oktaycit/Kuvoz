# Kuvoz Configuration Directory

This directory contains sensitive configuration files that should NOT be committed to git.

## Required Files

### 1. Firebase Credentials

**File:** `kuvoz-firebase-key.json`

Download from Firebase Console:
1. Go to https://console.firebase.google.com/
2. Select your project
3. Project Settings → Service Accounts
4. Click "Generate new private key"
5. Save as `kuvoz-firebase-key.json` in this directory

```bash
# Set proper permissions
chmod 600 kuvoz-firebase-key.json
```

### 2. Device Configuration (Optional)

**File:** `device.conf`

```bash
KUVOZ_DEVICE_ID="kuvoz1"
KUVOZ_DEVICE_NAME="Kuvoz Cage A"
KUVOZ_FIREBASE_URL="https://your-project-default-rtdb.firebaseio.com/"
```

## Security

⚠️ **IMPORTANT**: Never commit `kuvoz-firebase-key.json` to git!

The `.gitignore` file in this directory prevents accidental commits.

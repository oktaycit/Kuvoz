# Kuvoz Configuration Directory

This directory contains configuration files for system setup and deployment.

## Files

### 1. authorized_keys.pub (SSH Public Key)

**File:** `authorized_keys.pub`
**Purpose:** Admin SSH public key for automatic deployment to new devices
**Usage:** Automatically used by `setup-new-device.sh` script

This file contains your SSH public key that will be installed on all new Kuvoz devices for passwordless access.

**Generate your key (if needed):**
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**Update this file:**
```bash
cat ~/.ssh/id_ed25519.pub > config/authorized_keys.pub
```

**Security Note:** Public keys are safe to commit to git. Private keys (`~/.ssh/id_ed25519`) should NEVER be committed.

### 2. Firebase Credentials

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

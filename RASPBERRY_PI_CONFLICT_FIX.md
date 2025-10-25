# Raspberry Pi Git Conflict Solution
# GPIO 22 Update and File Cleanup - October 25, 2025

## Problem
Raspberry Pi'de `git pull` yaparken local changes conflict:
```
error: Your local changes to the following files would be overwritten by merge:
        Failure.dat
        cloud_transfer_method.sh  
        copy_to_pi.sh
        git_transfer_method.sh
        main3.py
        test_gpio_basic.py
        troubleshoot_connection.sh
Please commit your changes or stash them before you merge.
```

## Solution Commands (Run on Raspberry Pi)

### Method 1: Stash and Pull (Recommended)
```bash
cd /path/to/Kuvoz
git stash push -m "Local changes before GPIO 22 update"
git pull origin web-interface
```

### Method 2: Hard Reset (If no important local changes)
```bash
cd /path/to/Kuvoz
git fetch origin web-interface
git reset --hard origin/web-interface
```

### Method 3: Force Pull (Alternative)
```bash
cd /path/to/Kuvoz
git fetch origin web-interface
git reset --hard FETCH_HEAD
```

## After Successful Pull

### Verify GPIO 22 Configuration
```bash
# Test GPIO 22 functionality
make gpio-basic-test

# Test DHT11 on GPIO 22
make dht11-simple-test

# Full DHT11 native test
make dht11-native-test

# Start web server (uses GPIO 22)
make web-run
```

### Verify File Cleanup
These files should be REMOVED after pull:
- ✅ Kivy files: form.kv, main2.py, main3.py
- ✅ Old tests: test_dht11.py, simple_test.py
- ✅ Copy scripts: copy_to_pi.sh
- ✅ Transfer methods: git_transfer_method.sh, cloud_transfer_method.sh
- ✅ Debug files: Failure.dat, troubleshoot_connection.sh

### Expected DHT11 Wiring (GPIO 22)
```
DHT11 Pin 1 (VCC) → Raspberry Pi Pin 1 (3.3V)
DHT11 Pin 2 (DATA) → Raspberry Pi Pin 15 (GPIO 22) ⚡ UPDATED
DHT11 Pin 4 (GND) → Raspberry Pi Pin 6 (GND)
```

## Quick Test Sequence
```bash
# 1. Pull updates
git stash && git pull origin web-interface

# 2. Test sequence
make gpio-basic-test      # Test GPIO 22
make dht11-simple-test    # Test DHT11 connection  
make dht11-native-test    # Test DHT11 readings
make web-run              # Start web interface

# 3. Access web interface
# http://raspberry-pi-ip:5000
```

## Commit Information
- Latest commit: 85edcfa
- Changes: DHT11 GPIO 15 → GPIO 22, removed 29 unnecessary files
- Branch: web-interface
- Date: October 25, 2025
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCD30 Firmware Version Check
"""

import time

print("🔍 SCD30 Firmware Version Check")
print("=" * 50)

try:
    from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider
    from sensirion_i2c_scd30 import Scd30Device
    print("✅ Kütüphaneler yüklendi")
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    exit(1)

try:
    provider = LinuxI2cChannelProvider('/dev/i2c-1')
    provider.__enter__()
    channel = provider.get_channel(slave_address=0x61, crc_parameters=None)
    scd30 = Scd30Device(channel)
    
    print("\n📋 Sensör Bilgileri:")
    print("-" * 50)
    
    # Firmware version
    try:
        major, minor = scd30.read_firmware_version()
        print(f"Firmware Version: v{major}.{minor}")
        
        if major == 4 and minor <= 2:
            print("   → Eski versiyon (v4.x) - stable")
        elif major == 3:
            print("   → v3.x - eski firmware")
        else:
            print(f"   → v{major}.{minor} - yeni firmware")
            
    except Exception as e:
        print(f"❌ Firmware version okunamadı: {e}")
    
    # Measurement interval
    try:
        interval = scd30.get_measurement_interval()
        print(f"Measurement Interval: {interval} saniye")
    except Exception as e:
        print(f"⚠️  Measurement interval okunamadı: {e}")
    
    # Auto-calibration status
    try:
        asc_status = scd30.get_auto_calibration_status()
        print(f"Auto-Calibration (ASC): {'Aktif' if asc_status else 'Kapalı'}")
    except Exception as e:
        print(f"⚠️  ASC status okunamadı: {e}")
    
    # Temperature offset
    try:
        temp_offset = scd30.get_temperature_offset()
        print(f"Temperature Offset: {temp_offset / 100:.2f}°C")
    except Exception as e:
        print(f"⚠️  Temp offset okunamadı: {e}")
    
    # Altitude compensation
    try:
        altitude = scd30.get_altitude_compensation()
        print(f"Altitude Compensation: {altitude} m")
    except Exception as e:
        print(f"⚠️  Altitude okunamadı: {e}")
    
    # Force recalibration status
    try:
        frc_value = scd30.get_force_recalibration_status()
        print(f"Force Recalibration Value: {frc_value} ppm")
    except Exception as e:
        print(f"⚠️  FRC value okunamadı: {e}")
    
    print("\n" + "=" * 50)
    print("📝 Öneriler:")
    print("-" * 50)
    
    # v5 için özel öneriler
    print("SCD30 v5 için:")
    print("  1. Measurement interval: 5-10 saniye (2 saniye yerine)")
    print("  2. İlk okuma: 20-30 saniye warm-up")
    print("  3. Auto-calibration: Kapalı olmalı (tutarlılık için)")
    print("  4. Soft reset sonrası 2 saniye bekle")
    
    provider.__exit__(None, None, None)
    
except Exception as e:
    print(f"\n❌ Hata: {e}")
    import traceback
    traceback.print_exc()

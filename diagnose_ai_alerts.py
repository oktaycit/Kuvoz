#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Alert Diagnostic Tool - Kuvoz
AI alert sisteminin neden log almadığını teşhis eder
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Renkli output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_status(check, status, details=""):
    icon = "✅" if status else "❌"
    color = Colors.GREEN if status else Colors.RED
    print(f"{icon} {color}{check}{Colors.END}")
    if details:
        print(f"   {details}")

def check_data_directory():
    """data/ klasörü var mı?"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    exists = os.path.exists(data_dir)
    print_status("data/ klasörü mevcut", exists)
    if exists:
        files = os.listdir(data_dir)
        print(f"   İçerik: {files}")
    return exists

def check_ai_vitals_db():
    """AI vitals veritabanı var mı?"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ai_vitals.db')
    exists = os.path.exists(db_path)
    print_status("ai_vitals.db mevcut", exists)
    
    if exists:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ai_vital_readings")
            count = cursor.fetchone()[0]
            print(f"   Kayıt sayısı: {count}")
            
            if count > 0:
                cursor.execute("""
                    SELECT timestamp, patient_name, status, respiration_bpm, confidence
                    FROM ai_vital_readings
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)
                print(f"   {Colors.YELLOW}Son 5 kayıt:{Colors.END}")
                for row in cursor.fetchall():
                    print(f"     {row[0]} | {row[1] or '-'} | {row[2]} | {row[3]} BPM | {row[4]}")
            
            conn.close()
            return count > 0
        except Exception as e:
            print(f"   {Colors.RED}DB okuma hatası: {e}{Colors.END}")
            return False
    else:
        print(f"   {Colors.YELLOW}Veritabanı yok - AI hiç veri kaydetmemiş{Colors.END}")
        return False

def check_ai_module():
    """AI modülü import edilebiliyor mu?"""
    try:
        from lib.ai.manager import AIManager
        print_status("AI Manager import edilebilir", True)
        
        from lib.ai.vision import VisionEngine, PICAMERA2_AVAILABLE, OPENCV_AVAILABLE
        print_status("VisionEngine import edilebilir", True)
        print(f"   Picamera2: {PICAMERA2_AVAILABLE}")
        print(f"   OpenCV: {OPENCV_AVAILABLE}")
        
        return True
    except ImportError as e:
        print_status("AI Manager import edilebilir", False, str(e))
        return False

def check_web_server_ai_config():
    """web_server.py AI config'i"""
    try:
        # web_server.py'den AI_AVAILABLE'ı kontrol et
        import importlib.util
        spec = importlib.util.spec_from_file_location("web_server", "web_server.py")
        # Module'ü load etmeden sadece source'u oku
        with open('web_server.py', 'r') as f:
            content = f.read()
            
        ai_available = 'AI_AVAILABLE = True' in content or 'AI_AVAILABLE = False' in content
        
        if ai_available:
            # AI_AVAILABLE'ın değerini bul
            import re
            match = re.search(r'AI_AVAILABLE\s*=\s*(True|False)', content)
            if match:
                value = match.group(1)
                print_status("AI_AVAILABLE", value == 'True', f"AI_AVAILABLE = {value}")
        else:
            print_status("AI_AVAILABLE tanımı", False)
            
        return ai_available
    except Exception as e:
        print_status("web_server.py AI config", False, str(e))
        return False

def check_camera_device():
    """Camera device mevcut mu? (Raspberry Pi'de)"""
    video_devices = []
    for i in range(4):
        device = f'/dev/video{i}'
        if os.path.exists(device):
            video_devices.append(device)
    
    if video_devices:
        print_status("Camera device mevcut", True, f"{video_devices}")
        return True
    else:
        print_status("Camera device mevcut", False, "/dev/video* bulunamadı")
        print(f"   {Colors.YELLOW}Kamera bağlı değil veya sürücü yüklü değil{Colors.END}")
        return False

def analyze_ai_logs():
    """Son AI loglarını kontrol et"""
    log_files = [
        '/var/log/kuvoz-web.log',
        'kuvoz_web.log',
        'web_server.log'
    ]
    
    found_logs = False
    for log_file in log_files:
        if os.path.exists(log_file):
            found_logs = True
            print(f"\n{Colors.YELLOW}📄 {log_file} dosyasından son AI logları:{Colors.END}")
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    ai_lines = [l for l in lines if 'AI' in l or 'ai_' in l][-20:]
                    for line in ai_lines:
                        print(f"  {line.strip()}")
            except Exception as e:
                print(f"  {Colors.RED}Okuma hatası: {e}{Colors.END}")
            break
    
    if not found_logs:
        print(f"\n{Colors.YELLOW}⚠️  Log dosyası bulunamadı{Colors.END}")

def main():
    print_header("🤖 KUVOZ AI ALERT DIAGNOSTIC")
    print(f"⏰ Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_header("1️⃣  Dosya Sistemi Kontrolü")
    check_data_directory()
    db_has_data = check_ai_vitals_db()
    
    print_header("2️⃣  AI Modül Kontrolü")
    ai_importable = check_ai_module()
    check_web_server_ai_config()
    
    print_header("3️⃣  Hardware Kontrolü")
    check_camera_device()
    
    print_header("4️⃣  Log Analizi")
    analyze_ai_logs()
    
    print_header("📊 SONUÇLAR VE ÖNERİLER")
    
    if not db_has_data:
        print(f"{Colors.RED}❌ PROBLEM: AI veritabanı boş veya yok!{Colors.END}")
        print("\nOlası nedenler:")
        print("  1. AI modülü UI'dan enable edilmemiş")
        print("  2. Kamera başlatılamamış (hardware/driver sorunu)")
        print("  3. Kedi kamera görüş alanına girmiyor")
        print("  4. AI logging disabled")
        
        print("\nÇözüm önerileri:")
        print(f"  {Colors.GREEN}✓{Colors.END} Web UI'da AI'ı enable edin")
        print(f"  {Colors.GREEN}✓{Colors.END} Kamera bağlantısını kontrol edin")
        print(f"  {Colors.GREEN}✓{Colors.END} Kamera açısını ayarlayın (kedi görünmeli)")
        print(f"  {Colors.GREEN}✓{Colors.END} Web server loglarını kontrol edin:")
        print("      journalctl -u kuvoz-web -f")
        print("      veya")
        print("      make logs-web")
    else:
        print(f"{Colors.GREEN}✅ AI veritabanı aktif ve kayıt yapıyor!{Colors.END}")
    
    print()

if __name__ == '__main__':
    main()

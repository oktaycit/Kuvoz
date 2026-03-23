#!/bin/bash
# AI Vitals Database Fix - Kuvoz
# Boş/bozuk veritabanını düzeltir

set -e

DB_PATH="data/ai_vitals.db"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 AI Vitals Database Fix"
echo "========================="
echo ""

cd "$SCRIPT_DIR"

# 1. Mevcut veritabanını kontrol et
if [ ! -f "$DB_PATH" ]; then
    echo "✅ Veritabanı yok - yeni oluşturulacak"
else
    echo "📄 Mevcut veritabanı bulundu: $DB_PATH"
    
    # Tablo var mı kontrol et
    TABLES=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "")
    
    if [ -z "$TABLES" ]; then
        echo "⚠️  Veritabanı boş (tablo yok) - yeniden oluşturuluyor..."
        rm -f "$DB_PATH"
        echo "✅ Eski veritabanı silindi"
    else
        echo "✅ Veritabanı tabloları mevcut"
        echo "   Tablolar: $TABLES"
        
        # Kayıt sayısı
        COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM ai_vital_readings;" 2>/dev/null || echo "0")
        echo "   Kayıt sayısı: $COUNT"
        
        if [ "$COUNT" -eq 0 ]; then
            echo "⚠️  Veritabanı boş (kayıt yok) - AI hiç kayıt yapmamış"
        fi
    fi
fi

echo ""
echo "🧪 Test ediliyor..."

# Python ile test (project dizininden çalıştır)
cd "$SCRIPT_DIR/.."
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/vet/kuvoz')

from lib.data.ai_vitals_logger import AIVitalsLogger
import sqlite3
import os

db_path = "data/ai_vitals.db"

try:
    # Logger oluştur
    logger = AIVitalsLogger(db_path=db_path, min_interval=10, heartbeat_interval=60)
    print("✅ AIVitalsLogger oluşturuldu")
    
    # Tablo kontrolü
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"📊 Tablolar: {[t[0] for t in tables]}")
    
    # Kayıt sayısı
    cursor.execute("SELECT COUNT(*) FROM ai_vital_readings;")
    count = cursor.fetchone()[0]
    print(f"📈 Kayıt sayısı: {count}")
    
    conn.close()
    
    # Test kaydı ekle
    print("")
    print("📝 Test kaydı ekleniyor...")
    
    test_ai_data = {
        'vitals': {
            'status': 'OK',
            'respiration_bpm': 25.0,
            'confidence': 0.85,
            'method': 'test'
        },
        'vision': {
            'status': 'HAREKETSIZ',
            'activity': 0.12
        }
    }
    
    test_patient = {
        'id': 'test_patient',
        'name': 'Test Hasta',
        'species': 'Kedi'
    }
    
    logged = logger.log_if_changed(test_ai_data, patient_context=test_patient)
    
    if logged:
        print("✅ Test kaydı başarıyla eklendi!")
    else:
        print("⚠️  Test kaydı eklenmedi (change detection)")
    
    # Son durum
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ai_vital_readings;")
    final_count = cursor.fetchone()[0]
    print(f"📊 Son kayıt sayısı: {final_count}")
    
    if final_count > 0:
        cursor.execute("""
            SELECT timestamp, patient_name, status, respiration_bpm, confidence 
            FROM ai_vital_readings 
            ORDER BY timestamp DESC 
            LIMIT 3
        """)
        print("")
        print("📈 Son 3 kayıt:")
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} BPM | {row[4]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

echo ""
echo "✅ AI Vitals Database Fix tamamlandı!"
echo ""
echo "📋 Sonraki adımlar:"
echo "  1. Web server'ı yeniden başlat: sudo systemctl restart kuvoz-web"
echo "  2. Logları izle: journalctl -u kuvoz-web -f | grep 'AI vital'"
echo "  3. Kayıt sayısını kontrol et: make ai-db-status"

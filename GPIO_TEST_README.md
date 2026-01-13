# GPIO Test Aracı - Kullanım Kılavuzu

## 📖 Hızlı Başlangıç

GPIO pinlerini hızlıca test etmek için tasarlanmış basit bir araç.

## 🚀 Kullanım

### Doğrudan Python ile:
```bash
sudo python3 gpio_test.py -test <PIN_NO> <on|off>
```

### Makefile ile (Önerilen):
```bash
make gpio-test PIN=<PIN_NO> STATE=<on|off>
```

## 📝 Örnekler

### GPIO 12'yi açma (Soğutma sistemi):
```bash
# Python ile
sudo python3 gpio_test.py -test 12 on

# Makefile ile
make gpio-test PIN=12 STATE=on
```

### GPIO 12'yi kapatma:
```bash
# Python ile
sudo python3 gpio_test.py -test 12 off

# Makefile ile
make gpio-test PIN=12 STATE=off
```

### Diğer pin örnekleri:
```bash
# Fan'ı aç (GPIO 20)
make gpio-test PIN=20 STATE=on

# Nebulizer'ı kapat (GPIO 6)
make gpio-test PIN=6 STATE=off

# UV Sterilizasyon'u aç (GPIO 21)
make gpio-test PIN=21 STATE=on
```

## 🔌 Pin Eşleştirmeleri

| GPIO Pin | Fonksiyon |
|----------|-----------|
| GPIO5 | Terapötik Aydınlatma (b1) |
| GPIO6 | Nebulizer (b2) |
| GPIO13 | Nemlendirici (b3) |
| GPIO16 | Karbon Isıtıcı (b4) |
| GPIO19 | IR Isıtıcı (b5) |
| GPIO20 | Fan (b6) |
| GPIO21 | UV Sterilizasyon (b7) |
| GPIO26 | Ozon (b8) |
| GPIO12 | Soğutma (b9) |

## 💡 Önemli Notlar

### Röle Mantığı
- **ON komutu** → GPIO LOW → Röle AÇIK ✅
- **OFF komutu** → GPIO HIGH → Röle KAPALI ❌

### Güvenlik
- Komut çalıştırıldığında GPIO durumu değiştirilir
- Pin durumu kalıcıdır (script bittiğinde sıfırlanmaz)
- Güvenli durum için manuel olarak OFF yapın

### Doğrulama
- Her komut sonrası GPIO okuması yapılır
- Beklenen değerle karşılaştırılır
- ✅ başarılı, ❌ hatalı olarak gösterilir

## 🔍 Detaylı Test İçin

Daha kapsamlı testler için mevcut araçları kullanın:

```bash
# Uzun süreli toggle testi
sudo python3 test_gpio12.py 12 5 3

# Donanım teşhis
sudo python3 diagnose_gpio12.py
```

## ❓ Yardım

Komut satırından yardım almak için:

```bash
# Python script yardımı
sudo python3 gpio_test.py
sudo python3 gpio_test.py -h

# Makefile yardımı
make gpio-test
make help
```

## 🐛 Sorun Giderme

### "HATA: Geçersiz durum"
- Durum sadece 'on' veya 'off' olabilir
- Küçük/büyük harf duyarlı değil

### "HATA: Pin numarası sayı olmalı"
- Pin numarasını doğru girdiğinizden emin olun
- BCM numaralandırması kullanılıyor

### "Permission denied"
- `sudo` ile çalıştırmayı unutmayın
- GPIO erişimi root yetkileri gerektirir

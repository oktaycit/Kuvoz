# SCD30 CO2 Sensörü Entegrasyonu (Sensirion)

Bu doküman, SCD30 CO2 sensörünü Kuvoz sistemine donanımsal ve yazılımsal olarak eklemek için gereken adımları içerir.

## Donanım Bağlantıları (Raspberry Pi)

- Besleme: `3V3` (önerilen) veya `5V`
- Toprak: `GND`
- I2C SDA: `GPIO2` (Pin 3)
- I2C SCL: `GPIO3` (Pin 5)
- Adres: `0x61`

Notlar:
- I2C hatlarında dahili pull-up dirençler kullanılır; ek direnç gerekmez.
- Kabloları kısa tutun ve doğru pinlere bağlayın.

## Sistem Konfigürasyonu

I2C arayüzünü etkinleştirin:

```bash
sudo raspi-config nonint do_i2c 0
sudo reboot
```

Cihazı doğrulayın:

```bash
sudo i2cdetect -y 1
# Çıktıda 0x61 görülmelidir
```

## Gerekli Paketler

**Önemli:** SCD30 sensörü için `sensirion-i2c-scd30` paketi kullanılmalıdır. `sensirion-i2c-scd` paketi SCD40/41 sensörleri içindir ve SCD30 ile uyumlu değildir.

Aşağıdaki Python paketleri gereklidir:
- `sensirion-i2c-driver`
- `sensirion-i2c-scd30` (SCD30 özel)
- `smbus2`

Kurulum (sistem Python):

```bash
pip3 install sensirion-i2c-driver sensirion-i2c-scd30 smbus2 --break-system-packages
```

Makefile ile:

```bash
make deps-scd30
```

## Yazılım Entegrasyonu

Backend (`web_server.py`) SCD30 desteği ile güncellendi:
- CO2 için feature-flag: `co2_available`
- Sensör başlatma: I2C Bus 1, adres `0x61`
- Okuma: `self.sensor_data['co2'] = { value: 'PPM', status: 'OK' }`
- WebSocket payload: `sensor_update` içinde `co2` alanı opsiyonel olarak gelir

Önemli:
- Şu an UI'da CO2 kartı gösterilmez; backend verisi hazır. İstenirse `web/index.html` ve `web/script.js` içinde benzer bir kart eklenebilir.

## Hızlı Test

1) Bağımlılıkları kurun:

```bash
make deps-scd30
```

2) Sensörü test edin:

```bash
make test-scd30
```

Beklenen çıktı yaklaşık şöyle olmalıdır:

```
✅ SCD30 kütüphaneleri import edildi
✅ SCD30 sensörü başlatıldı
🔍 Ölçüm: CO2= 600 ppm, T= 24.1 °C, RH= 53.2 %
```

3) Web sunucusunu çalıştırın ve değerleri takip edin:

```bash
make web-start
```

## Sorun Giderme

- `i2cdetect` 0x61 göstermiyorsa: bağlantıları kontrol edin, I2C etkin mi, kullanıcı `i2c` grubunda mı.
- Import hatası: `make deps-scd30` çalıştırın; internet bağlantınızı doğrulayın.
- Ölçüm gelmiyor: SCD30 ilk ölçümü için ~2s gerekir; backend döngüsü 5s aralıklarla okur.


# Kuvoz Saha Kurulum Rehberi

Bu rehber teknisyenin klinikte cihazı kurarken güç, Wi-Fi ve Tailscale adımlarını hızlı doğrulaması için hazırlanmıştır.

## Hızlı Kontrol

Raspberry Pi üzerinde:

```bash
cd ~/kuvoz
make field-check
```

Web arayüzünden:

```text
Ana Ekran -> Saha Kurulum
```

Kontrol sonucu `HATA` ise cihaz teslim edilmeden önce sorun kapatılmalıdır. `UYARI` varsa cihaz çalışabilir, fakat aksiyon sahada not alınmalı ve mümkünse çözülmelidir.

## 1. Güç ve Undervoltage

Sahadaki en kritik sorun düşük voltajdır. Raspberry Pi bunu `vcgencmd get_throttled` ile bildirir.

Beklenen çıktı:

```bash
throttled=0x0
```

Sorunlu çıktılar:

```bash
throttled=0x1      # anlık undervoltage
throttled=0x50000  # geçmişte undervoltage + throttle
```

Teknisyen aksiyonu:

- 5V 3A kaliteli adaptör kullan.
- İnce veya uzun USB kabloyu değiştir.
- Mümkünse kısa ve kalın, 24AWG veya daha iyi kablo kullan.
- Röle, fan, kamera ve sensörler aktifken tekrar `make field-check` çalıştır.
- Sorun devam ederse güç dağıtımını ve sensörlerin 3.3V yükünü kontrol et.

Kurulum tamamlandı sayılması için:

- Anlık undervoltage olmamalı.
- Cihaz yük altındayken 10 dakika sonra tekrar kontrol temiz olmalı.

## 2. Wi-Fi

Kuvoz sahada en güvenilir şekilde 2.4 GHz ağ ile kullanılmalıdır. Raspberry Pi Zero 2 W, 5 GHz ağları görmez.

Web adımı:

```text
Ana Ekran -> Saha Kurulum -> Wi-Fi Kur
```

Kontrol edilecekler:

- SSID doğru seçildi.
- IP adresi alındı.
- Sinyal tercihen %50 üzeri.
- DNS ve internet kontrolü başarılı.

Sorun giderme:

- 5 GHz yerine 2.4 GHz ağ kullan.
- Şifreyi tekrar gir.
- Klinik ağında captive portal varsa önce tarayıcıdan giriş yap.
- Hızlı doğrulama için telefon hotspot kullan.
- IP alınmıyorsa modem DHCP ayarını kontrol et.

## 3. Tailscale

Tailscale kurulumu web arayüzünden QR kod ile yapılmalıdır.

Web adımı:

```text
Ana Ekran -> Saha Kurulum -> Tailscale
```

Komut satırı alternatifi:

```bash
make tailscale-install
make tailscale-up
make tailscale-status
```

Başarılı durumda `make field-check` Tailscale IP adresini gösterir:

```text
Tailscale bagli: 100.x.x.x
```

Tailscale giriş/onay bekliyorsa:

- Uzaktan Erişim sayfasında `Bağlantı Kur` butonuna bas.
- QR kodu telefonla okut.
- Tailscale hesabında cihazı onayla.
- Paylaşım gerekiyorsa Tailscale admin panelinden cihazı ilgili e-posta ile paylaş.

## 4. Teslim Öncesi Mini Checklist

- [ ] `make field-check` çalıştırıldı.
- [ ] Güç/undervoltage kontrolünde anlık hata yok.
- [ ] Wi-Fi bağlı ve IP adresi var.
- [ ] İnternet/DNS çalışıyor.
- [ ] Tailscale bağlı ve `100.x.x.x` IP adresi görünüyor.
- [ ] `kuvoz-web` servisi aktif.
- [ ] Dokunmatik/kiosk kullanılacaksa `kuvoz-kiosk` servisi aktif.
- [ ] Klinik yetkilisine erişim adresi verildi: `http://CIHAZ_IP:8000` veya `http://TAILSCALE_IP:8000`.

## Sahada Kullanılacak Kısa Komutlar

```bash
make field-check
make tailscale-status
make status-all
sudo journalctl -u kuvoz-web -n 80
vcgencmd get_throttled
vcgencmd measure_temp
hostname -I
```

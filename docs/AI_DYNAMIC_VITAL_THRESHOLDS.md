# AI Dinamik Vital Eşikleri - Kullanım Kılavuzu

Bu doküman, kamerada hayvan algılandığında üretilen `vital` değişim raporlarında kullanılan **dinamik eşik** sisteminin kullanımını açıklar.

## Amaç

`vital` değişim rapor eşiğini, hayvanın:

- türü (`species`)
- cinsi (`breed`)
- yaşı (`age`)
- kilosu (`weight`)

bilgilerine göre otomatik ayarlamak.

## Çalışma Mantığı

1. Hasta bilgisi frontend'de (`currentPatient`) tutulur.
2. WebSocket ile backend'e `update_patient_context` olayı gönderilir.
3. Backend bu bilgiyi `AIManager.set_patient_context(...)` ile AI modülüne aktarır.
4. `AIManager._get_dynamic_thresholds()` dinamik eşikleri hesaplar.
5. Vital değişim raporu bu eşiklere göre üretilir.

## Nerede Kullanılır

- `web/patient_info.html`: Hasta kaydetme/yükleme sırasında context gönderir.
- `web/script.js`: Socket bağlanınca mevcut hasta context'ini backend'e gönderir.
- `web/alerts.html`: Alerts sayfası açıldığında context gönderir.
- `web_server.py` / `web_server_remote.py`: `update_patient_context` event'ini işler.
- `lib/ai/manager.py`: Dinamik eşik hesaplama ve vital raporlama.

## Kullanım Adımları

1. `Hasta Bilgileri` sayfasına girin (`patient_info.html`).
2. En az şu alanları doldurun:
   - Tür
   - Cins
   - Yaş
   - Ağırlık (önerilir)
3. `Bilgileri Kaydet` butonuna basın.
4. AI aktifse (`alerts` veya ana sayfa AI paneli), yeni eşikler otomatik uygulanır.

## WebSocket Mesajı (Frontend -> Backend)

```json
{
  "name": "Minnos",
  "species": "Kedi",
  "breed": "Tekir",
  "age": "2 yil 3 ay",
  "weight": "3.8"
}
```

Event adı:

- `update_patient_context`

## Eşik Örnekleri

Temel varsayılanlar:

- `bpm_delta`: `4.0`
- `confidence_delta`: `0.20`
- `cooldown_seconds`: `8.0`

Profil bazlı örnek ayarlamalar:

- Kedi: daha hassas (`bpm_delta` düşer)
- Köpek: kiloya göre değişir (küçük ırk daha hassas, büyük ırk daha toleranslı)
- Kuş/tavşan/kemirgen: daha hassas eşikler
- Bazı brakiosefalik cinsler: daha hassas eşikler

## Kalıcılık

Hasta context bilgisi ayarlara kaydedilir:

- `failure.dat` içinde `patient_context` alanı

Sistem yeniden başlasa da son hasta context'i yüklenir.

## Doğrulama

Backend loglarında aşağıdaki satırı görmelisiniz:

```text
Patient context updated: species=..., breed=..., age=..., weight=...
```

Ardından AI loglarında vital değişim raporları yeni eşiklerle üretilir.

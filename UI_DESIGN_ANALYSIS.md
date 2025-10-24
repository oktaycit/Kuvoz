# Kuvoz İnkübatör Ekran Tasarımı Analizi

## Genel Tasarım Mimarisi

### Ana Yapı
- **Framework**: Kivy 2.1.0
- **Ana Container**: `TabbedPanel` (Sol üst sekme düzeni)
- **Sekme Boyutları**: 60px genişlik × 30px yükseklik
- **Sekme Sayısı**: 2 adet (Home, Settings)

## Özel Widget Tanımları

### MyLabel (Özel Etiket)
```kv
<MyLabel@Label>:
    font_size: "12sp"
    markup: True
    valign: "top"
```

### MyButton (Özel Buton)
```kv
<MyButton@ToggleButton>:
    border: 4,4,4,4
    on_press: root.buttonChange()
```
- **Tip**: ToggleButton (açık/kapalı durumlu)
- **Kenarlık**: 4px tüm kenarlar
- **Olay**: Basıldığında `buttonChange()` metodu çalışır

### MySlider (Özel Kaydırıcı)
```kv
<MySlider@Slider>:
    orientation: 'vertical'
    value_track: True
    value_track_color: 0, 1, 0, 1  # Yeşil iz
    padding: 0
```
- **Yön**: Dikey
- **İz Rengi**: Yeşil (RGB: 0,1,0)

## Ana Ekran (Home Tab) Düzeni

### Düzen Hiyerarşisi
```
AnaEkran (TabbedPanel)
└── TabbedPanelItem "Home"
    └── BoxLayout (vertical)
        ├── GridLayout (8 sütun) - Kontrol Butonları
        ├── GridLayout (5 sütun) - Kaydırıcılar ve Etiketler  
        └── BoxLayout - Görüntü ve Sensör Verileri
```

### 1. Kontrol Butonları Bölgesi

#### Düzen Özellikleri
- **Sütun Sayısı**: 8
- **Padding**: 60px (sol/sağ), 30px (üst), 60px (sağ), 0px (alt)
- **Spacing**: 15px (yatay), 0px (dikey)

#### Buton Haritası
| Pozisyon | ID | GPIO Pin | Fonksiyon | Etiket |
|----------|----|---------|-----------| -------|
| 1 | b1 | 5 | Lighting | "Lighting" |
| 2 | b2 | 6 | Nebulizer | "Neb" |
| 3 | b3 | 13 | Humidity Control | "Hum" |
| 4 | b4 | 16 | Carbon Heater | "Carbon\nTemp" |
| 5 | b5 | 19 | IR Heater | "ir\nTemp" |
| 6 | b6 | 20 | Fan | "Fan" |
| 7 | b7 | 21 | UV Lighting | "UV\nLighting" |
| 8 | b8 | 26 | Ozone Generator | "Ozon" |

### 2. Kaydırıcılar ve Ayar Etiketleri

#### Düzen Özellikleri
- **Sütun Sayısı**: 5 (kaydırıcı) + 5 (etiket) = 10 toplam
- **Padding**: 80px (sol/sağ), 0px (üst/alt)
- **Spacing**: 40px (yatay), 0px (dikey)

#### Kaydırıcı Konfigürasyonu
| ID | Min | Max | Step | Birim | Fonksiyon | Dinamik Etiket |
|----|-----|-----|------|-------|-----------|----------------|
| sld1 | 1 | 60 | 1 | dakika | Nebulizer ON süresi | `"Neb \n {:d} min"` |
| sld2 | 20 | 60 | 1 | %rH | Nem hedefi | `"Hum\n%{:d}rH"` |
| sld3 | 20 | 40 | 0.1 | °C | Sıcaklık hedefi | `"Temp\n{:2.1f}°C"` |
| sld4 | 20 | 40 | 0.1 | °C | IR Sıcaklık hedefi | `"irTemp\n{:2.1f}°C"` |
| sld5 | 1 | 60 | 1 | dakika | Ozon ON süresi | `"Ozon\n{:d} min"` |

### 3. Sensör Verileri ve Görsel Bölgesi

#### Düzen Özellikleri
- **Padding**: 80px sol kenar
- **Bileşenler**: Görsel + 3 Sensör Etiketi + Kontrol Paneli

#### Görsel Öğeler
```kv
Image:
    source: '/home/pi/Pictures/Images/antalyaKafes.jpg'
```

#### Sensör Etiketleri
| ID | Renk | Font Boyutu | Format | Sensör Tipi |
|----|------|-------------|---------|-------------|
| hum_label | Yeşil (0,1,0,1) | 45sp | `"%%%drH"` | Nem |
| oxygen_label | Kırmızı (1,0,0,1) | 25sp | `"%2.2f%%"` | Oksijen |
| temp_label | Cyan (0.1,0.9,0.9,1) | 45sp | `"%2.1f°C"` | Sıcaklık |

#### Kontrol Paneli (FloatLayout)
```kv
Label (anydeskid_lbl):
    size_hint: .2, .2
    pos: 170, 5
    
Button (clsBtn):
    text: "Close"
    size_hint: None, .2
    pos: 700, 5
    on_press: root.cikis()
```

## Ayarlar Ekranı (Settings Tab)

### Düzen Özellikleri
- **Renk**: Yeşil arka plan (0,1,0,1)
- **Sütun Sayısı**: 2
- **Padding**: 80px tüm kenarlar
- **Spacing**: 40px yatay, 0px dikey

### Gelişmiş Ayarlar
| ID | Min | Max | Step | Birim | Fonksiyon | Dinamik Etiket |
|----|-----|-----|------|-------|-----------|----------------|
| sld6 | 1 | 60 | 1 | dakika | Nebulizer OFF süresi | `"Neb Interval \n{:02d} min"` |
| sld7 | 0.25 | 15 | 0.25 | saat | Ozon OFF süresi | `"Ozon interval\n{:2.2f} hours"` |

## Renk Şeması

### Durum Renkleri (Python kodundan)
- **Aktif Röle**: Yeşil `[0,1,0,1]`
- **Pasif Röle**: Beyaz `[1,1,1,1]`
- **Ana Ekran**: Kırmızı arka plan `1,0,0,1`
- **Ayarlar Ekranı**: Yeşil arka plan `0,1,0,1`

### Sensör Renkleri
- **Nem**: Yeşil `(0,1,0,1)`
- **Sıcaklık**: Cyan `(0.1,0.9,0.9,1)`
- **Oksijen**: Kırmızı `(1,0,0,1)`

## Kullanıcı Etkileşimi

### Kaydırıcı Olayları
- **on_value**: Kaydırıcı değeri değiştiğinde etiket güncellenir
- **Anlık Güncelleme**: Slider hareket ederken gerçek zamanlı güncelleme

### Buton Olayları
- **on_press**: Her buton basımında `buttonChange()` metodu tetiklenir
- **Durum Değişimi**: Toggle butonlar açık/kapalı durumunu korur

### Sistem Kontrolleri
- **Kapatma Butonu**: `clsBtn` → `root.cikis()` metodu
- **Güvenli Kapatma**: Durum kaydedilip sistem kapatılır

## Responsive Tasarım

### Padding ve Spacing
```
Kontrol Butonları:
- Padding: (60, 30, 60, 0)
- Spacing: (15, 0)

Kaydırıcılar:
- Padding: (80, 0, 80, 0)  
- Spacing: (40, 0)

Ayarlar:
- Padding: (80, 80, 80, 80)
- Spacing: (40, 0)
```

### Boyut Esnekliği
- **size_hint**: Dinamik boyutlandırma
- **Fixed Positions**: FloatLayout içinde sabit konumlar
- **Font Scaling**: `sp` birimi ile ölçeklenebilir fontlar

## Eksik/Yorumlanmış Özellikler

### Kullanılmayan Icon Sistemı
```kv
# Yorumlanmış icon tanımları:
#background_normal:"icons/icons8-lightBlue-40.png"
#background_down:"icons/icons8-light-40.png"
```

### Gelecek Genişlemeler
```kv
# Yorumlanmış ekran tanımları:
#<GirisEkran>:
#    KontrolEkrani:
#       name: "Ekran 1"
#    AyarEkrani:
#        name: "Ekran2"
```

Bu tasarım, endüstriyel kullanım için optimize edilmiş, sade ve fonksiyonel bir arayüz sunar. Büyük butonlar ve net renkler ile dokunmatik ekran kullanımına uygundur.
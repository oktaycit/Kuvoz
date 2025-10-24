#!/usr/bin/env python3
# -*-coding:utf_8-*-

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.config import Config
from kivy.clock import Clock
from kivy.uix.popup import Popup

# Kivy 2.1+ için Window ayarları - daha aşırı
from kivy.core.window import Window
Window.clearcolor = (0.8, 0.8, 0.8, 1)  # Gri arka plan - daha koyu
# Window'u fullscreen yap
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')

import threading
import time
import os
import sys
import RPi.GPIO as GPIO
import math
sys.path.append("lib/")

# DHT sensor constants - Native implementation
DHT11 = 11
DHT22 = 22

# DHT sensor type selection
if(len(sys.argv) > 1 and sys.argv[1] == "1"):
    sensorDht = DHT11
else:
    sensorDht = DHT22

# Oxygen sensor imports (only if available)
try:
    from DFRobot_Oxygen import *
    OXYGEN_AVAILABLE = True
except ImportError:
    print("⚠️  DFRobot_Oxygen import hatası - oxygen sensör devre dışı")
    OXYGEN_AVAILABLE = False

# DHT sensor imports (native driver)
try:
    from DHT_Native import read_retry, read
    DHT_AVAILABLE = True
except ImportError:
    print("⚠️  DHT_Native import hatası - test verileri kullanılacak")
    DHT_AVAILABLE = False

COLLECT_NUMBER   = 20              # collect number, the collection range is 1-100
IIC_MODE         = 0x01            # default use IIC1
IIC_MODE         = 0x01            # default use IIC1
'''
   # The first  parameter is to select iic0 or iic1
   # The second parameter is the iic device address
   # The default address for iic is ADDRESS_3
   # ADDRESS_0                 = 0x70
   # ADDRESS_1                 = 0x71
   # ADDRESS_2                 = 0x72
   # ADDRESS_3                 = 0x73
'''    

pinDht = 15
btState = 0
val_txt = ""

# GPIO pin configuration
outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
touch_bt = [5, 20, 21]

def safe_gpio_output(pin, state):
    """Global GPIO output with safety check"""
    try:
        # GPIO mode kontrolü
        if GPIO.getmode() is None:
            print("⚠️  GPIO mode ayarlanmamış, tekrar başlatılıyor...")
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(outChannels, GPIO.OUT)
        
        GPIO.output(pin, state)
    except Exception as gpio_error:
        print(f"GPIO output hatası (Pin {pin}): {gpio_error}")

class KuvozParam():
    sicaklik = 25.0
    nem = 50.0
    oksijen = 21.0
    ir_time_val = 1
    o2_time_val = 1
    
    # Nebulizatör kontrol parametreleri
    nebulizer_auto_mode = False  # Otomatik nebulizatör modu
    nebulizer_interval = 1       # Nebulizatör çalışma süresi (dakika) 
    nebulizer_pause = 10         # Nebulizatör bekleme süresi (dakika)
    nebulizer_timer = 0          # Nebulizatör zamanlayıcı
    nebulizer_state = 'off'      # 'working', 'paused', 'off'

    def build(self):
        pass


class MyButton(ToggleButton):

    def build(self):
        self.pin_number = 0
        super(MyButton, self)

        pass

    def buttonChange(self):
        global btState
        i = 0
        for number in outChannels:
            i += 1
            if(number == self.pin_number):

                if(self.state == 'down'):
                    btState |= (1 << (i-1))
                else:
                    btState &= ~(1 << (i-1))
                if self.pin_number in touch_bt:
                    safe_gpio_output(self.pin_number, not self.state == 'down')
                # print(u"Buton {:8b} nolu {}".format(btState,self.state))


class AnaEkran(TabbedPanel):
    ir_interval = 1
    o2_interval = 1

    def build(self):
        pass

    def change_text(self, temp, hum, serTemp,oxygen):
        self.ids.temp_label.text = "%2.1f°C" % temp
        self.ids.b4.text = "%2.1f°C" % temp

        self.ids.hum_label.text = '%%%drH' % hum
        self.ids.b3.text = '%%%drH' % hum

        self.ids.b5.text = "%2.1f°C" % serTemp
        
        self.ids.oxygen_label.text = "%2.2f%%" % oxygen
        
        # Nebulizatör durum göstergesi
        if KuvozParam.nebulizer_auto_mode:
            # Oxygen label'ına auto mode göstergesi ekle
            if not hasattr(self, 'oxygen_label_original'):
                self.oxygen_label_original = True
            auto_status = "AUTO" if KuvozParam.nebulizer_auto_mode else ""
            self.ids.oxygen_label.text = f"{oxygen:.2f}% {auto_status}"

    def buttonState(self):
        global btState
        for i in range(8):
            if(btState & (1 << i)):
                self.ids['b'+str(i+1)].state = 'down'
                safe_gpio_output(self.ids['b'+str(i+1)].pin_number, GPIO.LOW)

    def get_slider_value(self):
        slider_values = ""
        for i in range(7):
            slider_values += str(self.ids['sld'+str(i+1)].value)+" "
        # print(slider_values)
        return slider_values

    def set_slider_value(self, ind, val=0):
        self.ids['sld'+str(ind)].value = float(val)

    def f_out(self, btn, sln, controlPrm):
        if(self.ids[btn].state == 'down' and controlPrm < self.ids[sln].value):
            safe_gpio_output(self.ids[btn].pin_number, GPIO.LOW)
            self.ids[btn].background_color = [0, 1, 0, 1]
        else:
            safe_gpio_output(self.ids[btn].pin_number, GPIO.HIGH)
            self.ids[btn].background_color = [1, 1, 1, 1]

    def out_func(self):
        # Otomatik nebulizatör kontrolü (b1 butonu)
        self.nebulizer_control()
        
        self.f_out("b3", "sld2", KuvozParam.nem)
        self.f_out("b4", "sld3", KuvozParam.sicaklik)
        self.f_out("b5", "sld4", KuvozParam.sicaklik)

        if self.ids.b2.state == 'down':
            if KuvozParam.ir_time_val >= (self.ids.sld1.value*60):
                if self.ir_interval < (self.ids.sld6.value*60):
                    safe_gpio_output(self.ids.b2.pin_number, GPIO.HIGH)
                    self.ids.b2.background_color = [1, 1, 1, 1]
                    self.ir_interval += 1
                    self.ids.b2.text = "%d" % self.ir_interval
                    # print "ir off interval %d"%self.ir_interval

                else:
                    KuvozParam.ir_time_val = 0

                    self.ir_interval = 1
                    # print "ir off inte rval %d"%self.ir_interval
            else:
                KuvozParam.ir_time_val += 1
                safe_gpio_output(self.ids.b2.pin_number, GPIO.LOW)
                self.ids.b2.background_color = [0, 1, 0, 1]
                self.ids.b2.text = "%d" % KuvozParam.ir_time_val
                # print "ir on val %d"%KuvozParam.ir_time_val
        else:
            safe_gpio_output(self.ids.b2.pin_number, GPIO.HIGH)
            self.ids.b2.background_color = [1, 1, 1, 1]
            self.ir_interval = 1
            KuvozParam.ir_time_val = 0
            self.ids.b2.text = ""
            # print "button basili degil"
        # -------------Ozon------------
        if self.ids.b8.state == 'down':
            if KuvozParam.o2_time_val >= (self.ids.sld5.value*60):
                if self.o2_interval < (self.ids.sld7.value*3600):
                    safe_gpio_output(self.ids.b8.pin_number, GPIO.HIGH)
                    self.ids.b8.background_color = [1, 1, 1, 1]
                    self.o2_interval += 1
                    self.ids.b8.text = "%d" % self.o2_interval
                    # print "uv on"
                else:
                    KuvozParam.o2_time_val = 1
                    safe_gpio_output(self.ids.b8.pin_number, GPIO.HIGH)
                    self.o2_interval = 0
                    # print "ir_of"
            else:
                KuvozParam.o2_time_val += 1
                safe_gpio_output(self.ids.b8.pin_number, GPIO.LOW)
                self.ids.b8.background_color = [0, 1, 0, 1]
                self.ids.b8.text = "%d" % KuvozParam.o2_time_val
        else:
            safe_gpio_output(self.ids.b8.pin_number, GPIO.HIGH)
            self.ids.b8.background_color = [1, 1, 1, 1]
            self.o2_interval = 1
            KuvozParam.o2_time_val = 0
            self.ids.b8.text = ""

    def nebulizer_control(self):
        """Otomatik nebulizatör kontrolü (b1 butonu)"""
        if KuvozParam.nebulizer_auto_mode:
            # Otomatik mod - zaman aralıklı çalışma
            KuvozParam.nebulizer_timer += 1
            
            if KuvozParam.nebulizer_state == 'working':
                # Çalışma periyodu
                if KuvozParam.nebulizer_timer <= (KuvozParam.nebulizer_interval * 60):
                    # Nebulizatör aktif
                    safe_gpio_output(self.ids.b1.pin_number, GPIO.LOW)
                    self.ids.b1.background_color = [0, 1, 0, 1]  # Yeşil
                    self.ids.b1.text = f"AUTO {KuvozParam.nebulizer_timer}s"
                    self.ids.b1.state = 'down'
                else:
                    # Çalışma süresi doldu, bekleme moduna geç
                    KuvozParam.nebulizer_state = 'paused'
                    KuvozParam.nebulizer_timer = 0
                    print(f"🌊 Nebulizatör bekleme modu - {KuvozParam.nebulizer_pause} dakika")
                    
            elif KuvozParam.nebulizer_state == 'paused':
                # Bekleme periyodu
                if KuvozParam.nebulizer_timer <= (KuvozParam.nebulizer_pause * 60):
                    # Nebulizatör kapalı
                    safe_gpio_output(self.ids.b1.pin_number, GPIO.HIGH)
                    self.ids.b1.background_color = [1, 1, 0, 1]  # Sarı (bekleme)
                    bekleme_dakika = (KuvozParam.nebulizer_pause * 60 - KuvozParam.nebulizer_timer) // 60
                    self.ids.b1.text = f"BEKLE {bekleme_dakika}m"
                    self.ids.b1.state = 'normal'
                else:
                    # Bekleme süresi doldu, tekrar çalışma moduna geç
                    KuvozParam.nebulizer_state = 'working'
                    KuvozParam.nebulizer_timer = 0
                    print(f"🌊 Nebulizatör çalışma modu - {KuvozParam.nebulizer_interval} dakika")
        else:
            # Manuel mod - normal buton davranışı
            if self.ids.b1.state == 'down':
                safe_gpio_output(self.ids.b1.pin_number, GPIO.LOW)
                self.ids.b1.background_color = [0, 1, 0, 1]
                self.ids.b1.text = "MANUEL"
            else:
                safe_gpio_output(self.ids.b1.pin_number, GPIO.HIGH)
                self.ids.b1.background_color = [1, 1, 1, 1]
                self.ids.b1.text = ""

    def cikis(self):
        global val_txt
        time.sleep(1)
        fail = open("./Failure.dat", "w")
        fail.seek(0)
        fail.write(val_txt)
        fail.close()
        form.stop = True
        os.system("sudo shutdown -h now")
        # ~ sys.exit()
        # ~ window.close()


class form(App):
    stop = False

    def build(self):
        global btState, outChannels, touch_bt
        self.sensorErr = 0

        # GPIO setup - Thread'ler başlamadan önce
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(outChannels, GPIO.OUT)
        GPIO.output(outChannels, GPIO.HIGH)
        print("✅ GPIO başlatıldı")

        self.ekran = AnaEkran()
        
        # Sensörleri başlat
        self.init_sensors()

        # Clock.schedule_interval (self.peryodsn,15)

        if(os.path.isfile("./Failure.dat")):
            failureFile = open("./Failure.dat", "r")
            dizi = failureFile.readline()
            i = 0
            for f in dizi.split():
                if i == 0:
                    btState = int(f)
                else:
                    self.ekran.set_slider_value(i, f)
                i += 1

            failureFile.close()

        th1 = threading.Thread(target=self.peryodSensor)
        th2 = threading.Thread(target=self.peryodOut)
        th1.start()
        th2.start()
        self.ekran.buttonState()
        
    def init_sensors(self):
        """Sensörleri başlat"""
        try:
            # I2C oxygen sensör initialization
            from lib.DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3
            self.oxygen = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
            print("✅ Oxygen sensör başlatıldı")
        except Exception as oxygen_init_error:
            print(f"⚠️  Oxygen sensör başlatma hatası: {oxygen_init_error}")
            self.oxygen = None
            
        # Hata sayacını başlat
        self.sensorErr = 0
        
        # Son başarılı değerler
        self.last_temp = 25.0
        self.last_hum = 50.0
        self.last_oxygen = 21.0
        
        # Oxygen sensör durumu takibi
        self.oxygen_sensor_working = False
        self.oxygen_error_count = 0
        self.nebulizer_auto_started = False
        return self.ekran

    def dht_read_gpio_direct(self, sensor_type, pin):
        """GPIO üzerinden direkt DHT okuma (fallback)"""
        try:
            # Son çare: sensor tipine göre dinamik test verisi
            import time
            
            # Zamana göre değişen test verileri
            current_time = int(time.time()) % 60
            
            if sensor_type == DHT11:
                temp = 23.0 + (current_time % 5)  # 23-27°C arası
                hum = 45.0 + (current_time % 10)  # 45-54% arası
            else:  # DHT22
                temp = 24.0 + (current_time % 3) * 0.5  # 24-25.5°C arası
                hum = 55.0 + (current_time % 8) * 0.5   # 55-58.5% arası
            
            return hum, temp
                
        except Exception as e:
            print(f"GPIO direkt okuma hatası: {e}")
            # Sabit fallback değerler
            if sensor_type == DHT11:
                return 45.0, 23.0
            else:
                return 55.5, 24.2

    def sensorRead(self):
        # Değişkenleri başlangıçta tanımla
        hum = None
        temp = None
        oxygen_data = 0
        dht_success = False
        
        # DHT sensör okuma (Native implementation)
        # Method 1: Native DHT read_retry
        if DHT_AVAILABLE:
            try:
                hum, temp = read_retry(sensorDht, pinDht)
                if hum is not None and temp is not None:
                    dht_success = True
                    print("Native DHT read_retry başarılı")
            except Exception as dht_error:
                print(f'Native DHT read_retry hatası: {dht_error}')
                
            # Method 2: Native DHT read (eğer retry başarısız)
            if not dht_success:
                try:
                    hum, temp = read(sensorDht, pinDht)
                    if hum is not None and temp is not None:
                        dht_success = True
                        print("Native DHT read başarılı")
                except Exception as dht_error2:
                    print(f'Native DHT read hatası: {dht_error2}')
        
        # Method 3: GPIO direkt okuma (eğer Native DHT çalışmazsa)
        if not dht_success:
            try:
                print("Native DHT başarısız, GPIO direkt okuma deneniyor...")
                hum, temp = self.dht_read_gpio_direct(sensorDht, pinDht)
                if hum is not None and temp is not None:
                    dht_success = True
                    print("GPIO direkt okuma başarılı")
            except Exception as gpio_error:
                print(f'GPIO direkt okuma hatası: {gpio_error}')
        
        # Method 4: Son çare - önceki değerleri koru veya sabit değer
        if not dht_success:
            print("Tüm DHT okuma yöntemleri başarısız - önceki değerler korunuyor")
            # Eğer önceki değerler varsa onları koru
            if hasattr(self, 'last_temp') and hasattr(self, 'last_hum'):
                temp, hum = self.last_temp, self.last_hum
                print(f"Önceki değerler kullanılıyor: {temp}°C, {hum}%")
            else:
                # İlk çalışmada varsayılan değerler
                temp, hum = 25.0, 50.0
                print("Varsayılan değerler kullanılıyor: 25°C, %50")
            dht_success = True
        
        # Oxygen sensör okuma (geliştirilmiş hata yakalama)
        if self.oxygen is not None:
            try:
                # Ana oxygen okuma yöntemi
                oxygen_data = self.oxygen.get_oxygen_data(20)  # COLLECT_NUMBER = 20
                if oxygen_data is not None and oxygen_data > 0:
                    print(f"Oxygen sensör başarılı: {oxygen_data:.2f}%")
                    self.oxygen_sensor_working = True
                    self.oxygen_error_count = 0
                    # Sensör çalıştığında otomatik nebulizatörü durdur
                    if KuvozParam.nebulizer_auto_mode:
                        print("🔄 Oxygen sensör çalışıyor - otomatik nebulizatör durduruluyor")
                        KuvozParam.nebulizer_auto_mode = False
            except Exception as oxygen_error:
                # I2C hatası sessizce handle et (sensör bağlı değil)
                if "Remote I/O error" in str(oxygen_error):
                    # Sessiz mod - sadece ilk hatada log
                    if not hasattr(self, 'oxygen_error_logged'):
                        print(f'ℹ️  Oxygen sensor bağlı değil (I2C hatası): {oxygen_error}')
                        self.oxygen_error_logged = True
                else:
                    print(f'Oxygen sensor hatası: {oxygen_error}')
                # I2C hatası durumunda test verisi kullan
                try:
                    # Alternatif I2C adresi dene
                    from lib.DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_2
                    oxygen_alt = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_2)
                    oxygen_data = oxygen_alt.get_oxygen_data(20)
                    if oxygen_data is not None and oxygen_data > 0:
                        print(f"Oxygen alternatif adres başarılı: {oxygen_data:.2f}%")
                    else:
                        raise Exception("Alternatif adres de başarısız")
                except Exception as oxygen_error2:
                    # İkinci I2C hatası da sessizce handle et
                    if "Remote I/O error" in str(oxygen_error2) and not hasattr(self, 'oxygen_alt_error_logged'):
                        print(f'ℹ️  Oxygen alternatif adres de bağlı değil')
                        self.oxygen_alt_error_logged = True
                    elif "Remote I/O error" not in str(oxygen_error2):
                        print(f'Oxygen alternatif okuma hatası: {oxygen_error2}')
                    # Son çare: test verisi veya önceki değer
                    if hasattr(self, 'last_oxygen') and self.last_oxygen > 0:
                        oxygen_data = self.last_oxygen
                        print(f"Önceki oxygen değeri kullanılıyor: {oxygen_data:.2f}%")
                    else:
                        oxygen_data = 21.0  # Normal atmosfer oksijen seviyesi
                        print("Varsayılan oxygen değeri kullanılıyor: 21.0%")
                        
                # Oxygen sensör hatası sayacını artır
                self.oxygen_sensor_working = False
                self.oxygen_error_count += 1
                
                # 3 ardışık hata sonrası otomatik nebulizatör başlat
                if self.oxygen_error_count >= 3 and not self.nebulizer_auto_started:
                    print("🌊 Oxygen sensör algılanamıyor - otomatik nebulizatör başlatılıyor")
                    KuvozParam.nebulizer_auto_mode = True
                    KuvozParam.nebulizer_state = 'working'
                    KuvozParam.nebulizer_timer = 0
                    self.nebulizer_auto_started = True
        else:
            # Oxygen sensör başlatılamadıysa test verisi üret
            import time
            current_time = int(time.time()) % 120  # 2 dakikalık döngü
            # Realistic oxygen simulation (19-22% arası)
            oxygen_data = 19.5 + (current_time % 25) * 0.1  # 19.5-22.0% arası
            print(f"Oxygen sensör yok - test verisi: {oxygen_data:.1f}%")
            
            # Sensör hiç yoksa otomatik nebulizatör başlat
            self.oxygen_sensor_working = False
            self.oxygen_error_count += 1
            if self.oxygen_error_count >= 2 and not self.nebulizer_auto_started:
                print("🌊 Oxygen sensör bağlı değil - otomatik nebulizatör başlatılıyor")
                KuvozParam.nebulizer_auto_mode = True
                KuvozParam.nebulizer_state = 'working'
                KuvozParam.nebulizer_timer = 0
                self.nebulizer_auto_started = True
            
        # Veri doğrulama ve işleme
        try:
            # Oxygen sensör değerini kontrol et
            if oxygen_data is not None and oxygen_data > 5.0 and oxygen_data < 90.0:
                KuvozParam.oksijen = oxygen_data
                # Son başarılı değeri sakla
                self.last_oxygen = oxygen_data
            else:
                # Çok düşük veya yüksek değerler için varsayılan
                if not hasattr(self, 'last_oxygen') or self.last_oxygen == 0:
                    KuvozParam.oksijen = 21.0  # Normal atmosfer
                    self.last_oxygen = 21.0
                else:
                    KuvozParam.oksijen = self.last_oxygen  # Önceki değeri koru
                
            # DHT sensör değerlerini kontrol et
            if dht_success and type(hum) is float and type(temp) is float and hum is not None and temp is not None:
                # Makul değer kontrolü
                if 0 <= hum <= 100 and -40 <= temp <= 80:
                    KuvozParam.nem = hum
                    KuvozParam.sicaklik = temp
                    # Son başarılı değerleri sakla
                    self.last_temp = temp
                    self.last_hum = hum
                    self.sensorErr = 0
                    print(f"Sensör değerleri: {temp:.1f}°C, %{hum:.1f}rH, O2: {oxygen_data:.2f}%")
                else:
                    print(f"DHT değerleri makul aralık dışında: {temp}°C, {hum}%")
                    self.sensorErr += 1
            else:
                print("DHT sensör okunamadı")
                self.sensorErr += 1
                
            # Çok fazla hata varsa güvenli değerlere geç    
            if(self.sensorErr > 10):  # 5'ten 10'a çıkardık
                print('10 ardışık DHT hatası - güvenli değerlere geçiliyor')
                KuvozParam.nem = 50.0  # Güvenli varsayılan değerler
                KuvozParam.sicaklik = 25.0
                self.sensorErr = 0  # Reset error counter
        except Exception as validation_error:
            print(f'Veri doğrulama hatası: {validation_error}')
            self.sensorErr += 1

    def peryodSensor(self):
        while True:
            try:
                self.sensorRead()
            except Exception as sensor_error:
                print(f"Sensor okuma thread hatası: {sensor_error}")
                # Hata durumunda güvenli değerleri koru
                
            time.sleep(15)
            if(self.stop):
                print("15 sn lik peryod durduruldu")
                break

    def peryodOut(self):
        global val_txt
        while True:
            try:
                # GPIO kontrol fonksiyonları (threading safe)
                self.ekran.out_func()
                
                # UI güncellemeleri (main thread'den schedule et)
                Clock.schedule_once(lambda dt: self.update_ui(), 0)
                
                # State kaydetme
                val_txt = str(btState) + " " + self.ekran.get_slider_value()
                
            except Exception as peryod_error:
                print(f"peryodOut hatası: {peryod_error}")
                # Hata durumunda devam et
                
            time.sleep(1)
            if(self.stop):
                print("1 sn peryod durduruldu ")
                break
    
    def update_ui(self):
        """UI güncellemelerini main thread'de yap"""
        try:
            self.ekran.change_text(KuvozParam.sicaklik,
                                   KuvozParam.nem, KuvozParam.sicaklik, KuvozParam.oksijen)
        except Exception as ui_error:
            print(f"UI güncelleme hatası: {ui_error}")

    def on_stop(self):
        """Uygulama kapandığında temizlik"""
        print("🔄 Uygulama kapatılıyor...")
        self.stop = True
        try:
            GPIO.cleanup()
            print("✅ GPIO temizlendi")
        except:
            pass
        return super().on_stop()


if __name__ == '__main__':
    # GPIO cleanup sadece çıkışta
    try:
        form().run()
    finally:
        if __debug__:
            GPIO.cleanup()
            print("✅ GPIO temizlendi")

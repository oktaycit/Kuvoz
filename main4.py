#!/usr/bin/env python3
# -*-coding:utf_8-*-

from kivy.app import App
from kivy.uix.checkbox import CheckBox
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
import threading
import time
import os
import sys
import RPi.GPIO as GPIO
#import paho.mqtt.client as mqtt
#import paho.mqtt.publish as publish
import Adafruit_DHT
if(len(sys.argv) > 1 and sys.argv[1] == "1"):
    sensorDht = Adafruit_DHT.DHT11
else:
    sensorDht = Adafruit_DHT.DHT22
import math
sys.path.append("lib/")
from DFRobot_Oxygen import *
import mqttPublish
import json

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
setDevice = 0
val_txt=""

class KuvozParam():
    sicaklik = 0.1
    nem = 0
    oksijen = 0
    # Ir_sicakligi=0
    ir_time_val = 1
    o2_time_val = 1
    
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
                    GPIO.output(self.pin_number, not self.state == 'down')
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

    def buttonState(self):
        global btState
        for i in range(8):
            if(btState & (1 << i)):
                self.ids['b'+str(i+1)].state = 'down'

                GPIO.output(self.ids['b'+str(i+1)].pin_number, GPIO.LOW)
    def checkState(self):
        global setDevice
    
        for i in range(4):
            if(setDevice & (1<<i)):
                self.ids['chk'+str(i)].state='down'

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
            GPIO.output(self.ids[btn].pin_number, GPIO.LOW)
            self.ids[btn].background_color = [0, 1, 0, 1]
        else:
            GPIO.output(self.ids[btn].pin_number, GPIO.HIGH)
            self.ids[btn].background_color = [1, 1, 1, 1]

    def out_func(self):
        self.f_out("b3", "sld2", KuvozParam.nem)
        self.f_out("b4", "sld3", KuvozParam.sicaklik)
        self.f_out("b5", "sld4", KuvozParam.sicaklik)

        if self.ids.b2.state == 'down':
            if KuvozParam.ir_time_val >= (self.ids.sld1.value*60):
                if self.ir_interval < (self.ids.sld6.value*60):
                    GPIO.output(self.ids.b2.pin_number, GPIO.HIGH)
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
                GPIO.output(self.ids.b2.pin_number, GPIO.LOW)
                self.ids.b2.background_color = [0, 1, 0, 1]
                self.ids.b2.text = "%d" % KuvozParam.ir_time_val
                # print "ir on val %d"%KuvozParam.ir_time_val
        else:
            GPIO.output(self.ids.b2.pin_number, GPIO.HIGH)
            self.ids.b2.background_color = [1, 1, 1, 1]
            self.ir_interval = 1
            KuvozParam.ir_time_val = 0
            self.ids.b2.text = ""
            # print "button basili degil"
        # -------------Ozon------------
        if self.ids.b8.state == 'down':
            if KuvozParam.o2_time_val >= (self.ids.sld5.value*60):
                if self.o2_interval < (self.ids.sld7.value*3600):
                    GPIO.output(self.ids.b8.pin_number, GPIO.HIGH)
                    self.ids.b8.background_color = [1, 1, 1, 1]
                    self.o2_interval += 1
                    self.ids.b8.text = "%d" % self.o2_interval
                    # print "uv on"
                else:
                    KuvozParam.o2_time_val = 1
                    GPIO.output(self.ids.b8.pin_number, GPIO.HIGH)
                    self.o2_interval = 0
                    # print "ir_of"
            else:
                KuvozParam.o2_time_val += 1
                GPIO.output(self.ids.b8.pin_number, GPIO.LOW)
                self.ids.b8.background_color = [0, 1, 0, 1]
                self.ids.b8.text = "%d" % KuvozParam.o2_time_val
        else:
            GPIO.output(self.ids.b8.pin_number, GPIO.HIGH)
            self.ids.b8.background_color = [1, 1, 1, 1]
            self.o2_interval = 1
            KuvozParam.o2_time_val = 0
            self.ids.b8.text = ""

    def cikis(self):
        form.stop = True
        os.system("sudo shutdown -h now")
        sys.exit()
        window.close()
    def saveSet(self):
        global val_txt
        
        time.sleep(1)
        fail = open("./Failure.dat", "w")
        fail.seek(0)
        fail.write(val_txt)
        fail.close()
    def saveMqttFile(self):
        import subprocess

        subprocess.run(['python3', 'dosyaKaydet.py'])
        
        

class form(App):
    stop = False
    
        
    def build(self):
        global btState
        global setDevice
        self.sensorErr = 1 #Başlangıçta sensör okunamıyor
        self.oldMsg=""
        self.ekran = AnaEkran()
    
        if(os.path.isfile("./Failure.dat")):
            failureFile = open("./Failure.dat", "r")
            dizi = failureFile.readline()
            i = 0
            for f in dizi.split():
                if i == 0:
                    btState = int(f)
                elif i==8:
                    setDevice =int(f)
                else:
                    self.ekran.set_slider_value(i, f)
                i += 1

            failureFile.close()
        self.ekran.checkState()
    
        if(self.ekran.ids.chk3.active):
            print("mqtt bağlanısı")
            self.data = mqttPublish.readFile()
            self.client=mqttPublish.connect_mqtt(self.data)
            
            mqttPublish.subscribe(self.client,self.data,KuvozParam)
          
        
        th1 = threading.Thread(target=self.peryodSensor)
        th2 = threading.Thread(target=self.peryodOut)
        th1.start()
        th2.start()
        if(self.ekran.ids.chk3.active):
            print("döngü")
            th3 = threading.Thread(target=self.client.loop_forever)
            th3.start()
        
        
        self.ekran.buttonState()
        self.ekran.checkState()
        if(self.ekran.ids.chk2.active):
            try:
                self.oxygen = DFRobot_Oxygen_IIC(IIC_MODE ,ADDRESS_3)
            except:
                self.oxygen = 0
        return self.ekran

    def sensorRead(self):
        if(self.ekran.ids.chk0.active):
            sensorDht = Adafruit_DHT.DHT11
        elif(self.ekran.ids.chk1.active):
            sensorDht = Adafruit_DHT.DHT22
        try:
            if(self.ekran.ids.chk0.active or self.ekran.ids.chk1.active):
                hum, temp = Adafruit_DHT.read_retry(sensorDht, pinDht)
            if(self.ekran.ids.chk2.active):
                try:
                    oxygen_data = self.oxygen.get_oxygen_data(COLLECT_NUMBER)
                except:
                    oxygen_data = 0
        except:
            print('Failed to get reading. Try again!')
        finally:
            if(self.ekran.ids.chk2.active):
                if(oxygen_data>5.0 and oxygen_data<90.0):
                    KuvozParam.oksijen = oxygen_data
                else:
                    KuvozParam.oksijen = 0
            if(self.ekran.ids.chk0.active or self.ekran.ids.chk1.active):
                if(type(hum) is float and type(temp) is float and hum < 100):
                    KuvozParam.nem = hum
                    KuvozParam.sicaklik = temp
                    self.sensorErr = 0
                elif(self.sensorErr > 5):
                    KuvozParam.nem = 0
                    KuvozParam.sicaklik = 0
                    print('Failed to get reading. Try again!')
                else:
                    self.sensorErr += 1
        # print(hum,temp)
   

    def peryodSensor(self):
        while True:
            self.sensorRead()
        
            time.sleep(15)
            if(self.stop):
                print("15 sn lik peryod durduruldu")
                break

    def peryodOut(self):
        global btState,val_txt
        
        while True:
            if(self.sensorErr==0):
                self.ekran.out_func()
            self.ekran.change_text(KuvozParam.sicaklik,
                                   KuvozParam.nem, KuvozParam.sicaklik,KuvozParam.oksijen)
            
            setDevice=0                      
            for i in range(4):
                
                if(self.ekran.ids['chk'+str(i)].active):
                    setDevice |= (1<<i)
                else:
                    setDevice &= ~(1<<i)
            
            val_txt = str(btState) + " " + self.ekran.get_slider_value() + str(setDevice)
            
            
            time.sleep(1)
            if(self.stop):
                
                print("Set değeri %d "%setDevice)
                print("1 sn peryod durduruldu ")
                break

    # ~ def on_stop(self):

        # ~ quit()
        # ~ os.system("sudo shutdown -r now")


if __name__ == '__main__':

    if __debug__:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        # set up GPIO output channel
        outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
        touch_bt = [5, 20, 21]
        GPIO.setup(outChannels, GPIO.OUT)
        GPIO.output(outChannels, GPIO.HIGH)
    
    form().run()

    if __debug__:
        GPIO.cleanup()

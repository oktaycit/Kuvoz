#!/usr/bin/env python3
#-*-coding:utf_8-*-

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import ScreenManager,Screen
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
# from kivy.factory import Factory
import os
import sys

if __debug__:
    # ~ try:
        # ~ from w1thermsensor import W1ThermSensor
        # ~ _w1Sensor=1
    # ~ except ModuleNotFoundError:
        # ~ print ("Onewire Modül Yüklenemiyor")
    # ~ else:
        # ~ _w1Sensor=0
    import RPi.GPIO as GPIO
    import Adafruit_DHT
    # ~ if (_w1Sensor):
        # ~ sensor = W1ThermSensor()
    if(len(sys.argv)>1 and sys.argv[1]=="1"):
        sensorDht= Adafruit_DHT.DHT11
        print("DHT11")
    else:
        sensorDht= Adafruit_DHT.DHT22
        print("DHT22")
        
    pinDht=15
btState = 0
val_txt=""
class KuvozParam():
    sicaklik=0.0
    nem=0
    oksijen=0
    #Ir_sicakligi=0
    ir_time_val=1
    o2_time_val=1

    def build(self):
        pass

class MyButton(ToggleButton):

    def build(self):
        self.pin_number=0
        super(MyButton,self)

        pass


    def buttonChange(self):
        if __debug__:
            global btState
            i=0
            for number in outChannels:
                i +=1
                if(number==self.pin_number):
                    
                    if(self.state=='down'):
                        btState |= (1<<(i-1))
                    else:
                        btState &= ~(1<<(i-1))
                    if self.pin_number in touch_bt:
                        GPIO.output(self.pin_number,not self.state=='down')
                    #print(u"Buton {:8b} nolu {}".format(btState,self.state))





class AnaEkran(TabbedPanel):
    ir_interval=1
    o2_interval=1
    def build(self):
        pass
   

    def change_text(self,temp,hum,serTemp):
        self.ids.temp_label.text="%2.1f°C"% temp
        self.ids.b4.text="%2.1f°C"% temp
        
        self.ids.hum_label.text='%%%drH'% hum
        self.ids.b3.text='%%%drH'% hum
        
        self.ids.b5.text="%2.1f°C"% serTemp 
        
    def buttonState(self):
        global btState
        for i in range(8):
            if(btState & (1<<i)):
                self.ids['b'+str(i+1)].state='down'
                
                GPIO.output(self.ids['b'+str(i+1)].pin_number,GPIO.LOW)
                
    def get_slider_value(self):
        slider_values=""
        for i in range(7):
            slider_values +=str(self.ids['sld'+str(i+1)].value)+" "
        #print(slider_values)
        return slider_values
    
    def set_slider_value(self,ind,val=0):
        self.ids['sld'+str(ind)].value=float(val)
    
    def f_out(self,btn,sln,controlPrm):
        if(self.ids[btn].state=='down' and controlPrm < self.ids[sln].value): 
            GPIO.output(self.ids[btn].pin_number,GPIO.LOW)            
            self.ids[btn].background_color=[0,1,0,1]
        else:
            GPIO.output(self.ids[btn].pin_number,GPIO.HIGH)
            self.ids[btn].background_color=[1,1,1,1]
                
    def out_func(self):
        # if(KuvozParam.nem == 0 and KuvozParam.sicaklik==0):
            # print("DHT sensor okunamıyor")
            # return False
        self.f_out("b3","sld2",KuvozParam.nem)
    
        self.f_out("b4","sld3",KuvozParam.sicaklik)
   
        self.f_out("b5","sld4",KuvozParam.sicaklik)
        
        
        if self.ids.b2.state=='down':
            if KuvozParam.ir_time_val >= (self.ids.sld1.value*60):
                if self.ir_interval < (self.ids.sld6.value*60):
                    GPIO.output(self.ids.b2.pin_number,GPIO.HIGH)
                    self.ids.b2.background_color=[1,1,1,1]
                    self.ir_interval +=1
                    self.ids.b2.text="%d"%self.ir_interval
                    #print "ir off interval %d"%self.ir_interval
                    
                else:
                    KuvozParam.ir_time_val=0
                    
                    self.ir_interval=1
                    #print "ir off inte rval %d"%self.ir_interval
            else:
                KuvozParam.ir_time_val +=1
                GPIO.output(self.ids.b2.pin_number,GPIO.LOW)            
                self.ids.b2.background_color=[0,1,0,1]
                self.ids.b2.text="%d"%KuvozParam.ir_time_val
                #print "ir on val %d"%KuvozParam.ir_time_val
        else:
            GPIO.output(self.ids.b2.pin_number,GPIO.HIGH)
            self.ids.b2.background_color=[1,1,1,1]
            self.ir_interval=1
            KuvozParam.ir_time_val=0;
            self.ids.b2.text=""
            #print "button basili degil"
        #-------------Ozon------------
        if self.ids.b8.state=='down':
            if KuvozParam.o2_time_val >= (self.ids.sld5.value*60): 
                if self.o2_interval < (self.ids.sld7.value*3600):
                    GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)            
                    self.ids.b8.background_color=[1,1,1,1]
                    self.o2_interval +=1
                    self.ids.b8.text="%d"%self.o2_interval
                    #print "uv on"
                else:
                    KuvozParam.o2_time_val=1
                    GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)
                    #self.ids.b8.background_color=[1,1,1,1]
                    self.o2_interval=0
                    #print "ir_of"
            else:
                KuvozParam.o2_time_val +=1
                GPIO.output(self.ids.b8.pin_number,GPIO.LOW)            
                self.ids.b8.background_color=[0,1,0,1]
                self.ids.b8.text="%d"%KuvozParam.o2_time_val    
        else:
            GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)
            self.ids.b8.background_color=[1,1,1,1]
            self.o2_interval=1
            KuvozParam.o2_time_val=0
            self.ids.b8.text=""
    def cikis(self):
        global val_txt
        """ popup = Popup(  title='Uyar',
                        content=Label(text="Sistem Kap"),
                        size_hint=(None, None), size=(400, 400))
        popup.open() """
        self.ids.clsBtn.text="Pls Wait"
        time.sleep(1)
        fail=open("./Failure.dat","w")
        fail.seek(0)
        fail.write(val_txt)
        fail.close()
        
        form.stop=True
        
        # App.get_running_app().stop()
        # ~ print("Çıkış")
        # ~ import sys
        os.system("sudo shutdown -h now")
        # ~ sys.exit()
        # ~ window.close()
        
       
        
class form(App):
    # ~ stop=threading.Event() 
    stop=False 
    def build(self):
        global btState
        self.sensorErr=0
            
        self.ekran = AnaEkran()
        
        #Clock.schedule_interval (self.peryodsn,15)
        
        if(os.path.isfile("./Failure.dat")):
            failureFile=open("./Failure.dat","r")
            dizi=failureFile.readline()
            i=0
            for f in dizi.split():
                if i==0:
                    btState=int(f)
                else:  
                    self.ekran.set_slider_value(i,f)
                i +=1
                
            failureFile.close()
            
        th1=threading.Thread(target=self.peryodSensor)
        th2=threading.Thread(target=self.peryodOut)
        #th1.deamon=True
        #th2.deamon=True
        th1.start()
        th2.start()
        self.ekran.buttonState()
		
        return self.ekran
  
    
    def sensorRead(self):
            try:
                hum,temp = Adafruit_DHT.read_retry(sensorDht, pinDht)
            except:
                print('Failed to get reading. Try again!')
            finally:        
                if(type(hum) is float and type(temp) is float):
                    # ~ if(hum>100 or hum==0):
                        # ~ sensorDht= Adafruit_DHT.DHT11
					
                    KuvozParam.nem=hum
                    KuvozParam.sicaklik=temp
                    self.sensorErr=0
                elif(self.sensorErr >5):
                    KuvozParam.nem=0
                    KuvozParam.sicaklik=0
                    print('Failed to get reading. Try again!')
                else:
                    self.sensorErr +=1
            #print(hum,temp)
            
            
   
    def peryodSensor(self):
        
        if __debug__:
            while True:
            
                # ~ if(_w1Sensor):
                    # ~ for sensor in W1ThermSensor.get_available_sensors():
                        # ~ print("Sensor %s has temperature %.2f" % (sensor, sensor.get_temperature()))
                        # ~ KuvozParam.serum_sicakligi=sensor.get_temperature()
                
                self.sensorRead()
                time.sleep(15)
                if(self.stop):
                    print("15 sn lik peryod durduruldu")
                    break
               
    def peryodOut(self):
        global val_txt
        while True:
            self.ekran.out_func()
            self.ekran.change_text(KuvozParam.sicaklik,KuvozParam.nem,KuvozParam.sicaklik)       
            val_txt=str(btState) + " "  + self.ekran.get_slider_value()
            time.sleep(1)
            if(self.stop):
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
        outChannels=[5,6,13,16,19,20,21,26]
        touch_bt=[5,20,21]
        GPIO.setup(outChannels, GPIO.OUT)
        GPIO.output(outChannels,GPIO.HIGH)
	
    form().run()
    
    
    if __debug__:
        GPIO.cleanup()


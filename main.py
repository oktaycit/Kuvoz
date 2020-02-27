#!/usr/bin/env python
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
import os

if __debug__:
    try:
        from w1thermsensor import W1ThermSensor
        _w1Sensor=1
    except ModuleNotFoundError:
        print ("Onewire Modül Yüklenemiyor")
        _w1Sensor=0
    import RPi.GPIO as GPIO
    import Adafruit_DHT
    if (_w1Sensor):
        sensor = W1ThermSensor()
    sensorDht= Adafruit_DHT.DHT11
    pinDht=15
btState = 0
val_txt="" 


class KuvozParam():
    sicaklik=0.0
    nem=0
    oksijen=0
    serum_sicakligi=0
    ir_time_val=15
    o2_time_val=15

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



# class GirisEkran(ScreenManager):
    # pass

class AnaEkran(TabbedPanel):
    ir_interval=15
    o2_interval=15
    def build(self):
        pass
    #def aydinlatmaSlider(self,touch):
        #print(self.ids.lightSliderId.value)

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
        
        self.f_out("b3","sld2",KuvozParam.nem)
    
        self.f_out("b4","sld3",KuvozParam.sicaklik)
   
        self.f_out("b5","sld4",KuvozParam.serum_sicakligi)
        
        
        if self.ids.b2.state=='down':
			if KuvozParam.ir_time_val >= (self.ids.sld1.value*60): 
				if self.ir_interval < (self.ids.sld6.value*60):
					GPIO.output(self.ids.b2.pin_number,GPIO.HIGH)
					self.ids.b2.background_color=[1,1,1,1]
					
					self.ir_interval +=15
					#print "ir off interval %d"%self.ir_interval
					
				else:
					KuvozParam.ir_time_val=0
					
					self.ir_interval=15
					#print "ir off inte rval %d"%self.ir_interval
			else:
				KuvozParam.ir_time_val +=15
				GPIO.output(self.ids.b2.pin_number,GPIO.LOW)            
				self.ids.b2.background_color=[0,1,0,1]
				#print "ir on val %d"%KuvozParam.ir_time_val
        else:
            GPIO.output(self.ids.b2.pin_number,GPIO.HIGH)
            self.ids.b2.background_color=[1,1,1,1]
            self.ir_interval=15
            KuvozParam.ir_time_val=0;
            #print "button basili degil"
        #-------------Ozon------------
        if self.ids.b8.state=='down':
            if KuvozParam.o2_time_val >= (self.ids.sld5.value*60): 
                if self.o2_interval < (self.ids.sld7.value*3600):
                    GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)            
                    self.ids.b8.background_color=[1,1,1,1]
                    
                    self.o2_interval +=15
                    #print "uv on"
                else:
                    KuvozParam.o2_time_val=15
                    GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)
                    self.ids.b8.background_color=[1,1,1,1]
                    self.o2_interval=0
                    #print "ir_of"
            else:
                KuvozParam.o2_time_val +=15
                GPIO.output(self.ids.b8.pin_number,GPIO.LOW)            
                self.ids.b8.background_color=[0,1,0,1]
                    
        else:
            GPIO.output(self.ids.b8.pin_number,GPIO.HIGH)
            self.ids.b8.background_color=[1,1,1,1]
            self.o2_interval=15
            KuvozParam.o2_time_val=0
    def cikis(self):
        global val_txt
        fail=open("./Failure.dat","wb")
        fail.seek(0)
        fail.write(val_txt)
        fail.close()
        App.get_running_app().stop()
        import sys
        sys.exit()
        window.close()
       
        
class form(App):
    def build(self):
        global btState
        self.ekran = AnaEkran()
        Clock.schedule_interval (self.peryodsn,15)
        if(os.path.isfile("./Failure.dat")):
            failureFile=open("./Failure.dat","rb")
            dizi=failureFile.readline()
            i=0
            for f in dizi.split():
                if i==0:
                    btState=int(f)
                else:  
                    self.ekran.set_slider_value(i,f)
                i +=1
                
            failureFile.close()
            #print ("%b ",btState)
        
        self.ekran.buttonState()
        #KuvozParam.ir_time_val=(int(self.ekran.ids.sld1.value)*60)
        #print (self.ekran.get_slider_value())
        return self.ekran

    def peryodsn(self,event):
        global val_txt
        cn=0
        if __debug__:
            humidity, temperature = Adafruit_DHT.read_retry(sensorDht, pinDht)

            if humidity is not None and temperature is not None:
               
                KuvozParam.nem=humidity 
                KuvozParam.sicaklik=temperature
                    

            else:
                print('Failed to get reading. Try again!')
            i=0
            if(_w1Sensor):
                for sensor in W1ThermSensor.get_available_sensors():
                    print("Sensor %s has temperature %.2f" % (sensor, sensor.get_temperature()))
                    KuvozParam.serum_sicakligi=sensor.get_temperature()
                
            self.ekran.out_func()
               
                
        #print(u"Kuvoz sıcaklığı=%2.1f Serum Sıcaklığı=%2.1f" % (KuvozParam.sicaklik,KuvozParam.serum_sicakligi))

        self.ekran.change_text(KuvozParam.sicaklik,KuvozParam.nem,KuvozParam.serum_sicakligi)
        #self.ekran.out_func()
        val_txt=str(btState) + " "  + self.ekran.get_slider_value()
        #print val_txt

        
    
    def on_stop(self):
        quit()
      
        #os.system("sudo shutdown -r now")

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

1

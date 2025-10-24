#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main3 Alternative - TabbedPanel yerine BoxLayout
Kivy 2.1+ uyumlu, görünürlük odaklı
"""

# Bu dosyayı Raspberry Pi'de test için kullan
print("main3_alt.py - Kivy 2.1+ görünürlük testi için hazırlandı")
print("form_simple.kv kullanır - TabbedPanel yerine BoxLayout")
print("")
print("Kullanım:")
print("1. Raspberry Pi'de python3 main3_alt.py")
print("2. Basit interface görünüyor mu kontrol et")
print("3. Görünüyorsa form.kv'yi güncelleyebiliriz")
print("")
print("Kivy 2.1+ değişiklikleri:")
print("- TabbedPanel canvas davranışı değişti")
print("- Canvas rendering order değişti") 
print("- Background_color bazen yok sayılıyor")
print("- Canvas ile manual rendering gerekli")

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.core.window import Window
    from kivy.config import Config
    from kivy.lang import Builder
    import os
    
    # Kesin görünürlük ayarları
    Window.clearcolor = (0.6, 0.6, 0.6, 1)  # Koyu gri window
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '600')
    
    class TestEkran(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            print("TestEkran initialized")
    
    class Main3AltApp(App):
        def build(self):
            print("Building app...")
            
            # Form_simple.kv kullan
            if os.path.exists("form_simple.kv"):
                print("Loading form_simple.kv")
                Builder.load_file("form_simple.kv")
                return TestEkran()
            else:
                print("form_simple.kv not found, using inline KV")
                # Inline basit test
                kv = '''
<TestEkran@BoxLayout>:
    orientation: 'vertical'
    canvas:
        Color:
            rgba: 0.8, 0.2, 0.2, 1  # Kırmızı - kesin görünür
        Rectangle:
            pos: self.pos
            size: self.size
    
    Label:
        text: 'KIVY 2.1+ TEST'
        color: (1, 1, 1, 1)  # Beyaz metin
        font_size: '48sp'
        canvas:
            Color:
                rgba: 0, 0, 0, 1  # Siyah arka plan
            Rectangle:
                pos: self.pos
                size: self.size
    
    Button:
        text: 'TEST BUTTON'
        background_color: (0, 1, 0, 1)  # Yeşil
        color: (0, 0, 0, 1)  # Siyah metin
        font_size: '24sp'
        canvas:
            Color:
                rgba: 0, 1, 0, 1
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: 0, 0, 0, 1
            Line:
                rectangle: [self.x, self.y, self.width, self.height]
                width: 5
'''
                return Builder.load_string(kv)
    
    if __name__ == '__main__':
        print("Starting Main3Alt app...")
        Main3AltApp().run()
        
except ImportError as e:
    print(f"❌ Kivy not available: {e}")
    print("Bu normal - Windows'ta Kivy yok")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
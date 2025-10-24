#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Test App - Kivy 2.1+ görünürlük testi
form_simple.kv kullanır
"""

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.core.window import Window
    from kivy.lang import Builder
    import os
    
    # Window ayarları - kesin görünürlük
    Window.clearcolor = (0.7, 0.7, 0.7, 1)  # Koyu gri
    
    class TestEkran(BoxLayout):
        pass
    
    class SimpleTestApp(App):
        def build(self):
            # KV dosyasını yükle
            if os.path.exists("form_simple.kv"):
                self.load_kv("form_simple.kv")
                return TestEkran()
            else:
                # KV dosyası yoksa inline
                kv = '''
TestEkran:
    orientation: 'vertical'
    canvas:
        Color:
            rgba: 0.8, 0.8, 0.8, 1
        Rectangle:
            pos: self.pos
            size: self.size
    
    Label:
        text: 'SIMPLE TEST'
        color: (0, 0, 0, 1)
        font_size: '32sp'
        canvas:
            Color:
                rgba: 1, 1, 0, 1
            Rectangle:
                pos: self.pos
                size: self.size
'''
                return Builder.load_string(kv)
    
    if __name__ == '__main__':
        print("✅ Simple test app created")
        print("Run: SimpleTestApp().run() to test GUI")
        # SimpleTestApp().run()  # Uncomment on Raspberry Pi
        
except ImportError as e:
    print(f"❌ Kivy not available: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
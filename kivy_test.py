#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal Kivy Test - Form.kv görünürlük testi
Sadece temel widget'ları test eder
"""

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.core.window import Window
    from kivy.lang import Builder
    
    # Window ayarları
    Window.clearcolor = (0.8, 0.8, 0.8, 1)
    
    # Test KV kodu
    kv_test = '''
BoxLayout:
    orientation: 'vertical'
    canvas:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Rectangle:
            pos: self.pos
            size: self.size
    
    Label:
        text: 'Test Label'
        color: (0, 0, 0, 1)
        font_size: '20sp'
        canvas:
            Color:
                rgba: 1, 1, 0, 1
            Rectangle:
                pos: self.pos
                size: self.size
    
    Button:
        text: 'Test Button'
        background_color: (0.5, 0.5, 0.5, 1)
        color: (1, 1, 1, 1)
        canvas:
            Color:
                rgba: 0.5, 0.5, 0.5, 1
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: 0, 0, 0, 1
            Line:
                rectangle: [self.x, self.y, self.width, self.height]
                width: 3
'''
    
    class TestApp(App):
        def build(self):
            return Builder.load_string(kv_test)
    
    if __name__ == '__main__':
        print("✅ Kivy test app created")
        print("Run: TestApp().run() to test GUI")
        # TestApp().run()  # Uncomment on Raspberry Pi
        
except ImportError as e:
    print(f"❌ Kivy not available: {e}")
    print("This test will work on Raspberry Pi with Kivy installed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
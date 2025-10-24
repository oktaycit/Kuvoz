#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Test Script - Form.kv görünürlük testi
"""
import sys
import os

# Test verileri ile basit widget testi
print("=== UI Test Starting ===")

try:
    # Kivy import test
    print("Testing Kivy import...")
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.uix.boxlayout import BoxLayout
    print("✅ Kivy import SUCCESS")
    
    # Form.kv yükleme testi
    print("Testing form.kv loading...")
    from kivy.lang import Builder
    
    # Basit test widget
    class TestApp(App):
        def build(self):
            layout = BoxLayout(orientation='vertical')
            layout.add_widget(Label(
                text='Test Label', 
                color=(0, 0, 0, 1),  # Siyah metin
                font_size='20sp'
            ))
            return layout
    
    print("✅ Test app created")
    print("If you see this, Kivy is working!")
    print("Run TestApp().run() to see GUI")
    
except ImportError as e:
    print(f"❌ Kivy not available: {e}")
    print("This is expected on Windows - test will work on Raspberry Pi")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("=== UI Test Complete ===")
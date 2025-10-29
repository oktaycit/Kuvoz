#!/usr/bin/env python3
"""
Test script for duty cycle logic
Tests the new duty/free time functionality without GPIO dependencies
"""

import time
import sys

class DutyCycleTester:
    def __init__(self):
        # Simulate the duty cycle settings
        self.slider_values = {
            'sld8': 2,   # Nebulizer duty time (2 min for quick test)
            'sld9': 3,   # Nebulizer free time (3 min for quick test)
            'sld10': 1,  # Ozone duty time (1 min for quick test)
            'sld11': 2   # Ozone free time (2 min for quick test)
        }
        
        # Duty cycle state tracking
        self.nebulizer_duty_start = 0
        self.nebulizer_in_duty = False
        self.ozone_duty_start = 0
        self.ozone_in_duty = False
        
        # Button states for display
        self.button_states = {'b2': False, 'b8': False}
        
    def update_nebulizer_duty_cycle(self):
        """Update nebulizer duty cycle state"""
        current_time = time.time()
        duty_duration = self.slider_values['sld8'] * 60
        free_duration = self.slider_values['sld9'] * 60
        
        if self.nebulizer_in_duty:
            # Check if duty time is complete
            if current_time - self.nebulizer_duty_start >= duty_duration:
                self.button_states['b2'] = False  # Turn OFF
                self.nebulizer_in_duty = False
                self.nebulizer_duty_start = current_time  # Start free time
                print(f"💧 Nebulizer FREE cycle started - OFF for {self.slider_values['sld9']} minutes")
        else:
            # Check if free time is complete
            if current_time - self.nebulizer_duty_start >= free_duration:
                # Ready for next duty cycle
                self.start_nebulizer_duty()
                
    def start_nebulizer_duty(self):
        """Start nebulizer duty cycle"""
        current_time = time.time()
        self.button_states['b2'] = True  # Turn ON
        self.nebulizer_duty_start = current_time
        self.nebulizer_in_duty = True
        print(f"💧 Nebulizer DUTY cycle started - ON for {self.slider_values['sld8']} minutes")
    
    def update_ozone_duty_cycle(self):
        """Update ozone duty cycle state"""
        current_time = time.time()
        duty_duration = self.slider_values['sld10'] * 60
        free_duration = self.slider_values['sld11'] * 60
        
        if self.ozone_in_duty:
            # Check if duty time is complete
            if current_time - self.ozone_duty_start >= duty_duration:
                self.button_states['b8'] = False  # Turn OFF
                self.ozone_in_duty = False
                self.ozone_duty_start = current_time  # Start free time
                print(f"💨 Ozone FREE cycle started - OFF for {self.slider_values['sld11']} minutes")
        else:
            # Check if free time is complete
            if current_time - self.ozone_duty_start >= free_duration:
                # Ready for next duty cycle
                self.start_ozone_duty()
    
    def start_ozone_duty(self):
        """Start ozone duty cycle"""
        current_time = time.time()
        self.button_states['b8'] = True  # Turn ON
        self.ozone_duty_start = current_time
        self.ozone_in_duty = True
        print(f"💨 Ozone DUTY cycle started - ON for {self.slider_values['sld10']} minutes")
    
    def get_remaining_times(self):
        """Get remaining time for current phase"""
        current_time = time.time()
        
        # Nebulizer remaining time
        if self.nebulizer_in_duty:
            duty_duration = self.slider_values['sld8'] * 60
            remaining = duty_duration - (current_time - self.nebulizer_duty_start)
            neb_status = f"DUTY: {max(0, remaining):.0f}s left"
        else:
            free_duration = self.slider_values['sld9'] * 60
            remaining = free_duration - (current_time - self.nebulizer_duty_start)
            neb_status = f"FREE: {max(0, remaining):.0f}s left"
        
        # Ozone remaining time
        if self.ozone_in_duty:
            duty_duration = self.slider_values['sld10'] * 60
            remaining = duty_duration - (current_time - self.ozone_duty_start)
            oz_status = f"DUTY: {max(0, remaining):.0f}s left"
        else:
            free_duration = self.slider_values['sld11'] * 60
            remaining = free_duration - (current_time - self.ozone_duty_start)
            oz_status = f"FREE: {max(0, remaining):.0f}s left"
        
        return neb_status, oz_status
    
    def run_test(self, duration_seconds=300):  # 5 minute test
        """Run duty cycle test"""
        print("🧪 Starting Duty Cycle Test...")
        print(f"⚙️  Settings: Nebulizer {self.slider_values['sld8']}m duty/{self.slider_values['sld9']}m free, Ozone {self.slider_values['sld10']}m duty/{self.slider_values['sld11']}m free")
        
        # Start both cycles
        self.start_nebulizer_duty()
        time.sleep(1)  # Slight delay
        self.start_ozone_duty()
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Update duty cycles
            self.update_nebulizer_duty_cycle()
            self.update_ozone_duty_cycle()
            
            # Display status
            neb_status, oz_status = self.get_remaining_times()
            nebulizer_icon = "🟢" if self.button_states['b2'] else "🔴"
            ozone_icon = "🟢" if self.button_states['b8'] else "🔴"
            
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed:3d}s] {nebulizer_icon} Nebulizer: {neb_status} | {ozone_icon} Ozone: {oz_status}")
            
            time.sleep(5)  # Update every 5 seconds
        
        print("✅ Test completed!")

if __name__ == "__main__":
    tester = DutyCycleTester()
    
    # Quick test or long test
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        tester.run_test(60)  # 1 minute test
    else:
        tester.run_test(300)  # 5 minute test
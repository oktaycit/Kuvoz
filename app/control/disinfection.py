"""Server-owned UV/ozone interlocks. No ventilation clearance is inferred."""
import time


class DisinfectionSafetyMixin:
    def init_disinfection_safety(self):
        self.disinfection_mode = False
        self.disinfection_start_time = 0
        self.disinfection_owner = None
        self.disinfection_heartbeat = 0
        self.disinfection_ventilation_required = False
        self.ozone_cycle_duration = None

    def resume_disinfection_safety(self):
        if self.disinfection_ventilation_required:
            return self.stop_disinfection()
        return True

    def disinfection_status(self):
        return dict(active=self.disinfection_mode,
                    ventilation_required=self.disinfection_ventilation_required)

    def start_disinfection(self, owner):
        with self.state_lock:
            if self.disinfection_mode:
                return self.disinfection_owner == owner
            if not self.control_active:
                return False
            # Cancel automatic requests AND physically remove power before UV/O3.
            ok = True
            for name in ('b1', 'b2', 'b3', 'b4', 'b5', 'b9'):
                self.button_states[name] = False
                pin = self.outChannels[int(name[1:]) - 1]
                ok = bool(self.safe_gpio_output(pin, 1)) and ok
            self.nebulizer_in_duty = False
            self.nebulizer_duty_start = 0
            self.button_states['b6'] = False
            self.button_states['b6_manual'] = False
            self.fan_auto_active = False
            ok = bool(self.apply_fan_output(False, source='disinfection_start')) and ok
            if not ok:
                return False
            self.disinfection_mode = True
            self.disinfection_owner = owner
            self.disinfection_start_time = time.time()
            self.disinfection_heartbeat = time.monotonic()
            # Persist BEFORE energizing UV/ozone, including interrupted sessions.
            self.disinfection_ventilation_required = True
            if self.save_settings() is False:
                self.stop_disinfection()
                return False
            return True

    def stop_disinfection(self):
        """Idempotent explicit OFF, acknowledged only after GPIO commands succeed."""
        with self.state_lock:
            was_active = self.disinfection_mode or self.disinfection_ventilation_required
            ok = True
            for name in ('b7', 'b8'):
                self.button_states[name] = False
                ok = bool(self.safe_gpio_output(self.outChannels[int(name[1:]) - 1], 1)) and ok
            self.ozone_in_duty = False
            self.ozone_duty_start = 0
            self.ozone_cycle_duration = None
            if was_active:
                self.disinfection_ventilation_required = True
                self.button_states['b6'] = True
                self.button_states['b6_manual'] = True
                fan_ok = self.apply_fan_output(True, duty=100, source='disinfection_stop')
            else:
                fan_ok = True
            if ok:
                self.disinfection_mode = False
                self.disinfection_start_time = 0
                self.disinfection_owner = None
            # On output failure retain mode so the loop retries OFF, never ON.
            self.schedule_settings_save(reason='disinfection_stop')
            return bool(ok and fan_ok)

    def control_disinfection(self):
        with self.state_lock:
            # Closing the owner page or losing heartbeats must not strand an output.
            if time.monotonic() - self.disinfection_heartbeat > 20:
                self.stop_disinfection()
                return
            if not any(self.button_states.get(k) for k in ('b7', 'b8')):
                self.stop_disinfection()
                return
            # Guard against other command paths attempting to re-enable normal loads.
            for name in ('b1', 'b2', 'b3', 'b4', 'b5', 'b9'):
                self.button_states[name] = False
                if not self.safe_gpio_output(self.outChannels[int(name[1:]) - 1], 1):
                    self.stop_disinfection()
                    return
            if self.button_states.get('b8'):
                self.update_ozone_duty_cycle()
                if not self.ozone_in_duty:
                    # One exposure, never silently restart after a free interval.
                    self.button_states['b8'] = False
                    if not self.button_states.get('b7'):
                        self.stop_disinfection()

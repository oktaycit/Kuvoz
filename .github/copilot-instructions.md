<!-- Copilot instructions for contributors and AI coding agents -->
# Kuvoz — Copilot instructions

These concise rules help AI agents (and human contributors) make safe, high-value edits to the Kuvoz web interface.

- Project overview (short): The repo provides a Raspberry Pi based veterinary incubator (kuvöz) control system. The web interface (HTML/CSS/JS) in `web/` talks to a Flask + Socket.IO backend `web_server.py` which performs GPIO and sensor control (DHT + DFRobot oxygen). Kiosk support and systemd service files are in `systemd/` and kiosk scripts are in `scripts/` and make targets are in `Makefile`.

- Editing contract (inputs/outputs):
  - Inputs: HTTP/Socket.IO messages from `web/script.js` (e.g. `get_status`, `toggle_button`, `update_slider`).
  - Outputs: JSON/socket events `sensor_update`, `button_update`, `status_response` and direct GPIO actions in `KuvozServer` methods. Keep web socket payload shapes consistent with examples found in `web_server.py` and `web/script.js`.

- Where to look for examples:
  - WebSocket message handlers and payload examples: `web/script.js` (methods: connectWebSocket, socket event handlers) and `web_server.py` (socketio emits and `KuvozServer` methods).
  - Sensor and GPIO mapping: `README_WEB.md` (pin list) and `web_server.py` (`self.outChannels`, `pinDht`).
  - Kiosk and start commands: `Makefile`, `scripts/start-kiosk.sh`, `systemd/kuvoz-web.service`.

- Coding style / conventions specific to this repo:
  - Backend uses plain Flask with Socket.IO; prefer emitting/receiving events (not raw HTTP polling) for state updates.
  - Use the existing JSON shapes: e.g. sensor update: {"type":"sensor_update","sensors":{...}}; button update: {"name":"b1","state":true}. Match property names (`temperature`, `humidity`, `oxygen`, `buttons`, `sliders`).
  - Hardware availability is feature-flagged at runtime (see `GPIO_AVAILABLE`, `DHT_AVAILABLE`, `OXYGEN_AVAILABLE`). Any code that touches hardware must check these flags.
  - Thread-safety: GPIO writes go through `KuvozServer.safe_gpio_output()` and hardware init uses `init_hardware()` — reuse these helpers rather than directly calling RPi.GPIO in new code.
  - Timer management: Original version had duty cycle and free time settings with dashboard timer tracking. Current web interface uses timed intervals (`nebulizer_interval`, `ozone_interval`) but lacks visual countdown timers on frontend. Duty and free time durations should be configurable via settings tab (not just interval timing).

- Tests, run & debug flow (practical commands):
  - Run dev server (no systemd): `make web-dev` (invokes Flask/Socket.IO on localhost:5000). If `make` isn't available, run `python3 web_server.py` from repo root.
  - Manual debug web terminal: `python3 web_debug_server.py` serves a quick command UI on port 8080 (useful for Pi debugging).
  - Service logs: `journalctl -u kuvoz-web -f` (on device with systemd).

- Integration and side-effects to be careful about:
  - Changing pin mappings or default slider IDs must be mirrored in `web/script.js` UI code and `KuvozServer` (pin numbers and slider keys like `sld1`..`sld7`).
  - Do NOT remove or rename socket event names (e.g. `get_status`, `sensor_update`, `toggle_button`) without updating both backend and frontend.
  - Long-running hardware operations should run in daemon threads and not block the main Socket.IO thread (follow patterns used in `nebulizer_control()` and `sensor_thread`).

- Small, low-risk improvements AI can make automatically:
  - Add defensive null-checks before DOM access in `web/script.js` (there are many guarded updates already; follow the existing try/catch patterns).
  - Centralize repeated string constants (event names) into a single object in `script.js` and mirror on server if adding new events.
  - Add feature-flag checks before touching hardware: consult `GPIO_AVAILABLE`, `DHT_AVAILABLE`, `oxygen_sensor_available`.
  - Restore duty/free time dashboard timers: Add countdown displays for nebulizer and ozone operations (original version had visual timer tracking that's missing in current web interface).
  - Add duty/free time controls to settings: Create sliders or input fields in the settings section for configuring duty cycle duration and free time duration separately (not just interval timing).

- When to ask the human maintainer:
  - If a change modifies GPIO pin numbers, slider IDs, or socket event names. These are high-risk and require confirmation.
  - When adding new dependencies (native libs or system packages) — include an update to `Makefile` with install steps.

- Examples from repo to copy-paste when implementing features:
  - Emitting a sensor update from server:
    - See `socketio.emit('sensor_update', {'sensors': self.sensor_data})` pattern in `web_server.py`.
  - Safe GPIO write:
    - Use `self.safe_gpio_output(pin, GPIO.LOW)` (see `KuvozServer.safe_gpio_output`).

Keep changes minimal and cross-checked: always run `make web-dev` (or `python3 web_server.py`) locally and verify the frontend still receives `status_response` after edits.

If anything above is unclear, tell me what area you want more detail on (hardware mapping, socket protocol, or make/systemd flows) and I'll expand the instructions.

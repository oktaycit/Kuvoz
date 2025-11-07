/**
 * Kuvoz Incubator Control System - Web Interface JavaScript
 * WebSocket tabanlı real-time kontrol sistemi
 */

// Translation dictionary
const translations = {
    tr: {
        app: {
            title: 'Kuvöz Kontrol Sistemi',
            web_interface: 'Web Arayüzü',
            cleaning_title: 'Temizlik Kontrolleri'
        },
        status: {
            status: 'Durum',
            time: 'Saat',
            quick_actions: 'Hızlı İşlemler',
            connected: 'Bağlandı',
            disconnected: 'Bağlantı Kesildi',
            connecting: 'Bağlanıyor...'
        },
        panel: {
            controls: 'Kontroller',
            sensors: 'Sensörler',
            timer: 'Zamanlayıcı',
            system: 'Sistem',
            sterilization: 'Sterilizasyon Kontrolleri',
            ozone_timer: 'Ozon Zamanlayıcı',
            navigation: 'Navigasyon'
        },
        button: {
            lighting: 'Aydınlatma',
            fan: 'Fan',
            carbon_temp: 'Karbon Isıtıcı',
            ir_temp: 'IR Isıtıcı',
            humidity: 'Nem Kontrol',
            nebulizer: 'Nemlendirici',
            uv_light: 'UV Işığı',
            ozone: 'Ozon'
        },
        slider: {
            temperature: 'Sıcaklık Hedefi (°C)',
            humidity: 'Nem Hedefi (%)'
        },
        mode: {
            select: 'Mod Seçimi',
            light: 'Hafif',
            medium: 'Orta',
            heavy: 'Yoğun',
            active: 'Aktif',
            waiting: 'Bekleme'
        },
        sensor: {
            temperature: 'Sıcaklık',
            humidity: 'Nem',
            oxygen: 'Oksijen',
            reading: 'Okunuyor...'
        },
        time: {
            minutes: 'dakika',
            duty: 'duty',
            free: 'free'
        },
        system: {
            cleaning: 'Temizlik',
            shutdown: 'Kapat',
            restart: 'Yeniden Başlat',
            save: 'Ayarları Kaydet',
            shutdown_confirm: 'Sistem kapatılacak. Emin misiniz?',
            restart_confirm: 'Sistem yeniden başlatılacak. Emin misiniz?',
            cancel: 'İptal',
            confirm: 'Onayla'
        },
        warning: {
            attention: 'DİKKAT:',
            sterilization_safety: 'UV ve Ozon sterilizasyonu sırasında hayvanların kafes içinde olmamasına dikkat edin.',
            ventilation: 'Ozon işlemi bitiminde ortamın havalandırıldığından emin olun.',
            simulation_title: 'SİMÜLASYON MODU AKTİF!',
            simulation_text: 'Sistem gerçek donanım olmadan test modunda çalışıyor. Sensör değerleri simüle ediliyor.'
        }
    },
    en: {
        app: {
            title: 'Kuvoz Control System',
            web_interface: 'Web Interface',
            cleaning_title: 'Cleaning Controls'
        },
        status: {
            connected: 'Connected',
            disconnected: 'Disconnected',
            connecting: 'Connecting...'
        },
        panel: {
            controls: 'Controls',
            sensors: 'Sensors',
            timer: 'Timer',
            system: 'System',
            sterilization: 'Sterilization Controls',
            ozone_timer: 'Ozone Timer',
            navigation: 'Navigation'
        },
        button: {
            lighting: 'Lighting',
            fan: 'Fan',
            carbon_temp: 'Carbon Heater',
            ir_temp: 'IR Heater',
            humidity: 'Humidity Control',
            nebulizer: 'Nebulizer',
            uv_light: 'UV Light',
            ozone: 'Ozone'
        },
        slider: {
            temperature: 'Temperature Target (°C)',
            humidity: 'Humidity Target (%)'
        },
        mode: {
            select: 'Mode Selection',
            light: 'Light',
            medium: 'Medium',
            heavy: 'Heavy',
            active: 'Active',
            waiting: 'Waiting'
        },
        sensor: {
            temperature: 'Temperature',
            humidity: 'Humidity',
            oxygen: 'Oxygen',
            reading: 'Reading...'
        },
        time: {
            minutes: 'minutes',
            duty: 'duty',
            free: 'free'
        },
        system: {
            cleaning: 'Cleaning',
            shutdown: 'Shutdown',
            restart: 'Restart',
            save: 'Save Settings',
            shutdown_confirm: 'System will be shut down. Are you sure?',
            restart_confirm: 'System will be restarted. Are you sure?',
            cancel: 'Cancel',
            confirm: 'Confirm'
        },
        warning: {
            attention: 'ATTENTION:',
            sterilization_safety: 'Ensure animals are not in the cage during UV and Ozone sterilization.',
            ventilation: 'Make sure the environment is ventilated after ozone treatment.',
            simulation_title: 'SIMULATION MODE ACTIVE!',
            simulation_text: 'System is running in test mode without real hardware. Sensor values are simulated.'
        }
    }
};

class KuvozController {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
        // Language management
        this.currentLanguage = localStorage.getItem('language') || 'tr';
        
        // Durum verileri
        this.sensorData = {
            temperature: { value: '--', status: 'Reading...' },
            humidity: { value: '--', status: 'Reading...' }
        };
        
        // Oksijen sensörü durumu - başlangıçta bilinmiyor
        this.oxygenSensorAvailable = false;
        
        this.buttonStates = {
            b1: false, b2: false, b3: false, b4: false,
            b5: false, b6: false, b7: false, b8: false
        };

        this.gpioOutputs = {
            b1: null, b2: null, b3: null, b4: null,
            b5: null, b6: null, b7: null, b8: null
        };
        
        this.sliderValues = {
            sld1: 30, sld2: 65, sld3: 25.0,
            sld5: 30, sld6: 12, sld7: 8.0,
            // Duty/Free Time Settings
            sld8: 5,   // Nebulizer Duty Time (min)
            sld9: 25,  // Nebulizer Free Time (min)
            sld10: 3,  // Ozone Duty Time (min)
            sld11: 60  // Ozone Free Time (min)
        };

        // Mode presets for Nebulizer and Ozone
        this.modePresets = {
            nebulizer: {
                light: { duty: 3, free: 60 },
                medium: { duty: 5, free: 30 },
                heavy: { duty: 10, free: 20 }
            },
            ozone: {
                light: { duty: 2, free: 120 },
                medium: { duty: 3, free: 60 },
                heavy: { duty: 5, free: 30 }
            }
        };

        this.gpioAvailable = null;
        // Timer state tracking
        this.timerData = {
            nebulizer: { phase: 'READY', remaining: 0, total: 0 },
            ozone: { phase: 'READY', remaining: 0, total: 0 }
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateDateTime();
        this.connectWebSocket();
        this.startTimerCountdown();
        
        // Initialize timer displays
        this.updateTimerDisplay('nebulizer');
        this.updateTimerDisplay('ozone');
        
        // DateTime güncellemesi her saniye
        setInterval(() => this.updateDateTime(), 1000);
        
        // Sensor güncelleme simülasyonu (Socket.IO bağlantısı yoksa)
        setTimeout(() => {
            if (!this.socket || !this.socket.connected) {
                this.startSimulation();
            }
        }, 3000); // Give more time for Socket.IO connection
    }
    
    setupEventListeners() {
        // GPIO Butonları - Touch ve Click desteği
        document.querySelectorAll('.control-btn').forEach(btn => {
            let touchHandled = false;

            // Touch event (dokunmatik ekranlar için)
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault(); // 300ms click delay'i önler
                touchHandled = true;
                console.log('Touch detected on button:', e.currentTarget.dataset.name);
                const pin = e.currentTarget.dataset.pin;
                const name = e.currentTarget.dataset.name;
                this.toggleButton(name, pin);
                // Touch handled flag'i reset et
                setTimeout(() => { touchHandled = false; }, 500);
            }, { passive: false });

            // Click event (mouse ve fallback için)
            btn.addEventListener('click', (e) => {
                if (touchHandled) {
                    console.log('Click event ignored (already handled by touch)');
                    return; // Touch event ile zaten handle edildi
                }
                console.log('Click detected on button:', e.currentTarget.dataset.name);
                const pin = e.currentTarget.dataset.pin;
                const name = e.currentTarget.dataset.name;
                this.toggleButton(name, pin);
            });
        });
        
        // Slider'lar
        document.querySelectorAll('.slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const id = e.target.id;
                const value = parseFloat(e.target.value);
                this.updateSlider(id, value);
            });
        });

        // Slider +/- butonları
        document.querySelectorAll('.slider-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sliderId = e.currentTarget.dataset.slider;
                const slider = document.getElementById(sliderId);

                if (!slider) return;

                const currentValue = parseFloat(slider.value);
                const min = parseFloat(slider.min);
                const max = parseFloat(slider.max);
                const step = parseFloat(slider.step) || 1;

                let newValue = currentValue;

                // Minus veya Plus buton kontrolü
                if (e.currentTarget.classList.contains('minus')) {
                    newValue = Math.max(min, currentValue - step);
                } else if (e.currentTarget.classList.contains('plus')) {
                    newValue = Math.min(max, currentValue + step);
                }

                // Değer değiştiyse güncelle
                if (newValue !== currentValue) {
                    slider.value = newValue;
                    this.updateSlider(sliderId, newValue);
                }
            });
        });

        // Mode butonları
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const device = e.currentTarget.dataset.device;
                const mode = e.currentTarget.dataset.mode;
                this.changeMode(device, mode, e.currentTarget);
            });
        });

        // Sistem butonları - Touch ve Click desteği
        const shutdownBtn = document.getElementById('shutdownBtn');
        if (shutdownBtn) {
            let touchHandled = false;
            
            shutdownBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                touchHandled = true;
                console.log('Shutdown button touched');
                this.confirmAction(this.t('system.shutdown_confirm'), () => {
                    console.log('Shutdown confirmed, sending command');
                    this.sendCommand('shutdown');
                });
                setTimeout(() => { touchHandled = false; }, 500);
            }, { passive: false });
            
            shutdownBtn.addEventListener('click', (e) => {
                if (touchHandled) return;
                console.log('Shutdown button clicked');
                this.confirmAction(this.t('system.shutdown_confirm'), () => {
                    console.log('Shutdown confirmed, sending command');
                    this.sendCommand('shutdown');
                });
            });
        } else {
            console.warn('shutdownBtn element not found');
        }

        const restartBtn = document.getElementById('restartBtn');
        if (restartBtn) {
            let touchHandled = false;
            
            restartBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                touchHandled = true;
                console.log('Restart button touched');
                this.confirmAction(this.t('system.restart_confirm'), () => {
                    console.log('Restart confirmed, sending command');
                    this.sendCommand('restart');
                });
                setTimeout(() => { touchHandled = false; }, 500);
            }, { passive: false });
            
            restartBtn.addEventListener('click', (e) => {
                if (touchHandled) return;
                console.log('Restart button clicked');
                this.confirmAction(this.t('system.restart_confirm'), () => {
                    console.log('Restart confirmed, sending command');
                    this.sendCommand('restart');
                });
            });
        } else {
            console.warn('restartBtn element not found');
        }

        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            let touchHandled = false;
            
            saveBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                touchHandled = true;
                console.log('Save button touched');
                this.saveSettings();
                setTimeout(() => { touchHandled = false; }, 500);
            }, { passive: false });
            
            saveBtn.addEventListener('click', (e) => {
                if (touchHandled) return;
                console.log('Save button clicked');
                this.saveSettings();
            });
        }
    }

    changeMode(device, mode, clickedBtn) {
        // Get preset values
        const preset = this.modePresets[device][mode];
        if (!preset) return;

        // Remove active class from all mode buttons of this device
        const allModeBtns = document.querySelectorAll(`.mode-btn[data-device="${device}"]`);
        allModeBtns.forEach(btn => btn.classList.remove('active'));

        // Add active class to clicked button
        clickedBtn.classList.add('active');

        // Update slider values based on device
        if (device === 'nebulizer') {
            // Update Nebulizer sliders: sld8 (duty), sld9 (free)
            this.updateSlider('sld8', preset.duty);
            this.updateSlider('sld9', preset.free);

            // Update slider UI (if sliders exist in HTML)
            const sld8 = document.getElementById('sld8');
            const sld9 = document.getElementById('sld9');
            if (sld8) sld8.value = preset.duty;
            if (sld9) sld9.value = preset.free;

            // Update mode info display - use IDs to preserve elements
            const dutyDisplay = document.getElementById('nebulizerDutyDisplay');
            const freeDisplay = document.getElementById('nebulizerFreeDisplay');
            if (dutyDisplay) dutyDisplay.textContent = preset.duty;
            if (freeDisplay) freeDisplay.textContent = preset.free;
        } else if (device === 'ozone') {
            // Update Ozone sliders: sld10 (duty), sld11 (free)
            this.updateSlider('sld10', preset.duty);
            this.updateSlider('sld11', preset.free);

            // Update slider UI (if sliders exist in HTML)
            const sld10 = document.getElementById('sld10');
            const sld11 = document.getElementById('sld11');
            if (sld10) sld10.value = preset.duty;
            if (sld11) sld11.value = preset.free;

            // Update mode info display - use IDs to preserve elements
            const dutyDisplay = document.getElementById('ozoneDutyDisplay');
            const freeDisplay = document.getElementById('ozoneFreeDisplay');
            if (dutyDisplay) dutyDisplay.textContent = preset.duty;
            if (freeDisplay) freeDisplay.textContent = preset.free;
        }

        console.log(`${device} mode changed to ${mode}: duty=${preset.duty}min, free=${preset.free}min`);
    }
    
    connectWebSocket() {
        try {
            // Socket.IO connection with options - use current host instead of hardcoded localhost
            const socketUrl = window.location.origin; // Uses current protocol, hostname, and port
            console.log('Connecting to Socket.IO at:', socketUrl);
            this.socket = io(socketUrl, {
                timeout: 5000,
                forceNew: true,
                transports: ['polling', 'websocket']
            });
            
            this.socket.on('connect', () => {
                console.log('Socket.IO connected successfully');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                
                // Request initial status after short delay
                setTimeout(() => {
                    console.log('DEBUG: Emitting get_status request');
                    this.socket.emit('get_status');
                }, 1000);
                
                // Request status every 10 seconds for debugging
                setInterval(() => {
                    if (this.socket && this.socket.connected) {
                        console.log('DEBUG: Periodic get_status request');
                        this.socket.emit('get_status');
                    }
                }, 10000);
            });
            
            this.socket.on('sensor_update', (data) => {
                try {
                    console.log('Received sensor update:', data);
                    if (data && data.sensors) {
                        this.updateSensorData(data.sensors);
                    }
                } catch (e) {
                    console.error('Error handling sensor update:', e);
                }
            });
            
            this.socket.on('button_update', (data) => {
                try {
                    console.log('Received button update:', data);
                    if (data) {
                        if (data.gpio_outputs) {
                            this.updateGpioOutputs(data.gpio_outputs);
                        }
                        if (data.buttons) {
                            this.updateButtonStates(data.buttons);
                        } else if (data.name !== undefined) {
                            const singleButton = {};
                            singleButton[data.name] = data.state;
                            this.updateButtonStates(singleButton);
                        }
                    }
                } catch (e) {
                    console.error('Error handling button update:', e);
                }
            });
            
            this.socket.on('status_response', (data) => {
                try {
                    console.log('Received status response:', data);
                    if (data) {
                        if (data.system) this.updateSystemStatus(data.system);
                        if (data.gpio_outputs) this.updateGpioOutputs(data.gpio_outputs);
                        if (data.buttons) this.updateButtonStates(data.buttons);
                        if (data.sensors) this.updateSensorData(data.sensors);
                        if (data.sliders) this.updateSliderStates(data.sliders);
                        if (data.timers) this.updateTimerData(data.timers);
                    }
                } catch (e) {
                    console.error('Error handling status response:', e);
                }
            });
            
            this.socket.on('timer_update', (data) => {
                try {
                    console.log('Received timer update:', data);
                    if (data) {
                        this.updateTimerData(data);
                    }
                } catch (e) {
                    console.error('Error handling timer update:', e);
                }
            });
            
            this.socket.on('disconnect', () => {
                console.log('Socket.IO disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            });
            
            this.socket.on('connect_error', (error) => {
                console.error('Socket.IO connection error:', error);
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            });
            
        } catch (error) {
            console.error('Socket.IO connection failed:', error);
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, this.reconnectDelay);
        } else {
            console.log('Max reconnect attempts reached. Starting simulation mode.');
            this.startSimulation();
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'sensor_update':
                this.updateSensorData(data.sensors);
                break;
                
            case 'button_update':
                if (data.gpio_outputs) {
                    this.updateGpioOutputs(data.gpio_outputs);
                }
                if (data.buttons) {
                    this.updateButtonStates(data.buttons);
                }
                break;
                
            case 'slider_update':
                this.updateSliderStates(data.sliders);
                break;
                
            case 'status_response':
                if (data.system) this.updateSystemStatus(data.system);
                if (data.gpio_outputs) this.updateGpioOutputs(data.gpio_outputs);
                if (data.sensors) this.updateSensorData(data.sensors);
                if (data.buttons) this.updateButtonStates(data.buttons);
                if (data.sliders) this.updateSliderStates(data.sliders);
                break;
                
            case 'error':
                this.showToast(data.message, 'error');
                break;
                
            case 'success':
                this.showToast(data.message, 'success');
                break;
        }
    }
    
    sendCommand(command, data = {}) {
        if (this.socket && this.socket.connected) {
            console.log(`Sending command: ${command}`, data);
            this.socket.emit(command, data);
        } else {
            console.log('Socket.IO not connected, command ignored:', command);
            this.showToast('Bağlantı yok - Komut gönderilemedi', 'error');
        }
    }
    
    toggleButton(name, pin) {
        console.log(`DEBUG: toggleButton called - name: ${name}, pin: ${pin}, gpioAvailable: ${this.gpioAvailable}`);

        if (this.gpioAvailable === false) {
            this.showToast('GPIO devre dışı - butonlar pasif', 'warning');
            return;
        }

        const newState = !this.buttonStates[name];
        this.buttonStates[name] = newState;

        // Gerçek GPIO yanıtını beklerken nötr görünümde kal
        if (this.gpioOutputs.hasOwnProperty(name)) {
            this.gpioOutputs[name] = null;
            this.applyButtonVisual(name);
        }

        // Komutu gönder
        this.sendCommand('toggle_button', {
            name: name,
            pin: parseInt(pin, 10),
            state: newState
        });
        
        console.log(`Button ${name} (pin ${pin}): ${newState ? 'ON' : 'OFF'}`);
    }
    
    updateSlider(id, value) {
        this.sliderValues[id] = value;

        // Değer göstergesini güncelle (eğer varsa)
        const valueDisplay = document.getElementById(`${id}_value`);
        if (valueDisplay) {
            if (id === 'sld3' || id === 'sld7') {
                valueDisplay.textContent = value.toFixed(1);
            } else {
                valueDisplay.textContent = Math.round(value);
            }
        }

        // Komutu gönder
        this.sendCommand('update_slider', {
            id: id,
            value: value
        });

        console.log(`Slider ${id}: ${value}`);

        // Update timer display if duty/free time sliders changed
        if (id === 'sld8' || id === 'sld9') {
            this.updateTimerDisplay('nebulizer');
        } else if (id === 'sld10' || id === 'sld11') {
            this.updateTimerDisplay('ozone');
        }
    }
    
    updateTimerData(timerUpdate) {
        if (timerUpdate.nebulizer) {
            this.timerData.nebulizer = timerUpdate.nebulizer;
            this.updateTimerDisplay('nebulizer');
        }
        
        if (timerUpdate.ozone) {
            this.timerData.ozone = timerUpdate.ozone;
            this.updateTimerDisplay('ozone');
        }
    }
    
    updateTimerDisplay(device) {
        const timer = this.timerData[device];
        const phaseElement = document.getElementById(`${device}Phase`);
        const countdownElement = document.getElementById(`${device}Countdown`);
        const progressElement = document.getElementById(`${device}Progress`);
        const dutyTimeElement = document.getElementById(`${device}DutyTime`);
        const freeTimeElement = document.getElementById(`${device}FreeTime`);
        
        if (!phaseElement || !countdownElement || !progressElement) return;
        
        // Update phase indicator
        phaseElement.textContent = timer.phase;
        phaseElement.className = `phase-indicator ${timer.phase.toLowerCase()}`;
        
        // Update countdown
        const minutes = Math.floor(timer.remaining / 60);
        const seconds = timer.remaining % 60;
        countdownElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update progress bar
        if (timer.total > 0) {
            const progress = Math.max(0, (timer.total - timer.remaining) / timer.total * 100);
            progressElement.style.width = `${progress}%`;
        } else {
            progressElement.style.width = '0%';
        }
        
        // Update duty/free time displays
        if (dutyTimeElement) {
            const dutySlider = device === 'nebulizer' ? 'sld8' : 'sld10';
            dutyTimeElement.textContent = this.sliderValues[dutySlider];
        }
        
        if (freeTimeElement) {
            const freeSlider = device === 'nebulizer' ? 'sld9' : 'sld11';
            freeTimeElement.textContent = this.sliderValues[freeSlider];
        }
    }
    
    startTimerCountdown() {
        // Update countdown displays every second
        setInterval(() => {
            // Decrement remaining times
            if (this.timerData.nebulizer.remaining > 0) {
                this.timerData.nebulizer.remaining--;
                this.updateTimerDisplay('nebulizer');
            }
            
            if (this.timerData.ozone.remaining > 0) {
                this.timerData.ozone.remaining--;
                this.updateTimerDisplay('ozone');
            }
        }, 1000);
    }
    
    checkSimulationMode(sensors) {
        // Sensör verilerinin status alanlarını kontrol et
        let isSimulation = false;

        if (sensors.temperature && sensors.temperature.status) {
            const tempStatus = sensors.temperature.status.toLowerCase();
            if (tempStatus.includes('simulation') || tempStatus.includes('simulated')) {
                isSimulation = true;
            }
        }

        if (sensors.humidity && sensors.humidity.status) {
            const humStatus = sensors.humidity.status.toLowerCase();
            if (humStatus.includes('simulation') || humStatus.includes('simulated')) {
                isSimulation = true;
            }
        }

        if (sensors.oxygen && sensors.oxygen.status) {
            const oxyStatus = sensors.oxygen.status.toLowerCase();
            if (oxyStatus.includes('simulation') || oxyStatus.includes('simulated')) {
                isSimulation = true;
            }
        }

        // Uyarı banner'ını göster veya gizle
        const warningBanner = document.getElementById('simulationWarning');
        if (warningBanner) {
            if (isSimulation) {
                warningBanner.style.display = 'flex';
                console.log('⚠️ SIMÜLASYON MODU AKTİF - Uyarı gösteriliyor');
            } else {
                warningBanner.style.display = 'none';
            }
        }
    }

    checkOxygenSensorAvailability(sensors) {
        const hasOxygen = sensors && sensors.oxygen !== undefined;

        if (hasOxygen !== this.oxygenSensorAvailable) {
            this.oxygenSensorAvailable = hasOxygen;
            this.toggleOxygenSensorDisplay(hasOxygen);
            this.updateOzoneMode(hasOxygen);

            if (hasOxygen) {
                console.log('✅ Oxygen sensor detected - showing on dashboard');
            } else {
                console.log('❌ Oxygen sensor not available - hiding from dashboard');
            }
        }
    }
    
    updateOzoneMode(hasOxygen) {
        const ozoneMode = document.getElementById('ozoneMode');
        if (ozoneMode) {
            if (hasOxygen) {
                ozoneMode.textContent = 'O2-SMART';
                ozoneMode.className = 'ozone-mode oxygen-based';
                ozoneMode.title = 'Oksijen sensörü bazlı akıllı ozon kontrolü';
            } else {
                ozoneMode.textContent = 'TIMED';
                ozoneMode.className = 'ozone-mode timed';
                ozoneMode.title = 'Zamanlı ozon kontrolü (oksijen sensörü yok)';
            }
        }
    }
    
    updateOzoneModeByOxygen(oxygenValue) {
        const ozoneMode = document.getElementById('ozoneMode');
        if (ozoneMode && oxygenValue !== '--') {
            try {
                const oxyLevel = parseFloat(oxygenValue);
                
                if (oxyLevel > 24.0) {
                    ozoneMode.textContent = 'HIGH-O2';
                    ozoneMode.className = 'ozone-mode oxygen-based';
                    ozoneMode.title = `Yüksek oksijen (${oxyLevel}%) - Aktif ozon`;
                } else if (oxyLevel > 22.0) {
                    ozoneMode.textContent = 'NORMAL+';
                    ozoneMode.className = 'ozone-mode oxygen-based';
                    ozoneMode.title = `Normal+ oksijen (${oxyLevel}%) - Standart ozon`;
                } else if (oxyLevel >= 18.0) {
                    ozoneMode.textContent = 'NORMAL';
                    ozoneMode.className = 'ozone-mode timed';
                    ozoneMode.title = `Normal oksijen (${oxyLevel}%) - Kısa ozon`;
                } else {
                    ozoneMode.textContent = 'LOW-O2';
                    ozoneMode.className = 'ozone-mode disabled';
                    ozoneMode.title = `Düşük oksijen (${oxyLevel}%) - Ozon devre dışı`;
                }
            } catch (e) {
                console.error('Oxygen value parse error:', e);
            }
        }
    }
    
    toggleOxygenSensorDisplay(show) {
        const oxygenCard = document.querySelector('.sensor-card.oxygen');
        const sensorGrid = document.querySelector('.sensor-grid');
        
        if (oxygenCard) {
            if (show) {
                oxygenCard.style.display = 'block';
                oxygenCard.classList.remove('sensor-hidden');
                if (sensorGrid) {
                    sensorGrid.classList.remove('no-oxygen');
                }
            } else {
                oxygenCard.style.display = 'none';
                oxygenCard.classList.add('sensor-hidden');
                if (sensorGrid) {
                    sensorGrid.classList.add('no-oxygen');
                }
            }
        }
    }
    
    updateSensorData(sensors) {
        console.log('DEBUG updateSensorData called with:', sensors);

        // Simülasyon modu kontrolü
        this.checkSimulationMode(sensors);

        // Oksijen sensörü durumunu kontrol et
        this.checkOxygenSensorAvailability(sensors);
        
        if (sensors.temperature !== undefined) {
            console.log('DEBUG temperature data:', sensors.temperature);
            this.sensorData.temperature = sensors.temperature;
            const tempElement = document.getElementById('temperature');
            const tempStatusElement = document.getElementById('tempStatus');
            
            if (tempElement) {
                tempElement.textContent = sensors.temperature.value + '°C';
                console.log('DEBUG temperature element updated:', sensors.temperature.value + '°C');
            } else {
                console.error('DEBUG temperature element not found');
            }
            
            if (tempStatusElement) {
                tempStatusElement.textContent = sensors.temperature.status;
                console.log('DEBUG temperature status updated:', sensors.temperature.status);
            } else {
                console.error('DEBUG tempStatus element not found');
            }
        }
        
        if (sensors.humidity !== undefined) {
            console.log('DEBUG humidity data:', sensors.humidity);
            this.sensorData.humidity = sensors.humidity;
            const humElement = document.getElementById('humidity');
            const humStatusElement = document.getElementById('humStatus');
            
            if (humElement) {
                humElement.textContent = sensors.humidity.value + '%';
                console.log('DEBUG humidity element updated:', sensors.humidity.value + '%');
            } else {
                console.error('DEBUG humidity element not found');
            }
            
            if (humStatusElement) {
                humStatusElement.textContent = sensors.humidity.status;
                console.log('DEBUG humidity status updated:', sensors.humidity.status);
            } else {
                console.error('DEBUG humStatus element not found');
            }
        }
        
        // Oksijen sensörü sadece mevcut olduğunda güncelle
        if (sensors.oxygen !== undefined && this.oxygenSensorAvailable) {
            console.log('DEBUG oxygen data:', sensors.oxygen);
            this.sensorData.oxygen = sensors.oxygen;
            const oxyElement = document.getElementById('oxygen');
            const oxyStatusElement = document.getElementById('oxyStatus');
            
            if (oxyElement) {
                oxyElement.textContent = sensors.oxygen.value + '%';
                console.log('DEBUG oxygen element updated:', sensors.oxygen.value + '%');
            } else {
                console.error('DEBUG oxygen element not found');
            }
            
            if (oxyStatusElement) {
                oxyStatusElement.textContent = sensors.oxygen.status;
                console.log('DEBUG oxygen status updated:', sensors.oxygen.status);
            } else {
                console.error('DEBUG oxyStatus element not found');
            }
            
            // Oksijen seviyesine göre ozon modu güncellemesi
            this.updateOzoneModeByOxygen(sensors.oxygen.value);
        }
    }
    
    updateButtonStates(buttons) {
        Object.keys(buttons).forEach(buttonName => {
            if (this.buttonStates.hasOwnProperty(buttonName)) {
                const oldState = this.buttonStates[buttonName];
                const newState = Boolean(buttons[buttonName]);
                this.buttonStates[buttonName] = newState;
                // Her zaman visual'ı güncelle (GPIO state değişmemiş olsa bile)
                this.applyButtonVisual(buttonName);
            }
        });
    }

    updateGpioOutputs(gpioOutputs) {
        console.log('DEBUG: updateGpioOutputs called with:', gpioOutputs);
        Object.keys(gpioOutputs).forEach(buttonName => {
            if (this.gpioOutputs.hasOwnProperty(buttonName)) {
                const oldValue = this.gpioOutputs[buttonName];
                const rawValue = gpioOutputs[buttonName];
                const newValue = rawValue === null ? null : Boolean(rawValue);
                this.gpioOutputs[buttonName] = newValue;
                console.log(`DEBUG: Button ${buttonName}: GPIO ${oldValue} -> ${newValue}, buttonState: ${this.buttonStates[buttonName]}`);
                // Her zaman visual'ı güncelle
                this.applyButtonVisual(buttonName);
            }
        });
    }

    applyButtonVisual(buttonName) {
        const btn = document.getElementById(`btn_${buttonName}`);
        if (!btn) return;

        // Tüm state sınıflarını kaldır
        btn.classList.remove('active', 'active-on', 'active-off', 'state-on', 'state-off', 'state-disabled', 'state-unknown');

        const buttonState = this.buttonStates[buttonName];  // Fonksiyon aktif mi?
        const gpioState = this.gpioOutputs[buttonName];     // GPIO çıkış durumu

        console.log(`DEBUG applyButtonVisual: ${buttonName} - buttonState=${buttonState}, gpioState=${gpioState}, gpioAvailable=${this.gpioAvailable}`);

        // GPIO kullanılamıyorsa -> Disabled (gri)
        if (this.gpioAvailable === false) {
            btn.classList.add('state-disabled');
            console.log(`DEBUG ${buttonName}: Added state-disabled (GPIO unavailable)`);
            return;
        }

        // Buton PASİF (fonksiyon kapalı) -> Beyaz
        if (!buttonState) {
            btn.classList.add('state-unknown');
            console.log(`DEBUG ${buttonName}: Added state-unknown (button OFF)`);
            return;
        }

        // Buton AKTİF (fonksiyon açık) -> GPIO durumuna göre yeşil/kırmızı
        if (gpioState === null || gpioState === undefined) {
            // GPIO durumu henüz bilinmiyor -> Beyaz
            btn.classList.add('state-unknown');
            console.log(`DEBUG ${buttonName}: Added state-unknown (GPIO null, waiting for response)`);
        } else if (gpioState === true) {
            // GPIO LOW (ON) = Çıkış VERİYOR -> Yeşil
            btn.classList.add('state-on');
            console.log(`DEBUG ${buttonName}: Added state-on (GPIO LOW/ON)`);
        } else {
            // GPIO HIGH (OFF) = Çıkış VERMİYOR -> Kırmızı
            btn.classList.add('state-off');
            console.log(`DEBUG ${buttonName}: Added state-off (GPIO HIGH/OFF)`);
        }
    }

    updateSystemStatus(system) {
        if (!system) {
            return;
        }

        const previousAvailability = this.gpioAvailable;
        if (system.gpio_available !== undefined) {
            this.gpioAvailable = Boolean(system.gpio_available);
        }

        if (system.oxygen_available !== undefined) {
            const hadOxygen = this.oxygenSensorAvailable;
            const hasOxygen = Boolean(system.oxygen_available);
            if (hadOxygen !== hasOxygen) {
                this.oxygenSensorAvailable = hasOxygen;
                this.toggleOxygenSensorDisplay(hasOxygen);
                this.updateOzoneMode(hasOxygen);
            }
        }

        if (this.gpioAvailable === false) {
            Object.keys(this.gpioOutputs).forEach(buttonName => {
                this.gpioOutputs[buttonName] = null;
                this.applyButtonVisual(buttonName);
            });
        } else if (previousAvailability === false && this.gpioAvailable === true) {
            Object.keys(this.buttonStates).forEach(buttonName => this.applyButtonVisual(buttonName));
        }
    }
    
    updateSliderStates(sliders) {
        Object.keys(sliders).forEach(sliderId => {
            if (this.sliderValues.hasOwnProperty(sliderId)) {
                this.sliderValues[sliderId] = sliders[sliderId];

                const slider = document.getElementById(sliderId);
                const valueDisplay = document.getElementById(`${sliderId}_value`);

                if (slider) {
                    slider.value = sliders[sliderId];
                }

                if (valueDisplay) {
                    if (sliderId === 'sld3' || sliderId === 'sld7') {
                        valueDisplay.textContent = sliders[sliderId].toFixed(1);
                    } else {
                        valueDisplay.textContent = Math.round(sliders[sliderId]);
                    }
                }
            }
        });

        // Sync mode buttons after all sliders are updated
        if ('sld8' in sliders || 'sld9' in sliders) {
            this.syncModeButtons('nebulizer', this.sliderValues['sld8'], this.sliderValues['sld9']);
        }
        if ('sld10' in sliders || 'sld11' in sliders) {
            this.syncModeButtons('ozone', this.sliderValues['sld10'], this.sliderValues['sld11']);
        }
    }

    syncModeButtons(device, dutyValue, freeValue) {
        console.log(`🔄 syncModeButtons called: device=${device}, duty=${dutyValue} (${typeof dutyValue}), free=${freeValue} (${typeof freeValue})`);

        // Find which mode matches the current values
        const presets = this.modePresets[device];
        if (!presets) {
            console.warn(`⚠️ No presets found for device: ${device}`);
            return;
        }

        let matchingMode = null;

        for (const [mode, preset] of Object.entries(presets)) {
            console.log(`  🔍 Checking ${mode}: duty=${preset.duty} vs ${dutyValue}, free=${preset.free} vs ${freeValue}`);
            // Use loose equality to handle number type differences
            if (preset.duty == dutyValue && preset.free == freeValue) {
                matchingMode = mode;
                console.log(`  ✅ Match found: ${mode}`);
                break;
            }
        }

        if (!matchingMode) {
            console.warn(`  ❌ No matching mode found for duty=${dutyValue}, free=${freeValue}`);
        }

        // Update active class on mode buttons
        const modeBtns = document.querySelectorAll(`.mode-btn[data-device="${device}"]`);
        console.log(`  📍 Found ${modeBtns.length} mode buttons for ${device}`);

        modeBtns.forEach(btn => {
            if (matchingMode && btn.dataset.mode === matchingMode) {
                btn.classList.add('active');
                console.log(`  ✅ Added 'active' to ${btn.dataset.mode} button`);
            } else {
                btn.classList.remove('active');
                console.log(`  ❌ Removed 'active' from ${btn.dataset.mode} button`);
            }
        });
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connectionStatus');
        if (connected) {
            statusEl.innerHTML = '<i class="fas fa-wifi"></i> Connected';
            statusEl.className = 'connection-status connected';
        } else {
            statusEl.innerHTML = '<i class="fas fa-wifi-slash"></i> Disconnected';
            statusEl.className = 'connection-status disconnected';
        }
    }
    
    updateDateTime() {
        const now = new Date();
        const dateTimeStr = now.toLocaleString('tr-TR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('datetime').textContent = dateTimeStr;
    }
    
    confirmAction(message, callback) {
        // Use custom modal instead of browser's confirm()
        const modal = document.getElementById('confirmModal');
        const modalMessage = document.getElementById('confirmModalMessage');
        const cancelBtn = document.getElementById('confirmModalCancel');
        const confirmBtn = document.getElementById('confirmModalConfirm');

        // Set message
        modalMessage.textContent = message;

        // Show modal
        modal.style.display = 'flex';

        // Remove previous event listeners to prevent duplicates
        const newCancelBtn = cancelBtn.cloneNode(true);
        const newConfirmBtn = confirmBtn.cloneNode(true);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        // Cancel button - just hide modal
        newCancelBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        // Confirm button - execute callback and hide modal
        newConfirmBtn.addEventListener('click', () => {
            modal.style.display = 'none';
            callback();
        });

        // Click outside to cancel
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    saveSettings() {
        this.sendCommand('save_settings', {
            buttons: this.buttonStates,
            sliders: this.sliderValues
        });
        this.showToast(this.t('system.save'), 'success');
    }
    
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Animasyon için timeout
        setTimeout(() => toast.classList.add('show'), 100);
        
        // 3 saniye sonra kaldır
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
    
    // Language management methods
    t(key) {
        // Get translation by key (e.g., 'button.lighting')
        const keys = key.split('.');
        let value = translations[this.currentLanguage];
        for (const k of keys) {
            value = value?.[k];
        }
        return value || key;
    }
    
    setLanguage(lang) {
        if (!translations[lang]) return;
        
        this.currentLanguage = lang;
        localStorage.setItem('language', lang);
        this.applyTranslations();
        this.updateLanguageButtons();
    }
    
    applyTranslations() {
        // Update all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            
            // Update text content (preserve icons if present)
            if (element.querySelector('i')) {
                // Has icon, update only text nodes
                const textNodes = Array.from(element.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
                if (textNodes.length > 0) {
                    textNodes[0].textContent = translation;
                }
            } else {
                element.textContent = translation;
            }
        });
        
        // Update sensor status if needed
        if (this.sensorData.temperature.status === 'Reading...') {
            document.getElementById('tempStatus').textContent = this.t('sensor.reading');
        }
        if (this.sensorData.humidity.status === 'Reading...') {
            document.getElementById('humStatus').textContent = this.t('sensor.reading');
        }
        if (document.getElementById('oxyStatus') && this.sensorData.oxygen?.status === 'Reading...') {
            document.getElementById('oxyStatus').textContent = this.t('sensor.reading');
        }
    }
    
    updateLanguageButtons() {
        document.querySelectorAll('.lang-btn').forEach(btn => {
            const lang = btn.getAttribute('data-lang');
            btn.classList.toggle('active', lang === this.currentLanguage);
        });
    }
    
    // Simülasyon modu - WebSocket bağlantısı yoksa
    startSimulation() {
        console.log('Starting simulation mode...');
        this.showToast('Simülasyon modu aktif', 'warning');
        
        // Fake sensor verisi üret - oksijen sensörü dahil değil
        setInterval(() => {
            const temp = (Math.random() * 5 + 23).toFixed(1);
            const hum = (Math.random() * 10 + 60).toFixed(0);
            
            this.updateSensorData({
                temperature: { value: temp, status: 'Simulated' },
                humidity: { value: hum, status: 'Simulated' }
                // Oksijen sensörü simülasyonda yok
            });
        }, 2000);
    }
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    window.kuvozController = new KuvozController();
    console.log('Kuvoz Controller initialized');
    
    // Apply initial translations
    kuvozController.applyTranslations();
    kuvozController.updateLanguageButtons();
    
    // Language switcher event listeners
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.getAttribute('data-lang');
            kuvozController.setLanguage(lang);
        });
    });
});

// Service Worker kayıt (offline çalışma için)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW registration failed'));
}
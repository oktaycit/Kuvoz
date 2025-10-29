/**
 * Kuvoz Incubator Control System - Web Interface JavaScript
 * WebSocket tabanlı real-time kontrol sistemi
 */

class KuvozController {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
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
        
        this.sliderValues = {
            sld1: 30, sld2: 65, sld3: 25.0, sld4: 25.0,
            sld5: 30, sld6: 12, sld7: 8.0,
            // Duty/Free Time Settings
            sld8: 5,   // Nebulizer Duty Time (min)
            sld9: 25,  // Nebulizer Free Time (min) 
            sld10: 3,  // Ozone Duty Time (min)
            sld11: 60  // Ozone Free Time (min)
        };
        
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
        // GPIO Butonları
        document.querySelectorAll('.control-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
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
        
        // Sistem butonları
        document.getElementById('shutdownBtn').addEventListener('click', () => {
            this.confirmAction('Sistem kapatılacak. Emin misiniz?', () => {
                this.sendCommand('shutdown');
            });
        });
        
        document.getElementById('restartBtn').addEventListener('click', () => {
            this.confirmAction('Sistem yeniden başlatılacak. Emin misiniz?', () => {
                this.sendCommand('restart');
            });
        });
        
        document.getElementById('saveBtn').addEventListener('click', () => {
            this.saveSettings();
        });
    }
    
    connectWebSocket() {
        try {
            // Socket.IO connection with options
            this.socket = io('http://localhost:5000', {
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
                    if (data && data.name !== undefined) {
                        this.updateButtonState(data.name, data.state);
                    }
                } catch (e) {
                    console.error('Error handling button update:', e);
                }
            });
            
            this.socket.on('status_response', (data) => {
                try {
                    console.log('Received status response:', data);
                    if (data) {
                        if (data.sensors) this.updateSensorData(data.sensors);
                        if (data.buttons) this.updateButtonStates(data.buttons);
                        if (data.sliders) this.updateSliderStates(data.sliders);
                        if (data.timers) this.updateTimerData(data.timers);
                        
                        // Oksijen sensörü durumunu kontrol et
                        this.checkOxygenSensorAvailability(data.sensors);
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
                this.updateButtonStates(data.buttons);
                break;
                
            case 'slider_update':
                this.updateSliderStates(data.sliders);
                break;
                
            case 'status_response':
                this.updateSensorData(data.sensors);
                this.updateButtonStates(data.buttons);
                this.updateSliderStates(data.sliders);
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
        const newState = !this.buttonStates[name];
        this.buttonStates[name] = newState;
        
        // UI'yi güncelle
        const btn = document.getElementById(`btn_${name}`);
        if (newState) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
        
        // Komutu gönder
        this.sendCommand('toggle_button', {
            name: name,
            pin: parseInt(pin),
            state: newState
        });
        
        console.log(`Button ${name} (pin ${pin}): ${newState ? 'ON' : 'OFF'}`);
    }
    
    updateSlider(id, value) {
        this.sliderValues[id] = value;
        
        // Değer göstergesini güncelle
        const valueDisplay = document.getElementById(`${id}_value`);
        if (id === 'sld3' || id === 'sld4' || id === 'sld7') {
            valueDisplay.textContent = value.toFixed(1);
        } else {
            valueDisplay.textContent = Math.round(value);
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
                this.buttonStates[buttonName] = buttons[buttonName];
                
                const btn = document.getElementById(`btn_${buttonName}`);
                if (buttons[buttonName]) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
        });
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
                    if (sliderId === 'sld3' || sliderId === 'sld4' || sliderId === 'sld7') {
                        valueDisplay.textContent = sliders[sliderId].toFixed(1);
                    } else {
                        valueDisplay.textContent = Math.round(sliders[sliderId]);
                    }
                }
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
        if (confirm(message)) {
            callback();
        }
    }
    
    saveSettings() {
        this.sendCommand('save_settings', {
            buttons: this.buttonStates,
            sliders: this.sliderValues
        });
        this.showToast('Ayarlar kaydedildi', 'success');
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
});

// Service Worker kayıt (offline çalışma için)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW registration failed'));
}
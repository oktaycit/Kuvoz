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
            humidity: { value: '--', status: 'Reading...' },
            oxygen: { value: '--', status: 'Reading...' }
        };
        
        this.buttonStates = {
            b1: false, b2: false, b3: false, b4: false,
            b5: false, b6: false, b7: false, b8: false
        };
        
        this.sliderValues = {
            sld1: 30, sld2: 65, sld3: 25.0, sld4: 25.0,
            sld5: 30, sld6: 12, sld7: 8.0
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateDateTime();
        this.connectWebSocket();
        
        // DateTime güncellemesi her saniye
        setInterval(() => this.updateDateTime(), 1000);
        
        // Sensor güncelleme simülasyonu (WebSocket bağlantısı yoksa)
        setTimeout(() => {
            if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                this.startSimulation();
            }
        }, 2000);
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
            // Raspberry Pi'de Flask server localhost:5000'de çalışacak
            this.ws = new WebSocket('ws://localhost:5000/ws');
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                
                // Başlangıç durumunu iste
                this.sendCommand('get_status');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (e) {
                    console.error('WebSocket message parse error:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
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
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                command: command,
                data: data
            }));
        } else {
            console.log('WebSocket not connected, command ignored:', command);
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
    }
    
    updateSensorData(sensors) {
        if (sensors.temperature !== undefined) {
            this.sensorData.temperature = sensors.temperature;
            document.getElementById('temperature').textContent = 
                sensors.temperature.value + '°C';
            document.getElementById('tempStatus').textContent = 
                sensors.temperature.status;
        }
        
        if (sensors.humidity !== undefined) {
            this.sensorData.humidity = sensors.humidity;
            document.getElementById('humidity').textContent = 
                sensors.humidity.value + '%';
            document.getElementById('humStatus').textContent = 
                sensors.humidity.status;
        }
        
        if (sensors.oxygen !== undefined) {
            this.sensorData.oxygen = sensors.oxygen;
            document.getElementById('oxygen').textContent = 
                sensors.oxygen.value + '%';
            document.getElementById('oxyStatus').textContent = 
                sensors.oxygen.status;
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
        
        // Fake sensor verisi üret
        setInterval(() => {
            const temp = (Math.random() * 5 + 23).toFixed(1);
            const hum = (Math.random() * 10 + 60).toFixed(0);
            const oxy = (Math.random() * 2 + 20).toFixed(1);
            
            this.updateSensorData({
                temperature: { value: temp, status: 'Simulated' },
                humidity: { value: hum, status: 'Simulated' },
                oxygen: { value: oxy, status: 'Simulated' }
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
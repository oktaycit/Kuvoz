/**
 * Kuvoz Incubator Control System - Web Interface JavaScript
 * WebSocket tabanlı real-time kontrol sistemi
 */

// Translation dictionary
const translations = {
    tr: {
        app: {
            title: 'Veteriner Yoğun Bakım Ünitesi',
            web_interface: 'Web Arayüzü',
            title: 'Veteriner Yoğun Bakım Ünitesi',
            web_interface: 'Web Arayüzü',
            cleaning_title: 'Dezenfeksiyon Kontrolleri'
        },
        ai: {
            title: 'AI Analiz',
            motion: 'Hareket',
            status: 'Durum'
        },
        vitals: {
            title: 'Hayati Değerler',
            respiration: 'Solunum',
            confidence: 'Güven',
            status: 'Durum',
            bpm: 'BPM'
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
            nebulizer: 'Nebülizatör',
            uv_light: 'UV Işığı',
            ozone: 'Ozon',
            cooling: 'Soğutma'
        },
        slider: {
            temperature: 'Sıcaklık Hedefi (°C)',
            humidity: 'Nem Hedefi (%)',
            cooling: 'Soğutma Hedefi (°C)'
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
            co2: 'CO₂',
            reading: 'Okunuyor...',
            co2_excellent: 'Mükemmel',
            co2_good: 'İyi',
            co2_moderate: 'Kabul Edilebilir',
            co2_poor: 'Orta',
            co2_bad: 'Kötü',
            co2_very_bad: 'Çok Kötü'
        },
        time: {
            minutes: 'dakika',
            duty: 'duty',
            free: 'free'
        },
        system: {
            cleaning: 'Dezenfeksiyon',
            shutdown: 'Kapat',
            restart: 'Yeniden Başlat',
            save: 'Ayarları Kaydet',
            logs: 'Sistem Logları',
            shutdown_confirm: 'Sistem kapatılacak. Emin misiniz?',
            restart_confirm: 'Sistem yeniden başlatılacak. Emin misiniz?',
            cancel: 'İptal',
            confirm: 'Onayla'
        },
        modal: {
            exit_title: 'Dezenfeksiyon Sonlandırılacak',
            exit_message: 'Ana sayfaya dönmek dezenfeksiyon işlemini sonlandıracaktır. UV ve Ozon cihazları kapatılacak. Emin misiniz?'
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
            title: 'Veterinary Intensive Care Unit',
            web_interface: 'Web Interface',
            title: 'Veterinary Intensive Care Unit',
            web_interface: 'Web Interface',
            cleaning_title: 'Disinfection Controls'
        },
        ai: {
            title: 'AI Analysis',
            motion: 'Motion',
            status: 'Status'
        },
        vitals: {
            title: 'Vital Signs',
            respiration: 'Respiration',
            confidence: 'Confidence',
            status: 'Status',
            bpm: 'BPM'
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
            ozone: 'Ozone',
            cooling: 'Cooling'
        },
        slider: {
            temperature: 'Temperature Target (°C)',
            humidity: 'Humidity Target (%)',
            cooling: 'Cooling Target (°C)'
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
            co2: 'CO₂',
            reading: 'Reading...',
            co2_excellent: 'Excellent',
            co2_good: 'Good',
            co2_moderate: 'Acceptable',
            co2_poor: 'Moderate',
            co2_bad: 'Bad',
            co2_very_bad: 'Very Bad'
        },
        time: {
            minutes: 'minutes',
            duty: 'duty',
            free: 'free'
        },
        system: {
            cleaning: 'Disinfection',
            shutdown: 'Shutdown',
            restart: 'Restart',
            save: 'Save Settings',
            logs: 'System Logs',
            shutdown_confirm: 'System will be shut down. Are you sure?',
            restart_confirm: 'System will be restarted. Are you sure?',
            cancel: 'Cancel',
            confirm: 'Confirm'
        },
        modal: {
            exit_title: 'Disinfection Will End',
            exit_message: 'Returning to main page will end disinfection. UV and Ozone devices will be turned off. Are you sure?'
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
        // CO2 sensörü durumu - başlangıçta bilinmiyor
        this.co2SensorAvailable = false;

        // System settings cache - feature visibility control
        this.systemSettings = {
            cooling_enabled: true,
            dht_enabled: true,
            oxygen_enabled: true,
            co2_enabled: true,
            ai_enabled: false,
            logging_enabled: true
        };

        this.buttonStates = {
            b1: false, b2: false, b3: false, b4: false,
            b5: false, b6: false, b7: false, b8: false, b9: false
        };

        this.gpioOutputs = {
            b1: null, b2: null, b3: null, b4: null,
            b5: null, b6: null, b7: null, b8: null, b9: null
        };

        this.sliderValues = {
            sld1: parseFloat(document.getElementById('sld1')?.value) || 0,
            sld2: parseFloat(document.getElementById('sld2')?.value) || 60,
            sld3: parseFloat(document.getElementById('sld3')?.value) || 32.0,
            sld4: parseFloat(document.getElementById('sld4')?.value) || 32.0,
            sld5: parseFloat(document.getElementById('sld5')?.value) || 0,
            sld6: parseFloat(document.getElementById('sld6')?.value) || 0,
            sld7: parseFloat(document.getElementById('sld7')?.value) || 0,
            // Duty/Free Time Settings
            sld8: parseFloat(document.getElementById('sld8')?.value) || 5,   // Nebulizer Duty Time (min)
            sld9: parseFloat(document.getElementById('sld9')?.value) || 30,  // Nebulizer Free Time (min)
            sld10: parseFloat(document.getElementById('sld10')?.value) || 3,  // Ozone Duty Time (min)
            sld11: parseFloat(document.getElementById('sld11')?.value) || 60, // Ozone Free Time (min)
            sld12: parseFloat(document.getElementById('sld12')?.value) || 25.0 // Cooling Target (°C)
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

        // CO2 alarm tracking
        this.lastCO2AlarmTime = 0;
        this.co2AlarmInterval = 30000; // 30 saniye arayla alarm
        this.audioContext = null;
        this.audioEnabled = false;

        // Frontend fallback simulation (used only when Socket.IO cannot connect)
        this.simulationActive = false;
        this.simulationIntervalId = null;

        // Avoid duplicate polling intervals after reconnects
        this.statusPollIntervalId = null;
        this.initialStatusReceived = false;
        this.statusAppliedSinceConnect = false;

        // Auto-save timer for slider changes
        this.autoSaveTimer = null;

        // Client telemetry queue (for kiosk environments without console)
        this.pendingClientEvents = [];
        this.statusFallbackTimer = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupErrorReporting();
        this.updateDateTime();
        this.updateIPAddress();

        // Initialize slider displays with default values immediately (will be updated by backend)
        this.initSliderDisplays();

        this.connectWebSocket();
        this.startTimerCountdown();
        this.setupPageUnloadHandler();
        this.initAudioContext();

        // Initialize timer displays
        this.updateTimerDisplay('nebulizer');
        this.updateTimerDisplay('ozone');

        // DateTime güncellemesi her saniye
        setInterval(() => this.updateDateTime(), 1000);

        // Safety timeout for splash screen - hide anyway after 6 seconds 
        // to prevent getting stuck if socket connection or data loading is slow
        setTimeout(() => {
            if (typeof hideSplashScreen === 'function' && document.getElementById('splashScreen')?.style.display !== 'none') {
                console.warn('Splash screen safety timeout triggered - hiding splash screen');
                hideSplashScreen();
            }
        }, 6000);
    }

    initSliderDisplays() {
        // Initialize slider value displays with default values
        // These will be overwritten when backend sends real values via status_response
        const displayElements = [
            { id: 'sld3', format: 'temp' },   // Temperature
            { id: 'sld2', format: 'humidity' }, // Humidity
            { id: 'sld12', format: 'temp' }   // Cooling
        ];

        displayElements.forEach(({ id, format }) => {
            const valueDisplay = document.getElementById(`${id}_value`);
            if (valueDisplay && this.sliderValues[id] !== undefined) {
                if (format === 'temp') {
                    valueDisplay.textContent = parseFloat(this.sliderValues[id]).toFixed(1) + '°C';
                } else if (format === 'humidity') {
                    valueDisplay.textContent = Math.round(this.sliderValues[id]) + '%';
                }
            }
        });

        console.log('Slider displays initialized with default values');
    }

    setupPageUnloadHandler() {
        // Dezenfeksiyon sayfasından ayrılırken UV ve Ozon butonlarını kapat
        window.addEventListener('beforeunload', () => {
            const currentPage = this.getCurrentPage();
            if (currentPage === 'cleaning') {
                // UV (b7) ve Ozon (b8) butonlarını kapat
                if (this.buttonStates.b7 === true) {
                    this.socket?.emit('toggle_button', { button: 'b7', page: 'cleaning' });
                }
                if (this.buttonStates.b8 === true) {
                    this.socket?.emit('toggle_button', { button: 'b8', page: 'cleaning' });
                }
            }
        });

        // Sayfa değişimini tespit et (SPA benzeri davranış için)
        window.addEventListener('pagehide', () => {
            const currentPage = this.getCurrentPage();
            if (currentPage === 'cleaning') {
                if (this.buttonStates.b7 === true) {
                    this.socket?.emit('toggle_button', { button: 'b7', page: 'cleaning' });
                }
                if (this.buttonStates.b8 === true) {
                    this.socket?.emit('toggle_button', { button: 'b8', page: 'cleaning' });
                }
            }
        });
    }

    setupErrorReporting() {
        // Report JS errors to backend for kiosk debugging
        window.addEventListener('error', (event) => {
            const payload = {
                message: event.message,
                source: event.filename,
                line: event.lineno,
                col: event.colno,
                stack: event.error?.stack
            };
            this.reportClientEvent('js_error', payload);
        });

        window.addEventListener('unhandledrejection', (event) => {
            const reason = event.reason;
            const payload = {
                message: reason?.message || String(reason),
                stack: reason?.stack
            };
            this.reportClientEvent('unhandledrejection', payload);
        });
    }

    reportClientEvent(type, payload = {}) {
        const event = {
            type,
            payload,
            ts: Date.now(),
            page: this.getCurrentPage()
        };

        if (this.socket && this.socket.connected) {
            this.socket.emit('client_event', event);
        } else {
            this.pendingClientEvents.push(event);
        }
    }

    flushPendingClientEvents() {
        if (!this.socket || !this.socket.connected || this.pendingClientEvents.length === 0) {
            return;
        }
        this.pendingClientEvents.forEach((evt) => this.socket.emit('client_event', evt));
        this.pendingClientEvents = [];
    }

    scheduleStatusFallback() {
        if (this.statusFallbackTimer) {
            clearTimeout(this.statusFallbackTimer);
        }
        this.statusFallbackTimer = setTimeout(() => {
            if (this.statusAppliedSinceConnect) return;
            console.warn('No status_response received in time, using /api/status fallback');
            this.reportClientEvent('status_fallback_triggered');
            this.applyApiStatusFallback();
        }, 3000);
    }

    applyApiStatusFallback() {
        fetch('/api/status', { cache: 'no-store' })
            .then((res) => res.json())
            .then((data) => {
                if (!data) return;
                if (data.sliders) this.updateSliderStates(data.sliders);
                if (data.buttons) this.updateButtonStates(data.buttons);
                if (data.gpio_outputs) this.updateGpioOutputs(data.gpio_outputs);
                if (data.sensors) this.updateSensorData(data.sensors);
                if (data.system) this.updateSystemStatus(data.system);
                if (data.system_settings) this.applyFeatureVisibility(data.system_settings);
                if (data.timers) this.updateTimerData(data.timers);

                this.statusAppliedSinceConnect = true;

                if (!this.initialStatusReceived) {
                    this.initialStatusReceived = true;
                    if (typeof hideSplashScreen === 'function') {
                        hideSplashScreen();
                    }
                    this.showToast('Ayarlar yüklendi (Fallback)', 'success');
                }

                const summary = data.sliders ? {
                    sld2: data.sliders.sld2,
                    sld3: data.sliders.sld3,
                    sld12: data.sliders.sld12
                } : null;
                this.reportClientEvent('status_fallback_applied', { sliders: summary });
            })
            .catch((err) => {
                this.reportClientEvent('status_fallback_error', { message: err?.message || String(err) });
            });
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
        document.querySelectorAll('.slider-btn, .target-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sliderId = e.currentTarget.dataset.slider;
                const slider = document.getElementById(sliderId);

                if (!slider) return;

                const currentValue = parseFloat(slider.value);
                const min = parseFloat(slider.getAttribute('data-min') || slider.min || 0);
                const max = parseFloat(slider.getAttribute('data-max') || slider.max || 100);
                const step = parseFloat(slider.getAttribute('data-step') || slider.step || 1);

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

        // VetMarketi link - Kiosk modunda harici linkleri engelle
        const vetmarketiLink = document.querySelector('.vetmarketi-link');
        if (vetmarketiLink) {
            vetmarketiLink.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('VetMarketi link blocked in kiosk mode');
                this.showToast('Harici web sitelerine kiosk modunda erişilemez. Lütfen ayrı bir cihaz kullanın.', 'warning');
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

        // Save settings to backend to persist the mode change
        setTimeout(() => {
            this.sendCommand('save_settings');
            console.log('Mode change saved to backend');
        }, 500); // Small delay to ensure slider updates are processed first
    }

    updateDisinfectionMode(active, message) {
        console.log('Disinfection mode:', active, message);

        // Show toast notification
        if (message) {
            this.showToast(message, active ? 'warning' : 'success');
        }

        // Update UI if on main page
        const mainPage = document.getElementById('mainPage');
        if (mainPage && mainPage.style.display !== 'none') {
            let banner = document.getElementById('disinfectionModeBanner');

            if (active) {
                // Create banner if it doesn't exist
                if (!banner) {
                    banner = document.createElement('div');
                    banner.id = 'disinfectionModeBanner';
                    banner.style.cssText = `
                        position: fixed;
                        top: 60px;
                        left: 0;
                        right: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 12px 20px;
                        text-align: center;
                        font-weight: bold;
                        font-size: 16px;
                        z-index: 999;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        animation: pulse 2s ease-in-out infinite;
                    `;
                    banner.innerHTML = '🦠 DEZENFEKSIYON MODU AKTİF - Normal kontroller devre dışı';
                    document.body.appendChild(banner);

                    // Add pulse animation if not exists
                    if (!document.getElementById('pulseStyle')) {
                        const style = document.createElement('style');
                        style.id = 'pulseStyle';
                        style.textContent = `
                            @keyframes pulse {
                                0%, 100% { opacity: 1; }
                                50% { opacity: 0.85; }
                            }
                        `;
                        document.head.appendChild(style);
                    }
                }
                banner.style.display = 'block';
            } else {
                // Remove banner
                if (banner) {
                    banner.style.display = 'none';
                }
            }
        }
    }

    toggleAI() {
        const aiToggleBtn = document.getElementById('aiToggleBtn');
        const isCurrentlyActive = aiToggleBtn && aiToggleBtn.classList.contains('active');
        const newState = !isCurrentlyActive;

        console.log('Toggling AI:', isCurrentlyActive, '->', newState);

        this.socket.emit('toggle_ai', {
            enabled: newState
        });
    }

    updateAIToggleButton(enabled) {
        const aiToggleBtn = document.getElementById('aiToggleBtn');
        const aiStatusBadge = document.getElementById('aiStatusBadge');
        const aiPanel = document.getElementById('aiPanel');
        const compactAiPanel = document.getElementById('compactAiPanel');
        const aiStatusBadgeMini = document.getElementById('aiStatusBadgeMini');

        if (aiToggleBtn) {
            if (enabled) {
                aiToggleBtn.classList.add('active');
                aiToggleBtn.classList.remove('inactive');
            } else {
                aiToggleBtn.classList.remove('active');
                aiToggleBtn.classList.add('inactive');
            }
        }

        if (aiStatusBadge) {
            aiStatusBadge.textContent = enabled ? 'ACTIVE' : 'OFFLINE';
            aiStatusBadge.style.background = enabled ? '#28a745' : '#95a5a6';
        }

        if (aiStatusBadgeMini) {
            aiStatusBadgeMini.textContent = enabled ? 'ACTIVE' : 'OFFLINE';
            aiStatusBadgeMini.style.background = enabled ? '#28a745' : '#95a5a6';
        }

        // Show/hide AI panel based on enabled state
        if (aiPanel) {
            aiPanel.style.display = enabled ? 'block' : 'none';
        }

        // Show/hide compact AI panel based on enabled state
        if (compactAiPanel) {
            compactAiPanel.style.display = enabled ? 'block' : 'none';
        }

        console.log('AI toggle button updated:', enabled);
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

            this.socket.on('active_connections_update', (data) => {
                this.updateActiveConnections(data.connections);
            });

            this.socket.on('connect', () => {
                console.log('Socket.IO connected successfully');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                this.statusAppliedSinceConnect = false;

                // If we previously fell back to frontend simulation, stop it now.
                this.stopSimulation();

                // Telemetry for kiosk debugging
                this.reportClientEvent('socket_connected', { origin: window.location.origin });
                this.flushPendingClientEvents();

                // Request initial status with minimal delay (backend needs time to be ready)
                setTimeout(() => {
                    console.log('DEBUG: Emitting get_status request');
                    this.socket.emit('get_status', { page: this.getCurrentPage() });
                }, 100); // 100ms is enough for backend to be ready

                // Fallback if status_response never arrives
                this.scheduleStatusFallback();

                // Request status every 10 seconds for debugging
                if (this.statusPollIntervalId) {
                    clearInterval(this.statusPollIntervalId);
                }
                this.statusPollIntervalId = setInterval(() => {
                    if (this.socket && this.socket.connected) {
                        console.log('DEBUG: Periodic get_status request');
                        this.socket.emit('get_status', { page: this.getCurrentPage() });
                    }
                }, 10000);
            });

            this.socket.on('sensor_update', (data) => {
                try {
                    console.log('Received sensor update:', data);
                    if (data && data.sensors) {
                        // If real data arrives, stop frontend fallback simulation.
                        this.stopSimulation();
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
                        console.log('--- Status Response Received ---');
                        if (data.sliders) {
                            console.log('📊 RECEIVED SLIDERS FROM SERVER:', JSON.stringify(data.sliders));
                            this.updateSliderStates(data.sliders);
                        } else {
                            console.warn('⚠️ No sliders found in status response');
                        }

                        if (data.system) {
                            console.log('⚙️ System status received');
                            this.updateSystemStatus(data.system);
                        }

                        if (data.gpio_outputs) this.updateGpioOutputs(data.gpio_outputs);
                        if (data.buttons) this.updateButtonStates(data.buttons);

                        if (data.sensors) {
                            console.log('🌡️ Sensors received:', Object.keys(data.sensors));
                            // If real data arrives, stop frontend fallback simulation.
                            this.stopSimulation();
                            this.updateSensorData(data.sensors);
                        }

                        if (data.timers) {
                            console.log('⏱️ Timers received');
                            this.updateTimerData(data.timers);
                        }

                        // Explicitly update duty/free displays for index.html if sliders are in data
                        if (data.sliders) {
                            if (data.sliders.sld8) {
                                const el = document.getElementById('nebulizerDutyDisplay');
                                if (el) el.textContent = data.sliders.sld8;
                            }
                            if (data.sliders.sld9) {
                                const el = document.getElementById('nebulizerFreeDisplay');
                                if (el) el.textContent = data.sliders.sld9;
                            }
                            if (data.sliders.sld10) {
                                const el = document.getElementById('ozoneDutyDisplay');
                                if (el) el.textContent = data.sliders.sld10;
                            }
                            if (data.sliders.sld11) {
                                const el = document.getElementById('ozoneFreeDisplay');
                                if (el) el.textContent = data.sliders.sld11;
                            }
                        }

                        // Apply feature visibility based on settings
                        if (data.system_settings) this.applyFeatureVisibility(data.system_settings);

                        // Update disinfection mode banner
                        if (data.disinfection_mode !== undefined) {
                            this.updateDisinfectionMode(data.disinfection_mode, null);
                        }

                        // Update AI enabled state and button
                        if (data.ai_enabled !== undefined) {
                            this.updateAIToggleButton(data.ai_enabled);
                        }

                        // Show/hide AI panel based on availability
                        if (data.ai_available === false) {
                            const aiPanel = document.getElementById('aiPanel');
                            if (aiPanel) {
                                aiPanel.style.display = 'none';
                            }
                        } else if (data.ai_available === true) {
                            // Show AI panel if available (even if not enabled yet)
                            const aiPanel = document.getElementById('aiPanel');
                            if (aiPanel) {
                                aiPanel.style.display = 'block';
                            }
                        }

                        // Mark status applied for this connection and cancel fallback timer
                        this.statusAppliedSinceConnect = true;
                        if (this.statusFallbackTimer) {
                            clearTimeout(this.statusFallbackTimer);
                            this.statusFallbackTimer = null;
                        }

                        const summary = data.sliders ? {
                            sld2: data.sliders.sld2,
                            sld3: data.sliders.sld3,
                            sld12: data.sliders.sld12
                        } : null;
                        this.reportClientEvent('status_response_applied', { sliders: summary });

                        // Signal ready
                        if (!this.initialStatusReceived) {
                            this.initialStatusReceived = true;
                            // Hide splash screen when initial data is received
                            if (typeof hideSplashScreen === 'function') {
                                hideSplashScreen();
                            }
                            this.showToast('Ayarlar yüklendi (Server Ready)', 'success');
                            console.log('✅ Initial status successfully applied');
                        }
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

            this.socket.on('disinfection_mode', (data) => {
                try {
                    console.log('Received disinfection mode update:', data);
                    if (data) {
                        this.updateDisinfectionMode(data.active, data.message);
                    }
                } catch (e) {
                    console.error('Error handling disinfection mode update:', e);
                }
            });

            this.socket.on('ai_status', (data) => {
                try {
                    console.log('Received AI status update:', data);
                    if (data) {
                        this.updateAIToggleButton(data.enabled);
                        if (data.message) {
                            this.showToast(data.message, data.enabled ? 'success' : 'info');
                        }
                    }
                } catch (e) {
                    console.error('Error handling AI status update:', e);
                }
            });

            this.socket.on('ai_update', (data) => {
                try {
                    // console.log('Received AI update'); // Too verbose
                    if (data) {
                        this.updateAIDisplay(data);
                    }
                } catch (e) {
                    console.error('Error handling AI update:', e);
                }
            });

            this.socket.on('error', (data) => {
                try {
                    console.log('Received error:', data);
                    if (data && data.message) {
                        this.showToast(data.message, 'error');
                    }
                } catch (e) {
                    console.error('Error handling error message:', e);
                }
            });

            this.socket.on('success', (data) => {
                try {
                    console.log('Received success:', data);
                    if (data && data.message) {
                        this.showToast(data.message, 'success');
                    }
                } catch (e) {
                    console.error('Error handling success message:', e);
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

        // Hemen visual feedback göster - socket yanıtı bekleme
        if (this.gpioOutputs.hasOwnProperty(name)) {
            this.gpioOutputs[name] = newState;
            this.applyButtonVisual(name);
        }

        // Komutu gönder
        this.sendCommand('toggle_button', {
            name: name,
            pin: parseInt(pin, 10),
            state: newState,
            page: this.getCurrentPage()  // Send current page info
        });

        console.log(`Button ${name} (pin ${pin}): ${newState ? 'ON' : 'OFF'}`);
    }

    getCurrentPage() {
        // Detect current page from URL or HTML
        const path = window.location.pathname;
        if (path.includes('cleaning.html')) {
            return 'cleaning';
        }
        return 'index';
    }

    updateSlider(id, value) {
        this.sliderValues[id] = value;

        // Değer göstergesini güncelle (eğer varsa)
        const valueDisplay = document.getElementById(`${id}_value`);
        if (valueDisplay) {
            if (id === 'sld3' || id === 'sld7' || id === 'sld12') {
                // Temperature sliders: 1 decimal place + °C suffix
                valueDisplay.textContent = value.toFixed(1) + '°C';
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

        // Auto-save after 3 seconds of inactivity (debounced)
        this.scheduleAutoSave();
    }

    scheduleAutoSave() {
        // Clear existing timer if any
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
        }

        // Schedule new save after 3 seconds
        this.autoSaveTimer = setTimeout(() => {
            console.log('Auto-saving settings after slider change...');
            this.sendCommand('save_settings');
        }, 3000);
    }

    updateTimerData(timerUpdate) {
        if (timerUpdate.nebulizer) {
            this.timerData.nebulizer = timerUpdate.nebulizer;
            this.updateTimerDisplay('nebulizer');
            // Update button visual when phase changes (DUTY/FREE transitions)
            this.applyButtonVisual('b2');
        }

        if (timerUpdate.ozone) {
            this.timerData.ozone = timerUpdate.ozone;
            this.updateTimerDisplay('ozone');
            // Update button visual when phase changes (DUTY/FREE transitions)
            this.applyButtonVisual('b8');
        }
    }


    updateTimerDisplay(device) {
        const timer = this.timerData[device];
        const phaseElement = document.getElementById(`${device}Phase`);
        const countdownElement = document.getElementById(`${device}Countdown`);
        const progressElement = document.getElementById(`${device}Progress`);
        const dutyDisplayElement = document.getElementById(`${device}DutyDisplay`);
        const freeDisplayElement = document.getElementById(`${device}FreeDisplay`);

        if (!phaseElement || !countdownElement || !progressElement) return;

        // Update phase indicator
        phaseElement.textContent = timer.phase;
        phaseElement.className = `phase-badge ${timer.phase.toLowerCase()}`;

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

        // Update duty/free time displays with correct IDs
        if (dutyDisplayElement) {
            const dutySlider = device === 'nebulizer' ? 'sld8' : 'sld10';
            dutyDisplayElement.textContent = this.sliderValues[dutySlider];
        }

        if (freeDisplayElement) {
            const freeSlider = device === 'nebulizer' ? 'sld9' : 'sld11';
            freeDisplayElement.textContent = this.sliderValues[freeSlider];
        }
    }

    updateAIDisplay(data) {
        // Show AI panel only if AI is available and there's data
        const aiPanel = document.getElementById('aiPanel');
        if (aiPanel && data.frame && aiPanel.style.display === 'none') {
            aiPanel.style.display = 'block';
        }

        // Show compact AI panel if data exists (for index.html)
        const compactAiPanel = document.getElementById('compactAiPanel');
        if (compactAiPanel && data.frame) {
            compactAiPanel.style.display = 'block';
        }

        // Update Camera Feed (both panels)
        if (data.frame) {
            const img = document.getElementById('aiCameraFeed');
            if (img) {
                img.src = 'data:image/jpeg;base64,' + data.frame;
            }

            const compactImg = document.getElementById('compactCameraFeed');
            if (compactImg) {
                compactImg.src = 'data:image/jpeg;base64,' + data.frame;
            }
        }

        // Update Vision Status
        if (data.vision) {
            const motionStatus = document.getElementById('aiMotionStatus');
            if (motionStatus) {
                motionStatus.textContent = `${data.vision.status} (%${Math.round(data.vision.activity)})`;
                motionStatus.style.color = data.vision.status === 'HAREKETLI' ? '#2ecc71' : '#fff';
            }

            const compactMotionStatus = document.getElementById('compactMotionStatus');
            if (compactMotionStatus) {
                compactMotionStatus.textContent = data.vision.status || 'Bekleniyor...';
            }
        }

        // Update Vitals (both panels)
        this.updateVitalsDisplay(data.vitals);

        // Update Alerts
        if (data.analytics && data.analytics.anomalies) {
            const alertsList = document.getElementById('aiAlertsList');
            if (alertsList) {
                alertsList.innerHTML = ''; // Clear old alerts
                data.analytics.anomalies.forEach(alert => {
                    const li = document.createElement('li');
                    li.className = 'ai-alert-item';
                    li.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${alert}`;
                    alertsList.appendChild(li);
                });

                // Show notification for critical alerts (with 🔥 or ❗ emoji)
                if (!this.lastAlertCount) this.lastAlertCount = 0;
                const criticalAlerts = data.analytics.anomalies.filter(a =>
                    a.includes('KRİTİK') || a.includes('🔥') || a.includes('❗')
                );
                if (criticalAlerts.length > this.lastAlertCount) {
                    // New critical alert appeared
                    criticalAlerts.slice(this.lastAlertCount).forEach(alert => {
                        this.showToast('⚠️ AI Uyarı: ' + alert, 'error');
                    });
                }
                this.lastAlertCount = criticalAlerts.length;
            }
        }
    }

    updateVitalsDisplay(vitals) {
        const respirationEl = document.getElementById('vitalRespiration');
        const confidenceEl = document.getElementById('vitalConfidence');
        const statusEl = document.getElementById('vitalStatus');

        // Compact panel elements
        const compactRespirationEl = document.getElementById('compactRespiration');
        const compactConfidenceEl = document.getElementById('compactConfidence');
        const compactStatusEl = document.getElementById('compactStatus');

        // If not on this page / panel not present
        if (!respirationEl && !confidenceEl && !statusEl &&
            !compactRespirationEl && !compactConfidenceEl && !compactStatusEl) return;

        const bpmLabel = translations[this.currentLanguage]?.vitals?.bpm || 'BPM';

        if (!vitals || typeof vitals !== 'object') {
            if (respirationEl) respirationEl.textContent = '--';
            if (confidenceEl) confidenceEl.textContent = '--';
            if (statusEl) statusEl.textContent = '--';
            if (compactRespirationEl) compactRespirationEl.textContent = '--';
            if (compactConfidenceEl) compactConfidenceEl.textContent = '--';
            if (compactStatusEl) compactStatusEl.textContent = '--';
            return;
        }

        const bpm = vitals.respiration_bpm;
        const confidence = vitals.confidence;
        const status = vitals.status;

        if (respirationEl) {
            if (typeof bpm === 'number' && isFinite(bpm)) {
                respirationEl.textContent = `${bpm.toFixed(1)} ${bpmLabel}`;
            } else {
                respirationEl.textContent = '--';
            }
        }

        if (confidenceEl) {
            if (typeof confidence === 'number' && isFinite(confidence)) {
                confidenceEl.textContent = `%${Math.round(confidence * 100)}`;
            } else {
                confidenceEl.textContent = '--';
            }
        }

        if (statusEl) {
            statusEl.textContent = status || '--';
        }

        // Update compact panel
        if (compactRespirationEl) {
            if (typeof bpm === 'number' && isFinite(bpm)) {
                compactRespirationEl.textContent = `${bpm.toFixed(1)} ${bpmLabel}`;
            } else {
                compactRespirationEl.textContent = '--';
            }
        }

        if (compactConfidenceEl) {
            if (typeof confidence === 'number' && isFinite(confidence)) {
                compactConfidenceEl.textContent = `%${Math.round(confidence * 100)}`;
            } else {
                compactConfidenceEl.textContent = '--';
            }
        }

        if (compactStatusEl) {
            compactStatusEl.textContent = status || '--';
        }
    }

    startTimerCountdown() {
        // Update countdown displays every second
        // Backend handles button state logic and sends correct phase (DUTY/FREE/READY)
        // Frontend just counts down based on phase
        setInterval(() => {
            // Nebulizer timer - countdown if active phase
            if (this.timerData.nebulizer.remaining > 0 &&
                (this.timerData.nebulizer.phase === 'DUTY' || this.timerData.nebulizer.phase === 'FREE')) {
                this.timerData.nebulizer.remaining--;
                this.updateTimerDisplay('nebulizer');
            }

            // Ozone timer - countdown if active phase
            if (this.timerData.ozone.remaining > 0 &&
                (this.timerData.ozone.phase === 'DUTY' || this.timerData.ozone.phase === 'FREE')) {
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
        if (sensors.co2 && sensors.co2.status) {
            const co2Status = sensors.co2.status.toLowerCase();
            if (co2Status.includes('simulation') || co2Status.includes('simulated')) {
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
        // Daha sağlam kontrol: sensors.oxygen var mı ve value değeri geçerli mi?
        const hasOxygen = sensors &&
            sensors.oxygen !== undefined &&
            sensors.oxygen !== null &&
            sensors.oxygen.value !== undefined &&
            sensors.oxygen.value !== null &&
            sensors.oxygen.value !== '--';

        // Her zaman güncelle (durum değişmese bile ilk yüklemede)
        const wasAvailable = this.oxygenSensorAvailable;
        this.oxygenSensorAvailable = hasOxygen;

        // Toggle her zaman çağır (display durumu doğru olsun)
        this.toggleOxygenSensorDisplay(hasOxygen);

        // Sadece durum değiştiğinde log ve ozone mode güncelle
        if (hasOxygen !== wasAvailable) {
            this.updateOzoneMode(hasOxygen);

            if (hasOxygen) {
                console.log('✅ Oxygen sensor detected - showing on dashboard');
            } else {
                console.log('❌ Oxygen sensor not available - hiding from dashboard');
            }
        }
    }

    checkCO2SensorAvailability(sensors) {
        // Daha sağlam kontrol: sensors.co2 var mı ve value değeri geçerli mi?
        const hasCO2 = sensors &&
            sensors.co2 !== undefined &&
            sensors.co2 !== null &&
            sensors.co2.value !== undefined &&
            sensors.co2.value !== null &&
            sensors.co2.value !== '--';

        // Her zaman güncelle (durum değişmese bile ilk yüklemede)
        const wasAvailable = this.co2SensorAvailable;
        this.co2SensorAvailable = hasCO2;

        // Toggle her zaman çağır (display durumu doğru olsun)
        this.toggleCO2SensorDisplay(hasCO2);
        this.syncGasRowLayout();

        // Sadece durum değiştiğinde log
        if (hasCO2 !== wasAvailable) {
            if (hasCO2) {
                console.log('✅ CO2 sensor detected - showing on dashboard');
            } else {
                console.log('❌ CO2 sensor not available - hiding from dashboard');
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

    getCO2Comment(co2Value) {
        // CO2 değerini yorumla ve uygun yorum döndür
        if (co2Value === '--' || co2Value === null || co2Value === undefined) {
            return '';
        }

        try {
            const co2Level = parseFloat(co2Value);

            if (co2Level < 450) {
                return this.t('sensor.co2_excellent'); // Mükemmel / Excellent
            } else if (co2Level < 600) {
                return this.t('sensor.co2_good'); // İyi / Good
            } else if (co2Level < 1000) {
                return this.t('sensor.co2_moderate'); // Kabul Edilebilir / Acceptable
            } else if (co2Level < 1500) {
                return this.t('sensor.co2_poor'); // Orta / Moderate
            } else if (co2Level < 2000) {
                return this.t('sensor.co2_bad'); // Kötü / Bad
            } else {
                return this.t('sensor.co2_very_bad'); // Çok Kötü / Very Bad
            }
        } catch (e) {
            console.error('CO2 value parse error:', e);
            return '';
        }
    }

    // Audio context'i başlat ve kullanıcı etkileşimini bekle
    initAudioContext() {
        // Kullanıcı etkileşimi olduğunda audio'yu etkinleştir
        const enableAudio = () => {
            if (!this.audioContext) {
                try {
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    console.log('AudioContext oluşturuldu');
                } catch (e) {
                    console.error('AudioContext oluşturulamadı:', e);
                    return;
                }
            }

            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume().then(() => {
                    this.audioEnabled = true;
                    console.log('Audio etkinleştirildi (kullanıcı etkileşimi)');
                });
            } else {
                this.audioEnabled = true;
                console.log('Audio zaten aktif');
            }
        };

        // Herhangi bir tıklama veya dokunmada audio'yu etkinleştir
        document.addEventListener('click', enableAudio, { once: true });
        document.addEventListener('touchstart', enableAudio, { once: true });
        document.addEventListener('keydown', enableAudio, { once: true });
    }

    // CO2 alarm sesi çal
    playAlarmBeep() {
        if (!this.audioEnabled || !this.audioContext) {
            console.warn('Audio henüz etkinleştirilmedi - ekrana tıklayın');
            return;
        }

        try {
            // 3 kısa beep sesi
            for (let i = 0; i < 3; i++) {
                setTimeout(() => {
                    const oscillator = this.audioContext.createOscillator();
                    const gainNode = this.audioContext.createGain();

                    oscillator.connect(gainNode);
                    gainNode.connect(this.audioContext.destination);

                    oscillator.frequency.value = 800; // Hz
                    oscillator.type = 'square';

                    gainNode.gain.value = 0.5; // Ses seviyesi artırıldı

                    oscillator.start(this.audioContext.currentTime);
                    oscillator.stop(this.audioContext.currentTime + 0.2);
                }, i * 250);
            }

            console.log('CO2 alarm sesi çalındı');
        } catch (e) {
            console.error('Alarm sesi çalınamadı:', e);
        }
    }

    // CO2 değerini kontrol et ve gerekirse alarm çal
    checkCO2Alarm(co2Value) {
        if (co2Value === '--' || co2Value === null || co2Value === undefined) {
            return;
        }

        try {
            const co2Level = parseFloat(co2Value);
            const now = Date.now();

            // CO2 >= 1500 ppm ise alarm çal (Kötü veya Çok Kötü)
            if (co2Level >= 1500) {
                // Son alarmdan bu yana yeterli süre geçti mi?
                if (now - this.lastCO2AlarmTime >= this.co2AlarmInterval) {
                    this.playAlarmBeep();
                    this.lastCO2AlarmTime = now;
                    console.log(`CO2 ALARM: ${co2Level} ppm - Kötü hava kalitesi!`);
                }
            }
        } catch (e) {
            console.error('CO2 alarm kontrolü hatası:', e);
        }
    }

    toggleOxygenSensorDisplay(show) {
        const oxygenCard = document.querySelector('.sensor-card-large.oxygen');
        const oxygenCardOld = document.querySelector('.sensor-card.oxygen');
        const sensorGrid = document.querySelector('.sensor-grid-large');

        // Yeni büyük kart formatı
        if (oxygenCard) {
            if (show) {
                oxygenCard.style.display = 'flex';
                oxygenCard.classList.remove('sensor-hidden');
            } else {
                oxygenCard.style.display = 'none';
                oxygenCard.classList.add('sensor-hidden');
            }
        }

        // Eski kart formatı (geriye uyumluluk)
        if (oxygenCardOld) {
            if (show) {
                oxygenCardOld.style.display = 'block';
                oxygenCardOld.classList.remove('sensor-hidden');
            } else {
                oxygenCardOld.style.display = 'none';
                oxygenCardOld.classList.add('sensor-hidden');
            }
        }

        this.syncGasRowLayout();
    }

    toggleCO2SensorDisplay(show) {
        const co2Card = document.querySelector('.sensor-card-large.co2');
        const co2CardOld = document.querySelector('.sensor-card.co2');

        // Yeni büyük kart formatı
        if (co2Card) {
            if (show) {
                co2Card.style.display = 'flex';
                co2Card.classList.remove('sensor-hidden');
            } else {
                co2Card.style.display = 'none';
                co2Card.classList.add('sensor-hidden');
            }
        }

        // Eski kart formatı (geriye uyumluluk)
        if (co2CardOld) {
            if (show) {
                co2CardOld.style.display = 'block';
                co2CardOld.classList.remove('sensor-hidden');
            } else {
                co2CardOld.style.display = 'none';
                co2CardOld.classList.add('sensor-hidden');
            }
        }

        this.syncGasRowLayout();
    }

    syncGasRowLayout() {
        const gasRow = document.getElementById('gasRow');
        const oxygenCard = document.getElementById('oxygenCard');
        const co2Card = document.getElementById('co2Card');
        if (!gasRow) return;

        const o2Visible = oxygenCard && oxygenCard.style.display !== 'none';
        const co2Visible = co2Card && co2Card.style.display !== 'none';

        if (o2Visible && co2Visible) {
            gasRow.classList.add('duo');
        } else {
            gasRow.classList.remove('duo');
        }
    }

    updateSensorData(sensors) {
        console.log('DEBUG updateSensorData called with:', sensors);

        // Simülasyon modu kontrolü
        this.checkSimulationMode(sensors);

        // Oksijen sensörü durumunu kontrol et
        this.checkOxygenSensorAvailability(sensors);
        // CO2 sensörü durumunu kontrol et
        this.checkCO2SensorAvailability(sensors);

        if (sensors.temperature !== undefined) {
            console.log('DEBUG temperature data:', sensors.temperature);
            this.sensorData.temperature = sensors.temperature.value;
            const tempElement = document.getElementById('temperature');
            const tempStatusElement = document.getElementById('tempStatus');

            if (tempElement) {
                const tempValue = sensors.temperature.value;
                tempElement.textContent = tempValue === '--' ? '--' : tempValue + '°C';
                console.log('DEBUG temperature element updated:', tempElement.textContent);
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
                const humValue = sensors.humidity.value;
                humElement.textContent = humValue === '--' ? '--' : humValue + '%';
                console.log('DEBUG humidity element updated:', humElement.textContent);
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
                const oxyValue = sensors.oxygen.value;
                oxyElement.textContent = oxyValue === '--' ? '--' : oxyValue + '%';
                console.log('DEBUG oxygen element updated:', oxyElement.textContent);
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

        // CO2 sensörü sadece mevcut olduğunda güncelle
        if (sensors.co2 !== undefined && this.co2SensorAvailable) {
            console.log('DEBUG CO2 data:', sensors.co2);
            const co2Element = document.getElementById('co2');
            const co2StatusElement = document.getElementById('co2Status');
            const co2CommentElement = document.getElementById('co2Comment');

            if (co2Element) {
                const co2Value = sensors.co2.value;
                co2Element.textContent = co2Value === '--' ? '--' : co2Value + 'ppm';
                console.log('DEBUG co2 element updated:', co2Element.textContent);
            } else {
                console.error('DEBUG co2 element not found');
            }

            if (co2StatusElement) {
                co2StatusElement.textContent = sensors.co2.status || '';
                console.log('DEBUG co2 status updated:', sensors.co2.status);
            } else {
                console.error('DEBUG co2Status element not found');
            }

            // CO2 yorumunu güncelle
            if (co2CommentElement) {
                const comment = this.getCO2Comment(sensors.co2.value);
                co2CommentElement.textContent = comment;
                console.log('DEBUG co2 comment updated:', comment);
            }

            // CO2 alarm kontrolü
            this.checkCO2Alarm(sensors.co2.value);
        }
    }

    updateButtonStates(buttons) {
        Object.keys(buttons).forEach(buttonName => {
            if (this.buttonStates.hasOwnProperty(buttonName)) {
                const oldState = this.buttonStates[buttonName];
                const newState = Boolean(buttons[buttonName]);
                this.buttonStates[buttonName] = newState;

                // Special case: On cleaning page, sync b7/b8 buttonState with GPIO state
                const currentPage = this.getCurrentPage();
                if (currentPage === 'cleaning' && (buttonName === 'b7' || buttonName === 'b8')) {
                    const gpioState = this.gpioOutputs[buttonName];
                    if (gpioState !== null && gpioState !== undefined) {
                        // If GPIO is actually OFF but button state is ON, correct it
                        if (newState === true && gpioState === false) {
                            console.log(`Correcting ${buttonName} buttonState to match GPIO (OFF)`);
                            this.buttonStates[buttonName] = false;
                        }
                    }
                }

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
        if (!btn) {
            console.log(`DEBUG applyButtonVisual: Button ${buttonName} element not found!`);
            return;
        }

        // Tüm state sınıflarını kaldır
        btn.classList.remove('active', 'active-on', 'active-off', 'state-on', 'state-off', 'state-disabled', 'state-unknown');

        const buttonState = this.buttonStates[buttonName];  // Fonksiyon aktif mi?
        const gpioState = this.gpioOutputs[buttonName];     // GPIO çıkış durumu

        console.log(`DEBUG applyButtonVisual: ${buttonName} - buttonState=${buttonState}, gpioState=${gpioState}, gpioAvailable=${this.gpioAvailable}`);

        // B9 (Cooling) - Özel soğutma mantığı
        if (buttonName === 'b9') {
            if (!buttonState) {
                // Buton kapalı → Beyaz
                btn.classList.add('state-unknown');
                console.log(`DEBUG b9: state-unknown (white) - button OFF`);
                return;
            }

            // Buton açık → Hedef kontrolü
            const currentTemp = parseFloat(this.sensorData.temperature?.value || 0);
            const coolingTarget = this.sliderValues['sld12'] || 0;

            if (coolingTarget === 0) {
                // Manuel mod → Yeşil
                btn.classList.add('state-on');
                console.log(`DEBUG b9: state-on (green) - MANUAL mode`);
            } else if (gpioState === true) {
                // Aktif soğutuyor (GPIO LOW) → Kırmızı
                btn.classList.add('state-off');
                console.log(`DEBUG b9: state-off (red) - COOLING (${currentTemp}°C > ${coolingTarget}°C)`);
            } else {
                // Hedefte (GPIO HIGH) → Yeşil
                btn.classList.add('state-on');
                console.log(`DEBUG b9: state-on (green) - TARGET REACHED (${currentTemp}°C ≤ ${coolingTarget}°C)`);
            }
            return;
        }

        // Special handling for UV/Ozone buttons on non-cleaning pages
        const currentPage = this.getCurrentPage();
        if ((buttonName === 'b7' || buttonName === 'b8') && currentPage !== 'cleaning') {
            // On non-cleaning pages, always show UV/Ozone as disabled/unknown
            btn.classList.add('state-disabled');
            console.log(`DEBUG ${buttonName}: Disabled on non-cleaning page`);
            return;
        }

        // GPIO kullanılamıyorsa -> Disabled (gri)
        if (this.gpioAvailable === false) {
            btn.classList.add('state-disabled');
            console.log(`DEBUG ${buttonName}: Added state-disabled (GPIO unavailable)`);
            return;
        }

        // SPECIAL: B2 (Nebulizer) and B8 (Ozone) - Phase-based coloring
        // Check buttonState first, then use phase for color
        if (buttonName === 'b2') {
            console.log(`DEBUG B2 Nebulizer: buttonState=${buttonState}, phase=${this.timerData.nebulizer?.phase}`);

            // Button OFF → Beyaz
            if (!buttonState) {
                btn.classList.add('state-unknown');
                console.log(`DEBUG B2: Button OFF - state-unknown (white)`);
                return;
            }

            // Button ON → Phase-based coloring
            const phase = this.timerData.nebulizer?.phase || 'READY';
            if (phase === 'DUTY') {
                btn.classList.add('state-off'); // Kırmızı - Aktif çalışıyor
                console.log(`DEBUG B2: DUTY - state-off (red)`);
            } else {
                // READY or FREE → Yeşil
                btn.classList.add('state-on');
                console.log(`DEBUG B2: ${phase} - state-on (green)`);
            }
            return;
        }

        if (buttonName === 'b8') {
            console.log(`DEBUG B8 Ozone: buttonState=${buttonState}, phase=${this.timerData.ozone?.phase}`);

            // Button OFF → Beyaz
            if (!buttonState) {
                btn.classList.add('state-unknown');
                console.log(`DEBUG B8: Button OFF - state-unknown (white)`);
                return;
            }

            // Button ON → Phase-based coloring
            const phase = this.timerData.ozone?.phase || 'READY';
            if (phase === 'DUTY') {
                btn.classList.add('state-off'); // Kırmızı - Aktif çalışıyor
                console.log(`DEBUG B8: DUTY - state-off (red)`);
            } else {
                // READY or FREE → Yeşil
                btn.classList.add('state-on');
                console.log(`DEBUG B8: ${phase} - state-on (green)`);
            }
            return;
        }

        // Buton PASİF (fonksiyon kapalı) -> Beyaz
        if (!buttonState) {
            btn.classList.add('state-unknown');
            console.log(`DEBUG ${buttonName}: Added state-unknown (button OFF)`);
            return;
        }

        // Buton AKTİF (fonksiyon açık) -> Hedef değer kontrolü + GPIO durumu
        if (gpioState === null || gpioState === undefined) {
            // GPIO durumu henüz bilinmiyor -> Beyaz
            btn.classList.add('state-unknown');
            console.log(`DEBUG ${buttonName}: Added state-unknown (GPIO null, waiting for response)`);
            return;
        }

        // Hedef değere ulaşıldı mı kontrolü
        let targetReached = false;
        let targetInfo = '';

        try {
            // B3: Nem Kontrol
            if (buttonName === 'b3') {
                const currentHumidity = parseFloat(this.sensorData.humidity?.value || 0);
                const targetHumidity = this.sliderValues['sld2'] || 0;
                targetReached = currentHumidity >= (targetHumidity - 2); // 2% hysteresis tolerance
                targetInfo = `Humidity ${currentHumidity}% vs target ${targetHumidity}%`;
            }
            // B4: Karbon Isıtıcı
            else if (buttonName === 'b4') {
                const currentTemp = parseFloat(this.sensorData.temperature?.value || 0);
                const targetTemp = this.sliderValues['sld3'] || 0;
                targetReached = currentTemp >= (targetTemp - 0.5); // 0.5°C hysteresis tolerance
                targetInfo = `Carbon Temp ${currentTemp}°C vs target ${targetTemp}°C`;
            }
            // B5: IR Isıtıcı
            else if (buttonName === 'b5') {
                const currentTemp = parseFloat(this.sensorData.temperature?.value || 0);
                const targetTemp = this.sliderValues['sld3'] || 0;
                targetReached = currentTemp >= (targetTemp - 0.5); // 0.5°C hysteresis tolerance
                targetInfo = `IR Temp ${currentTemp}°C vs target ${targetTemp}°C`;
            }
            // B9: Soğutma - Sıcaklık kontrollü (cooling target)
            else if (buttonName === 'b9') {
                const currentTemp = parseFloat(this.sensorData.temperature?.value || 0);
                const coolingTarget = this.sliderValues['sld12'] || 0;

                if (coolingTarget === 0) {
                    // Manuel mod - slider 0 ise
                    targetReached = true;
                    targetInfo = `Cooling MANUAL mode - always ON`;
                } else {
                    // Oto mod - hedef sıcaklığın altındaysa hedef ulaşıldı (soğutma kapanmalı)
                    targetReached = currentTemp <= (coolingTarget + 0.5); // 0.5°C hysteresis tolerance
                    targetInfo = `Cooling ${currentTemp}°C vs target ${coolingTarget}°C`;
                }
            }
            // B1, B6, B7: Manuel butonlar - hedef yok, sadece aktifse yeşil
            // B2 and B8 handled above with phase-based coloring
            else {
                targetReached = true; // Manuel butonlar her zaman "hedefte"
                targetInfo = 'Manual button - always target reached when ON';
            }
        } catch (e) {
            console.error(`Error calculating target for ${buttonName}:`, e);
            targetReached = false;
        }

        // Renk ataması: Hedef + GPIO state kombinasyonu
        if (targetReached) {
            // Hedef değere ulaşıldı → YEŞİL (başarı)
            btn.classList.add('state-on');
            console.log(`DEBUG ${buttonName}: Added state-on (TARGET REACHED) - ${targetInfo}`);
        } else if (gpioState === true) {
            // Hedefin altında VE GPIO LOW (çalışıyor) → KIRMIZI (aktif çalışıyor)
            btn.classList.add('state-off');
            console.log(`DEBUG ${buttonName}: Added state-off (WORKING - below target) - ${targetInfo}`);
        } else {
            // Hedefin altında ama GPIO HIGH (bekliyor) → YEŞİL (normal durum)
            btn.classList.add('state-on');
            console.log(`DEBUG ${buttonName}: Added state-on (IDLE - waiting) - ${targetInfo}`);
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
                // Only show if both hardware available AND enabled in settings
                const shouldShow = hasOxygen && this.systemSettings.oxygen_enabled !== false;
                this.toggleOxygenSensorDisplay(shouldShow);
                this.updateOzoneMode(hasOxygen);
            }
        }

        if (system.co2_available !== undefined) {
            const hadCO2 = this.co2SensorAvailable;
            const hasCO2 = Boolean(system.co2_available);
            if (hadCO2 !== hasCO2) {
                this.co2SensorAvailable = hasCO2;
                // Only show if both hardware available AND enabled in settings
                const shouldShow = hasCO2 && this.systemSettings.co2_enabled !== false;
                this.toggleCO2SensorDisplay(shouldShow);
            }
        }

        // Update IP address display if network_ip is provided
        if (system.network_ip && system.port) {
            this.updateIPAddress(`${system.network_ip}:${system.port}`);
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

    applyFeatureVisibility(settings) {
        // Ayarlar sayfasından devre dışı bırakılan özellikleri gizle
        console.log('🔧 Applying feature visibility:', settings);

        // Cache settings for later use
        this.systemSettings = { ...this.systemSettings, ...settings };

        // DHT Sensör kartlarını gizle/göster (Sıcaklık ve Nem)
        if (settings.dht_enabled === false) {
            const tempCard = document.querySelector('.sensor-card-large.temperature');
            const humCard = document.querySelector('.sensor-card-large.humidity');
            if (tempCard) tempCard.style.display = 'none';
            if (humCard) humCard.style.display = 'none';
        } else {
            const tempCard = document.querySelector('.sensor-card-large.temperature');
            const humCard = document.querySelector('.sensor-card-large.humidity');
            if (tempCard) tempCard.style.display = '';
            if (humCard) humCard.style.display = '';
        }

        // Oksijen Sensör kartını gizle/göster
        if (settings.oxygen_enabled === false) {
            // Ayarlardan kapatılmış - her durumda gizle
            this.toggleOxygenSensorDisplay(false);
        } else if (settings.oxygen_enabled === true && this.oxygenSensorAvailable) {
            // Ayarlardan açık VE donanım mevcut - göster
            this.toggleOxygenSensorDisplay(true);
        }

        // CO2 Sensör kartını gizle/göster
        if (settings.co2_enabled === false) {
            // Ayarlardan kapatılmış - her durumda gizle
            this.toggleCO2SensorDisplay(false);
        } else if (settings.co2_enabled === true && this.co2SensorAvailable) {
            // Ayarlardan açık VE donanım mevcut - göster
            this.toggleCO2SensorDisplay(true);
        }

        // Soğutma butonunu ve hedef kartını gizle/göster (b9)
        if (settings.cooling_enabled === false) {
            const coolingBtn = document.getElementById('btn_b9');
            const coolingTarget = document.querySelector('.target-item.cooling-target');
            if (coolingBtn) coolingBtn.style.display = 'none';
            if (coolingTarget) coolingTarget.style.display = 'none';
        } else {
            const coolingBtn = document.getElementById('btn_b9');
            const coolingTarget = document.querySelector('.target-item.cooling-target');
            if (coolingBtn) coolingBtn.style.display = '';
            if (coolingTarget) coolingTarget.style.display = '';
        }

        // AI panelini gizle/göster
        if (settings.ai_enabled === false) {
            const aiPanel = document.getElementById('aiPanel');
            const compactAiPanel = document.getElementById('compactAiPanel');
            if (aiPanel) aiPanel.style.display = 'none';
            if (compactAiPanel) compactAiPanel.style.display = 'none';
        } else {
            // AI panelleri sadece veri geldiğinde gösterilir, burada sadece enable ediyoruz
            // Gerçek görünürlük updateAIDisplay tarafından kontrol edilir
        }
    }

    updateSliderStates(sliders) {
        console.log('UPDATING SLIDERS:', JSON.stringify(sliders));
        Object.keys(sliders).forEach(sliderId => {
            // Update local memory
            this.sliderValues[sliderId] = sliders[sliderId];

            const slider = document.getElementById(sliderId);
            const valueDisplay = document.getElementById(`${sliderId}_value`);

            console.log(`- Slider ${sliderId}: value=${sliders[sliderId]}, elementFound=${!!slider}, displayFound=${!!valueDisplay}`);

            if (slider) {
                slider.value = sliders[sliderId];
            }

            if (valueDisplay) {
                if (sliderId === 'sld3' || sliderId === 'sld7' || sliderId === 'sld12' || sliderId === 'sld4') {
                    // Temperature and special float sliders
                    valueDisplay.textContent = parseFloat(sliders[sliderId]).toFixed(1) + '°C';
                } else if (sliderId === 'sld2') {
                    // Humidity
                    valueDisplay.textContent = Math.round(sliders[sliderId]) + '%';
                } else {
                    // Integer sliders
                    valueDisplay.textContent = Math.round(sliders[sliderId]);
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

    updateActiveConnections(connections) {
        // Optional UI hook; keep safe to avoid crashing if element is missing
        try {
            const el = document.getElementById('activeConnections');
            if (!el) return;
            if (!Array.isArray(connections)) {
                el.textContent = '--';
                return;
            }
            el.textContent = connections.length.toString();
        } catch (e) {
            console.warn('updateActiveConnections failed:', e);
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

    updateIPAddress(networkIP = null) {
        const ipAddressElement = document.getElementById('ipAddressValue');
        if (ipAddressElement) {
            if (networkIP) {
                // Backend'den gelen network IP varsa onu göster
                ipAddressElement.textContent = networkIP;
            } else {
                // Yoksa window.location.host'u göster
                const host = window.location.host;
                ipAddressElement.textContent = host;
            }
        }
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
        console.log('setLanguage called with:', lang);
        if (!translations[lang]) {
            console.error('Translation not found for language:', lang);
            return;
        }

        console.log('Changing language to:', lang);
        this.currentLanguage = lang;
        localStorage.setItem('language', lang);
        this.applyTranslations();
        this.updateLanguageButtons();
        console.log('Language changed successfully to:', lang);
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
        const tempStatus = document.getElementById('tempStatus');
        if (tempStatus && this.sensorData.temperature.status === 'Reading...') {
            tempStatus.textContent = this.t('sensor.reading');
        }

        const humStatus = document.getElementById('humStatus');
        if (humStatus && this.sensorData.humidity.status === 'Reading...') {
            humStatus.textContent = this.t('sensor.reading');
        }

        const oxyStatus = document.getElementById('oxyStatus');
        if (oxyStatus && this.sensorData.oxygen?.status === 'Reading...') {
            oxyStatus.textContent = this.t('sensor.reading');
        }

        const co2Status = document.getElementById('co2Status');
        if (co2Status) {
            const st = document.getElementById('co2Status').textContent;
            if (!st || st.toLowerCase().includes('reading') || st.toLowerCase().includes('okunuyor')) {
                document.getElementById('co2Status').textContent = this.t('sensor.reading');
            }
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
        if (this.simulationActive) return;

        console.log('Starting simulation mode (frontend fallback)...');
        this.simulationActive = true;
        this.showToast('Simülasyon modu aktif (bağlantı yok)', 'warning');

        // Fake sensor verisi üret - oksijen sensörü dahil değil
        this.simulationIntervalId = setInterval(() => {
            const temp = (Math.random() * 5 + 23).toFixed(1);
            const hum = (Math.random() * 10 + 60).toFixed(0);

            this.updateSensorData({
                temperature: { value: temp, status: 'Simulated' },
                humidity: { value: hum, status: 'Simulated' }
                // Oksijen sensörü simülasyonda yok
            });
        }, 2000);
    }

    stopSimulation() {
        if (!this.simulationActive) return;

        console.log('Stopping simulation mode (frontend fallback)...');
        this.simulationActive = false;

        if (this.simulationIntervalId) {
            clearInterval(this.simulationIntervalId);
            this.simulationIntervalId = null;
        }
    }
}

// Splash screen'i kaldır
function hideSplashScreen() {
    const splashScreen = document.getElementById('splashScreen');
    if (splashScreen) {
        console.log('Hiding splash screen...');
        splashScreen.classList.add('fade-out');
        setTimeout(() => {
            splashScreen.style.display = 'none';
            console.log('Splash screen hidden');
        }, 500);
    }
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Splash'i artık otomatik kaldırmıyoruz, veriler geldiğinde kalkacak
        // Ancak KuvozController içinde bir safety timeout (6s) ekledik.

        window.kuvozController = new KuvozController();
        window.kuvoz = window.kuvozController; // Alias for shorter HTML onclick handlers
        console.log('Kuvoz Controller initialized');
    } catch (e) {
        console.error('CRITICAL ERROR during initialization:', e);
        // Hata durumunda splash screen'i kaldır ki arayüz görülebilsin
        if (typeof hideSplashScreen === 'function') hideSplashScreen();
    }

    // Başlangıçta sensör kartlarını gizle (sensör verisi gelene kadar)
    const oxygenCard = document.getElementById('oxygenCard');
    const co2Card = document.getElementById('co2Card');
    if (oxygenCard) {
        oxygenCard.style.display = 'none';
        oxygenCard.classList.add('sensor-hidden');
    }
    if (co2Card) {
        co2Card.style.display = 'none';
        co2Card.classList.add('sensor-hidden');
    }
    console.log('Initial sensor cards hidden - waiting for sensor data');

    // Apply initial translations
    kuvozController.applyTranslations();
    kuvozController.updateLanguageButtons();

    // Language switcher event listeners
    console.log('Setting up language button listeners...');
    const langButtons = document.querySelectorAll('.lang-btn');
    console.log('Found language buttons:', langButtons.length);

    langButtons.forEach(btn => {
        console.log('Adding listener to button:', btn.getAttribute('data-lang'));
        btn.addEventListener('click', () => {
            const lang = btn.getAttribute('data-lang');
            console.log('Language button clicked:', lang);
            window.kuvozController.setLanguage(lang);
        });
    });

    // Cleaning page specific logic - Exit confirmation modal
    const homeBtn = document.getElementById('homeBtn');
    const exitModal = document.getElementById('exitModal');
    const exitModalCancel = document.getElementById('exitModalCancel');
    const exitModalConfirm = document.getElementById('exitModalConfirm');

    if (homeBtn && exitModal) {
        console.log('Cleaning page detected - setting up exit confirmation');

        // Show exit confirmation modal when home button clicked
        homeBtn.addEventListener('click', function () {
            exitModal.style.display = 'flex';
        });

        // Cancel - hide modal
        if (exitModalCancel) {
            exitModalCancel.addEventListener('click', function () {
                exitModal.style.display = 'none';
            });
        }

        // Confirm - turn off UV/Ozone and navigate home
        if (exitModalConfirm) {
            exitModalConfirm.addEventListener('click', function () {
                console.log('Exit confirm clicked - turning off UV and Ozone');

                // Turn off B7 (UV) and B8 (Ozone) using KuvozController
                if (kuvozController.buttonStates['b7']) {
                    kuvozController.toggleButton('b7', 21);
                }
                if (kuvozController.buttonStates['b8']) {
                    kuvozController.toggleButton('b8', 26);
                }

                // Wait for commands to be sent, then navigate
                setTimeout(function () {
                    console.log('Navigating to index.html');
                    window.location.href = 'index.html';
                }, 500);
            });
        }
    }
});

// Service Worker kaldırıldı: sw.js dosyası yoktu ve her yüklemede hata üretiyordu.

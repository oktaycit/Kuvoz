/**
 * Kuvoz Incubator Control System - Web Interface JavaScript
 * WebSocket tabanlı real-time kontrol sistemi
 */

// Translation dictionary
// Global translations object for compatibility with other pages (e.g., patient_info.html)
globalThis.translations = {};

const KUVOZ_SOCKET_TRANSPORTS = ['polling'];

function kuvozSocketOptions(options = {}) {
    return {
        timeout: 5000,
        upgrade: false,
        rememberUpgrade: false,
        ...options,
        transports: options.transports || KUVOZ_SOCKET_TRANSPORTS
    };
}

function createKuvozSocket(urlOrOptions, maybeOptions) {
    if (typeof io === 'undefined') {
        throw new Error('Socket.IO client is not loaded');
    }

    if (typeof urlOrOptions === 'string') {
        return io(urlOrOptions, kuvozSocketOptions(maybeOptions || {}));
    }

    return io(kuvozSocketOptions(urlOrOptions || {}));
}

globalThis.kuvozSocketOptions = kuvozSocketOptions;
globalThis.createKuvozSocket = createKuvozSocket;

async function loadTranslationFile(lang) {
    if (globalThis.translations[lang]) return true;

    try {
        console.log(`Fetching translation file for: ${lang}`);
        const response = await fetch(`translations/${lang}.json?v=${new Date().getTime()}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        globalThis.translations[lang] = data;
        console.log(`Translations loaded for: ${lang}`);
        return true;
    } catch (error) {
        console.error(`Failed to load translations for ${lang}:`, error);
        return false;
    }
}

function resolveCurrentPageName() {
    const dataPage = document.documentElement?.dataset?.page;
    if (typeof dataPage === 'string' && dataPage.trim()) {
        return dataPage.trim().toLowerCase();
    }

    const fileName = (window.location.pathname.split('/').pop() || 'index.html').toLowerCase();
    if (!fileName || fileName === '/') {
        return 'index';
    }

    return fileName.endsWith('.html') ? (fileName.slice(0, -5) || 'index') : fileName;
}

class KuvozController {
    constructor(options = {}) {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.pageName = options.pageName || resolveCurrentPageName();
        this.connectSocketEnabled = options.connectSocket !== false;
        this.socket = null;

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
            logging_enabled: true,
            fan_output_mode: 'relay',
            fan_control_mode: 'auto',
            screen_orientation: 'auto',
            camera_transform: 'normal'
        };
        this.primaryClimateSensor = null;
        this.fallbackClimateSensor = null;
        this.oxygenSensorMode = 'optional';
        this.careSettings = {
            mode: 'manual',
            auto_available: false,
            manual_locked: false,
            profile_code: null,
            reason_code: null,
            patient_name: '',
            patient_species: '',
            patient_age: '',
            targets: {
                sld2: parseFloat(document.getElementById('sld2')?.value) || 60,
                sld3: parseFloat(document.getElementById('sld3')?.value) || 32.0,
                sld12: parseFloat(document.getElementById('sld12')?.value) || 25.0
            },
            bands: {}
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
            sld12: parseFloat(document.getElementById('sld12')?.value) || 25.0, // Cooling Target (°C)
            sld13: parseFloat(document.getElementById('sld13')?.value) || 100 // Manual PWM fan duty (%)
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
        this.fanPwmAvailable = false;
        // Timer state tracking
        this.timerData = {
            nebulizer: { phase: 'READY', remaining: 0, total: 0 },
            ozone: { phase: 'READY', remaining: 0, total: 0 }
        };
        this.latestAIData = null;
        this.lastAIAlerts = [];
        this.lastClinicalEvent = '';
        this.lastClinicalEventAt = null;
        this.cameraFeedbackOverride = '';
        this.cameraFeedbackOverrideUntil = 0;
        this.lastAIStatusSignature = '';
        this.lastAIEnabledState = null;

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
        this.clientHeartbeatIntervalId = null;
        this.lastViewportSignature = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupErrorReporting();
        this.updateDateTime();
        this.updateIPAddress();

        // Apply translations based on saved language
        this.applyTranslations();
        this.updateLanguageButtons();
        this.applyViewportProfile();
        this.setupViewportObserver();

        // Initialize slider displays with default values immediately (will be updated by backend)
        this.initSliderDisplays();
        this.renderCareModeState();
        this.renderClinicalMonitorState();

        if (this.connectSocketEnabled) {
            this.connectWebSocket();
        } else {
            console.log(`KuvozController initialized without Socket.IO on page: ${this.pageName}`);
        }
        this.startTimerCountdown();
        this.setupPageUnloadHandler();
        this.setupDocumentVisibilityHandler();
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
                } else if (format === 'humidity' || format === 'percent') {
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

    setupDocumentVisibilityHandler() {
        document.addEventListener('visibilitychange', () => {});
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
        if (!this.connectSocketEnabled) {
            return;
        }

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

    startClientHeartbeat() {
        if (this.clientHeartbeatIntervalId) {
            clearInterval(this.clientHeartbeatIntervalId);
        }
        this.clientHeartbeatIntervalId = setInterval(() => {
            if (!this.socket || !this.socket.connected) return;
            this.reportClientEvent('ui_heartbeat', {
                visibility: document.visibilityState,
                online: navigator.onLine
            });
        }, 30000);
    }

    stopClientHeartbeat() {
        if (!this.clientHeartbeatIntervalId) return;
        clearInterval(this.clientHeartbeatIntervalId);
        this.clientHeartbeatIntervalId = null;
    }

    applyViewportProfile() {
        const body = document.body;
        if (!body) return;

        const width = window.innerWidth || document.documentElement?.clientWidth || 0;
        const height = window.innerHeight || document.documentElement?.clientHeight || 0;
        const actualLandscape = width >= height;
        const kioskOnlyPreference = this.getLocalKioskScreenOrientation();
        const effectiveLandscape = kioskOnlyPreference === 'portrait'
            ? false
            : kioskOnlyPreference === 'landscape'
                ? true
                : actualLandscape;
        const compactLandscape = effectiveLandscape && width <= 920 && height <= 540;
        const compact800x480 = effectiveLandscape && width <= 820 && height <= 520;
        const kiosk1024x600 = effectiveLandscape && width >= 960 && width <= 1060 && height >= 560 && height <= 640;

        body.classList.toggle('viewport-compact-landscape', compactLandscape);
        body.classList.toggle('viewport-800x480-ish', compact800x480);
        body.classList.toggle('viewport-kiosk-1024x600', kiosk1024x600);
        body.classList.toggle('screen-orientation-portrait', !effectiveLandscape);
        body.classList.toggle('screen-orientation-landscape', effectiveLandscape);
        body.classList.toggle('screen-orientation-forced', kioskOnlyPreference !== 'auto');
        body.dataset.screenOrientation = kioskOnlyPreference;

        const signature = `${width}x${height}@${window.devicePixelRatio || 1}:${compactLandscape ? 1 : 0}:${compact800x480 ? 1 : 0}:${kiosk1024x600 ? 1 : 0}:${kioskOnlyPreference}:${effectiveLandscape ? 1 : 0}`;
        if (signature !== this.lastViewportSignature) {
            this.lastViewportSignature = signature;
            this.reportClientEvent('viewport_profile', {
                width,
                height,
                dpr: window.devicePixelRatio || 1,
                screen_orientation: kioskOnlyPreference,
                actual_landscape: actualLandscape,
                effective_landscape: effectiveLandscape,
                compact_landscape: compactLandscape,
                compact_800x480: compact800x480,
                kiosk_1024x600: kiosk1024x600
            });
        }
    }

    isLocalKioskBrowser() {
        const host = String(window.location.hostname || '').trim().toLowerCase();
        return host === 'localhost' || host === '127.0.0.1' || host === '::1';
    }

    normalizeScreenOrientationPreference(value) {
        const normalized = String(value || 'auto').trim().toLowerCase();
        if (normalized === 'portrait' || normalized === 'landscape') {
            return normalized;
        }
        return 'auto';
    }

    getLocalKioskScreenOrientation() {
        if (!this.isLocalKioskBrowser()) {
            return 'auto';
        }
        return this.normalizeScreenOrientationPreference(this.systemSettings?.screen_orientation);
    }

    setupViewportObserver() {
        let resizeTimer = null;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => this.applyViewportProfile(), 120);
        });
        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.applyViewportProfile(), 150);
        });
    }

    clearStatusSyncTimers() {
        if (this.statusPollIntervalId) {
            clearInterval(this.statusPollIntervalId);
            this.statusPollIntervalId = null;
        }

        if (this.statusFallbackTimer) {
            clearTimeout(this.statusFallbackTimer);
            this.statusFallbackTimer = null;
        }
    }

    scheduleStatusFallback() {
        this.clearStatusSyncTimers();
        this.statusFallbackTimer = setTimeout(() => {
            if (this.statusAppliedSinceConnect) return;
            console.warn('No status_response received in time, using /api/status fallback');
            this.reportClientEvent('status_fallback_triggered');
            this.applyApiStatusFallback();
        }, 6000);
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
                if (data.care_settings) this.updateCareSettings(data.care_settings);
                if (data.timers) this.updateTimerData(data.timers);

                this.statusAppliedSinceConnect = true;

                if (!this.initialStatusReceived) {
                    this.initialStatusReceived = true;
                    if (typeof hideSplashScreen === 'function') {
                        hideSplashScreen();
                    }
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

        document.querySelectorAll('.care-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setCareMode(btn.dataset.mode);
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
        }

        // Kaydet butonu kaldırıldı (auto-save aktif)

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
                    banner.innerHTML = this.t('system.cleaning').toUpperCase() + ' ' + (this.currentLanguage === 'en' ? 'MODE ACTIVE - Normal controls disabled' : 'MODU AKTİF - Normal kontroller devre dışı');
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
        const enabledState = Boolean(enabled);
        const previousEnabledState = this.lastAIEnabledState;
        const enabledChanged = previousEnabledState !== null && previousEnabledState !== enabledState;
        const aiToggleBtn = document.getElementById('aiToggleBtn');
        const aiStatusBadge = document.getElementById('aiStatusBadge');
        const aiPanel = document.getElementById('aiPanel');
        const compactAiPanel = document.getElementById('compactAiPanel');
        const aiStatusBadgeMini = document.getElementById('aiStatusBadgeMini');

        if (aiToggleBtn) {
            if (enabledState) {
                aiToggleBtn.classList.add('active');
                aiToggleBtn.classList.remove('inactive');
            } else {
                aiToggleBtn.classList.remove('active');
                aiToggleBtn.classList.add('inactive');
            }
        }

        if (aiStatusBadge) {
            aiStatusBadge.textContent = enabledState ? 'ACTIVE' : 'OFFLINE';
            aiStatusBadge.style.background = enabledState ? '#28a745' : '#95a5a6';
        }

        if (aiStatusBadgeMini) {
            aiStatusBadgeMini.textContent = enabledState ? 'ACTIVE' : 'OFFLINE';
            aiStatusBadgeMini.style.background = enabledState ? '#28a745' : '#95a5a6';
        }

        // Show/hide AI panel based on enabled state
        if (aiPanel) {
            aiPanel.style.display = enabledState ? 'block' : 'none';
        }

        // Show/hide compact AI panel based on enabled state
        if (compactAiPanel) {
            compactAiPanel.style.display = enabledState ? 'block' : 'none';
        }

        this.lastAIEnabledState = enabledState;

        if (enabledChanged && this.statusAppliedSinceConnect) {
            const copy = this.getClinicalMonitorCopy();
            const statusMessage = enabledState ? copy.aiEnabled : copy.aiDisabled;
            this.recordClinicalEvent(statusMessage);
            this.setCameraMicroFeedback(statusMessage, 10000);
        }

        this.renderClinicalMonitorState();
        console.log('AI toggle button updated:', enabledState);
    }


    connectWebSocket() {
        try {
            if (!this.connectSocketEnabled) {
                return;
            }

            if (this.socket) {
                console.log('Socket.IO already initialized for this controller');
                return;
            }

            // Socket.IO connection with options - use current host instead of hardcoded localhost
            const socketUrl = window.location.origin; // Uses current protocol, hostname, and port
            console.log('Connecting to Socket.IO at:', socketUrl);
            this.socket = createKuvozSocket(socketUrl, {
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay,
                reconnectionDelayMax: this.reconnectDelay
            });

            if (this.socket.io) {
                this.socket.io.on('reconnect_attempt', (attempt) => {
                    this.reconnectAttempts = attempt;
                    console.log(`Reconnect attempt ${attempt}/${this.maxReconnectAttempts}`);
                });

                this.socket.io.on('reconnect_error', (error) => {
                    console.error('Socket.IO reconnect error:', error);
                });

                this.socket.io.on('reconnect_failed', () => {
                    console.log('Max reconnect attempts reached. Starting simulation mode.');
                    this.startSimulation();
                });
            }

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
                this.startClientHeartbeat();
                this.emitPatientContext();

                // Backend already emits status_response on connect.
                // Keep only a delayed HTTP fallback for rare startup stalls.
                this.scheduleStatusFallback();
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
                        if (data.care_settings) this.updateCareSettings(data.care_settings);

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
                        this.clearStatusSyncTimers();

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

            this.socket.on('care_settings_update', (data) => {
                try {
                    if (!data) return;
                    if (data.sliders) this.updateSliderStates(data.sliders);
                    if (data.care_settings) this.updateCareSettings(data.care_settings);
                } catch (e) {
                    console.error('Error handling care settings update:', e);
                }
            });

            this.socket.on('patient_context_updated', (data) => {
                try {
                    if (!data) return;
                    if (data.sliders) this.updateSliderStates(data.sliders);
                    if (data.care_settings) this.updateCareSettings(data.care_settings);
                } catch (e) {
                    console.error('Error handling patient context update:', e);
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

            // Temperature alarm handlers from backend
            this.socket.on('temperature_alarm', (data) => {
                try {
                    console.log('Received temperature alarm:', data);
                    if (data) {
                        const message = data.message || 'Sıcaklık uyarısı!';
                        const temperature = data.temperature || '--';
                        const threshold = data.threshold || '--';
                        this.showWarningToast(`${message} - Sıcaklık: ${temperature}°C (Limit: ${threshold}°C)`);
                    }
                } catch (e) {
                    console.error('Error handling temperature alarm:', e);
                }
            });

            this.socket.on('critical_alarm', (data) => {
                try {
                    console.log('Received critical alarm:', data);
                    if (data) {
                        const message = data.message || 'Kritik alarm!';
                        const temperature = data.temperature || '--';
                        const threshold = data.threshold || '--';
                        
                        // Show critical alarm notification
                        this.showCriticalAlarm(message, temperature, threshold);
                        
                        // Play alarm sound if available
                        this.playCriticalAlarmSound();
                    }
                } catch (e) {
                    console.error('Error handling critical alarm:', e);
                }
            });

            this.socket.on('disconnect', () => {
                console.log('Socket.IO disconnected');
                this.stopClientHeartbeat();
                this.clearStatusSyncTimers();
                this.updateConnectionStatus(false);
            });

            this.socket.on('connect_error', (error) => {
                console.error('Socket.IO connection error:', error);
                this.stopClientHeartbeat();
                this.clearStatusSyncTimers();
                this.updateConnectionStatus(false);
            });

        } catch (error) {
            console.error('Socket.IO connection failed:', error);
            this.stopClientHeartbeat();
            this.clearStatusSyncTimers();
            this.updateConnectionStatus(false);
            this.startSimulation();
        }
    }

    emitPatientContext(patientData = null) {
        try {
            if (!this.socket || !this.socket.connected) return;

            const source = patientData || JSON.parse(localStorage.getItem('currentPatient') || '{}');
            if (!source || typeof source !== 'object') return;

            const payload = {
                name: source.name || '',
                species: source.species || '',
                breed: source.breed || '',
                age: source.age || '',
                weight: source.weight || ''
            };

            if (!payload.species && !payload.breed) return;
            this.socket.emit('update_patient_context', payload);
        } catch (e) {
            console.error('Failed to emit patient context:', e);
        }
    }

    getCareUnavailableMessage(reasonCode) {
        if (!reasonCode) return this.t('environment.missing_patient');
        return this.t(`environment.${reasonCode}`);
    }

    getCareProfileLabel() {
        if (!this.careSettings.profile_code) return '';
        return this.t(`environment.profile_${this.careSettings.profile_code}`);
    }

    formatCareTargets() {
        const targets = this.careSettings.targets || {};
        const temp = targets.sld3;
        const hum = targets.sld2;
        const cooling = targets.sld12;

        if (temp === undefined || hum === undefined || cooling === undefined) {
            return '';
        }

        return `${this.t('environment.active_targets')}: ${Number(temp).toFixed(1)}°C • ${Math.round(hum)}% • ${Number(cooling).toFixed(1)}°C`;
    }

    updateCareSettings(careSettings) {
        if (!careSettings || typeof careSettings !== 'object') return;

        this.careSettings = {
            ...this.careSettings,
            ...careSettings,
            targets: {
                ...this.careSettings.targets,
                ...(careSettings.targets || {})
            },
            bands: careSettings.bands || this.careSettings.bands || {}
        };

        this.renderCareModeState();
    }

    syncTargetControlState() {
        const lockedSliders = new Set(['sld2', 'sld3', 'sld12']);
        const isLocked = Boolean(this.careSettings.manual_locked);
        const fanSpeedLocked = (
            this.systemSettings.fan_output_mode !== 'pwm' ||
            this.systemSettings.fan_control_mode !== 'manual'
        );

        document.querySelectorAll('.target-btn').forEach((btn) => {
            const sliderId = btn.dataset.slider;
            const shouldLock = (
                (isLocked && lockedSliders.has(sliderId)) ||
                (sliderId === 'sld13' && fanSpeedLocked)
            );
            btn.disabled = shouldLock;
        });

        document.querySelectorAll('.target-item').forEach((item) => {
            const sliderId = item.querySelector('input')?.id;
            const shouldLock = (
                (isLocked && lockedSliders.has(sliderId)) ||
                (sliderId === 'sld13' && fanSpeedLocked)
            );
            item.classList.toggle('auto-locked', shouldLock);
        });
    }

    renderCareModeState() {
        const currentEl = document.getElementById('careModeCurrent');
        const summaryEl = document.getElementById('careModeSummary');
        const profileEl = document.getElementById('careModeProfile');
        const targetsEl = document.getElementById('careModeTargets');
        const manualBtn = document.getElementById('careModeManualBtn');
        const autoBtn = document.getElementById('careModeAutoBtn');

        if (!currentEl || !summaryEl || !profileEl || !targetsEl || !manualBtn || !autoBtn) {
            return;
        }

        const isAuto = this.careSettings.mode === 'auto';
        const autoAvailable = Boolean(this.careSettings.auto_available);
        const patientParts = [
            this.careSettings.patient_name,
            this.careSettings.patient_species,
            this.careSettings.patient_age
        ].filter(Boolean);
        const patientText = patientParts.length > 0
            ? `${this.t('environment.patient')}: ${patientParts.join(' • ')}`
            : this.t('environment.no_patient');
        const profileLabel = autoAvailable ? this.getCareProfileLabel() : '';

        currentEl.textContent = isAuto ? this.t('environment.auto_mode') : this.t('environment.manual_mode');

        if (isAuto && autoAvailable) {
            summaryEl.textContent = `${this.t('environment.auto_hint')} ${this.t('environment.locked_hint')}`;
            profileEl.textContent = profileLabel
                ? `${this.t('environment.profile')}: ${profileLabel}`
                : patientText;
            targetsEl.textContent = this.formatCareTargets();
        } else if (isAuto) {
            summaryEl.textContent = this.getCareUnavailableMessage(this.careSettings.reason_code);
            profileEl.textContent = patientText;
            targetsEl.textContent = '';
        } else {
            summaryEl.textContent = this.t('environment.manual_hint');
            profileEl.textContent = patientText;
            targetsEl.textContent = autoAvailable && profileLabel
                ? `${this.t('environment.profile')}: ${profileLabel}`
                : '';
        }

        manualBtn.classList.toggle('active', !isAuto);
        autoBtn.classList.toggle('active', isAuto);
        autoBtn.classList.toggle('unavailable', !autoAvailable);

        this.syncTargetControlState();
    }

    setCareMode(mode) {
        if (!mode) return;
        if (mode === this.careSettings.mode) return;

        if (mode === 'auto' && !this.careSettings.auto_available) {
            // Show concise message based on reason
            const reasonMsg = this.getCareUnavailableMessage(this.careSettings.reason_code);
            this.showToast(reasonMsg, 'warning');
            return;
        }

        this.sendCommand('save_settings', {
            care_settings: { mode }
        });
    }

    isCareTargetLocked(sliderId) {
        return Boolean(this.careSettings.manual_locked) && ['sld2', 'sld3', 'sld12'].includes(sliderId);
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
        return this.pageName || resolveCurrentPageName();
    }

    updateSlider(id, value) {
        if (id === 'sld13') {
            if (
                this.systemSettings.fan_output_mode !== 'pwm' ||
                this.systemSettings.fan_control_mode !== 'manual'
            ) {
                this.showToast(this.t('slider.fan_speed_auto'), 'warning');
                return;
            }

            value = Math.min(100, Math.max(20, Number(value) || 100));
            const slider = document.getElementById(id);
            if (slider) slider.value = value;
        }

        // SAFETY: Validate cooling target slider (sld12) - prevent dangerous values
        if (id === 'sld12') {
            const COOLING_TARGET_MIN = 15.0;  // Minimum cooling target
            const COOLING_TARGET_MAX = 35.0;  // Maximum cooling target (danger zone above this)
            
            if (value > COOLING_TARGET_MAX) {
                this.showWarningToast(`⚠️ Soğutma hedefi çok yüksek! Maksimum ${COOLING_TARGET_MAX}°C olabilir.`);
                value = COOLING_TARGET_MAX;
                // Update slider UI to reflect clamped value
                const slider = document.getElementById(id);
                if (slider) slider.value = value;
            } else if (value < COOLING_TARGET_MIN && value !== 0) {
                this.showWarningToast(`⚠️ Soğutma hedefi çok düşük! Minimum ${COOLING_TARGET_MIN}°C olabilir.`);
                value = COOLING_TARGET_MIN;
                // Update slider UI to reflect clamped value
                const slider = document.getElementById(id);
                if (slider) slider.value = value;
            }
        }
        
        if (this.isCareTargetLocked(id)) {
            this.showToast(this.t('environment.locked_toast'), 'warning');
            return;
        }

        this.sliderValues[id] = value;

        // Değer göstergesini güncelle (eğer varsa)
        const valueDisplay = document.getElementById(`${id}_value`);
        if (valueDisplay) {
            if (id === 'sld3' || id === 'sld7' || id === 'sld12') {
                // Temperature sliders: 1 decimal place + °C suffix
                valueDisplay.textContent = value.toFixed(1) + '°C';
            } else if (id === 'sld2' || id === 'sld13') {
                valueDisplay.textContent = Math.round(value) + '%';
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

    getClinicalMonitorCopy() {
        const lang = this.currentLanguage === 'tr' ? 'tr' : 'en';
        const catalogs = {
            tr: {
                aiWaiting: 'AI verisi bekleniyor.',
                alarmWaiting: 'Alarm özeti hazırlanıyor.',
                noAlarm: 'Aktif alarm yok, AI normal izleme yapıyor.',
                noEvent: 'Henüz olay kaydı yok.',
                aiEnabled: 'AI izleme aktif.',
                aiDisabled: 'AI izleme kapalı.',
                motionReadable: 'Hareket var, solunum takibi şu an net değil.',
                respirationReadable: 'Solunum okunuyor, takip kararlı.',
                lowConfidence: 'Solunum okunuyor ancak güven düşük, izleme sürüyor.',
                trackingLost: 'Takip kaybedildi, kamera kadrajını ve ışığı kontrol edin.',
                collecting: 'Takip başlatıldı, ilk ölçüm verileri toplanıyor.',
                activityPulse: 'Hareket artışı var, kısa süreli bulanıklık beklenebilir.',
                feedbackWaiting: 'Kamera geri bildirimi bekleniyor.',
                feedbackLightingOn: 'Aydınlatma açıldı, görüş iyileşti.',
                feedbackLightingOff: 'Aydınlatma kapandı, düşük ışıkta izleme sürüyor.',
                feedbackFanOn: 'Fan aktif, görüntüde hafif hareket artışı olabilir.',
                feedbackFanOff: 'Fan durdu, görüntü daha stabil okunabilir.',
                feedbackNebulizerOn: 'Nebülizatör aktif, buhar görüşü kısa süre azaltabilir.',
                feedbackNebulizerOff: 'Nebülizatör beklemede, görüntü netleşiyor.',
                feedbackHumidityOn: 'Nem kontrolü aktif, lens üzerinde hafif buğu olabilir.',
                feedbackHumidityOff: 'Nem kontrolü durdu, görüntü daha berrak kalabilir.',
                feedbackCarbonOn: 'Karbon ısıtıcı aktif, davranış değişimleri izleniyor.',
                feedbackCarbonOff: 'Karbon ısıtıcı pasif, termal hareket azalabilir.',
                feedbackIrOn: 'IR ısıtıcı aktif, görüşte konfor kaynaklı hareket beklenebilir.',
                feedbackIrOff: 'IR ısıtıcı durdu, kadraj yeniden dengeleniyor.',
                feedbackCoolingOn: 'Soğutma aktif, hava akışı kadrajı etkileyebilir.',
                feedbackCoolingOff: 'Soğutma pasif, görüntü yeniden stabilize oluyor.',
                feedbackGenericOn: 'Cihaz açıldı, kamera etkisi izleniyor.',
                feedbackGenericOff: 'Cihaz kapandı, kamera koşulları güncelleniyor.',
                alarmCritical: 'Kritik alarm var, hızlı müdahale önerilir.',
                alarmWarningOne: '1 AI uyarısı izleniyor.',
                alarmWarningMany: '{count} AI uyarısı izleniyor.',
                alarmInfo: 'AI izleme aktif, kritik alarm görünmüyor.',
                eventTemplate: '{time} • {message}'
            },
            en: {
                aiWaiting: 'Waiting for AI data.',
                alarmWaiting: 'Preparing alarm summary.',
                noAlarm: 'No active alarm, AI monitoring is normal.',
                noEvent: 'No recent event yet.',
                aiEnabled: 'AI monitoring enabled.',
                aiDisabled: 'AI monitoring disabled.',
                motionReadable: 'Motion detected, respiration tracking is not clear right now.',
                respirationReadable: 'Respiration is readable and tracking is stable.',
                lowConfidence: 'Respiration is readable but confidence is low.',
                trackingLost: 'Tracking lost, check framing and lighting.',
                collecting: 'Tracking started, first measurements are being collected.',
                activityPulse: 'Movement increased, brief blur may be expected.',
                feedbackWaiting: 'Waiting for camera feedback.',
                feedbackLightingOn: 'Lighting turned on, visibility improved.',
                feedbackLightingOff: 'Lighting turned off, low-light monitoring continues.',
                feedbackFanOn: 'Fan is active, slight movement may appear on camera.',
                feedbackFanOff: 'Fan stopped, the image may stabilize.',
                feedbackNebulizerOn: 'Nebulizer is active, mist may reduce visibility briefly.',
                feedbackNebulizerOff: 'Nebulizer is idle, visibility is clearing.',
                feedbackHumidityOn: 'Humidity control is active, mild lens fog may appear.',
                feedbackHumidityOff: 'Humidity control stopped, the view may stay clearer.',
                feedbackCarbonOn: 'Carbon heater is active, behaviour changes are being watched.',
                feedbackCarbonOff: 'Carbon heater is off, thermal movement may reduce.',
                feedbackIrOn: 'IR heater is active, comfort-related movement may increase.',
                feedbackIrOff: 'IR heater stopped, the frame is rebalancing.',
                feedbackCoolingOn: 'Cooling is active, airflow may affect the frame.',
                feedbackCoolingOff: 'Cooling is inactive, the image is stabilizing.',
                feedbackGenericOn: 'Device turned on, camera impact is being monitored.',
                feedbackGenericOff: 'Device turned off, camera conditions are updating.',
                alarmCritical: 'Critical alarm present, rapid intervention is recommended.',
                alarmWarningOne: '1 AI alert is being monitored.',
                alarmWarningMany: '{count} AI alerts are being monitored.',
                alarmInfo: 'AI monitoring is active, no critical alarm is visible.',
                eventTemplate: '{time} • {message}'
            }
        };

        return catalogs[lang];
    }

    interpolateMessage(template, values = {}) {
        return Object.entries(values).reduce((result, [key, value]) => {
            return result.replaceAll(`{${key}}`, String(value));
        }, String(template || ''));
    }

    formatClinicalEventTime(dateLike) {
        if (!dateLike) return '';
        const date = dateLike instanceof Date ? dateLike : new Date(dateLike);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleTimeString(this.currentLanguage === 'tr' ? 'tr-TR' : 'en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    recordClinicalEvent(message) {
        if (!message) return;
        this.lastClinicalEvent = String(message);
        this.lastClinicalEventAt = new Date();
        this.renderClinicalMonitorState();
    }

    setCameraMicroFeedback(message, durationMs = 12000) {
        if (!message) return;
        this.cameraFeedbackOverride = String(message);
        this.cameraFeedbackOverrideUntil = Date.now() + durationMs;
        this.renderClinicalMonitorState();
    }

    buildAIInsightSentence(data) {
        const copy = this.getClinicalMonitorCopy();
        if (!data) {
            return copy.aiWaiting;
        }

        const visionStatus = String(data?.vision?.status || '').toUpperCase();
        const vitalStatus = String(data?.vitals?.status || '').toUpperCase();
        const activity = Number(data?.vision?.activity);
        const confidence = Number(data?.vitals?.confidence);

        if (vitalStatus === 'TOO_MUCH_MOTION' || visionStatus === 'HAREKETLI' || (Number.isFinite(activity) && activity >= 35)) {
            return copy.motionReadable;
        }

        if (vitalStatus === 'OK') {
            return copy.respirationReadable;
        }

        if (vitalStatus === 'LOW_CONF' || (Number.isFinite(confidence) && confidence > 0 && confidence < 0.65)) {
            return copy.lowConfidence;
        }

        if (vitalStatus === 'UNAVAILABLE') {
            return copy.trackingLost;
        }

        if (vitalStatus === 'NOT_ENOUGH_DATA' || !data?.vitals) {
            return copy.collecting;
        }

        return copy.aiWaiting;
    }

    buildAlarmSummary(alerts = []) {
        const copy = this.getClinicalMonitorCopy();
        if (!Array.isArray(alerts) || alerts.length === 0) {
            return copy.noAlarm;
        }

        const criticalCount = alerts.filter((alert) => alert.severity === 'critical').length;
        if (criticalCount > 0) {
            return copy.alarmCritical;
        }

        if (alerts.length === 1) {
            return copy.alarmWarningOne;
        }

        return this.interpolateMessage(copy.alarmWarningMany, { count: alerts.length });
    }

    buildDefaultCameraFeedback(data) {
        const copy = this.getClinicalMonitorCopy();
        if (!data) {
            return copy.feedbackWaiting;
        }

        const activity = Number(data?.vision?.activity);
        if (Number.isFinite(activity) && activity >= 35) {
            return copy.activityPulse;
        }

        return copy.alarmInfo;
    }

    buildDeviceFeedback(buttonName, enabled) {
        const copy = this.getClinicalMonitorCopy();
        const map = {
            b1: enabled ? copy.feedbackLightingOn : copy.feedbackLightingOff,
            b2: enabled ? copy.feedbackNebulizerOn : copy.feedbackNebulizerOff,
            b3: enabled ? copy.feedbackHumidityOn : copy.feedbackHumidityOff,
            b4: enabled ? copy.feedbackCarbonOn : copy.feedbackCarbonOff,
            b5: enabled ? copy.feedbackIrOn : copy.feedbackIrOff,
            b6: enabled ? copy.feedbackFanOn : copy.feedbackFanOff,
            b9: enabled ? copy.feedbackCoolingOn : copy.feedbackCoolingOff
        };
        return map[buttonName] || (enabled ? copy.feedbackGenericOn : copy.feedbackGenericOff);
    }

    buildButtonEventMessage(buttonName, enabled) {
        const labelMap = {
            b1: this.t('button.lighting'),
            b2: this.t('button.nebulizer'),
            b3: this.t('button.humidity'),
            b4: this.t('button.carbon_temp'),
            b5: this.t('button.ir_temp'),
            b6: this.t('button.fan'),
            b9: this.t('button.cooling')
        };
        const label = labelMap[buttonName];
        if (!label) return '';
        return `${label} ${enabled ? (this.currentLanguage === 'tr' ? 'açıldı' : 'enabled') : (this.currentLanguage === 'tr' ? 'kapandı' : 'disabled')}.`;
    }

    renderClinicalMonitorState() {
        const copy = this.getClinicalMonitorCopy();
        const insightEl = document.getElementById('aiInsightSentence');
        const alarmEl = document.getElementById('aiAlarmSummary');
        const eventEl = document.getElementById('aiLastEvent');
        const feedbackEl = document.getElementById('cameraMicroFeedback');
        const motionStatusEl = document.getElementById('compactMotionStatus');

        if (insightEl) {
            insightEl.textContent = this.buildAIInsightSentence(this.latestAIData);
        }

        if (alarmEl) {
            alarmEl.textContent = this.buildAlarmSummary(this.lastAIAlerts);
        }

        if (eventEl) {
            if (this.lastClinicalEvent) {
                eventEl.textContent = this.interpolateMessage(copy.eventTemplate, {
                    time: this.formatClinicalEventTime(this.lastClinicalEventAt),
                    message: this.lastClinicalEvent
                });
            } else {
                eventEl.textContent = copy.noEvent;
            }
        }

        if (feedbackEl) {
            const hasOverride = this.cameraFeedbackOverride && Date.now() < this.cameraFeedbackOverrideUntil;
            feedbackEl.textContent = hasOverride
                ? this.cameraFeedbackOverride
                : this.buildDefaultCameraFeedback(this.latestAIData);
        }

        if (motionStatusEl && !this.latestAIData?.vision?.status) {
            motionStatusEl.textContent = copy.aiWaiting;
        }
    }

    updateAIDisplay(data) {
        this.latestAIData = data || null;

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
        const activeAlerts = this.buildActiveAIAlerts(data);
        this.lastAIAlerts = activeAlerts;
        const alertsList = document.getElementById('aiAlertsList');
        if (alertsList) {
            alertsList.innerHTML = '';
            if (activeAlerts.length === 0) {
                const li = document.createElement('li');
                li.className = 'ai-alert-item';
                li.innerHTML = `
                    <i class="fas fa-check-circle"></i>
                    <div>
                        <strong>${this.currentLanguage === 'en' ? 'No active alert' : 'Aktif uyarı yok'}</strong>
                        <div>${this.currentLanguage === 'en' ? 'AI is monitoring normally.' : 'AI normal izleme yapıyor.'}</div>
                    </div>
                `;
                alertsList.appendChild(li);
            } else {
                activeAlerts.slice(0, 3).forEach((alert) => {
                    const li = document.createElement('li');
                    li.className = 'ai-alert-item';
                    li.innerHTML = `
                        <i class="fas ${alert.icon || 'fa-exclamation-circle'}"></i>
                        <div>
                            <strong>${alert.title}</strong>
                            <div>${alert.summary}</div>
                        </div>
                    `;
                    alertsList.appendChild(li);
                });
            }
        }

        const aiSignature = JSON.stringify({
            enabled: this.lastAIEnabledState,
            vision: String(data?.vision?.status || ''),
            vital: String(data?.vitals?.status || ''),
            alerts: activeAlerts.map((alert) => `${alert.key}:${alert.severity}`).sort()
        });

        if (this.lastAIStatusSignature && aiSignature !== this.lastAIStatusSignature && this.statusAppliedSinceConnect) {
            const insightSentence = this.buildAIInsightSentence(data);
            if (insightSentence) {
                this.recordClinicalEvent(insightSentence);
            }
        }
        this.lastAIStatusSignature = aiSignature;

        const criticalAlerts = activeAlerts.filter((alert) => alert.severity === 'critical');
        const currentCriticalKeys = criticalAlerts.map((alert) => alert.key);
        const previousCriticalKeys = this.lastCriticalAlertKeys || [];
        criticalAlerts
            .filter((alert) => !previousCriticalKeys.includes(alert.key))
            .forEach((alert) => {
                this.showToast(alert.title, 'error');
            });
        this.lastCriticalAlertKeys = currentCriticalKeys;
        this.renderClinicalMonitorState();
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

        const bpmLabel = globalThis.translations[this.currentLanguage]?.vitals?.bpm || 'BPM';

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
        const statusPresentation = this.getVitalStatusPresentation(status);

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
            statusEl.textContent = statusPresentation.label;
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
            compactStatusEl.textContent = statusPresentation.shortLabel;
        }
    }

    // Hayvan yaşam döngüsü davranışlarını izlemek için yeni fonksiyon
    updateLifeCycleDisplay(behaviorData) {
        // Yeme-içme, dinlenme, boşaltım gibi davranışları izle
        if (behaviorData && typeof behaviorData === 'object') {
            // Burada davranış verilerini işleyebiliriz
            console.log('Hayvan davranış verileri güncellendi:', behaviorData);
            
            // Eğer life_cycle.html sayfasında isek, oradaki verileri de güncelleyebiliriz
            if (window.location.pathname.includes('life_cycle.html') && window.lifeCycleAnalytics) {
                window.lifeCycleAnalytics.handleBehaviorUpdate(behaviorData);
            }
        }
    }

    getVitalStatusPresentation(status) {
        const copy = this.getAIAlertCopy();
        const normalized = String(status || '').toUpperCase();
        const fallback = {
            label: status || '--',
            shortLabel: status || '--',
            icon: 'fa-minus',
            trendClass: 'trend-stable',
            severity: 'info'
        };
        const map = {
            OK: {
                label: copy.vitalStable,
                shortLabel: copy.vitalStable,
                icon: 'fa-check',
                trendClass: 'trend-down',
                severity: 'success'
            },
            LOW_CONF: {
                label: copy.vitalLowConfidence,
                shortLabel: copy.vitalLowConfidence,
                icon: 'fa-exclamation',
                trendClass: 'trend-stable',
                severity: 'info'
            },
            TOO_MUCH_MOTION: {
                label: copy.vitalTooMuchMotion,
                shortLabel: copy.vitalTooMuchMotion,
                icon: 'fa-person-running',
                trendClass: 'trend-up',
                severity: 'warning'
            },
            NOT_ENOUGH_DATA: {
                label: copy.vitalWaiting,
                shortLabel: copy.vitalWaiting,
                icon: 'fa-hourglass-half',
                trendClass: 'trend-stable',
                severity: 'info'
            },
            UNAVAILABLE: {
                label: copy.vitalUnavailable,
                shortLabel: copy.vitalUnavailable,
                icon: 'fa-camera',
                trendClass: 'trend-stable',
                severity: 'info'
            }
        };
        return map[normalized] || fallback;
    }

    getAIAlertCopy() {
        const lang = this.currentLanguage === 'tr' ? 'tr' : 'en';
        const catalogs = {
            tr: {
                sourceEnvironment: 'Ortam',
                sourceVitals: 'Solunum',
                genericTitle: 'AI uyarısı',
                genericHint: 'Durumu izleyin ve sistemi kontrol edin.',
                vitalStable: 'Stabil',
                vitalLowConfidence: 'Ölçüm net değil',
                vitalTooMuchMotion: 'Çok hareket var',
                vitalWaiting: 'Veri toplanıyor',
                vitalUnavailable: 'Hazır değil',
                motionTitle: 'Hayvan çok hareketli',
                motionSummary: 'Hareket arttığı için solunum ölçümü şu anda net alınamıyor.',
                motionHint: 'Hayvan sakinleştiğinde ölçüm yeniden netleşir.',
                tempDropTitle: 'Sıcaklık düşüyor',
                tempDropSummary: 'Isıtıcı açık olmasına rağmen sıcaklık beklenen şekilde artmıyor.',
                tempDropHint: 'Isıtıcıyı, prob yerleşimini ve kapak durumunu kontrol edin.',
                tempRiseFastTitle: 'Sıcaklık hızlı yükseliyor',
                tempRiseFastSummary: 'Sistem normalden hızlı ısınıyor.',
                tempRiseFastHint: 'Isıtıcı ayarını ve hava dolaşımını kontrol edin.',
                tempCriticalTitle: 'Sıcaklık çok yüksek',
                tempCriticalSummary: 'Sıcaklık güvenli aralığın üstüne çıktı.',
                tempCriticalHint: 'Hemen ısıtıcıyı azaltın ve cihazı kontrol edin.',
                tempLowTitle: 'Sıcaklık çok düşük',
                tempLowSummary: 'Sıcaklık hedef aralığın belirgin şekilde altında.',
                tempLowHint: 'Isıtıcıyı ve ortam ısı kaybını kontrol edin.',
                tempHighTitle: 'Sıcaklık yüksek',
                tempHighSummary: 'Sıcaklık önerilen seviyenin üzerinde seyrediyor.',
                tempHighHint: 'İzlemeye devam edin, gerekirse hedefi düşürün.',
                oxygenDropTitle: 'Oksijen hızla düştü',
                oxygenDropSummary: 'Kısa sürede belirgin oksijen kaybı algılandı.',
                oxygenDropHint: 'Ventilasyon ve oksijen beslemesini kontrol edin.',
                oxygenCriticalTitle: 'Oksijen kritik seviyede',
                oxygenCriticalSummary: 'Oksijen seviyesi acil müdahale gerektirecek kadar düştü.',
                oxygenCriticalHint: 'Hemen havalandırmayı ve oksijen kaynağını kontrol edin.',
                oxygenLowTitle: 'Oksijen düşük',
                oxygenLowSummary: 'Oksijen seviyesi hedefin altında.',
                oxygenLowHint: 'Ventilasyon ayarlarını gözden geçirin.',
                humidityHighTitle: 'Nem çok yüksek',
                humidityHighSummary: 'Nem seviyesi önerilen aralığın üstüne çıktı.',
                humidityHighHint: 'Havalandırmayı ve nem kaynağını kontrol edin.',
                humidityLowTitle: 'Nem çok düşük',
                humidityLowSummary: 'Nem seviyesi önerilen aralığın altına indi.',
                humidityLowHint: 'Nemlendirmeyi ve su seviyesini kontrol edin.',
                tempUnstableTitle: 'Sıcaklık dengesiz',
                tempUnstableSummary: 'Sıcaklık kısa aralıklarla dalgalanıyor.',
                tempUnstableHint: 'Isıtıcı çevrimi ve sensör konumunu gözden geçirin.',
                humidityUnstableTitle: 'Nem dengesiz',
                humidityUnstableSummary: 'Nem seviyesi kısa aralıklarla dalgalanıyor.',
                humidityUnstableHint: 'Nem kontrol ayarlarını ve hava akışını kontrol edin.'
            },
            en: {
                sourceEnvironment: 'Environment',
                sourceVitals: 'Respiration',
                genericTitle: 'AI alert',
                genericHint: 'Keep monitoring and review the system.',
                vitalStable: 'Stable',
                vitalLowConfidence: 'Measurement unclear',
                vitalTooMuchMotion: 'Too much motion',
                vitalWaiting: 'Collecting data',
                vitalUnavailable: 'Not ready',
                motionTitle: 'Animal is moving too much',
                motionSummary: 'Respiration cannot be measured clearly while movement is high.',
                motionHint: 'The reading should recover once the animal settles.',
                tempDropTitle: 'Temperature is dropping',
                tempDropSummary: 'Temperature is not rising as expected while the heater is on.',
                tempDropHint: 'Check the heater, probe placement, and door state.',
                tempRiseFastTitle: 'Temperature is rising fast',
                tempRiseFastSummary: 'The system is heating faster than expected.',
                tempRiseFastHint: 'Check heater settings and airflow.',
                tempCriticalTitle: 'Temperature is critically high',
                tempCriticalSummary: 'Temperature moved above the safe range.',
                tempCriticalHint: 'Reduce heating immediately and inspect the device.',
                tempLowTitle: 'Temperature is too low',
                tempLowSummary: 'Temperature is clearly below the target range.',
                tempLowHint: 'Check heating and possible heat loss.',
                tempHighTitle: 'Temperature is high',
                tempHighSummary: 'Temperature is above the recommended level.',
                tempHighHint: 'Keep monitoring and lower the target if needed.',
                oxygenDropTitle: 'Oxygen dropped quickly',
                oxygenDropSummary: 'A noticeable oxygen drop was detected in a short time.',
                oxygenDropHint: 'Check ventilation and oxygen supply.',
                oxygenCriticalTitle: 'Oxygen is critical',
                oxygenCriticalSummary: 'Oxygen level is low enough to require urgent action.',
                oxygenCriticalHint: 'Check ventilation and oxygen source immediately.',
                oxygenLowTitle: 'Oxygen is low',
                oxygenLowSummary: 'Oxygen level is below the target range.',
                oxygenLowHint: 'Review ventilation settings.',
                humidityHighTitle: 'Humidity is too high',
                humidityHighSummary: 'Humidity moved above the recommended range.',
                humidityHighHint: 'Check ventilation and humidity source.',
                humidityLowTitle: 'Humidity is too low',
                humidityLowSummary: 'Humidity moved below the recommended range.',
                humidityLowHint: 'Check humidification and water level.',
                tempUnstableTitle: 'Temperature is unstable',
                tempUnstableSummary: 'Temperature is fluctuating within short intervals.',
                tempUnstableHint: 'Review heater cycling and sensor placement.',
                humidityUnstableTitle: 'Humidity is unstable',
                humidityUnstableSummary: 'Humidity is fluctuating within short intervals.',
                humidityUnstableHint: 'Review humidity control and airflow.'
            }
        };
        return catalogs[lang];
    }

    cleanRawAIAlertMessage(message) {
        return String(message || '')
            .replace(/[🔥❗⚠️❄️🌬️💧🏜️📊💦]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    buildAIAlert(key, data = {}) {
        return {
            key,
            source: data.source || 'environment',
            sourceLabel: data.sourceLabel || '',
            severity: data.severity || 'info',
            icon: data.icon || 'fa-exclamation-triangle',
            title: data.title || '',
            summary: data.summary || '',
            hint: data.hint || '',
            timestamp: data.timestamp || new Date().toISOString(),
            rawMessage: data.rawMessage || ''
        };
    }

    normalizeEnvironmentAlert(message) {
        const copy = this.getAIAlertCopy();
        const lower = String(message || '').toLowerCase();
        const base = {
            source: 'environment',
            sourceLabel: copy.sourceEnvironment,
            rawMessage: message
        };

        if (lower.includes('ısıtıcı açık ama sıcaklık düşüyor')) {
            return this.buildAIAlert('env_temp_drop', {
                ...base,
                severity: 'warning',
                icon: 'fa-fire',
                title: copy.tempDropTitle,
                summary: copy.tempDropSummary,
                hint: copy.tempDropHint
            });
        }
        if (lower.includes('sıcaklık çok hızlı yükseliyor')) {
            return this.buildAIAlert('env_temp_rise_fast', {
                ...base,
                severity: 'warning',
                icon: 'fa-temperature-high',
                title: copy.tempRiseFastTitle,
                summary: copy.tempRiseFastSummary,
                hint: copy.tempRiseFastHint
            });
        }
        if (lower.includes("sıcaklık 40°c'nin üzerinde")) {
            return this.buildAIAlert('env_temp_critical', {
                ...base,
                severity: 'critical',
                icon: 'fa-temperature-high',
                title: copy.tempCriticalTitle,
                summary: copy.tempCriticalSummary,
                hint: copy.tempCriticalHint
            });
        }
        if (lower.includes("sıcaklık 15°c'nin altında")) {
            return this.buildAIAlert('env_temp_low', {
                ...base,
                severity: 'warning',
                icon: 'fa-temperature-low',
                title: copy.tempLowTitle,
                summary: copy.tempLowSummary,
                hint: copy.tempLowHint
            });
        }
        if (lower.includes('sıcaklık yüksek')) {
            return this.buildAIAlert('env_temp_high', {
                ...base,
                severity: 'warning',
                icon: 'fa-temperature-high',
                title: copy.tempHighTitle,
                summary: copy.tempHighSummary,
                hint: copy.tempHighHint
            });
        }
        if (lower.includes('oksijen seviyesinde ani düşüş')) {
            return this.buildAIAlert('env_oxygen_drop', {
                ...base,
                severity: 'warning',
                icon: 'fa-wind',
                title: copy.oxygenDropTitle,
                summary: copy.oxygenDropSummary,
                hint: copy.oxygenDropHint
            });
        }
        if (lower.includes("oksijen seviyesi %18'in altında")) {
            return this.buildAIAlert('env_oxygen_critical', {
                ...base,
                severity: 'critical',
                icon: 'fa-wind',
                title: copy.oxygenCriticalTitle,
                summary: copy.oxygenCriticalSummary,
                hint: copy.oxygenCriticalHint
            });
        }
        if (lower.includes('oksijen seviyesi düşük')) {
            return this.buildAIAlert('env_oxygen_low', {
                ...base,
                severity: 'warning',
                icon: 'fa-wind',
                title: copy.oxygenLowTitle,
                summary: copy.oxygenLowSummary,
                hint: copy.oxygenLowHint
            });
        }
        if (lower.includes('nem seviyesi çok yüksek')) {
            return this.buildAIAlert('env_humidity_high', {
                ...base,
                severity: 'warning',
                icon: 'fa-tint',
                title: copy.humidityHighTitle,
                summary: copy.humidityHighSummary,
                hint: copy.humidityHighHint
            });
        }
        if (lower.includes('nem seviyesi çok düşük')) {
            return this.buildAIAlert('env_humidity_low', {
                ...base,
                severity: 'warning',
                icon: 'fa-tint',
                title: copy.humidityLowTitle,
                summary: copy.humidityLowSummary,
                hint: copy.humidityLowHint
            });
        }
        if (lower.includes('sıcaklık değerleri dengesiz')) {
            return this.buildAIAlert('env_temp_unstable', {
                ...base,
                severity: 'info',
                icon: 'fa-chart-line',
                title: copy.tempUnstableTitle,
                summary: copy.tempUnstableSummary,
                hint: copy.tempUnstableHint
            });
        }
        if (lower.includes('nem seviyesi dengesiz')) {
            return this.buildAIAlert('env_humidity_unstable', {
                ...base,
                severity: 'info',
                icon: 'fa-chart-line',
                title: copy.humidityUnstableTitle,
                summary: copy.humidityUnstableSummary,
                hint: copy.humidityUnstableHint
            });
        }

        return this.buildAIAlert(`env_generic_${this.cleanRawAIAlertMessage(message).toLowerCase()}`, {
            ...base,
            severity: lower.includes('kritik') || lower.includes('critical') ? 'critical' : 'info',
            icon: 'fa-exclamation-triangle',
            title: copy.genericTitle,
            summary: this.cleanRawAIAlertMessage(message),
            hint: copy.genericHint
        });
    }

    buildVitalStatusAlert(vitals) {
        const copy = this.getAIAlertCopy();
        const status = String(vitals?.status || '').toUpperCase();
        if (status !== 'TOO_MUCH_MOTION') {
            return null;
        }
        return this.buildAIAlert('vital_too_much_motion', {
            source: 'vitals',
            sourceLabel: copy.sourceVitals,
            severity: 'warning',
            icon: 'fa-person-running',
            title: copy.motionTitle,
            summary: copy.motionSummary,
            hint: copy.motionHint
        });
    }

    isOxygenAlertMessage(message) {
        const lower = String(message || '').toLowerCase();
        return lower.includes('oksijen seviyesinde ani düşüş') ||
            lower.includes("oksijen seviyesi %18'in altında") ||
            lower.includes('oksijen seviyesi düşük');
    }

    buildActiveAIAlerts(data) {
        const anomalies = Array.isArray(data?.analytics?.anomalies) ? data.analytics.anomalies : [];
        const visibleAnomalies = this.systemSettings.oxygen_enabled === false
            ? anomalies.filter((message) => !this.isOxygenAlertMessage(message))
            : anomalies;

        const alerts = visibleAnomalies
            .map((message) => this.normalizeEnvironmentAlert(message))
            .filter(Boolean);

        const vitalAlert = this.buildVitalStatusAlert(data?.vitals);
        if (vitalAlert) {
            alerts.push(vitalAlert);
        }

        const severityOrder = { critical: 0, warning: 1, info: 2, success: 3 };
        const seen = new Set();
        return alerts
            .filter((alert) => {
                if (!alert?.key || seen.has(alert.key)) return false;
                seen.add(alert.key);
                return true;
            })
            .sort((a, b) => {
                const severityDiff = (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99);
                if (severityDiff !== 0) return severityDiff;
                return String(a.title || '').localeCompare(String(b.title || ''));
            });
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

        const wasAvailable = this.oxygenSensorAvailable;
        this.oxygenSensorAvailable = hasOxygen;

        // Toggle only if state changed or initially
        if (hasOxygen !== wasAvailable || !this.initialStatusReceived) {
            this.toggleOxygenSensorDisplay(hasOxygen);
            if (hasOxygen !== wasAvailable) {
                this.updateOzoneMode(hasOxygen);
            }
        }

        if (hasOxygen !== wasAvailable) {
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

    getCO2LevelClass(co2Value) {
        if (co2Value === '--' || co2Value === null || co2Value === undefined) {
            return 'co2-level-unknown';
        }

        const co2Level = parseFloat(co2Value);
        if (Number.isNaN(co2Level)) {
            return 'co2-level-unknown';
        }
        if (co2Level < 600) return 'co2-level-good';
        if (co2Level < 1000) return 'co2-level-watch';
        if (co2Level < 1500) return 'co2-level-high';
        return 'co2-level-critical';
    }

    // Audio context'i başlat ve kullanıcı etkileşimini bekle
    initAudioContext() {
        const enableAudio = () => {
            this.activateAudioContext()
                .then((enabled) => {
                    if (enabled) {
                        console.log('Audio etkinleştirildi (kullanıcı etkileşimi)');
                    }
                })
                .catch((e) => {
                    console.error('Audio etkinleştirilemedi:', e);
                });
        };

        // Herhangi bir tıklama veya dokunmada audio'yu etkinleştir
        document.addEventListener('click', enableAudio, { once: true });
        document.addEventListener('touchstart', enableAudio, { once: true });
        document.addEventListener('keydown', enableAudio, { once: true });
    }

    async activateAudioContext() {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) {
            this.audioEnabled = false;
            return false;
        }

        if (!this.audioContext || this.audioContext.state === 'closed') {
            this.audioContext = new AudioContextClass();
            console.log('AudioContext oluşturuldu');
        }

        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        this.audioEnabled = this.audioContext.state === 'running';
        return this.audioEnabled;
    }

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
            const isCurrentlyShowing = oxygenCard.style.display !== 'none';
            if (show && !isCurrentlyShowing) {
                oxygenCard.style.display = 'flex';
                oxygenCard.classList.remove('sensor-hidden');
            } else if (!show && isCurrentlyShowing) {
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
            const isCurrentlyShowing = co2Card.style.display !== 'none';
            if (show && !isCurrentlyShowing) {
                co2Card.style.display = 'flex';
                co2Card.classList.remove('sensor-hidden');
            } else if (!show && isCurrentlyShowing) {
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

    updateAutoFanSpeedDisplay(system) {
        const fanSpeedValue = document.getElementById('sld13_value');
        const fanSpeedInput = document.getElementById('sld13');
        const fanSpeedTarget = document.getElementById('fanSpeedTarget');
        const fanSpeedLabel = fanSpeedTarget?.querySelector('.target-label');
        if (!fanSpeedValue) {
            return;
        }

        if (this.systemSettings.fan_output_mode !== 'pwm') {
            fanSpeedValue.textContent = '--%';
            return;
        }

        const manualMode = this.systemSettings.fan_control_mode === 'manual';
        if (fanSpeedLabel) {
            fanSpeedLabel.textContent = manualMode
                ? this.t('slider.fan_speed')
                : this.t('slider.fan_speed_auto');
        }

        if (manualMode) {
            const manualDuty = Number(system?.fan_pwm_manual_duty ?? this.sliderValues.sld13 ?? 100);
            const duty = Number.isFinite(manualDuty) ? manualDuty : 100;
            if (fanSpeedInput) {
                fanSpeedInput.value = String(duty);
            }
            this.sliderValues.sld13 = duty;
            fanSpeedValue.textContent = `${Math.round(duty)}%`;
            return;
        }

        const dutyValue = system?.fan_pwm_duty;
        const duty = dutyValue === null || dutyValue === undefined
            ? Number.NaN
            : Number(dutyValue);
        fanSpeedValue.textContent = Number.isFinite(duty)
            ? `${Math.round(duty)}%`
            : '--%';
    }

    toggleFanSpeedControl(show) {
        const fanSpeedTarget = document.getElementById('fanSpeedTarget');
        if (!fanSpeedTarget) {
            return;
        }

        const manualMode = this.systemSettings.fan_control_mode === 'manual';
        fanSpeedTarget.style.display = show ? '' : 'none';
        fanSpeedTarget.classList.toggle('auto-locked', !manualMode);
        fanSpeedTarget.querySelectorAll('.target-btn').forEach((btn) => {
            btn.disabled = !manualMode;
        });
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

        // Simülasyon modu kontrolü
        this.checkSimulationMode(sensors);

        // Oksijen sensörü durumunu kontrol et
        this.checkOxygenSensorAvailability(sensors);
        // CO2 sensörü durumunu kontrol et
        this.checkCO2SensorAvailability(sensors);

        if (sensors.temperature !== undefined) {
            this.sensorData.temperature = sensors.temperature; // Store entire object for consistency
            const tempElement = document.getElementById('temperature');
            const tempStatusElement = document.getElementById('tempStatus');

            if (tempElement) {
                const tempValue = sensors.temperature.value;
                tempElement.textContent = tempValue === '--' ? '--' : tempValue + '°C';
            }

            if (tempStatusElement) {
                tempStatusElement.textContent = sensors.temperature.status;
            }
        }

        if (sensors.humidity !== undefined) {
            this.sensorData.humidity = sensors.humidity; // Store object
            const humElement = document.getElementById('humidity');
            const humStatusElement = document.getElementById('humStatus');

            if (humElement) {
                const humValue = sensors.humidity.value;
                humElement.textContent = humValue === '--' ? '--' : humValue + '%';
            }

            if (humStatusElement) {
                humStatusElement.textContent = sensors.humidity.status;
            }
        }

        // Oksijen sensörü sadece mevcut olduğunda güncelle
        if (sensors.oxygen !== undefined && this.oxygenSensorAvailable) {
            this.sensorData.oxygen = sensors.oxygen;
            const oxygenCard = document.getElementById('oxygenCard');
            const oxyElement = document.getElementById('oxygen');
            const oxyStatusElement = document.getElementById('oxyStatus');
            const oxygenStatus = String(sensors.oxygen.status || '');
            const oxygenEstimated = /tahmini|estimated|co2/i.test(oxygenStatus);

            if (oxygenCard) {
                oxygenCard.classList.toggle('oxygen-estimated', oxygenEstimated);
            }

            if (oxyElement) {
                const oxyValue = sensors.oxygen.value;
                oxyElement.textContent = oxyValue === '--' ? '--' : oxyValue + '%';
            }

            if (oxyStatusElement) {
                oxyStatusElement.textContent = sensors.oxygen.status;
            }

            // Oksijen seviyesine göre ozon modu güncellemesi
            this.updateOzoneModeByOxygen(sensors.oxygen.value);
        }

        // CO2 sensörü sadece mevcut olduğunda güncelle
        if (sensors.co2 !== undefined && this.co2SensorAvailable) {
            const co2Card = document.getElementById('co2Card');
            const co2Element = document.getElementById('co2');
            const co2StatusElement = document.getElementById('co2Status');
            const co2CommentElement = document.getElementById('co2Comment');
            const levelClass = this.getCO2LevelClass(sensors.co2.value);

            if (co2Card) {
                co2Card.classList.remove('co2-level-unknown', 'co2-level-good', 'co2-level-watch', 'co2-level-high', 'co2-level-critical');
                co2Card.classList.add(levelClass);
            }

            if (co2Element) {
                const co2Value = sensors.co2.value;
                co2Element.textContent = co2Value === '--' ? '--' : co2Value + 'ppm';
            } else {
            }

            if (co2StatusElement) {
                co2StatusElement.textContent = sensors.co2.status || '';
            } else {
            }

            // CO2 yorumunu güncelle
            if (co2CommentElement) {
                const comment = this.getCO2Comment(sensors.co2.value);
                co2CommentElement.textContent = comment;
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

                const appliedState = this.buttonStates[buttonName];

                // Her zaman visual'ı güncelle (GPIO state değişmemiş olsa bile)
                this.applyButtonVisual(buttonName);

                if (this.statusAppliedSinceConnect && oldState !== appliedState) {
                    const eventMessage = this.buildButtonEventMessage(buttonName, appliedState);
                    if (eventMessage) {
                        this.recordClinicalEvent(eventMessage);
                    }

                    const feedbackMessage = this.buildDeviceFeedback(buttonName, appliedState);
                    if (feedbackMessage) {
                        this.setCameraMicroFeedback(feedbackMessage);
                    }
                }
            }
        });
    }

    updateGpioOutputs(gpioOutputs) {
        Object.keys(gpioOutputs).forEach(buttonName => {
            if (this.gpioOutputs.hasOwnProperty(buttonName)) {
                const oldValue = this.gpioOutputs[buttonName];
                const rawValue = gpioOutputs[buttonName];
                const newValue = rawValue === null ? null : Boolean(rawValue);
                this.gpioOutputs[buttonName] = newValue;
                // Her zaman visual'ı güncelle
                this.applyButtonVisual(buttonName);
            }
        });
    }

    applyButtonVisual(buttonName) {
        const btn = document.getElementById(`btn_${buttonName}`);
        if (!btn) {
            return;
        }

        // Tüm state sınıflarını kaldır
        btn.classList.remove('active', 'active-on', 'active-off', 'state-on', 'state-off', 'state-disabled', 'state-unknown');

        const buttonState = this.buttonStates[buttonName];  // Fonksiyon aktif mi?
        const gpioState = this.gpioOutputs[buttonName];     // GPIO çıkış durumu


        // B9 (Cooling) - Özel soğutma mantığı
        if (buttonName === 'b9') {
            if (!buttonState) {
                // Buton kapalı → Beyaz
                btn.classList.add('state-unknown');
                return;
            }

            // Buton açık → Hedef kontrolü
            const currentTemp = parseFloat(this.sensorData.temperature?.value || 0);
            const coolingTarget = this.sliderValues['sld12'] || 0;

            if (coolingTarget === 0) {
                // Manuel mod → Yeşil
                btn.classList.add('state-on');
            } else if (gpioState === true) {
                // Aktif soğutuyor (GPIO LOW) → Kırmızı
                btn.classList.add('state-off');
            } else {
                // Hedefte (GPIO HIGH) → Yeşil
                btn.classList.add('state-on');
            }
            return;
        }

        // Special handling for UV/Ozone buttons on non-cleaning pages
        const currentPage = this.getCurrentPage();
        if ((buttonName === 'b7' || buttonName === 'b8') && currentPage !== 'cleaning') {
            // On non-cleaning pages, always show UV/Ozone as disabled/unknown
            btn.classList.add('state-disabled');
            return;
        }

        // GPIO kullanılamıyorsa -> Disabled (gri)
        if (this.gpioAvailable === false) {
            btn.classList.add('state-disabled');
            return;
        }

        // SPECIAL: B2 (Nebulizer) and B8 (Ozone) - Phase-based coloring
        // Check buttonState first, then use phase for color
        if (buttonName === 'b2') {

            // Button OFF → Beyaz
            if (!buttonState) {
                btn.classList.add('state-unknown');
                return;
            }

            // Button ON → Phase-based coloring
            const phase = this.timerData.nebulizer?.phase || 'READY';
            if (phase === 'DUTY') {
                btn.classList.add('state-off'); // Kırmızı - Aktif çalışıyor
            } else {
                // READY or FREE → Yeşil
                btn.classList.add('state-on');
            }
            return;
        }

        if (buttonName === 'b8') {

            // Button OFF → Beyaz
            if (!buttonState) {
                btn.classList.add('state-unknown');
                return;
            }

            // Button ON → Phase-based coloring
            const phase = this.timerData.ozone?.phase || 'READY';
            if (phase === 'DUTY') {
                btn.classList.add('state-off'); // Kırmızı - Aktif çalışıyor
            } else {
                // READY or FREE → Yeşil
                btn.classList.add('state-on');
            }
            return;
        }

        // Buton PASİF (fonksiyon kapalı) -> Beyaz
        if (!buttonState) {
            btn.classList.add('state-unknown');
            return;
        }

        // Buton AKTİF (fonksiyon açık) -> Hedef değer kontrolü + GPIO durumu
        if (gpioState === null || gpioState === undefined) {
            // GPIO durumu henüz bilinmiyor -> Beyaz
            btn.classList.add('state-unknown');
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
        } else if (gpioState === true) {
            // Hedefin altında VE GPIO LOW (çalışıyor) → KIRMIZI (aktif çalışıyor)
            btn.classList.add('state-off');
        } else {
            // Hedefin altında ama GPIO HIGH (bekliyor) → YEŞİL (normal durum)
            btn.classList.add('state-on');
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

        if (system.fan_output_mode !== undefined) {
            this.systemSettings = {
                ...this.systemSettings,
                fan_output_mode: system.fan_output_mode
            };
        }

        if (system.fan_control_mode !== undefined) {
            this.systemSettings = {
                ...this.systemSettings,
                fan_control_mode: system.fan_control_mode
            };
        }

        if (system.primary_climate_sensor !== undefined) {
            this.primaryClimateSensor = system.primary_climate_sensor;
        }

        if (system.climate_sensor_fallback !== undefined) {
            this.fallbackClimateSensor = system.climate_sensor_fallback;
        }

        if (system.oxygen_sensor_mode !== undefined) {
            this.oxygenSensorMode = system.oxygen_sensor_mode;
        }

        if (system.fan_pwm_available !== undefined) {
            this.fanPwmAvailable = Boolean(system.fan_pwm_available);
        }

        this.updateAutoFanSpeedDisplay(system);
        this.toggleFanSpeedControl(this.systemSettings.fan_output_mode === 'pwm');

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
        this.systemSettings = {
            ...this.systemSettings,
            ...settings
        };
        this.toggleFanSpeedControl(this.systemSettings.fan_output_mode === 'pwm');
        this.systemSettings.screen_orientation = this.normalizeScreenOrientationPreference(this.systemSettings.screen_orientation);
        this.applyViewportProfile();

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
                } else if (sliderId === 'sld2' || sliderId === 'sld13') {
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
        if (!statusEl) {
            console.warn('connectionStatus element not found; skipping connection badge update');
            return;
        }

        if (connected) {
            statusEl.innerHTML = `<i class="fas fa-wifi"></i> ${this.t('status.connected')}`;
            statusEl.className = 'connection-status connected';
        } else {
            statusEl.innerHTML = `<i class="fas fa-wifi-slash"></i> ${this.t('status.disconnected')}`;
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
        const datetimeEl = document.getElementById('datetime');
        if (!datetimeEl) return;

        const now = new Date();
        const dateTimeStr = now.toLocaleString('tr-TR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        datetimeEl.textContent = dateTimeStr;
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
        this.showToast(this.t('system.saved'), 'success');
    }

    showToast(message, type = 'success') {
        // Eski toastları temizle
        document.querySelectorAll('.toast').forEach(t => t.remove());

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Mesaj uzunluğuna göre süre (min 3.5s, max 8s)
        const duration = Math.min(8000, Math.max(3500, message.length * 60));

        // Animasyon için timeout
        setTimeout(() => toast.classList.add('show'), 10);

        // Süre dolunca kaldır
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) document.body.removeChild(toast);
            }, 300);
        }, duration);
    }

    showWarningToast(message) {
        // Show warning toast with longer duration for safety warnings
        this.showToast(message, 'warning');
    }

    showCriticalAlarm(message, temperature, threshold) {
        // Create critical alarm overlay
        const overlay = document.createElement('div');
        overlay.className = 'critical-alarm-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 0, 0, 0.9);
            z-index: 9999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            animation: alarm-pulse 0.5s infinite alternate;
        `;
        
        overlay.innerHTML = `
            <h1 style="font-size: 3em; margin-bottom: 20px;">🚨 KRİTİK ALARM 🚨</h1>
            <p style="font-size: 2em;">${message}</p>
            <p style="font-size: 1.5em; margin-top: 20px;">Sıcaklık: ${temperature}°C</p>
            <p style="font-size: 1.2em;">Limit: ${threshold}°C</p>
            <button onclick="this.parentElement.remove()" style="margin-top: 30px; padding: 15px 30px; font-size: 1.2em; background: white; color: red; border: none; border-radius: 5px; cursor: pointer;">
                TAMAM
            </button>
        `;
        
        // Add pulse animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes alarm-pulse {
                from { opacity: 1; }
                to { opacity: 0.7; }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(overlay);
        
        // Auto-remove after 30 seconds
        setTimeout(() => {
            if (overlay.parentElement) {
                overlay.remove();
            }
        }, 30000);
    }

    playCriticalAlarmSound() {
        // Try to play alarm sound using Web Audio API
        try {
            if (!this.audioEnabled || !this.audioContext) {
                console.warn('Audio not enabled for critical alarm');
                return;
            }
            
            const audioContext = this.audioContext;
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1000; // 1kHz - higher pitch for critical alarm
            oscillator.type = 'square';
            gainNode.gain.value = 0.5;
            
            oscillator.start();
            
            // Continuous alarm pattern for critical alarm
            setTimeout(() => { oscillator.stop(); }, 500);
            setTimeout(() => {
                const osc2 = audioContext.createOscillator();
                const gain2 = audioContext.createGain();
                osc2.connect(gain2);
                gain2.connect(audioContext.destination);
                osc2.frequency.value = 1000;
                osc2.type = 'square';
                gain2.gain.value = 0.5;
                osc2.start();
                setTimeout(() => { osc2.stop(); }, 500);
            }, 600);
            setTimeout(() => {
                const osc3 = audioContext.createOscillator();
                const gain3 = audioContext.createGain();
                osc3.connect(gain3);
                gain3.connect(audioContext.destination);
                osc3.frequency.value = 1000;
                osc3.type = 'square';
                gain3.gain.value = 0.5;
                osc3.start();
                setTimeout(() => { osc3.stop(); }, 500);
            }, 1200);
        } catch (e) {
            console.error('Critical alarm sound error:', e);
        }
    }

    // Language management methods
    t(key) {
        // Get translation by key (e.g., 'button.lighting')
        const keys = key.split('.');
        let value = globalThis.translations[this.currentLanguage];
        for (const k of keys) {
            value = value?.[k];
        }
        return value || key;
    }

    async setLanguage(lang) {
        console.log('setLanguage called with:', lang);

        await loadTranslationFile(lang);
        if (!globalThis.translations[lang]) {
            console.error('Translation not found for language:', lang);
            return;
        }

        console.log('Changing language to:', lang);
        this.currentLanguage = lang;
        localStorage.setItem('language', lang);
        this.applyTranslations();
        this.updateLanguageButtons();
        document.dispatchEvent(new CustomEvent('kuvoz:language-changed', {
            detail: { language: lang }
        }));
        console.log('Language changed successfully to:', lang);
    }

    applyTranslations() {
        // Keep document language in sync with current selection
        document.documentElement.lang = this.currentLanguage;

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
            const st = co2Status.textContent;
            if (!st || st.toLowerCase().includes('reading') || st.toLowerCase().includes('okunuyor')) {
                co2Status.textContent = this.t('sensor.reading');
            }
        }

        this.renderCareModeState();
        this.renderClinicalMonitorState();
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
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const initialLang = localStorage.getItem('language') || 'tr';
        await loadTranslationFile(initialLang);

        const currentPage = resolveCurrentPageName();
        const shouldInitializeController = currentPage !== 'patient_info';
        const liveSocketPages = new Set(['index', 'cleaning']);

        if (shouldInitializeController) {
            if (!window.kuvozController) {
                window.kuvozController = new KuvozController({
                    connectSocket: liveSocketPages.has(currentPage),
                    pageName: currentPage
                });
            }
            window.kuvoz = window.kuvozController;
            console.log('Kuvoz Controller initialized with language:', initialLang, 'page:', currentPage, 'socket:', liveSocketPages.has(currentPage));
        } else {
            // For patient_info.html and other pages, just apply translations
            console.log('Non-index page detected, skipping KuvozController initialization');
            // Manually apply translations for non-index pages
            document.documentElement.lang = initialLang;
            document.querySelectorAll('[data-i18n]').forEach(element => {
                const key = element.getAttribute('data-i18n');
                const keys = key.split('.');
                let value = globalThis.translations[initialLang];
                for (const k of keys) {
                    value = value?.[k];
                }
                if (element.querySelector('i')) {
                    const textNodes = Array.from(element.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
                    if (textNodes.length > 0) {
                        textNodes[0].textContent = value || key;
                    }
                } else {
                    element.textContent = value || key;
                }
            });
        }

    } catch (e) {
        console.error('CRITICAL ERROR during initialization:', e);
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

    // Language switcher event listeners
    const langButtons = document.querySelectorAll('.lang-btn');
    langButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const lang = btn.getAttribute('data-lang');
            if (window.kuvozController) {
                await window.kuvozController.setLanguage(lang);
            } else {
                // For non-index pages, manually change language
                localStorage.setItem('language', lang);
                document.documentElement.lang = lang;
                location.reload();
            }
        });
    });

});

// Service Worker kaldırıldı: sw.js dosyası yoktu ve her yüklemede hata üretiyordu.

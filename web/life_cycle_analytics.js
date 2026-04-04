/**
 * Hayvan Yaşam Döngüsü Analitiği
 * Veteriner kliniği özelinde davranış takibi ve analiz modülü
 */

class LifeCycleAnalytics {
    constructor() {
        this.behaviorData = [];
        this.patientId = null;
        this.patientName = null;
        this.patientSpecies = null;
        this.chart = null;
        this.dailyChart = null;
        this.behaviorTypes = {
            'feeding': 'feeding',
            'drinking': 'drinking',
            'resting': 'resting',
            'elimination': 'elimination',
            'activity': 'activity',
            'sleep': 'sleep',
            'play': 'play',
            'grooming': 'grooming',
            'social': 'social'
        };
        
        this.init();
    }

    init() {
        this.loadPatients();
        this.loadBehaviorData();
        this.setupEventListeners();
        this.renderDashboard();
    }

    /**
     * Get translated behavior type label
     * @param {string} type - Behavior type key
     * @returns {string} Translated label
     */
    getBehaviorLabel(type) {
        const controller = window.kuvozController;
        if (controller && typeof controller.t === 'function') {
            return controller.t(`life_cycle.behavior_${type}`) || type;
        }
        // Fallback to English labels
        const fallbackLabels = {
            'feeding': 'Feeding',
            'drinking': 'Drinking',
            'resting': 'Resting',
            'elimination': 'Elimination',
            'activity': 'Activity',
            'sleep': 'Sleep',
            'play': 'Play',
            'grooming': 'Grooming',
            'social': 'Social'
        };
        return fallbackLabels[type] || type;
    }

    /**
     * Get translation for a key
     * @param {string} key - Translation key
     * @returns {string} Translated text
     */
    t(key) {
        const controller = window.kuvozController;
        if (controller && typeof controller.t === 'function') {
            // Try direct translation first
            let result = controller.t(key);
            if (result && result !== key) {
                return result;
            }
            // Try with life_cycle prefix for life_cycle keys
            if (key.startsWith('life_cycle.')) {
                const shortKey = key.replace('life_cycle.', '');
                result = controller.t('life_cycle.' + shortKey);
                if (result && result !== 'life_cycle.' + shortKey) {
                    return result;
                }
            }
        }
        // Fallback translations
        const fallbacks = {
            'life_cycle.all_patients': 'Tüm Hastalar',
            'life_cycle.unnamed_patient': 'İsimsiz',
            'life_cycle.nav_life_cycle': 'Yaşam Döngüsü'
        };
        return fallbacks[key] || key;
    }

    setupEventListeners() {
        // Yeni davranış ekleme formu
        const addBehaviorForm = document.getElementById('add-behavior-form');
        if (addBehaviorForm) {
            addBehaviorForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addManualBehavior();
            });
        }

        // Filtre değişiklikleri
        const dateFilter = document.getElementById('date-filter');
        if (dateFilter) {
            dateFilter.addEventListener('change', () => {
                this.loadBehaviorData();
            });
        }

        // Hasta seçimi
        const patientSelect = document.getElementById('patient-select');
        if (patientSelect) {
            patientSelect.addEventListener('change', (e) => {
                this.patientId = e.target.value;
                this.loadBehaviorData();
            });
        }
    }

    async loadPatients() {
        try {
            const response = await fetch('/api/patients');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            const patients = result.patients || [];
            
            this.populatePatientSelect(patients);
        } catch (error) {
            console.error(this.t('life_cycle.error_load_patients_failed'), error);
        }
    }

    populatePatientSelect(patients) {
        const select = document.getElementById('patient-select');
        if (!select) return;

        // Clear existing options except "All Patients"
        select.innerHTML = `<option value="">${this.t('life_cycle.all_patients')}</option>`;

        // Species translation map
        const speciesTranslations = {
            'Kedi': this.t('patient.species_cat'),
            'Köpek': this.t('patient.species_dog'),
            'Kuş': this.t('patient.species_bird'),
            'Tavşan': this.t('patient.species_rabbit'),
            'Kemirgen': this.t('patient.species_rodent'),
            'Diğer': this.t('patient.species_other'),
            'Cat': this.t('patient.species_cat'),
            'Dog': this.t('patient.species_dog'),
            'Bird': this.t('patient.species_bird'),
            'Rabbit': this.t('patient.species_rabbit'),
            'Rodent': this.t('patient.species_rodent'),
            'Other': this.t('patient.species_other')
        };

        // Add each patient as an option
        patients.forEach(patient => {
            const option = document.createElement('option');
            option.value = patient.id || '';
            
            // Format: Name - Species (Age) with translation
            let label = patient.name || this.t('life_cycle.unnamed_patient');
            if (patient.species) {
                const translatedSpecies = speciesTranslations[patient.species] || patient.species;
                label += ` - ${translatedSpecies}`;
            }
            if (patient.age) label += ` (${patient.age})`;
            
            option.textContent = label;
            select.appendChild(option);
        });

        console.log(`✅ ${patients.length} ${this.t('life_cycle.nav_life_cycle')}`);
    }

    async loadBehaviorData() {
        try {
            const dateFilter = document.getElementById('date-filter');
            const startDate = dateFilter ? dateFilter.value : '';
            
            let url = `/api/behaviors`;
            const params = new URLSearchParams();
            
            if (this.patientId) params.append('patient_id', this.patientId);
            if (startDate) params.append('start_date', startDate);
            params.append('limit', '1000');
            
            url += '?' + params.toString();

            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.behaviorData = data.data || [];
            
            this.renderDashboard();
        } catch (error) {
            console.error(this.t('life_cycle.error_load_failed'), error);
            this.showError(this.t('life_cycle.error_load_failed') + ' ' + error.message);
        }
    }

    async addManualBehavior() {
        const behaviorType = document.getElementById('behavior-type').value;
        const duration = parseInt(document.getElementById('behavior-duration').value) || 0;
        const intensity = parseFloat(document.getElementById('behavior-intensity').value) || 0;
        const notes = document.getElementById('behavior-notes').value;

        if (!behaviorType) {
            this.showError(this.t('life_cycle.error_select_type'));
            return;
        }

        try {
            const response = await fetch('/api/behaviors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    behavior_type: behaviorType,
                    duration: duration,
                    intensity: intensity,
                    notes: notes,
                    patient_context: {
                        id: this.patientId,
                        name: this.patientName,
                        species: this.patientSpecies
                    }
                })
            });

            if (response.ok) {
                this.showSuccess(this.t('life_cycle.success_saved'));
                document.getElementById('add-behavior-form').reset();
                this.loadBehaviorData(); // Refresh
            } else {
                const errorData = await response.json();
                this.showError(errorData.message || this.t('life_cycle.error_save_failed'));
            }
        } catch (error) {
            this.showError(this.t('life_cycle.error_save_failed') + ': ' + error.message);
        }
    }

    renderDashboard() {
        this.renderBehaviorChart();
        this.renderBehaviorSummary();
        this.renderDailyPattern();
        this.renderRecentBehaviors();
        this.renderAnomalyAlerts(); // Rutin dışı durum uyarıları
    }

    renderBehaviorChart() {
        const ctx = document.getElementById('behavior-chart');
        if (!ctx) return;

        // Chart.js kaldır
        if (this.chart) {
            this.chart.destroy();
        }

        // Verileri hazırla
        const behaviorCounts = {};
        Object.keys(this.behaviorTypes).forEach(type => {
            behaviorCounts[type] = 0;
        });

        this.behaviorData.forEach(behavior => {
            if (behavior.behavior_type && behaviorCounts.hasOwnProperty(behavior.behavior_type)) {
                behaviorCounts[behavior.behavior_type]++;
            }
        });

        const labels = [];
        const data = [];
        const backgroundColors = [];

        Object.entries(behaviorCounts).forEach(([type, count]) => {
            if (count > 0) {
                labels.push(this.behaviorTypes[type]);
                data.push(count);
                backgroundColors.push(this.getColorForBehavior(type));
            }
        });

        if (labels.length === 0) {
            ctx.style.display = 'none';
            document.getElementById('chart-placeholder').style.display = 'block';
            return;
        }

        ctx.style.display = 'block';
        document.getElementById('chart-placeholder').style.display = 'none';

        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderBehaviorSummary() {
        const summaryDiv = document.getElementById('behavior-summary');
        if (!summaryDiv) return;

        if (this.behaviorData.length === 0) {
            summaryDiv.innerHTML = `<p class="no-data">${this.t('life_cycle.no_data')}</p>`;
            return;
        }

        // İstatistikleri hesapla
        const stats = this.calculateBehaviorStats();

        // Get the translated label for the most common behavior
        const mostCommonLabel = this.getBehaviorLabel(stats.mostCommonBehavior.type);

        let html = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>${stats.totalBehaviors}</h3>
                    <p>${this.t('life_cycle.total_behaviors')}</p>
                </div>
                <div class="stat-card">
                    <h3>${Math.round(stats.totalDuration / 60)}${this.t('life_cycle.duration_suffix')}</h3>
                    <p>${this.t('life_cycle.total_duration')}</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.avgIntensity.toFixed(1)}</h3>
                    <p>${this.t('life_cycle.avg_intensity')}</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.mostCommonBehavior.count}</h3>
                    <p>${this.t('life_cycle.most_common')}: ${mostCommonLabel}</p>
                </div>
            </div>
        `;

        summaryDiv.innerHTML = html;
    }

    calculateBehaviorStats() {
        let totalBehaviors = 0;
        let totalDuration = 0;
        let totalIntensity = 0;
        let intensityCount = 0;
        const typeCounts = {};

        this.behaviorData.forEach(behavior => {
            totalBehaviors++;
            if (behavior.duration) totalDuration += behavior.duration;
            if (behavior.intensity !== null && behavior.intensity !== undefined) {
                totalIntensity += behavior.intensity;
                intensityCount++;
            }
            if (behavior.behavior_type) {
                typeCounts[behavior.behavior_type] = (typeCounts[behavior.behavior_type] || 0) + 1;
            }
        });

        let mostCommonType = '';
        let mostCommonCount = 0;
        Object.entries(typeCounts).forEach(([type, count]) => {
            if (count > mostCommonCount) {
                mostCommonCount = count;
                mostCommonType = type;
            }
        });

        return {
            totalBehaviors: totalBehaviors,
            totalDuration: totalDuration,
            avgIntensity: intensityCount > 0 ? totalIntensity / intensityCount : 0,
            mostCommonBehavior: {
                type: mostCommonType,
                count: mostCommonCount
            }
        };
    }

    renderDailyPattern() {
        const patternDiv = document.getElementById('daily-pattern');
        if (!patternDiv) return;

        if (this.behaviorData.length === 0) {
            patternDiv.innerHTML = `<p class="no-data">${this.t('life_cycle.no_daily_pattern')}</p>`;
            return;
        }

        // Saatlik desenleri hesapla
        const hourlyPatterns = {};
        this.behaviorData.forEach(behavior => {
            const hour = new Date(behavior.timestamp).getHours();
            const type = behavior.behavior_type;
            
            if (!hourlyPatterns[hour]) {
                hourlyPatterns[hour] = {};
            }
            hourlyPatterns[hour][type] = (hourlyPatterns[hour][type] || 0) + 1;
        });

        // Grafik için veri hazırla
        const hours = Array.from({length: 24}, (_, i) => i);
        const datasets = [];

        Object.keys(this.behaviorTypes).forEach(type => {
            const data = hours.map(hour => hourlyPatterns[hour] && hourlyPatterns[hour][type] ? hourlyPatterns[hour][type] : 0);
            if (data.some(val => val > 0)) {
                datasets.push({
                    label: this.getBehaviorLabel(type),
                    data: data,
                    borderColor: this.getColorForBehavior(type),
                    backgroundColor: this.getColorForBehavior(type) + '20',
                    tension: 0.4,
                    fill: true
                });
            }
        });

        if (datasets.length === 0) {
            patternDiv.innerHTML = `<p class="no-data">${this.t('life_cycle.no_display_data')}</p>`;
            return;
        }

        const ctx = document.getElementById('daily-pattern-chart');
        if (ctx) {
            if (this.dailyChart) {
                this.dailyChart.destroy();
            }

            this.dailyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: hours.map(h => `${h}:00`),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: this.t('life_cycle.behavior_count')
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: this.t('life_cycle.hour')
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }
    }

    renderRecentBehaviors() {
        const recentDiv = document.getElementById('recent-behaviors');
        if (!recentDiv) return;

        if (this.behaviorData.length === 0) {
            recentDiv.innerHTML = `<p class="no-data">${this.t('life_cycle.no_recent')}</p>`;
            return;
        }

        // En son 20 davranışı al
        const recentBehaviors = this.behaviorData.slice(0, 20);

        let html = '<div class="behaviors-list">';
        recentBehaviors.forEach((behavior, index) => {
            const timestamp = new Date(behavior.timestamp).toLocaleString();
            const durationStr = behavior.duration ? `${behavior.duration}s` : '-';
            const intensityStr = behavior.intensity ? behavior.intensity.toFixed(1) : '-';
            const behaviorId = `behavior-${index}`;
            const behaviorLabel = this.getBehaviorLabel(behavior.behavior_type);
            
            html += `
                <div class="behavior-item">
                    <div class="behavior-header" onclick="lifeCycleAnalytics.toggleBehavior(${index})">
                        <div class="behavior-header-left">
                            <span class="behavior-type" style="color: ${this.getColorForBehavior(behavior.behavior_type)}">
                                ${behaviorLabel}
                            </span>
                            <span class="behavior-time">${timestamp}</span>
                        </div>
                        <span class="behavior-toggle"><i class="fas fa-chevron-down"></i></span>
                    </div>
                    <div id="${behaviorId}" class="behavior-content">
                        <div class="behavior-details">
                            <span class="duration">${this.t('life_cycle.total_duration')}: ${durationStr}</span>
                            <span class="intensity">${this.t('life_cycle.intensity_label')}: ${intensityStr}</span>
                        </div>
                        ${behavior.notes ? `<div class="notes">${this.t('life_cycle.notes_label')}: ${behavior.notes}</div>` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';

        recentDiv.innerHTML = html;
    }

    toggleBehavior(index) {
        const behaviorId = `behavior-${index}`;
        const content = document.getElementById(behaviorId);
        if (content) {
            content.classList.toggle('collapsed');
        }
    }

    getColorForBehavior(type) {
        const colors = {
            'feeding': '#FF6B6B',
            'drinking': '#4ECDC4',
            'resting': '#45B7D1',
            'elimination': '#96CEB4',
            'activity': '#FFEAA7',
            'sleep': '#DDA0DD',
            'play': '#98D8C8',
            'grooming': '#F7DC6F',
            'social': '#BB8FCE'
        };
        return colors[type] || '#95A5A6';
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success';
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }

    // WebSocket ile gerçek zamanlı veri alımı
    setupWebSocket() {
        if (typeof io !== 'undefined') {
            const socket = io();
            
            socket.on('behavior_update', (data) => {
                // Yeni davranış geldiğinde ekle
                this.behaviorData.unshift(data);
                // En eski kayıtları sınırla
                if (this.behaviorData.length > 1000) {
                    this.behaviorData = this.behaviorData.slice(0, 1000);
                }
                this.renderDashboard();
            });
        }
    }

    /**
     * Rutin dışı durumları tespit et ve raporla
     * Anomaly detection for abnormal behavior patterns
     */
    renderAnomalyAlerts() {
        const alertsDiv = document.getElementById('anomaly-alerts');
        if (!alertsDiv) return;

        if (this.behaviorData.length === 0) {
            alertsDiv.innerHTML = `<p class="no-data">${this.t('life_cycle.no_anomalies')}</p>`;
            return;
        }

        const anomalies = this.detectAnomalies();

        if (anomalies.length === 0) {
            alertsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    ${this.t('life_cycle.all_normal')}
                </div>
            `;
            return;
        }

        let html = '<div class="anomaly-list">';
        anomalies.forEach(anomaly => {
            const severityClass = anomaly.severity === 'critical' ? 'critical' : 
                                  anomaly.severity === 'warning' ? 'warning' : 'info';
            const icon = anomaly.severity === 'critical' ? 'fa-exclamation-triangle' :
                         anomaly.severity === 'warning' ? 'fa-exclamation-circle' : 'fa-info-circle';
            
            html += `
                <div class="anomaly-item ${severityClass}">
                    <div class="anomaly-header">
                        <i class="fas ${icon}"></i>
                        <span class="anomaly-type">${anomaly.type}</span>
                        <span class="anomaly-severity ${severityClass}">${this.getSeverityLabel(anomaly.severity)}</span>
                    </div>
                    <div class="anomaly-details">
                        <p class="anomaly-message">${anomaly.message}</p>
                        <p class="anomaly-time">${anomaly.timestamp}</p>
                        ${anomaly.recommendation ? `<p class="anomaly-recommendation">💡 ${anomaly.recommendation}</p>` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';

        alertsDiv.innerHTML = html;
    }

    /**
     * Detect anomalies in behavior patterns
     * @returns {Array} Array of anomaly objects
     */
    detectAnomalies() {
        const anomalies = [];
        const now = new Date();
        const hours24Ago = new Date(now.getTime() - 24 * 60 * 60 * 1000);

        // Son 24 saatlik veriyi al
        const recentData = this.behaviorData.filter(b => 
            new Date(b.timestamp) >= hours24Ago
        );

        if (recentData.length === 0) {
            return anomalies;
        }

        // Davranış tiplerine göre grupla
        const behaviorGroups = {};
        recentData.forEach(b => {
            const type = b.behavior_type;
            if (!behaviorGroups[type]) {
                behaviorGroups[type] = [];
            }
            behaviorGroups[type].push(b);
        });

        // 1. YEME İÇME anomalileri
        const feedingCount = (behaviorGroups['feeding'] || []).length;
        const drinkingCount = (behaviorGroups['drinking'] || []).length;
        
        if (feedingCount === 0 && drinkingCount === 0) {
            anomalies.push({
                type: this.t('life_cycle.anomaly_no_feeding'),
                severity: 'critical',
                message: this.t('life_cycle.anomaly_no_feeding_msg'),
                timestamp: now.toLocaleString(),
                recommendation: this.t('life_cycle.anomaly_no_feeding_rec')
            });
        } else if (feedingCount < 2) {
            anomalies.push({
                type: this.t('life_cycle.anomaly_low_feeding'),
                severity: 'warning',
                message: this.t('life_cycle.anomaly_low_feeding_msg').replace('{count}', feedingCount),
                timestamp: now.toLocaleString(),
                recommendation: this.t('life_cycle.anomaly_low_feeding_rec')
            });
        }

        // 2. AŞIRI AKTİVİTE anomalisi
        const activityCount = (behaviorGroups['activity'] || []).length;
        const activityAvgIntensity = this.calculateAverageIntensity(behaviorGroups['activity'] || []);
        
        if (activityCount > 50 && activityAvgIntensity > 7) {
            anomalies.push({
                type: this.t('life_cycle.anomaly_hyperactivity'),
                severity: 'warning',
                message: this.t('life_cycle.anomaly_hyperactivity_msg').replace('{count}', activityCount),
                timestamp: now.toLocaleString(),
                recommendation: this.t('life_cycle.anomaly_hyperactivity_rec')
            });
        }

        // 3. DİNLENME anomalileri
        const restingCount = (behaviorGroups['resting'] || []).length;
        const totalBehaviors = recentData.length;
        const restingRatio = restingCount / totalBehaviors;

        if (restingRatio > 0.8) {
            anomalies.push({
                type: this.t('life_cycle.anomaly_excessive_rest'),
                severity: 'warning',
                message: this.t('life_cycle.anomaly_excessive_rest_msg').replace('{percent}', Math.round(restingRatio * 100)),
                timestamp: now.toLocaleString(),
                recommendation: this.t('life_cycle.anomaly_excessive_rest_rec')
            });
        } else if (restingCount === 0 && totalBehaviors > 10) {
            anomalies.push({
                type: this.t('life_cycle.anomaly_no_rest'),
                severity: 'warning',
                message: this.t('life_cycle.anomaly_no_rest_msg'),
                timestamp: now.toLocaleString(),
                recommendation: this.t('life_cycle.anomaly_no_rest_rec')
            });
        }

        // 4. YOĞUNLUK anomalileri
        recentData.forEach(behavior => {
            if (behavior.intensity !== null && behavior.intensity !== undefined) {
                if (behavior.intensity > 9) {
                    anomalies.push({
                        type: this.t('life_cycle.anomaly_high_intensity'),
                        severity: 'warning',
                        message: this.t('life_cycle.anomaly_high_intensity_msg')
                            .replace('{type}', this.getBehaviorLabel(behavior.behavior_type))
                            .replace('{intensity}', behavior.intensity.toFixed(1)),
                        timestamp: new Date(behavior.timestamp).toLocaleString(),
                        recommendation: this.t('life_cycle.anomaly_high_intensity_rec')
                    });
                }
            }
        });

        // 5. UZUN SÜRELİ davranış anomalisi
        recentData.forEach(behavior => {
            if (behavior.duration && behavior.duration > 3600) { // 1 saatten uzun
                anomalies.push({
                    type: this.t('life_cycle.anomaly_long_duration'),
                    severity: 'info',
                    message: this.t('life_cycle.anomaly_long_duration_msg')
                        .replace('{type}', this.getBehaviorLabel(behavior.behavior_type))
                        .replace('{duration}', Math.round(behavior.duration / 60)),
                    timestamp: new Date(behavior.timestamp).toLocaleString(),
                    recommendation: this.t('life_cycle.anomaly_long_duration_rec')
                });
            }
        });

        // 6. SOLUNUM anomalileri (AI vitals'dan)
        if (typeof window.kuvozController !== 'undefined' && window.kuvozController.aiVitalsData) {
            const aiData = window.kuvozController.aiVitalsData;
            if (aiData.status === 'TOO_MUCH_MOTION') {
                anomalies.push({
                    type: this.t('life_cycle.anomaly_motion'),
                    severity: 'info',
                    message: this.t('life_cycle.anomaly_motion_msg'),
                    timestamp: now.toLocaleString(),
                    recommendation: this.t('life_cycle.anomaly_motion_rec')
                });
            } else if (aiData.status === 'LOW_CONF' && aiData.confidence < 0.3) {
                anomalies.push({
                    type: this.t('life_cycle.anomaly_low_confidence'),
                    severity: 'warning',
                    message: this.t('life_cycle.anomaly_low_confidence_msg')
                        .replace('{confidence}', (aiData.confidence * 100).toFixed(0)),
                    timestamp: now.toLocaleString(),
                    recommendation: this.t('life_cycle.anomaly_low_confidence_rec')
                });
            }
        }

        // Tekrarlayan anomalileri filtrele (son 1 saat içinde aynı tip)
        const uniqueAnomalies = [];
        const seenTypes = new Set();
        anomalies.forEach(a => {
            if (!seenTypes.has(a.type + a.severity)) {
                uniqueAnomalies.push(a);
                seenTypes.add(a.type + a.severity);
            }
        });

        // Öncelik sırasına göre sırala (critical > warning > info)
        const severityOrder = { 'critical': 0, 'warning': 1, 'info': 2 };
        uniqueAnomalies.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

        return uniqueAnomalies;
    }

    calculateAverageIntensity(behaviors) {
        if (behaviors.length === 0) return 0;
        const total = behaviors.reduce((sum, b) => {
            return sum + (b.intensity !== null && b.intensity !== undefined ? b.intensity : 0);
        }, 0);
        return total / behaviors.length;
    }

    getSeverityLabel(severity) {
        const labels = {
            'critical': this.t('life_cycle.severity_critical'),
            'warning': this.t('life_cycle.severity_warning'),
            'info': this.t('life_cycle.severity_info')
        };
        return labels[severity] || severity;
    }
}

// Sayfa yüklendiğinde başlat
// Global instance for onclick handlers
window.lifeCycleAnalytics = null;

document.addEventListener('DOMContentLoaded', function() {
    window.lifeCycleAnalytics = new LifeCycleAnalytics();
    window.lifeCycleAnalytics.setupWebSocket();
});

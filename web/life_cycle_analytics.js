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
        this.behaviorTypes = {
            'feeding': 'Yeme',
            'drinking': 'İçme',
            'resting': 'Dinlenme',
            'elimination': 'Boşaltım',
            'activity': 'Aktivite',
            'sleep': 'Uyku',
            'play': 'Oyun',
            'grooming': 'Tımar',
            'social': 'Sosyal'
        };
        
        this.init();
    }

    init() {
        this.loadBehaviorData();
        this.setupEventListeners();
        this.renderDashboard();
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
            console.error('Davranış verileri yüklenemedi:', error);
            this.showError('Davranış verileri yüklenemedi: ' + error.message);
        }
    }

    async addManualBehavior() {
        const behaviorType = document.getElementById('behavior-type').value;
        const duration = parseInt(document.getElementById('behavior-duration').value) || 0;
        const intensity = parseFloat(document.getElementById('behavior-intensity').value) || 0;
        const notes = document.getElementById('behavior-notes').value;

        if (!behaviorType) {
            this.showError('Lütfen bir davranış türü seçin.');
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
                this.showSuccess('Davranış başarıyla kaydedildi.');
                document.getElementById('add-behavior-form').reset();
                this.loadBehaviorData(); // Yenile
            } else {
                const errorData = await response.json();
                this.showError(errorData.message || 'Davranış kaydedilemedi.');
            }
        } catch (error) {
            this.showError('Davranış kaydedilirken hata oluştu: ' + error.message);
        }
    }

    renderDashboard() {
        this.renderBehaviorChart();
        this.renderBehaviorSummary();
        this.renderDailyPattern();
        this.renderRecentBehaviors();
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
            summaryDiv.innerHTML = '<p class="no-data">Henüz davranış verisi yok.</p>';
            return;
        }

        // İstatistikleri hesapla
        const stats = this.calculateBehaviorStats();

        let html = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>${stats.totalBehaviors}</h3>
                    <p>Toplam Davranış</p>
                </div>
                <div class="stat-card">
                    <h3>${Math.round(stats.totalDuration / 60)}dk</h3>
                    <p>Toplam Süre</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.avgIntensity.toFixed(1)}</h3>
                    <p>Ortalama Yoğunluk</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.mostCommonBehavior.count}</h3>
                    <p>En Sık: ${this.behaviorTypes[stats.mostCommonBehavior.type] || stats.mostCommonBehavior.type}</p>
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
            patternDiv.innerHTML = '<p class="no-data">Günlük desen verisi yok.</p>';
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
                    label: this.behaviorTypes[type],
                    data: data,
                    borderColor: this.getColorForBehavior(type),
                    backgroundColor: this.getColorForBehavior(type) + '20',
                    tension: 0.4,
                    fill: true
                });
            }
        });

        if (datasets.length === 0) {
            patternDiv.innerHTML = '<p class="no-data">Gösterilecek veri yok.</p>';
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
                                text: 'Davranış Sayısı'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Saat'
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
            recentDiv.innerHTML = '<p class="no-data">Yakın dönem davranış kaydı yok.</p>';
            return;
        }

        // En son 20 davranışı al
        const recentBehaviors = this.behaviorData.slice(0, 20);

        let html = '<div class="behaviors-list">';
        recentBehaviors.forEach(behavior => {
            const timestamp = new Date(behavior.timestamp).toLocaleString('tr-TR');
            const durationStr = behavior.duration ? `${behavior.duration}s` : '-';
            const intensityStr = behavior.intensity ? behavior.intensity.toFixed(1) : '-';
            
            html += `
                <div class="behavior-item">
                    <div class="behavior-header">
                        <span class="behavior-type" style="color: ${this.getColorForBehavior(behavior.behavior_type)}">
                            ${this.behaviorTypes[behavior.behavior_type] || behavior.behavior_type}
                        </span>
                        <span class="behavior-time">${timestamp}</span>
                    </div>
                    <div class="behavior-details">
                        <span class="duration">Süre: ${durationStr}</span>
                        <span class="intensity">Yoğunluk: ${intensityStr}</span>
                        ${behavior.notes ? `<div class="notes">Not: ${behavior.notes}</div>` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';

        recentDiv.innerHTML = html;
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
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', function() {
    const analytics = new LifeCycleAnalytics();
    analytics.setupWebSocket();
});
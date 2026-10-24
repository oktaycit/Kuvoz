/* Shared appearance preference only. Never writes device settings or emits hardware events. */
(() => {
    'use strict';
    const key = 'kuvoz.theme';
    const themes = ['clinical', 'night', 'care'];
    const normalize = value => themes.includes(value) ? value : 'clinical';
    let current = 'clinical';
    try { current = normalize(localStorage.getItem(key)); } catch (_) { /* Private/kiosk storage may be unavailable. */ }
    const copy = {
        tr: ['Görünüm', 'Tema', 'Bu tarayıcı için seçilir ve tüm menülere anında uygulanır.', 'Klinik', 'Ölçümler ön planda, açık ve sade görünüm.', 'Gece', 'Koyu görünüm ve kamera odaklı yerleşim.', 'Bakım', 'Hedef ayarları ve ekipman kontrolleri ön planda.', 'Tema uygulandı.', 'Tema uygulandı; tarayıcı kaydına izin vermedi.'],
        en: ['Appearance', 'Theme', 'Applies immediately to every menu in this browser.', 'Clinical', 'Light, clear layout focused on measurements.', 'Night', 'Dark appearance with a camera-focused layout.', 'Care', 'Target settings and equipment controls come first.', 'Theme applied.', 'Theme applied; browser storage is unavailable.'],
        de: ['Darstellung', 'Design', 'Gilt sofort für alle Menüs in diesem Browser.', 'Klinik', 'Helle, klare Ansicht mit Fokus auf Messwerte.', 'Nacht', 'Dunkle Ansicht mit Fokus auf die Kamera.', 'Pflege', 'Zielwerte und Gerätesteuerung im Vordergrund.', 'Design angewendet.', 'Design angewendet; Browserspeicher nicht verfügbar.']
    };
    function apply(value) {
        current = normalize(value);
        document.documentElement.dataset.theme = current;
        document.documentElement.style.colorScheme = current === 'night' ? 'dark' : 'light';
        document.querySelectorAll('input[name="kuvoz-theme"]').forEach(input => { input.checked = input.value === current; });
        window.dispatchEvent(new CustomEvent('kuvoz:themechange', {detail: {theme: current}}));
    }
    apply(current); // Before first paint, including pages without the main controller.
    window.addEventListener('storage', event => { if (event.key === key || event.key === null) apply(event.newValue); });
    function language() {
        let lang = document.documentElement.lang;
        try { lang = localStorage.getItem('language') || lang; } catch (_) {}
        return copy[lang] || copy.tr;
    }
    document.addEventListener('DOMContentLoaded', () => {
        // Canvas charts need their own palette; CSS cannot recolor drawn labels.
        const Chart = window.Chart;
        if (Chart && typeof Chart.register === 'function') {
            Chart.register({
                id: 'kuvoz-appearance',
                beforeUpdate(chart) {
                    const palette = getComputedStyle(document.documentElement);
                    const text = palette.getPropertyValue('--ui-text').trim();
                    const line = palette.getPropertyValue('--ui-border').trim();
                    const surface = palette.getPropertyValue('--ui-surface').trim();
                    for (const scale of Object.values(chart.options.scales || {})) {
                        if (scale.ticks) scale.ticks.color = text;
                        if (scale.grid) scale.grid.color = line;
                        if (scale.title) scale.title.color = text;
                        if (scale.border) scale.border.color = line;
                    }
                    const plugins = chart.options.plugins;
                    if (plugins?.legend?.labels) plugins.legend.labels.color = text;
                    if (plugins?.title) plugins.title.color = text;
                    if (plugins?.tooltip) Object.assign(plugins.tooltip, {backgroundColor: surface, titleColor: text, bodyColor: text, borderColor: line, borderWidth: 1});
                }
            });
            window.addEventListener('kuvoz:themechange', () => {
                Object.values(Chart.instances || {}).forEach(chart => chart.update('none'));
            });
        }
        const host = document.getElementById('themeSettings');
        if (!host) return;
        const title = document.createElement('h2');
        const description = document.createElement('p');
        const fieldset = document.createElement('fieldset');
        const legend = document.createElement('legend');
        const options = document.createElement('div'); options.className = 'theme-options';
        const status = document.createElement('p'); status.className = 'theme-status'; status.setAttribute('role', 'status');
        fieldset.append(legend, options);
        const labels = [];
        themes.forEach((value, index) => {
            const label = document.createElement('label'); label.className = 'theme-option';
            const input = document.createElement('input'); input.type = 'radio'; input.name = 'kuvoz-theme'; input.value = value;
            const swatch = document.createElement('span'); swatch.className = 'theme-swatch theme-swatch-' + value; swatch.setAttribute('aria-hidden', 'true');
            const text = document.createElement('span'); text.className = 'theme-option-text';
            const name = document.createElement('strong'); const detail = document.createElement('span');
            text.append(name, detail); label.append(input, swatch, text); options.append(label); labels.push([name, detail]);
            input.checked = value === current;
            input.addEventListener('change', () => {
                if (!input.checked) return;
                let saved = true;
                try { localStorage.setItem(key, value); } catch (_) { saved = false; }
                apply(value); status.textContent = language()[saved ? 9 : 10];
            });
        });
        function translate() {
            const words = language(); host.setAttribute('aria-label', words[0]); title.textContent = words[0]; legend.textContent = words[1]; description.textContent = words[2];
            labels.forEach(([name, detail], index) => { name.textContent = words[3 + index * 2]; detail.textContent = words[4 + index * 2]; });
        }
        host.append(title, description, fieldset, status); translate();
        new MutationObserver(translate).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
    });
})();

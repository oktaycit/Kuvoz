/* Dashboard presentation only: never changes analysis regions or hardware state. */
(() => {
    'use strict';
    function animalBox(vision) {
        if (!vision || vision.available === false) return null;
        const tracking = vision.region_tracking;
        let box;
        if (tracking && tracking.state !== 'unselected') {
            if (!['locked', 'moving'].includes(tracking.state) || !Number.isFinite(tracking.confidence) || tracking.confidence < 0.6) return null;
            box = tracking.boxes?.animal;
        } else {
            if (vision.subject_tracking_state !== 'locked' ||
                !vision.subject_tracking_locked || !Number.isFinite(vision.subject_tracking_confidence) || vision.subject_tracking_confidence < 0.6) return null;
            const subject = vision.subject_box;
            if (subject) box = {x: subject.x_norm, y: subject.y_norm,
                width: subject.width_norm, height: subject.height_norm};
        }
        if (!box || !['x', 'y', 'width', 'height'].every(k => Number.isFinite(box[k])) ||
            box.x < 0 || box.y < 0 || box.width <= 0 || box.height <= 0 ||
            box.x + box.width > 1.001 || box.y + box.height > 1.001) return null;
        return box;
    }
    function cropFor(box, width, height) {
        // Keep the complete animal with context; preserve the source aspect ratio.
        const span = Math.min(1, Math.max(box.width * 1.3, box.height * 1.3, 1 / 2.5));
        const x = Math.max(0, Math.min(1 - span, box.x + box.width / 2 - span / 2));
        const y = Math.max(0, Math.min(1 - span, box.y + box.height / 2 - span / 2));
        return {x: x * width, y: y * height, width: span * width, height: span * height};
    }
    if (typeof module !== 'undefined' && module.exports) module.exports = {animalBox, cropFor};
    if (typeof document === 'undefined') return;
    document.addEventListener('DOMContentLoaded', () => {
        const panel = document.getElementById('compactAiPanel');
        const image = document.getElementById('compactCameraFeed');
        if (!panel || !image) return;
        const camera = image.parentElement;
        const timer = document.querySelector('.timer-section');
        const controls = timer.parentElement;
        const kiosk = window.matchMedia('(min-width:701px) and (max-width:1100px) and (max-height:650px)');
        const placeTimer = () => (kiosk.matches ? document.querySelector('.control-grid') : controls).append(timer);
        placeTimer();
        kiosk.addEventListener('change', placeTimer);
        const canvas = document.createElement('canvas');
        canvas.className = 'animal-camera-canvas';
        canvas.setAttribute('role', 'img');
        canvas.setAttribute('aria-label', 'Canlı kamera görüntüsü');
        camera.insertBefore(canvas, image);
        image.classList.add('camera-source-image');
        const context = canvas.getContext('2d');
        const focusLabel = document.getElementById('cameraFocusStatus');
        const focusButton = document.getElementById('cameraFocusToggle');
        let automatic = true, box = null, crop = null, lastFrame = 0;
        function label(text) { focusLabel.textContent = text; }
        function draw() {
            if (!image.naturalWidth || !context) return;
            const width = image.naturalWidth, height = image.naturalHeight;
            if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; crop = null; }
            const next = automatic && box ? cropFor(box, width, height) : null;
            if (next) {
                if (crop) for (const key of Object.keys(next)) next[key] = crop[key] * 0.65 + next[key] * 0.35;
                crop = next;
            } else crop = null;
            context.clearRect(0, 0, width, height);
            if (crop) context.drawImage(image, crop.x, crop.y, crop.width, crop.height, 0, 0, width, height);
            else context.drawImage(image, 0, 0, width, height);
        }
        function wide(text) { box = null; crop = null; label(text); draw(); }
        image.addEventListener('load', draw);
        focusButton.addEventListener('click', () => {
            automatic = !automatic;
            focusButton.setAttribute('aria-pressed', String(automatic));
            focusButton.textContent = automatic ? 'Otomatik odak' : 'Geniş kadraj';
            label(automatic && box ? 'Hayvan odakta' : 'Geniş kadraj');
            crop = null; draw();
        });
        const expand = document.getElementById('cameraExpand');
        expand.addEventListener('click', () => {
            const expanded = panel.classList.toggle('camera-expanded');
            expand.setAttribute('aria-expanded', String(expanded));
            expand.textContent = expanded ? 'Küçült' : 'Büyüt';
        });
        const system = document.querySelector('.system-panel');
        const menu = document.getElementById('dashboardMenu');
        function closeMenu() { system.classList.remove('dashboard-menu-open'); menu.setAttribute('aria-expanded', 'false'); }
        menu.addEventListener('click', () => {
            const open = system.classList.toggle('dashboard-menu-open');
            menu.setAttribute('aria-expanded', String(open));
            if (open) document.getElementById('dashboardMenuClose').focus();
        });
        document.getElementById('dashboardMenuClose').addEventListener('click', () => { closeMenu(); menu.focus(); });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') { closeMenu(); panel.classList.remove('camera-expanded'); expand.setAttribute('aria-expanded', 'false'); expand.textContent = 'Büyüt'; }
        });
        // Reuse the controller connection; do not open another Socket.IO client.
        let boundSocket;
        function bindSocket() {
            const socket = window.kuvozController?.socket;
            if (!socket || socket === boundSocket) return;
            boundSocket = socket;
            socket.on('ai_update', data => {
                box = animalBox(data?.vision);
                if (data?.frame) lastFrame = Date.now();
                if (!box) wide('Geniş kadraj · takip bekleniyor');
                else { label(automatic ? 'Hayvan odakta' : 'Geniş kadraj'); if (!data.frame) draw(); }
            });
            socket.on('disconnect', () => wide('Bağlantı kesildi · geniş kadraj'));
            socket.on('ai_status', data => { if (data?.enabled === false) wide('Kamera izleme kapalı'); });
        }
        bindSocket();
        setInterval(() => {
            bindSocket();
            if (!lastFrame || Date.now() - lastFrame > 5000) wide('Canlı görüntü bekleniyor · geniş kadraj');
        }, 1000);
        // Mirrors keep existing target controls and protocol unchanged.
        for (const [target, host] of [['sld3_value', 'temperature'], ['sld2_value', 'humidity']]) {
            const source = document.getElementById(target), value = document.getElementById(host);
            const hint = document.createElement('div'); hint.className = 'measurement-target';
            value.after(hint);
            const update = () => { hint.textContent = 'Hedef ' + source.textContent; };
            new MutationObserver(update).observe(source, {childList: true, characterData: true, subtree: true}); update();
        }
        document.querySelectorAll('.target-btn').forEach(button => {
            const name = button.closest('.target-item').querySelector('.target-label').textContent;
            button.setAttribute('aria-label', name + (button.classList.contains('plus') ? ' artır' : ' azalt'));
        });
    });
})();

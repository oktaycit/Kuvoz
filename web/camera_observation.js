(() => {
    const qualityLabels = {usable: 'Gözleme uygun', dark: 'Karanlık', overexposed: 'Aşırı aydınlık', blurred: 'Görüntü net değil', lighting_changed: 'Işık değişti; görüntü dengeleniyor', tracking_lost: 'Takip güvenilir değil', unavailable: 'Güncel görüntü yok'};
    const set = (id, value) => { document.getElementById(id).textContent = value; };
    const duration = seconds => `${Math.floor((seconds || 0) / 60)} dk ${(seconds || 0) % 60} sn`;
    let received = 0, lastFrame = 0;
    const notice = text => {
        const node = document.getElementById('cameraNotice');
        node.textContent = text || '';
        node.hidden = !text;
    };
    function render(data) {
        const o = data?.observation || data?.vision?.observation || {};
        const usable = o.quality === 'usable';
        if (data?.frame) lastFrame = Date.now();
        notice(!lastFrame ? 'Canlı görüntü bekleniyor.' : !usable ? (qualityLabels[o.quality] || 'Görüntü henüz değerlendirilemiyor.') : '');
        set('quality', qualityLabels[o.quality] || 'Veri yok');
        set('movement', !usable ? 'Belirsiz' : o.movement === 'active' ? 'Hareketli' : 'Düşük hareket');
        set('posture', !usable ? 'Belirsiz' : ({horizontal: 'Yatay yönelim · tahmin', vertical: 'Dikey yönelim · tahmin'})[o.posture] || 'Belirsiz');
        set('changes', o.position_changes ?? '—');
        set('active', duration(o.summary?.active_seconds));
        set('still', duration(o.summary?.low_motion_seconds));
        set('summary', `Değerlendirilebilir görüntü: ${duration(o.summary?.observed_seconds)}. Son konum değişimi: ${o.last_position_change ? new Date(o.last_position_change * 1000).toLocaleTimeString('tr-TR') : 'Henüz gözlenmedi'}.`);
        const bars = document.getElementById('activityTimeline');
        bars.replaceChildren();
        for (const minute of o.timeline || []) {
            const bar = document.createElement('div');
            const active = Math.min(100, minute.active_seconds / 60 * 100);
            const observed = Math.min(100, minute.observed_seconds / 60 * 100);
            bar.style.cssText = `flex:1;min-width:0;background:linear-gradient(to top,#168577 0% ${active}%,#d9e5e2 ${active}% ${observed}%,#66787b ${observed}% 100%)`;
            bar.title = `${new Date(minute.timestamp * 1000).toLocaleTimeString('tr-TR')} · ${minute.active_seconds} sn hareket · ${minute.observed_seconds} sn gözlem`;
            bars.appendChild(bar);
        }
        const timeline = document.getElementById('timeline');
        timeline.replaceChildren();
        for (const event of [...(o.events || [])].reverse()) {
            const li = document.createElement('li');
            li.textContent = `${new Date(event.timestamp * 1000).toLocaleTimeString('tr-TR')} · Konum değişimi`;
            timeline.appendChild(li);
        }
        if (!timeline.children.length) {
            const li = document.createElement('li'); li.textContent = 'Henüz kayıt yok.'; timeline.appendChild(li);
        }
        if (data?.frame) {
            document.getElementById('preview').src = `data:image/jpeg;base64,${data.frame}`;
            document.getElementById('preview').hidden = false;
            document.getElementById('previewPlaceholder').hidden = true;
        }
    }
    const socket = io();
    socket.on('connect', () => socket.emit('get_status'));
    socket.on('ai_update', data => { received = Date.now(); render(data); });
    const unavailable = () => { lastFrame = 0; notice('Güncel kamera görüntüsü yok.'); set('quality', 'Güncel görüntü yok'); set('movement', 'Belirsiz'); set('posture', 'Belirsiz'); document.getElementById('preview').removeAttribute('src'); document.getElementById('preview').hidden = true; document.getElementById('previewPlaceholder').hidden = false; };
    socket.on('disconnect', unavailable);
    setInterval(() => { if (!received || Date.now() - received > 15000 || (lastFrame && Date.now() - lastFrame > 15000)) unavailable(); }, 3000);
})();

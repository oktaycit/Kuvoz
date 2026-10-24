/* Read-only presentation of confirmed server outputs; no control decisions here. */
(() => {
    'use strict';
    const number = value => value !== null && value !== '' && value !== '--' && Number.isFinite(Number(value)) ? Number(value) : null;
    function deviceStatus(id, state, fresh) {
        if (!fresh) return 'Durum bekleniyor';
        const output = state.gpio_outputs?.[id], enabled = state.buttons?.[id] === true;
        if (output === null || output === undefined) return 'Çıkış bilinmiyor';
        if (output === true) {
            if (id === 'b6') {
                const duty = number(state.system?.fan_pwm_duty);
                return state.system?.fan_output_mode === 'pwm' && duty !== null ? `Çıkış %${Math.round(duty)}` : 'Çıkış açık';
            }
            return ({b4:'Isıtıyor', b5:'Isıtıyor', b9:'Soğutuyor', b3:'Nem veriyor', b2:'Çalışıyor'})[id] || 'Açık';
        }
        if (id === 'b6' && state.gpio_outputs?.b2 === true) return 'Nebülizatör kilidi';
        if (!enabled) return 'Kapalı';
        if (id === 'b9' && state.system_settings?.cooling_enabled === false) return 'Özellik kapalı';
        if (id === 'b9' && (state.gpio_outputs?.b4 === true || state.gpio_outputs?.b5 === true)) return 'Isıtma kilidi';
        if (['b4','b5','b9'].includes(id) && number(state.sensors?.temperature?.value) === null) return 'Sensör bekleniyor';
        if (id === 'b9' && !number(state.sliders?.sld12)) return 'Hedef gerekli';
        return id === 'b2' ? 'Aralık bekliyor' : 'Beklemede';
    }
    function summary(state, notifications, fresh, sensorsFresh) {
        const items = notifications.filter(n => !n.expiresAt || n.expiresAt > Date.now());
        if (!fresh) items.push({severity:'warning', title:'Cihaz durumu güncel değil'});
        if (fresh && ['b4','b5','b6','b9'].some(id=>state.buttons?.[id]===true && typeof state.gpio_outputs?.[id]!=='boolean'))
            items.push({severity:'warning', title:'Etkin cihazın çıkışı doğrulanamıyor'});
        if (!sensorsFresh || number(state.sensors?.temperature?.value) === null || number(state.sensors?.humidity?.value) === null)
            items.push({severity:'warning', title:'Sensör verisi bekleniyor'});
        if (state.system?.simulation_mode || /simulat/i.test(state.sensors?.temperature?.status || ''))
            items.push({severity:'warning', title:'Simülasyon verisi'});
        if ((state.buttons?.b4 || state.buttons?.b5) && state.buttons?.b9 &&
            number(state.sliders?.sld12) !== null && number(state.sliders?.sld3) !== null &&
            Number(state.sliders.sld12) < Number(state.sliders.sld3))
            items.push({severity:'warning', title:'Isıtma ve soğutma hedefleri çakışıyor', detail:'İki kontrol etkin. Isıtma önceliklidir; hedefleri kontrol edin.'});
        return {items, severity:items.some(n=>n.severity==='critical') ? 'critical' : items.some(n=>n.severity==='warning') ? 'warning' : 'info'};
    }
    if (typeof module !== 'undefined' && module.exports) module.exports = {deviceStatus, summary};
    if (typeof document === 'undefined') return;
    document.addEventListener('DOMContentLoaded', () => {
        let state = {}, outputAt = 0, sensorAt = 0, socket, fetching = false;
        const $ = id => document.getElementById(id);
        const badge = $('dashboardAlarm'), dialog = $('dashboardAlertDialog'), list = $('dashboardAlertList');
        const lock = $('dashboardLockDialog'), unlock = $('dashboardUnlock');
        const statusNodes = {};
        for (const id of ['b4','b5','b9','b6','b1','b3','b2']) {
            const button = $('btn_'+id), node = document.createElement('small');
            node.className='device-status'; node.textContent='Durum bekleniyor'; button.append(node); statusNodes[id]=node;
        }
        const care = document.querySelector('.care-mode-buttons');
        const careHome = care.parentElement;
        const media = window.matchMedia('(min-width:701px) and (max-width:1100px) and (max-height:650px)');
        const placeCare = () => (media.matches ? $('dashboardCareSlot') : careHome).append(care);
        placeCare(); media.addEventListener('change', placeCare);
        $('careModeProfile').setAttribute('role','link'); $('careModeProfile').tabIndex=0;
        const patient = () => { window.location.href='patient_info.html'; };
        $('careModeProfile').addEventListener('click', patient);
        $('careModeProfile').addEventListener('keydown', e=>{if(e.key==='Enter') patient();});
        function update(data) {
            if (!data) return;
            for (const key of ['buttons','gpio_outputs','sliders','system','system_settings','sensors','care_settings'])
                if (data[key]) state[key]={...state[key], ...data[key]};
            if (data.gpio_outputs) outputAt=Date.now();
            if (data.sensors) sensorAt=Date.now();
            render();
        }
        function render() {
            const controller=window.kuvozController;
            const fresh=Date.now()-outputAt<10000 && socket?.connected === true;
            const sensorsFresh=Date.now()-sensorAt<45000 && socket?.connected === true;
            for (const id of Object.keys(statusNodes)) {
                statusNodes[id].textContent=deviceStatus(id,state,fresh);
                $('btn_'+id).dataset.output=fresh ? String(state.gpio_outputs?.[id]) : 'unknown';
            }
            const notifications=controller?.homeNotifications ? [...controller.homeNotifications.values()] : [];
            const result=summary(state,notifications,fresh,sensorsFresh);
            badge.dataset.severity=result.severity;
            const count=result.items.length;
            badge.textContent=count ? `${result.severity==='critical'?'Kritik':'Uyarı'} · ${count}` : 'Uyarı yok';
            badge.title='Bildirilen alarmlar ve veri güncelliği';
            $('dashboardLockStatus').textContent=badge.textContent;
            $('dashboardLockStatus').dataset.severity=result.severity;
            list.replaceChildren();
            if (!count) { const p=document.createElement('p');p.textContent='Bildirilen aktif uyarı yok.'; list.append(p); }
            for (const item of result.items) { const p=document.createElement('p');p.textContent=item.title+(item.detail?' — '+item.detail:''); list.append(p); }
            const tempStatus=$('temperatureWorkStatus');
            tempStatus.textContent=!fresh ? 'Durum bekleniyor' : state.gpio_outputs?.b4 || state.gpio_outputs?.b5 ? 'Isıtma çıkışı açık' : state.gpio_outputs?.b9 ? 'Soğutma çıkışı açık' : 'Isıtma / soğutma kapalı';
            const speedLabel=document.querySelector('#fanSpeedTarget .target-label');
            if(speedLabel) speedLabel.textContent=state.system?.fan_control_mode==='manual' ? 'Fan ayarı (%)' : 'Fan çıkışı (%)';
            const oxygen=document.querySelector('#oxygenCard .sensor-status');
            if (oxygen && state.system?.oxygen_estimated) oxygen.textContent='Tahmini · O₂ sensörü yok';
            const tempCard=document.querySelector('.sensor-card-large.temperature');
            tempCard.dataset.severity=notifications.some(n=>n.severity==='critical'&&/temp/.test(n.key||''))?'critical':notifications.some(n=>/temp/.test(n.key||''))?'warning':'info';
        }
        async function initialStatus() {
            if(fetching) return;fetching=true;
            try { const r=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(5000)}); if(r.ok) update(await r.json()); }
            catch (_) { /* The visible freshness indicator remains unknown. */ } finally {fetching=false;}
        }
        function bind() {
            const next=window.kuvozController?.socket;
            if (!next || socket===next) return;
            socket=next;
            for (const event of ['status_response','button_update','sensor_update','care_settings_update','settings_update']) socket.on(event,update);
            socket.on('disconnect',()=>{outputAt=0;sensorAt=0;render();});
            socket.on('connect',initialStatus);
            initialStatus();
        }
        badge.addEventListener('click',()=>dialog.showModal());
        $('dashboardAlertClose').addEventListener('click',()=>dialog.close());
        $('dashboardLockAlerts').addEventListener('click',()=>dialog.showModal());
        $('dashboardLock').addEventListener('click',()=>lock.showModal());
        lock.addEventListener('cancel', e=>e.preventDefault());
        let hold;
        const cancelHold=()=>{clearTimeout(hold);hold=null;unlock.classList.remove('holding');};
        const beginHold=()=>{if(hold)return;unlock.classList.add('holding');hold=setTimeout(()=>{lock.close();cancelHold();},1500);};
        unlock.addEventListener('pointerdown',e=>{if(e.isPrimary!==false && e.button===0){unlock.setPointerCapture(e.pointerId);beginHold();}});
        for(const event of ['pointerup','pointercancel','pointerleave','lostpointercapture','blur']) unlock.addEventListener(event,cancelHold);
        unlock.addEventListener('keydown',e=>{if([' ','Enter'].includes(e.key)){e.preventDefault();if(!e.repeat)beginHold();}});
        unlock.addEventListener('keyup',cancelHold);
        document.addEventListener('visibilitychange',cancelHold);
        bind();setInterval(()=>{bind();render();},1000);
    });
})();

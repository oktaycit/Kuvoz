/* Persistent clinical reminders: the server clock determines when an alarm is due. */
(() => {
    if (window.kuvozReminders) return;
    window.kuvozReminders = true;
    const languages = {tr:'Türkçe',en:'English',de:'Deutsch',es:'Español',pt:'Português',ru:'Русский',ko:'한국어',zh:'中文',ja:'日本語',ar:'العربية'};
    const t = key => {
        const lang = localStorage.getItem('language') || 'tr';
        return globalThis.translations?.[lang]?.reminders?.[key] || globalThis.translations?.en?.reminders?.[key] || key;
    };
    let rows = [], audio = null, lastSound = 0, busy = false, hadError = false;
    const banner = document.createElement('aside');
    banner.className = 'clinical-reminder-banner'; banner.hidden = true;
    banner.setAttribute('role', 'alert'); document.body.append(banner);
    const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = 'reminders.css'; document.head.append(link);
    function languageSelect() {
        document.querySelectorAll('.language-selector').forEach(host => {
            host.replaceChildren();
            const select = document.createElement('select'); select.className = 'kuvoz-language-select'; select.setAttribute('aria-label','Language');
            Object.entries(languages).forEach(([code,name]) => select.add(new Option(name,code)));
            select.value = localStorage.getItem('language') || 'tr';
            select.addEventListener('change', async () => {
                if (window.kuvozController) await window.kuvozController.setLanguage(select.value);
                else { localStorage.setItem('language',select.value); location.reload(); }
            }); host.append(select);
        });
    }
    async function api(path = '', options = {}) {
        const response = await fetch('/api/reminders' + path, {cache:'no-store', ...options, headers:{'Content-Type':'application/json'}});
        const body = await response.json();
        if (!response.ok || !body.success) throw new Error(body.error || 'storage_error');
        return body;
    }
    const node = (tag, text) => { const el = document.createElement(tag); el.textContent = text; return el; };
    function error(message) {
        hadError = true;
        const host = document.getElementById('reminderError');
        if (host) host.textContent = message;
        else { render(); banner.hidden = false; banner.append(node('p',message)); }
    }
    async function action(row, name) {
        try { await api('/'+encodeURIComponent(row.id),{method:'PATCH',body:JSON.stringify({action:name})}); await refresh(); }
        catch (_) { error(t('error')); }
    }
    function actions(row, host) {
        const bar = node('div',''); bar.className = 'reminder-actions';
        for (const name of row.due ? ['acknowledge','snooze','cancel'] : ['cancel']) {
            const button = node('button',t(name)); button.type='button';
            button.addEventListener('click',async () => {button.disabled=true; await action(row,name); button.disabled=false;}); bar.append(button);
        } host.append(bar);
    }
    function render() {
        const due = rows.filter(r => r.due);
        banner.replaceChildren(); banner.hidden = due.length === 0;
        due.forEach(row => {
            const box = node('div',''); box.append(node('strong',t(row.kind)+': '+row.title));
            if(row.patient_name) box.append(node('p',row.patient_name));
            box.append(node('p',new Date(row.due_at*1000).toLocaleString(document.documentElement.lang)));
            actions(row,box); banner.append(box);
        });
        const list = document.getElementById('reminderList');
        if (list) {
            list.replaceChildren();
            const pending = rows.filter(r => r.status === 'pending').sort((a,b)=>a.due_at-b.due_at);
            if(!pending.length) list.append(node('p',t('empty')));
            pending.forEach(row => {
                const box=node('article',''); box.className='reminder-row'; box.dataset.due=String(row.due);
                box.append(node('strong',t(row.kind)+': '+row.title));
                box.append(node('p',[row.patient_name,new Date(row.due_at*1000).toLocaleString(document.documentElement.lang)].filter(Boolean).join(' · ')));
                if(row.repeat_minutes) box.append(node('p',t('repeat')+': '+row.repeat_minutes));
                actions(row,box); list.append(box);
            });
        }
        playSound();
    }
    function playSound() {
        if (rows.some(r => r.due) && Date.now()-lastSound >= 30000 && audio?.state === 'running') {
            lastSound=Date.now();
            for(let i=0;i<3;i++) {
                const osc=audio.createOscillator(), gain=audio.createGain();
                osc.connect(gain);gain.connect(audio.destination);osc.frequency.value=880;gain.gain.value=0.15;
                osc.start(audio.currentTime+i*0.35);osc.stop(audio.currentTime+i*0.35+0.2);
            }
        }
    }
    async function refresh() {
        if(busy) return; busy=true;
        try { const next=(await api()).reminders;
            if(hadError || JSON.stringify(next)!==JSON.stringify(rows)){rows=next;render();} else {playSound();}
            hadError=false;
            const e=document.getElementById('reminderError');if(e)e.textContent=''; }
        catch (_) { error(t('connection_error')); }
        finally {busy=false;}
    }
    document.addEventListener('pointerdown',() => {
        try {audio ||= new (window.AudioContext || window.webkitAudioContext)();audio.resume().then(playSound).catch(()=>{});}catch(_){}
    });
    document.addEventListener('kuvoz:language-changed',() => {languageSelect();render();});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
    const form=document.getElementById('reminderForm');
    if(form) form.addEventListener('submit',async event => {
        event.preventDefault(); const f=form.elements, button=form.querySelector('button[type="submit"]');button.disabled=true;
        try {
            await api('',{method:'POST',body:JSON.stringify({kind:f.kind.value,title:f.title.value,due_at:new Date(f.due.value).getTime()/1000,repeat_minutes:Number(f.repeat.value)})});
            form.reset();await refresh();
        } catch (_) {error(t('error'));} finally {button.disabled=false;}
    });
    languageSelect();render();refresh();setInterval(refresh,5000);
})();

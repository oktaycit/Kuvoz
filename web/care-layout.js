/* Shared reference layouts: move existing controls, never duplicate device handlers or sockets. */
(() => {
    'use strict';
    document.addEventListener('DOMContentLoaded', () => {
        if (!document.body.classList.contains('dashboard-touch')) return;
        const $ = id => document.getElementById(id);
        const source = document.querySelector('.main-content');
        const equipment = document.querySelector('.control-grid');
        const targets = document.querySelector('.target-values');
        const modes = document.querySelector('.care-mode-buttons');
        const system = document.querySelector('.system-panel');
        if (!source || !equipment || !targets || !modes || !system) return;
        const homes = new Map();
        let active = false, layoutTheme = null, hostnameRequested = false, lastCameraFrame = 0, cameraStaleTimer;
        const make = (tag, cls, text) => { const e = document.createElement(tag); e.className = cls || ''; if (text) e.textContent = text; return e; };
        const icon = cls => { const i = make('i', 'fas ' + cls); i.setAttribute('aria-hidden', 'true'); return i; };
        const move = (node, host) => {
            if (!node) return;
            if (!homes.has(node)) { const marker = document.createComment('care-layout-home'); node.before(marker); homes.set(node, marker); }
            host.append(node);
        };
        const header = make('header', 'care-reference-header');
        const brand = make('div', 'care-reference-brand');
        const wordmark = make('strong', '', 'KUVOZ'); wordmark.append(icon('fa-paw'));
        const subtitle = make('span', '', 'Veteriner Yoğun Bakım Ünitesi'); brand.append(wordmark, subtitle);
        const patient = make('div', 'care-reference-patient'); patient.append(icon('fa-cat'));
        const status = make('div', 'care-reference-status');
        const clock = make('div', 'care-reference-clock'); const date = make('span'); const time = make('strong'); clock.append(date, time);
        const deviceName=make('span','clinical-device-name',window.location.hostname);
        const nightSettings=make('button','night-settings'); nightSettings.type='button'; nightSettings.append(icon('fa-sliders-h'));
        const lockCaption=make('span','night-lock-caption'); $('dashboardLock')?.append(lockCaption);
        header.append(brand, deviceName, patient, status, clock, nightSettings);
        const stage = make('main', 'care-reference-stage');
        const left = make('section', 'care-reference-monitor'); left.setAttribute('aria-label', 'Ortam ölçümleri');
        const alertLine = make('div', 'care-reference-alert');
        const readings = make('div', 'care-reference-readings');
        const footer = make('div', 'care-reference-footer');
        const cameraButton = make('button', 'care-reference-camera'); cameraButton.type = 'button';
        const cameraText = make('span'); const cameraTitle = make('strong'); const cameraDetail = make('span');
        cameraText.append(cameraTitle, cameraDetail); cameraButton.append(icon('fa-video-slash'), cameraText);
        const oxygenHost = make('div', 'care-reference-oxygen');
        footer.append(cameraButton, oxygenHost); left.append(alertLine, readings, footer);
        const right = make('section', 'care-reference-controls');
        const title = make('h2'); title.append(icon('fa-cog')); const titleText = make('span'); title.append(titleText);
        const modeHost = make('div', 'care-reference-mode');
        const targetHost = make('div', 'care-reference-targets'); targetHost.id='careReferenceTargets';
        const deviceHead = make('div', 'care-reference-device-head'); const deviceTitle = make('h3');
        const edit = make('button', 'care-reference-edit'); edit.type = 'button'; edit.append(icon('fa-sliders-h')); const editText = make('span'); edit.append(editText);
        const list = make('div', 'care-reference-devices'); deviceHead.append(deviceTitle, edit);
        right.append(title, modeHost, targetHost, deviceHead, list); stage.append(left, right);
        const clinicalPanel=make('section','clinical-control-panel');
        const clinicalHead=make('div','clinical-control-head'); const clinicalTitle=make('h2');
        const targetEdit=make('button','clinical-target-edit'); targetEdit.type='button';
        clinicalHead.append(clinicalTitle,targetEdit);
        const clinicalEquipment=make('div','clinical-equipment-host'); clinicalPanel.append(clinicalHead,clinicalEquipment);
        const clinicalCamera=make('section','clinical-camera-panel');
        const clinicalCameraHead=make('div','clinical-camera-head'); const clinicalCameraTitle=make('h2');
        const clinicalExpand=make('button','clinical-camera-expand'); clinicalExpand.type='button'; clinicalExpand.append(icon('fa-expand'));
        clinicalCameraHead.append(clinicalCameraTitle,clinicalExpand);
        const clinicalCameraSurface=make('div','clinical-camera-surface');
        const clinicalWaiting=make('div','clinical-camera-waiting'); const clinicalWaitTitle=make('strong'); const clinicalWaitText=make('p');
        clinicalWaiting.append(icon('fa-video-slash'),clinicalWaitTitle,clinicalWaitText);
        clinicalCameraSurface.append(clinicalWaiting); clinicalCamera.append(clinicalCameraHead,clinicalCameraSurface);
        stage.append(clinicalPanel,clinicalCamera);
        const nav = make('nav', 'care-reference-nav'); nav.setAttribute('aria-label', 'Ana gezinme');
        const navItems = [];
        for (const [tag, glyph, href] of [['button','fa-heartbeat',null],['a','fa-paw','patient_info.html'],['a','fa-broom','cleaning.html'],['button','fa-cog',null]]) {
            const node = make(tag); if (href) node.href = href; else node.type = 'button';
            const label = make('span'); node.append(icon(glyph), label); nav.append(node); navItems.push([node,label]);
        }
        const nightFooter=make('footer','night-reference-footer');
        const nightTime=make('span'); const nightOxygen=make('span'); const nightBrand=make('strong','','KUVOZ');
        nightFooter.append(nightTime,make('span','',subtitle.textContent),nightOxygen,nightBrand);
        navItems[0][0].setAttribute('aria-current', 'page');
        navItems[0][0].addEventListener('click', () => stage.scrollIntoView({block:'start'}));
        function dialog(id) {
            const d = make('dialog', 'care-reference-dialog'); d.id = id;
            const close = make('button', 'care-reference-close'); close.type = 'button'; close.append(icon('fa-times')); const text = make('span'); close.append(text);
            close.addEventListener('click', () => d.close()); d.append(close); document.body.append(d);
            return {node:d, closeText:text};
        }
        const controlDialog = dialog('careEquipmentDialog'); const controlTitle = make('h2'); controlTitle.id = 'careEquipmentTitle'; controlDialog.node.append(controlTitle); controlDialog.node.setAttribute('aria-labelledby', controlTitle.id);
        const extraTargets = make('div', 'care-reference-extra-targets');
        const systemDialog = dialog('careSystemDialog'); const systemTitle = make('h2'); systemTitle.id = 'careSystemTitle'; systemDialog.node.setAttribute('aria-labelledby', systemTitle.id); systemDialog.node.append(systemTitle);
        const quickLinks = make('div', 'care-reference-quick-links');
        const cameraLink = make('a'); cameraLink.href = 'help.html'; const themeLink = make('a'); themeLink.href = 'settings.html'; quickLinks.append(cameraLink, themeLink); systemDialog.node.append(quickLinks);
        const cameraDialog = dialog('careCameraDialog'); const cameraHeading = make('h2'); cameraHeading.id = 'careCameraTitle'; cameraDialog.node.setAttribute('aria-labelledby',cameraHeading.id); cameraDialog.node.append(cameraHeading);
        const cameraFallback = make('p'); cameraDialog.node.append(cameraFallback);
        nightSettings.addEventListener('click', () => open(controlDialog.node));
        targetEdit.addEventListener('click', () => open(controlDialog.node));
        clinicalExpand.addEventListener('click', () => { move($('compactAiPanel'),cameraDialog.node); open(cameraDialog.node); });
        cameraDialog.node.addEventListener('close', () => {
            if(active && ['clinical','night'].includes(layoutTheme)) clinicalCameraSurface.append($('compactAiPanel'));
            $('compactAiPanel')?.classList.remove('camera-expanded');
            const expand=$('cameraExpand');
            if(expand) { expand.setAttribute('aria-expanded','false'); expand.textContent='Büyüt'; }
        });
        const open = d => { if (!d.open) d.showModal(); };
        edit.addEventListener('click', () => open(controlDialog.node));
        navItems[3][0].addEventListener('click', () => open(systemDialog.node));
        cameraButton.addEventListener('click', () => open(cameraDialog.node));
        const records = [];
        for (const id of ['b6','b4','b5','b3','b1','b2','b9']) {
            const button = $('btn_' + id); if (!button) continue;
            const row = make('div', 'care-reference-device');
            const name = make('span', 'care-reference-device-name');
            const glyph = button.querySelector('i')?.cloneNode(true); if (glyph) name.append(glyph);
            const label = make('span'); name.append(label);
            const badge = make('span', 'care-reference-device-badge'); row.append(name,badge); list.append(row);
            const toggle=make('span','clinical-toggle'); toggle.setAttribute('aria-hidden','true'); button.append(toggle);
            records.push({id,button,row,label,badge});
        }
        let words;
        const translations = {
            tr:['Bakım kontrolü','Ekipman durumu','Kontroller','İzlem','Hasta','Temizlik','Menü','Kamera görüntüsü','Canlı görüntü bekleniyor','O₂ sensörü yok','Oksijen ölçümü yapılmıyor.','Kapat','Ekipman kontrolleri','Kullanım kılavuzu','Ayarlar','Kamera kapalı veya kullanılamıyor.'],
            en:['Care controls','Equipment status','Controls','Monitor','Patient','Cleaning','Menu','Camera view','Waiting for live video','No O₂ sensor','Oxygen is not measured.','Close','Equipment controls','User guide','Settings','Camera is off or unavailable.'],
            de:['Pflegesteuerung','Gerätestatus','Steuerung','Überblick','Patient','Reinigung','Menü','Kamerabild','Warten auf Livebild','Kein O₂-Sensor','Keine Sauerstoffmessung.','Schließen','Gerätesteuerung','Bedienungsanleitung','Einstellungen','Kamera aus oder nicht verfügbar.']
        };
        function translate() {
            words = translations[document.documentElement.lang] || translations.tr;
            titleText.textContent=words[0]; deviceTitle.textContent=words[1]; editText.textContent=words[2];
            navItems.forEach(([,text],i)=>text.textContent=words[3+i]);
            cameraTitle.textContent=words[7]; cameraDetail.textContent=words[8];
            for (const d of [controlDialog,systemDialog,cameraDialog]) d.closeText.textContent=words[11];
            controlTitle.textContent=words[12]; systemTitle.textContent=words[6]; cameraLink.textContent=words[13]; themeLink.textContent=words[14]; cameraHeading.textContent=words[7]; cameraFallback.textContent=words[15];
            const clinicalCopy={
                tr:['Cihaz Kontrolleri','Hedefler ve süreler','Kamera','Kamerayı büyüt','Oksijen'],
                en:['Device Controls','Targets and timers','Camera','Expand camera','Oxygen'],
                de:['Gerätesteuerung','Zielwerte und Timer','Kamera','Kamera vergrößern','Sauerstoff']
            }[document.documentElement.lang] || ['Cihaz Kontrolleri','Hedefler ve süreler','Kamera','Kamerayı büyüt','Oksijen'];
            clinicalTitle.textContent=clinicalCopy[0]; targetEdit.textContent=clinicalCopy[1]; clinicalCameraTitle.textContent=clinicalCopy[2]; clinicalExpand.setAttribute('aria-label',clinicalCopy[3]);
            if(['clinical','night'].includes(layoutTheme)) controlTitle.textContent=clinicalCopy[1];
            nightSettings.setAttribute('aria-label',clinicalCopy[1]); nightSettings.title=clinicalCopy[1];
            sync();
        }
        function sync() {
            if (!active) return;
            for (const {id,button,row,label,badge} of records) {
                row.hidden = button.style.display === 'none' || button.hidden;
                const names={b6:'Fan',b4:'Karbon',b5:'IR (Isıtıcı)',b3:'Nem (Nemlendirici)',b1:'Işık',b2:'Nebülizatör',b9:'Soğutma'};
                label.textContent=document.documentElement.lang === 'tr' ? names[id] : (button.querySelector('[data-i18n],span:not(.device-status)')?.textContent || '');
                badge.textContent=button.querySelector('.device-status')?.textContent || '—';
                row.dataset.state = (button.classList.contains('state-on') || button.classList.contains('state-off')) ? 'on' : button.classList.contains('state-unknown') ? 'unknown' : 'off';
            }
            const oxygen=$('oxygenCard');
            const missing=!oxygen || oxygen.style.display==='none' || oxygen.classList.contains('sensor-hidden') || /tahmin|estimated|geschätzt|sensörü yok/i.test($('oxyStatus')?.textContent || '');
            oxygenHost.classList.toggle('care-oxygen-missing',missing);
            oxygenHost.hidden=missing;
            footer.classList.toggle('care-footer-camera-only',missing);
            readings.classList.toggle('clinical-oxygen-missing',missing);
            if(!hostnameRequested && window.kuvozController?.socket?.connected) {
                hostnameRequested=true;
                window.kuvozController.socket.once('settings_response', data => { deviceName.textContent=data?.device?.hostname || window.location.hostname; });
                window.kuvozController.socket.emit('get_settings');
            }
            const panel=$('compactAiPanel'); const unavailable=!panel || panel.style.display==='none';
            cameraFallback.hidden=!unavailable;
            cameraDetail.textContent=unavailable ? words[15] : ($('cameraFocusStatus')?.textContent || words[8]);
            const waiting=unavailable || !lastCameraFrame || Date.now()-lastCameraFrame > 5000;
            const noFrame={tr:'Kamera görüntüsü yok',en:'No camera image',de:'Kein Kamerabild'};
            cameraTitle.textContent=waiting ? (noFrame[document.documentElement.lang] || noFrame.tr) : words[7];
            cameraButton.querySelector('i').className='fas ' + (waiting ? 'fa-video-slash' : 'fa-video');
            clinicalWaiting.hidden=!waiting;
            clinicalWaitTitle.textContent=layoutTheme==='night' && waiting && !unavailable ? words[8] : cameraTitle.textContent; clinicalWaitText.textContent=cameraDetail.textContent;
            date.textContent=new Intl.DateTimeFormat(document.documentElement.lang || 'tr',{day:'numeric',month:'long',year:'numeric'}).format(new Date());
            time.textContent=new Intl.DateTimeFormat(document.documentElement.lang || 'tr',{hour:'2-digit',minute:'2-digit'}).format(new Date());
            nightTime.textContent=date.textContent+'  '+time.textContent;
            nightOxygen.textContent='';
            lockCaption.textContent=$('dashboardLock').getAttribute('aria-label') || '';
        }
        function update() {
            const nextTheme=document.documentElement.dataset.theme;
            const next=['care','clinical','night'].includes(nextTheme);
            if(active && layoutTheme===nextTheme) return;
            if(active) {
                active=false; layoutTheme=null;
                for(const d of [controlDialog,systemDialog,cameraDialog]) if(d.node.open) d.node.close();
                document.body.classList.remove('reference-layout-ready','care-reference-ready','clinical-reference-ready','night-reference-ready');
                for(const [node,marker] of [...homes].reverse()) marker.replaceWith(node);
                homes.clear(); header.remove(); stage.remove(); nav.remove(); nightFooter.remove();
                const kiosk=window.matchMedia('(min-width:701px) and (max-width:1100px) and (max-height:650px)').matches;
                (kiosk ? $('dashboardCareSlot') : document.querySelector('.care-mode-header')).append(modes);
                (kiosk ? equipment : document.querySelector('.control-panel')).append(document.querySelector('.timer-section'));
            }
            if(!next) return;
            active=true; layoutTheme=nextTheme;
            navItems[0][0].querySelector('i').className='fas '+(nextTheme==='night' ? 'fa-eye' : 'fa-heartbeat');
            navItems[2][0].querySelector('i').className='fas fa-broom';
            source.before(header,stage); source.after(nav,nightFooter);
            title.after(modeHost,targetHost);
            move($('careModeProfile'),patient);
            move($('connectionStatus'),status); move($('dashboardLock'),status);
            move($('criticalNotifications'),alertLine); move($('dashboardAlarm'),alertLine);
            for(const cls of ['temperature','humidity','co2']) move(document.querySelector('.sensor-card-large.'+cls),readings);
            move(modes,modeHost); move(targets,targetHost);
            move(document.querySelector('.timer-section'),controlDialog.node);
            move(document.querySelector('.mode-selector-section'),controlDialog.node);
            for(const cls of ['cooling-target','fan-speed-target']) move(document.querySelector('.'+cls),extraTargets);
            controlDialog.node.append(extraTargets);
            move(system,systemDialog.node);
            if(['clinical','night'].includes(nextTheme)) {
                move($('oxygenCard'),readings);
                if(nextTheme==='night') controlDialog.node.append(modeHost);
                else clinicalHead.append(modeHost);
                controlDialog.node.append(targetHost);
                move(equipment,clinicalEquipment); move($('compactAiPanel'),clinicalCameraSurface);
            } else {
                move($('oxygenCard'),oxygenHost); move(equipment,controlDialog.node);
                move($('compactAiPanel'),cameraDialog.node);
            }
            document.body.classList.add('reference-layout-ready',nextTheme+'-reference-ready');
            translate();
        }
        translate();
        // Other dashboard scripts finish their normal setup before we move their controls.
        queueMicrotask(update);
        window.addEventListener('kuvoz:themechange', update);
        window.matchMedia('(min-width:701px) and (max-width:1100px) and (max-height:650px)').addEventListener('change', () => {
            queueMicrotask(() => {
                if (!active) return;
                modeHost.append(modes);
                controlDialog.node.append(document.querySelector('.timer-section'));
            });
        });
        new MutationObserver(translate).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
        for(const node of [equipment,$('oxygenCard'),$('compactAiPanel'),$('cameraFocusStatus')]) {
            if(node) new MutationObserver(sync).observe(node,{subtree:true,attributes:true,childList:true,characterData:true});
        }
        $('compactCameraFeed')?.addEventListener('load', event => {
            if(event.target.naturalWidth<=1) return;
            lastCameraFrame=Date.now();
            clearTimeout(cameraStaleTimer); cameraStaleTimer=setTimeout(sync,5100); sync();
        });
        setInterval(sync,30000);
    });
})();

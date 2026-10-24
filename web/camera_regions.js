(() => {
    'use strict';
    const $ = id => document.getElementById(id);
    const canvas = $('camera'), ctx = canvas.getContext('2d');
    const image = new Image();
    const socket = io(window.location.origin, {reconnection:true});
    const boxes = {animal:null, respiration:null};
    let mode='animal', start=null, draft=null, loaded=false, saving=false, lastFrame=0, dirty=false, signature='', timer, pendingSettings=null;
    const message = text => { $('status').textContent=text; };
    const cameraSignature = s => JSON.stringify([s.camera_source||'raspberry_pi',s.ip_camera_url||'',s.camera_transform||'normal']);
    const fresh = () => socket.connected && lastFrame && Date.now()-lastFrame<5000;
    function refreshButton() { $('save').disabled=!loaded||!fresh()||saving||!!start; }
    function draw() {
        ctx.fillStyle='#162a36'; ctx.fillRect(0,0,canvas.width,canvas.height);
        if(image.complete && image.naturalWidth) ctx.drawImage(image,0,0,canvas.width,canvas.height);
        for(const name of ['animal','respiration']) {
            const b=(name===mode&&draft)?draft:boxes[name]; if(canvas.dataset.trackingLost==='true'&&!dirty&&!draft)continue; if(!b||(!$('use-'+name).checked&&!(name===mode&&draft))) continue;
            if(name==='respiration'&&canvas.dataset.respirationReady==='false'&&!dirty&&!draft)continue;
            ctx.strokeStyle=name==='animal'?'#60a5fa':'#fbbf24'; ctx.lineWidth=3;
            ctx.setLineDash($('use-'+name).checked?[]:[8,5]);
            ctx.strokeRect(b.x*canvas.width,b.y*canvas.height,b.width*canvas.width,b.height*canvas.height);
            ctx.fillStyle=ctx.strokeStyle; ctx.font='14px sans-serif';
            ctx.fillText(name==='animal'?'Hayvan':'Solunum',b.x*canvas.width+4,Math.max(16,b.y*canvas.height-5));
        }
        ctx.setLineDash([]);
        if(!fresh()) {ctx.fillStyle='rgba(0,0,0,.65)';ctx.fillRect(0,0,canvas.width,40);ctx.fillStyle='white';ctx.font='16px sans-serif';ctx.fillText('Canlı görüntü bekleniyor — seçim kapalı',10,26);}
        refreshButton();
    }
    image.onload=()=>{ if(canvas.width!==image.naturalWidth||canvas.height!==image.naturalHeight){canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;} draw(); };
    function normalizedPoint(e) {
        const r=canvas.getBoundingClientRect();
        return {x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))};
    }
    canvas.addEventListener('pointerdown',e=>{
        if(!loaded||!fresh()||saving||e.isPrimary===false||e.button!==0) return;
        e.preventDefault();start=normalizedPoint(e);draft=null;canvas.setPointerCapture(e.pointerId);refreshButton();
    });
    canvas.addEventListener('pointermove',e=>{
        if(!start) return;
        const p=normalizedPoint(e);draft={x:Math.min(start.x,p.x),y:Math.min(start.y,p.y),width:Math.abs(p.x-start.x),height:Math.abs(p.y-start.y)};draw();
    });
    canvas.addEventListener('pointerup',e=>{
        if(!start) return;
        if(fresh()&&draft&&draft.width>=.04&&draft.height>=.04) {
            boxes[mode]=draft;$('use-'+mode).checked=true;dirty=true;message('Alan seçildi. Kaydetmeden önce iki kutuyu kontrol edin.');
        } else message('Seçim kaydedilmedi. Canlı görüntüde daha büyük bir kutu çizin.');
        start=null;draft=null;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);draw();
    });
    canvas.addEventListener('pointercancel',()=>{start=null;draft=null;draw();});
    for(const name of ['animal','respiration']) {
        $(name).onclick=()=>{mode=name;start=null;draft=null;for(const n of ['animal','respiration'])$(n).setAttribute('aria-pressed',String(n===mode));draw();};
        $('use-'+name).onchange=()=>{dirty=true;draw();};
    }
    $('clear').onclick=()=>{boxes[mode]=null;$('use-'+mode).checked=false;dirty=true;message('Kutu silindi; uygulamak için kaydedin.');draw();};
    $('reload').onclick=()=>{dirty=false;socket.emit('get_settings');};
    socket.on('connect',()=>{message('Canlı görüntü bekleniyor…');socket.emit('get_settings');});
    socket.on('disconnect',()=>{lastFrame=0;start=null;draft=null;message('Bağlantı kesildi. Seçim ve kaydetme durduruldu.');draw();});
    socket.on('settings_response',data=>{
        if(dirty||saving)return;
        const s=data.settings||{};signature=cameraSignature(s);
        for(const name of ['animal','respiration']){boxes[name]=s[name+'_roi']||null;$('use-'+name).checked=s[name+'_roi_enabled']===true;}
        loaded=true;message('Alan seçmek için görüntü üzerinde sürükleyin.');draw();
    });
    socket.on('ai_update',data=>{
        const tracking=data.vision?.region_tracking;
        if(tracking){
            const labels={unselected:'Alan seçilmedi',acquiring:'Hayvan bulundu — takip doğrulanıyor',locked:'Takip kararlı',moving:'Hareket var — solunum duraklatıldı',lost:'Hayvan otomatik aranıyor — solunum bekliyor.'};
            $('tracking-status').textContent=tracking.state==='locked'&&tracking.respiration_ready===false
                ? 'Yaşam döngüsü takibi sürüyor — solunum alanı otomatik doğrulanıyor'
                : tracking.state==='locked'&&!tracking.respiration_allowed
                ? 'Takip güveni düşük — solunum bekliyor' : (labels[tracking.state]||'Takip bekleniyor');
            if(!dirty&&!start&&!saving&&tracking.state!=='lost'){
                for(const name of ['animal','respiration']) if(tracking.boxes?.[name])boxes[name]=tracking.boxes[name];
            }
            canvas.dataset.trackingLost=String(tracking.state==='lost');
            canvas.dataset.respirationReady=String(tracking.respiration_ready!==false);
        }
        if(!data.frame)return;lastFrame=Date.now();
        if(!start)image.src='data:image/jpeg;base64,'+data.frame;
        $('summary').textContent='Canlı görüntü · Mavi: hayvan · Sarı: solunum';refreshButton();
    });
    function validation() {
        if($('use-respiration').checked&&!$('use-animal').checked)return 'Otomatik solunum takibi için önce hayvanın tamamını seçin.';
        for(const name of ['animal','respiration']) {
            if($('use-'+name).checked&&!boxes[name])return 'Etkin alan için önce bir kutu çizin.';
        }
        if($('use-animal').checked&&$('use-respiration').checked){
            const a=boxes.animal,r=boxes.respiration;
            if(r.x<a.x-1e-5||r.y<a.y-1e-5||r.x+r.width>a.x+a.width+1e-5||r.y+r.height>a.y+a.height+1e-5)return 'Solunum kutusu hayvan kutusunun içinde olmalı.';
        }
        return '';
    }
    $('save').onclick=async()=>{
        if(!fresh()||saving)return;
        const error=validation();if(error){message(error);return;}
        saving=true;refreshButton();
        try{
            const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw Error();
            const current=await response.json();
            if(cameraSignature(current.system_settings||{})!==signature){
                loaded=false;dirty=false;lastFrame=0;socket.emit('get_settings');throw Error('Kamera kaynağı veya yönü değişti; alanları yeniden seçin.');
            }
            if(!fresh())throw Error('Canlı bağlantı kesildi; tekrar deneyin.');
            const settings={region_tracking_revision:Date.now()};for(const name of ['animal','respiration']){settings[name+'_roi_enabled']=$('use-'+name).checked;if(boxes[name])settings[name+'_roi']=boxes[name];}
            pendingSettings=settings;
            socket.emit('save_settings',{system_settings:settings});
            message('Alanlar kaydediliyor…');timer=setTimeout(()=>{saving=false;message('Kaydetme yanıtı alınamadı; kayıtlı alanları yükleyerek kontrol edin.');refreshButton();},8000);
        }catch(e){saving=false;message(e.message||'Ayarlar kontrol edilemedi.');refreshButton();}
    };
    socket.on('settings_saved',async()=>{
        if(!saving||!pendingSettings)return;
        try {
            const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)return;
            const s=(await response.json()).system_settings||{};
            const matches=Object.entries(pendingSettings).every(([key,value])=>typeof value==='object'
                ? Object.keys(value).every(k=>Math.abs(Number(s[key]?.[k])-value[k])<.00001)
                : s[key]===value);
            if(!matches)return;
            clearTimeout(timer);saving=false;dirty=false;pendingSettings=null;
            message('Alanlar kaydedildi ve analize uygulandı.');refreshButton();
        } catch (_) { /* Keep timeout active until persistence can be verified. */ }
    });
    socket.on('error',data=>{if(!saving)return;clearTimeout(timer);saving=false;message(data.message||'Alanlar kaydedilemedi.');refreshButton();});
    setInterval(()=>{if(!fresh()){start=null;draft=null;draw();}refreshButton();},1000);
    window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
    draw();
})();

const {test} = require('node:test');
const assert = require('node:assert/strict');
const {animalBox, cropFor} = require('../web/dashboard.js');
const animal = {x:.2,y:.3,width:.3,height:.2};
const region = state => ({available:true, region_tracking:{state,confidence:.9,boxes:{animal}}});
test('only reliable animal tracking enables focus', () => {
    assert.deepEqual(animalBox(region('locked')), animal);
    assert.deepEqual(animalBox(region('moving')), animal);
    for(const state of ['lost','acquiring','holding']) assert.equal(animalBox(region(state)),null);
    assert.equal(animalBox({...region('locked'), available:false}),null);
    assert.equal(animalBox({...region('locked'),region_tracking:{state:'locked',confidence:.2,boxes:{animal}}}),null);
});
test('lost region tracking cannot fall back to an older subject box', () => {
    assert.equal(animalBox({...region('lost'),subject_tracking_state:'locked',subject_tracking_locked:true,
        subject_tracking_confidence:1,subject_box:{x_norm:.1,y_norm:.1,width_norm:.3,height_norm:.3}}),null);
});
test('automatic tracking uses normalized full-frame subject coordinates', () => {
    assert.deepEqual(animalBox({subject_tracking_state:'locked',subject_tracking_locked:true,
        subject_tracking_confidence:.9, subject_box:{x_norm:.2,y_norm:.3,width_norm:.3,height_norm:.2}}), animal);
});
test('reject invalid coordinates and respiration-only regions', () => {
    assert.equal(animalBox({region_tracking:{state:'locked',confidence:.9,boxes:{respiration:animal}}}),null);
    for(const box of [{...animal,x:NaN},{...animal,width:-1},{...animal,x:.9}])
        assert.equal(animalBox({region_tracking:{state:'locked',confidence:.9,boxes:{animal:box}}}),null);
});
test('crop preserves animal, frame aspect ratio, context and zoom limit at edges', () => {
    for (const b of [animal,{x:0,y:0,width:.1,height:.1},{x:.8,y:.8,width:.2,height:.2},{x:0,y:0,width:1,height:1}]) {
        const c=cropFor(b,640,480);
        assert.ok(c.x>=0 && c.y>=0 && c.x+c.width<=640.001 && c.y+c.height<=480.001);
        assert.ok(c.x<=b.x*640 && c.y<=b.y*480);
        assert.ok(c.x+c.width>=(b.x+b.width)*640-.001);
        assert.ok(c.y+c.height>=(b.y+b.height)*480-.001);
        assert.ok(Math.abs(c.width/c.height-640/480)<.0001);
        assert.ok(c.width>=640/2.5);
    }
});
test('late controller connection, focus, loss, disconnect and stale frames use wide view', () => {
    const vm = require('node:vm'), fs = require('node:fs');
    const handlers = {}, intervals = [], drawings = [];
    let now=10000;
    function element() { return {textContent:'',className:'',style:{},classList:{add(){},remove(){},toggle(){return false;}},
        setAttribute(){},addEventListener(name,fn){this[name]=fn;},append(){},after(){},focus(){}}; }
    const ids={};
    for(const id of ['compactAiPanel','compactCameraFeed','cameraFocusStatus','cameraFocusToggle','cameraExpand',
        'dashboardMenu','dashboardMenuClose','sld3_value','sld2_value','temperature','humidity']) ids[id]=element();
    const image=ids.compactCameraFeed;
    image.naturalWidth=640;image.naturalHeight=480;image.parentElement={insertBefore(){}};
    const canvas=element();canvas.getContext=()=>({clearRect(){},drawImage(...args){drawings.push(args);}});
    const document={addEventListener(name,fn){handlers[name]=fn;},getElementById:id=>ids[id],createElement:tag=>tag==='canvas'?canvas:element(),
        querySelector:()=>({...element(),parentElement:element()}),querySelectorAll:()=>[]};
    const window={matchMedia:()=>({matches:true,addEventListener(){}})};
    vm.runInNewContext(fs.readFileSync(require.resolve('../web/dashboard.js'),'utf8'),{
        document,window,MutationObserver:class{observe(){}},setInterval:fn=>intervals.push(fn),Date:{now:()=>now}
    });
    handlers.DOMContentLoaded(); // controller is still loading translations
    const events={};window.kuvozController={socket:{on:(name,fn)=>{events[name]=fn;}}};
    intervals[0]();assert.equal(typeof events.ai_update,'function');
    events.ai_update({frame:'jpeg',vision:region('locked')});image.load();
    assert.equal(drawings.at(-1).length,9);assert.equal(ids.cameraFocusStatus.textContent,'Hayvan odakta');
    image.naturalWidth=1280;image.naturalHeight=960;image.load();
    assert.equal(drawings.at(-1)[3],512); // A new resolution must not blend old pixel coordinates.
    events.ai_update({frame:'jpeg',vision:region('lost')});assert.equal(drawings.at(-1).length,5);
    events.ai_update({frame:'jpeg',vision:region('locked')});image.load();events.disconnect();
    assert.equal(drawings.at(-1).length,5);
    events.ai_update({frame:'jpeg',vision:region('locked')});image.load();now+=6000;intervals[0]();
    assert.equal(drawings.at(-1).length,5);assert.match(ids.cameraFocusStatus.textContent,/bekleniyor/);
});

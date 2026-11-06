const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync(require.resolve('../web/script.js'),'utf8');
const start=src.indexOf('class KuvozController {'),end=src.indexOf('\n}\n',start)+2;
const handlers={},sent=[],toasts=[];
let empty=false,ack,interval;
const context={window:{addEventListener:(name,fn)=>handlers[name]=fn},document:{getElementById:()=>({checked:empty})},setInterval:fn=>{interval=fn;}};
vm.createContext(context);vm.runInContext(src.slice(start,end)+'\nglobalThis.Controller=KuvozController;',context);
function controller() {
 sent.length=0;toasts.length=0;empty=false;
 const c=Object.create(context.Controller.prototype);
 Object.assign(c, {
  pageName:'cleaning',buttonStates:{b7:false,b8:false},gpioOutputs:{b7:false,b8:false},
  t:key=>key,showToast:(...args)=>toasts.push(args),
  socket:{connected:true,emit:(...args)=>sent.push(args),
   timeout:()=>({emit:(event,data,cb)=>{sent.push([event,data]);ack=cb;}})}
 });
 return c;
}
test('UV and ozone require explicit empty-cabin confirmation and connected socket',()=>{
 const c=controller();c.toggleButton('b8',26);assert.equal(sent.length,0);assert.equal(toasts[0][0],'disinfection.require_empty');
 empty=true;c.socket.connected=false;c.toggleButton('b8',26);assert.equal(sent.length,0);
});
test('start sends explicit state and waits for authoritative button update',()=>{
 const c=controller();empty=true;c.toggleButton('b8',26);assert.equal(sent[0][0],'toggle_button');
 assert.equal(sent[0][1].empty_confirmed,true);assert.equal(sent[0][1].state,true);assert.equal(sent[0][1].pin,26);
 assert.equal(c.buttonStates.b8,false);assert.equal(c.gpioOutputs.b8,false);
});
test('navigation callback runs only after confirmed shutdown',()=>{
 const c=controller();let navigated=false;c.updateDisinfectionMode=()=>{};
 c.stopDisinfection(()=>navigated=true);assert.equal(navigated,false);
 ack(new Error('timeout'));assert.equal(navigated,false);
 c.stopDisinfection(()=>navigated=true);ack(null,{success:false});assert.equal(navigated,false);
 c.stopDisinfection(()=>navigated=true);ack(null,{success:true,disinfection:{active:false,ventilation_required:true}});assert.equal(navigated,true);
});
test('page unload sends idempotent stop instead of a malformed toggle; heartbeat renews lease',()=>{
 const c=controller();c.buttonStates.b8=true;c.setupPageUnloadHandler();handlers.beforeunload();handlers.pagehide();interval();
 assert.deepEqual(sent.map(x=>x[0]),['stop_disinfection','stop_disinfection','disinfection_heartbeat']);
});
test('logical enable is not overwritten by a previous GPIO sample',()=>{
 const c=controller();c.applyButtonVisual=()=>{};c.statusAppliedSinceConnect=false;
 c.updateButtonStates({b8:true});assert.equal(c.buttonStates.b8,true);
});
test('ozone indicator does not claim low O2 disables exposure',()=>{
 const c=controller(),mode={};context.document.getElementById=()=>mode;
 c.updateOzoneModeByOxygen('15');assert.equal(mode.textContent,'TIMED');assert.equal(mode.className,'ozone-mode timed');
 context.document.getElementById=()=>({checked:empty});
});

test('a rejected start does not stop another session; an ambiguous timeout does',()=>{
 const c=controller();empty=true;let stops=0;c.stopDisinfection=()=>stops++;
 c.toggleButton('b8',26);ack(null,{success:false});assert.equal(stops,0);
 c.toggleButton('b8',26);ack(new Error('timeout'));assert.equal(stops,1);
});

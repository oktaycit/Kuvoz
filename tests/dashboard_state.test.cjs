const {test}=require('node:test');
const assert=require('node:assert/strict');
const {deviceStatus,summary}=require('../web/dashboard-state.js');
const state={buttons:{b4:false,b5:false,b6:false,b9:true},gpio_outputs:{b4:false,b5:false,b6:false,b9:false,b2:false},sliders:{sld3:33,sld12:15},sensors:{temperature:{value:'27'},humidity:{value:'68'}},system:{fan_output_mode:'pwm',fan_pwm_duty:0},system_settings:{cooling_enabled:true}};
test('heater off does not claim a failure or heating merely because target is higher',()=>{
 assert.equal(deviceStatus('b4',state,true),'Kapalı');
 assert.equal(deviceStatus('b4',{...state,buttons:{b4:true}},true),'Beklemede');
 assert.equal(deviceStatus('b4',{...state,gpio_outputs:{b4:true}},true),'Isıtıyor');
 assert.equal(deviceStatus('b4',state,false),'Durum bekleniyor');
 assert.equal(deviceStatus('b4',{...state,gpio_outputs:{b4:null}},true),'Çıkış bilinmiyor');
});
test('cooling explains heater interlock, feature disable and missing target',()=>{
 assert.equal(deviceStatus('b9',{...state,gpio_outputs:{b4:true,b9:false}},true),'Isıtma kilidi');
 assert.equal(deviceStatus('b9',{...state,system_settings:{cooling_enabled:false}},true),'Özellik kapalı');
 assert.equal(deviceStatus('b9',{...state,sliders:{sld12:0}},true),'Hedef gerekli');
 assert.equal(deviceStatus('b9',{...state,sensors:{temperature:{value:'--'}}},true),'Sensör bekleniyor');
});
test('fan reports confirmed output not configured speed, nebulizer has priority',()=>{
 assert.equal(deviceStatus('b6',state,true),'Kapalı');
 assert.equal(deviceStatus('b6',{...state,gpio_outputs:{b6:false,b2:true}},true),'Nebülizatör kilidi');
 assert.equal(deviceStatus('b6',{...state,gpio_outputs:{b6:true},system:{fan_output_mode:'pwm',fan_pwm_duty:55}},true),'Çıkış %55');
});
test('missing/stale data must not produce a normal badge',()=>{
 assert.equal(summary(state,[],true,true).items.length,0);
 assert.ok(summary(state,[],false,false).items.length>=2);
 assert.ok(summary({...state,sensors:{}},[],true,true).items.length);
 assert.equal(summary(state,[{severity:'critical',title:'Alarm'}],true,true).severity,'critical');
});
test('conflicting setpoints warn only while both climate functions are enabled',()=>{
 assert.equal(summary(state,[],true,true).items.length,0);
 assert.ok(summary({...state,buttons:{b4:true,b9:true}},[],true,true).items.some(i=>/çakış/.test(i.title)));
});

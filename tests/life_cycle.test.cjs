const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
function setup() {
    const elements = {'date-filter': {value:''}, 'anomaly-alerts': {}, 'goal-readout': {}};
    const context = {window:{}, document:{addEventListener(){},getElementById:id=>elements[id]},localStorage:{getItem:()=> 'tr'},console:{...console,error(){}},Date,setTimeout,URLSearchParams};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('web/life_cycle_analytics.js','utf8')+'\nthis.Analytics = LifeCycleAnalytics;',context);
    const a = Object.create(context.Analytics.prototype);
    Object.assign(a,{patientId:'p1',patientName:'Test',loadState:'ready',requestSequence:0,behaviorData:[],aiCameraData:null});
    a.t = key=>key;
    return {a,elements,context};
}
const row = (type='resting',intensity=1)=>({patient_id:'p1',behavior_type:type,intensity,duration:1,timestamp:new Date().toISOString()});
test('aggregate, empty, error, history and capped data never report normal',()=>{
 const {a,elements}=setup();
 a.behaviorData=[row(),row(),row()];
 for (const state of ['aggregate','empty','error','history','limit']) {
  a.patientId=state==='aggregate'?null:'p1';a.loadState=state==='error'?'error':'ready';
  a.behaviorData=state==='empty'?[]:state==='limit'?Array(1000).fill(row()):[row(),row(),row()];
  elements['date-filter'].value=state==='history'?'2020-01-01':'';
  assert.ok(a.assessmentNote(),state);
  a.renderAnomalyAlerts();
  assert.ok(elements['anomaly-alerts'].textContent,state);
 }
});
test('rest percentage counts samples rather than treating them as elapsed time',()=>{
 const {a}=setup();a.behaviorData=[{...row(),duration:100},row('feeding')];
 assert.equal(a.calculateGoalMetrics().restRatio,0.5);
});
test('intensity 8 produces warning consistently with goal card threshold',()=>{
 const {a}=setup();a.behaviorData=[row('feeding'),row('feeding'),row('resting'),row('activity',8)];
 assert.equal(a.assessmentNote(),'');
 assert.ok(a.detectAnomalies().some(x=>x.severity==='warning'));
});
test('live records obey patient and last 24 hours filters',()=>{
 const {a}=setup();assert.equal(a.matchesActiveFilters(row()),true);
 assert.equal(a.matchesActiveFilters({...row(),patient_id:'other'}),false);
 assert.equal(a.matchesActiveFilters({...row(),timestamp:'2020-01-01'}),false);
 assert.equal(a.matchesActiveFilters({...row(),timestamp:'bad'}),false);
});
test('latest filter request wins when responses arrive out of order',async()=>{
 const {a,context}=setup();const resolvers=[];context.fetch=()=>new Promise(resolve=>resolvers.push(resolve));
 a.renderDashboard=()=>{};
 const older=a.loadBehaviorData();const newer=a.loadBehaviorData();
 resolvers[1]({ok:true,json:async()=>({data:[row('feeding')]})});await newer;
 resolvers[0]({ok:true,json:async()=>({data:[row('activity')]})});await older;
 assert.equal(a.behaviorData[0].behavior_type,'feeding');
 assert.equal(a.loadState,'ready');
});
test('HTTP failure remains distinguishable from empty records',async()=>{
 const {a,context}=setup();context.fetch=async()=>({ok:false,status:500});a.renderDashboard=()=>{};
 await a.loadBehaviorData();assert.equal(a.loadState,'error');assert.ok(a.assessmentNote());
});
test('duplicate socket records do not inflate metrics and expired samples are removed',()=>{
 const {a}=setup();a.renderDashboard=()=>{};
 a.behaviorData=[{...row(),id:1},{...row(),id:2,timestamp:'2020-01-01'}];
 a.handleBehaviorUpdate({...row(),id:1});assert.equal(a.behaviorData.length,2);
 a.handleBehaviorUpdate({...row(),id:3});assert.equal(a.behaviorData.length,2);
 assert.ok(a.behaviorData.every(item=>item.id!==2));
});

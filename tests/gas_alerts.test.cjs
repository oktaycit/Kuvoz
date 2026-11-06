const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync(process.env.KUVOZ_GAS_SCRIPT || require.resolve('../web/script.js'),'utf8');
const start=src.indexOf('class KuvozController {'),end=src.indexOf('\n}\n',start)+2;
const context={};vm.createContext(context);vm.runInContext(src.slice(start,end)+'\nglobalThis.Controller=KuvozController;',context);
function controller(){const c=Object.create(context.Controller.prototype);Object.assign(c,{currentLanguage:'tr',systemSettings:{},sensorData:{},homeNotifications:new Map(),renderCriticalNotifications(){}});return c;}
test('estimated oxygen never becomes a measured oxygen alarm and clears old alarms',()=>{
 const c=controller();c.updateOxygenSafetyNotification({value:'17',status:'OK'});assert.ok(c.homeNotifications.has('sensor_oxygen_critical'));
 c.updateOxygenSafetyNotification({value:'17',status:'Tahmini (CO2: 1800ppm)'});assert.equal(c.homeNotifications.size,0);
 c.oxygenMeasurementEstimated=true;c.updateOxygenSafetyNotification({value:'17',status:'OK'});assert.equal(c.homeNotifications.size,0);
 c.oxygenMeasurementEstimated=false;c.physicalOxygenSensorAvailable=false;c.updateOxygenSafetyNotification({value:'17',status:'OK'});assert.equal(c.homeNotifications.size,0);
});
test('real oxygen warnings remain active',()=>{
 const c=controller();c.physicalOxygenSensorAvailable=true;c.updateOxygenSafetyNotification({value:'19',status:'OK'});assert.ok(c.homeNotifications.has('sensor_oxygen_low'));
 c.updateOxygenSafetyNotification({value:'17',status:'OK'});assert.ok(c.homeNotifications.has('sensor_oxygen_critical'));
 c.updateOxygenSafetyNotification({value:'21',status:'OK'});assert.equal(c.homeNotifications.size,0);
});
test('CO2 alerts use CO2 measurements and existing thresholds independently of estimated oxygen',()=>{
 const c=controller();c.oxygenMeasurementEstimated=true;
 c.updateCO2SafetyNotification({value:'1000'});assert.equal(c.homeNotifications.size,0);
 c.updateCO2SafetyNotification({value:'1500'});assert.equal(c.homeNotifications.get('sensor_co2_warning').title,'Karbondioksit yüksek');
 c.updateCO2SafetyNotification({value:'2000'});assert.equal(c.homeNotifications.get('sensor_co2_critical').title,'Karbondioksit çok yüksek');
 c.updateCO2SafetyNotification({value:'900'});assert.equal(c.homeNotifications.size,0);
});
test('AI oxygen anomalies from estimated readings are filtered while CO2 anomalies remain',()=>{
 const c=controller();c.sensorData.oxygen={value:'19',status:'Tahmini'};
 c.isOxygenAlertMessage=m=>m.includes('oxygen');c.normalizeEnvironmentAlert=m=>({key:m,title:m,severity:'warning'});c.buildVitalStatusAlert=()=>null;
 const list=c.buildActiveAIAlerts({analytics:{anomalies:['oxygen low','CO2 high']}});assert.equal(list.length,1);assert.equal(list[0].title,'CO2 high');
});

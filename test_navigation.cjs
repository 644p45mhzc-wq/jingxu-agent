const fs=require('fs'),vm=require('vm'),assert=require('assert');
const catalog=[{id:'cumcm',short:'数学建模',fit_reason:'数据训练'},{id:'innovation',short:'创新大赛',fit_reason:'创新项目'}];
function setup(detail=false){
 const nodes=new Map(),events={},docEvents={},store=new Map();let quota=false,confirmation=true;
 function node(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',hidden:false,attributes:{},dataset:{},handlers:{},classList:{toggle(){}},setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]},addEventListener(k,h){this.handlers[k]=h},focus(){this.focused=true}});return nodes.get(id);}
 const tabs=['plan','calendar','review','resources','daily'].map(view=>({...node('tab-'+view),dataset:{workspaceTab:view}}));
 store.set('jingxu-library-v1',JSON.stringify({favorites:['cumcm'],otherSetting:'keep'}));
 store.set('jingxu-v2-cumcm',JSON.stringify({plan:{summary:'保留旧计划'}}));
 store.set('jingxu-growth-v1','{"logs":["keep history"]}');
 const sandbox={location:{pathname:detail?'/competitions/cumcm':'/',hash:''},document:{querySelector:node,getElementById:node,querySelectorAll:s=>s==='[data-workspace-tab]'?tabs:[],addEventListener:(name,fn)=>docEvents[name]=fn},window:{addEventListener:(name,fn)=>(events[name]??=[]).push(fn),dispatchEvent:event=>(events[event.type]||[]).forEach(fn=>fn(event)),scrollTo(){}},localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>{if(quota)throw new Error('quota');store.set(k,v)}},Event:class{constructor(type){this.type=type}},confirm:()=>confirmation,fetch:async()=>({ok:true,json:async()=>({contests:catalog})})};
 vm.createContext(sandbox);
 for(const file of ['contest-library.js','app-navigation.js'])vm.runInContext(fs.readFileSync(require.resolve('../frontend/'+file),'utf8'),sandbox);
 function click(kind,id){docEvents.click({target:{closest:selector=>selector===`button[data-${kind}]`?{dataset:{[kind]:id}}:null}});}
 function route(hash){sandbox.location.hash=hash;(events.hashchange||[]).forEach(fn=>fn());}
 return {sandbox,node,store,click,route,tabs,setQuota:v=>quota=v,setConfirm:v=>confirmation=v};
}
(async()=>{
 const h=setup();await new Promise(resolve=>setImmediate(resolve));
 assert(h.node('#app-sidebar').innerHTML.includes('总日历'));
 assert(h.node('#app-sidebar').innerHTML.includes('正在参加比赛'));
 assert(!h.node('#app-sidebar').innerHTML.includes('href="/competitions/cumcm"'));
 assert.equal(h.node('all-contests').hidden,false);assert.equal(h.node('annual-timeline').hidden,true);assert.equal(h.node('profile').hidden,true);
 h.click('participate','cumcm');
 assert.equal(h.sandbox.window.ContestLibrary.isParticipating('cumcm'),true);
 assert(h.node('#app-sidebar').innerHTML.includes('href="/competitions/cumcm"'));
 assert(!h.node('#app-sidebar').innerHTML.includes('href="/competitions/innovation"'));
 assert.deepEqual(JSON.parse(h.store.get('jingxu-library-v1')).favorites,['cumcm']);
 assert.equal(JSON.parse(h.store.get('jingxu-library-v1')).otherSetting,'keep');
 h.route('#plan-calendar');assert.equal(h.node('plan-calendar').hidden,false);assert.equal(h.node('annual-timeline').hidden,true);
 h.route('#profile');assert.equal(h.node('profile').hidden,false);assert.equal(h.node('plan-calendar').hidden,true);
 h.route('#growth-summary');assert.equal(h.node('growth-summary').hidden,false);assert.equal(h.node('growth-memory').hidden,true);
 h.route('#growth-memory');assert.equal(h.node('growth-memory').hidden,false);assert.equal(h.node('growth-summary').hidden,true);
 h.route('#participating');assert.equal(h.node('participating').hidden,false);
 h.setConfirm(false);h.click('participate','cumcm');assert(h.sandbox.window.ContestLibrary.isParticipating('cumcm'));
 h.setConfirm(true);h.click('participate','cumcm');assert(!h.sandbox.window.ContestLibrary.isParticipating('cumcm'));
 assert.equal(JSON.parse(h.store.get('jingxu-v2-cumcm')).plan.summary,'保留旧计划');
 assert.equal(h.store.get('jingxu-growth-v1'),'{"logs":["keep history"]}');
 h.click('participate','cumcm');h.click('archive','cumcm');
 assert(!h.sandbox.window.ContestLibrary.isParticipating('cumcm'));
 assert(h.sandbox.window.ContestLibrary.archived().includes('cumcm'));
 assert(h.node('#archived-list').innerHTML.includes('数学建模'));
 assert(!h.node('#app-sidebar').innerHTML.includes('href="/competitions/cumcm"'));
 h.click('participate','cumcm');assert(h.sandbox.window.ContestLibrary.isParticipating('cumcm'));assert(!h.sandbox.window.ContestLibrary.archived().includes('cumcm'));
 h.setQuota(true);h.click('participate','innovation');assert(!h.sandbox.window.ContestLibrary.isParticipating('innovation'));
 h.setQuota(false);h.click('favorite','innovation');assert(!h.sandbox.window.ContestLibrary.isParticipating('innovation'));
 const d=setup(true);await new Promise(resolve=>setImmediate(resolve));
 assert.equal(d.node('plan').hidden,false);assert.equal(d.node('submission-panel').hidden,true);
 d.route('#submission-panel');assert.equal(d.node('submission-panel').hidden,false);assert.equal(d.node('plan').hidden,true);
 d.route('#resources');assert.equal(d.node('resources').hidden,false);assert.equal(d.node('official-schedule').hidden,false);assert.equal(d.node('growth-memory').hidden,true);
 d.node('#coach-toggle').handlers.click();assert.equal(d.node('.chat-panel').hidden,false);assert.equal(d.node('#coach-toggle').attributes['aria-expanded'],'true');
 d.node('#coach-close').handlers.click();assert.equal(d.node('.chat-panel').hidden,true);
 console.log('Hierarchical navigation, explicit enrollment, favorites separation, hash routes, coach toggle, storage rollback and preservation of existing data passed.');
})().catch(error=>{console.error(error);process.exitCode=1});

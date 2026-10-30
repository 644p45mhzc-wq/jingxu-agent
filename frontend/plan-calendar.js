(function(root){
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function validDay(day){if(typeof day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day))return false;const d=new Date(day+'T00:00:00Z');return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===day;}
  function monthDays(month){
    if(!/^\d{4}-\d{2}$/.test(month)||!validDay(month+'-01'))throw new Error('无效月份');
    const first=new Date(month+'-01T00:00:00Z'),offset=(first.getUTCDay()+6)%7;
    return Array.from({length:42},(_,i)=>{const d=new Date(first);d.setUTCDate(d.getUTCDate()-offset+i);return d.toISOString().slice(0,10);});
  }
  function moveMonth(month,offset){const d=new Date(month+'-01T00:00:00Z');d.setUTCMonth(d.getUTCMonth()+offset);return d.toISOString().slice(0,7);}
  function eventsFor(plans){
    return plans.flatMap(({id,name,plan,completed={},reviews=[]},color)=>{
      if(!plan||!Array.isArray(plan.weeks))return [];
      return plan.weeks.flatMap((week,index)=>{
        if(!validDay(week.start)||!validDay(week.end)||week.end<week.start||!Array.isArray(week.tasks)||!week.tasks.length)return [];
        const done=week.tasks.filter(t=>completed[t.id]).length;
        const hours=week.tasks.reduce((n,t)=>n+(Number.isFinite(t.hours)&&t.hours>0?t.hours:0),0);
        return [{id,name,color:color%5,index,title:week.title||'本周训练',start:week.start,end:week.end,tasks:week.tasks,completed,done,total:week.tasks.length,hours:Math.round(hours*100)/100,focus:week.review_focus,status:root.WorkspaceData?.weekStatus(week,completed,reviews)||(done===week.tasks.length?'自报完成 · 待验收':'进行中')}];
      });
    });
  }
  function onDay(events,day){return events.filter(e=>e.start<=day&&e.end>=day);}
  const api={validDay,monthDays,moveMonth,eventsFor,onDay};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.PlanCalendar=api;
  if(typeof document==='undefined')return;
  const mount=document.querySelector('#plan-calendar');if(!mount)return;
  const $=s=>mount.querySelector(s),today=()=>ProfileStore.today();
  let month=today().slice(0,7),selected=today(),filter='',catalog=[],events=[],sourceError='';
  const overrides=new Map();
  const current=mount.dataset.contest==='current'?decodeURIComponent(location.pathname.split('/').filter(Boolean).pop()):null;
  mount.innerHTML=`<div class="section-heading"><div><span class="eyebrow">YOUR TRAINING CALENDAR</span><h2>${current?'备赛日历':'总日历'}</h2></div><a href="${current?'#plan':'#annual-timeline'}">${current?'查看完整计划':'选择竞赛'} ↗</a></div>
    <p class="quiet">按周展示训练主题与完成进度；点击日期查看该周概括。日历属于个人训练安排，未分配具体每日任务。</p>
    <div class="plan-calendar-toolbar"><div class="plan-month-nav"><button type="button" class="secondary" id="calendar-prev" aria-label="上个月">‹</button><strong id="calendar-month" aria-live="polite"></strong><button type="button" class="secondary" id="calendar-next" aria-label="下个月">›</button></div><div class="plan-calendar-actions"><button type="button" class="text-button" id="calendar-today">今天</button><button type="button" class="text-button" id="calendar-start">计划开始</button><label class="sr-only" for="calendar-filter">筛选竞赛</label><select id="calendar-filter"><option value="">全部已保存计划</option></select></div></div>
    <p id="calendar-summary" class="quiet" role="status"></p><div class="plan-calendar-scroll"><div class="plan-calendar-weekdays" aria-hidden="true">${['一','二','三','四','五','六','日'].map(s=>`<span>周${s}</span>`).join('')}</div><div id="calendar-grid" class="plan-calendar-grid" role="group" aria-label="月历日期"></div></div><div class="calendar-legend"><span>● 训练周</span><span>✓ 该周已自报完成</span><span>· 当日有成长记录</span></div>
    <div id="calendar-agenda" aria-live="polite"></div>`;
  function collect(){
    sourceError='';
    const ids=new Set([...catalog.map(c=>c.id),...overrides.keys()]);
    if(current)ids.add(current);
    const plans=[];
    for(const id of ids){
      if(current&&id!==current)continue;
      if(!current&&root.ContestLibrary&&!root.ContestLibrary.isParticipating(id))continue;
      try{
        const saved=overrides.has(id)?overrides.get(id):JSON.parse(localStorage.getItem('jingxu-v2-'+id)||(id==='cumcm'?localStorage.getItem('jingxu-v1'):null)||'null');
        if(saved?.plan)plans.push({id,name:catalog.find(c=>c.id===id)?.short||saved.plan.contest_name||id,plan:saved.plan,completed:saved.completed||{},reviews:saved.reviews||[]});
      }catch{sourceError='部分已保存计划无法读取，请到对应竞赛页检查。';}
    }
    events=eventsFor(plans);
    $('#calendar-filter').hidden=Boolean(current);
    const names=[...new Map(events.map(e=>[e.id,e.name])).entries()];
    if(filter&&!names.some(([id])=>id===filter))filter='';
    $('#calendar-filter').innerHTML='<option value="">全部已保存计划</option>'+names.map(([id,name])=>`<option value="${esc(id)}">${esc(name)}</option>`).join('');
    $('#calendar-filter').value=filter;
  }
  function growthLogs(){try{return root.GrowthMemory?root.GrowthMemory.load().filter(l=>validDay(l.day)&&(!current||l.contest_id===current)&&(!filter||l.contest_id===filter)&&(current||!root.ContestLibrary||root.ContestLibrary.isParticipating(l.contest_id))):[];}catch{return [];}}
  function render(){
    const shown=events.filter(e=>!filter||e.id===filter),logs=growthLogs(),days=monthDays(month);
    $('#calendar-month').textContent=month.replace('-',' 年 ')+' 月';
    const monthEnd=moveMonth(month,1)+'-01';
    const inMonth=shown.filter(e=>e.start<monthEnd&&e.end>=month+'-01');
    $('#calendar-summary').textContent=sourceError||(events.length?(inMonth.length?`本月 ${new Set(inMonth.map(e=>e.id)).size} 项竞赛 · ${inMonth.length} 个训练周`:'本月没有训练安排，可切换月份或点击“计划开始”。'):(current?'还没有保存的训练计划，生成计划后自动显示。':'还没有正在参加比赛的训练计划。先参加比赛，再生成计划即可显示。'));
    $('#calendar-start').disabled=!shown.length;
    $('#calendar-grid').innerHTML=days.map(day=>{
      const items=onDay(shown,day),recorded=logs.filter(l=>l.day===day);
      const label=`${day}${items.length?'，'+items.map(e=>`${e.name} W${String(e.index+1).padStart(2,'0')} ${e.title}，完成${e.done}/${e.total}`).join('；'):'，无训练安排'}${recorded.length?'，有成长记录':''}`;
      return `<button type="button" class="plan-calendar-day ${day.slice(0,7)!==month?'outside':''} ${day===today()?'is-today':''} ${day===selected?'selected':''}" data-calendar-day="${day}" aria-pressed="${day===selected}" aria-label="${esc(label)}"><span class="calendar-day-number">${Number(day.slice(8))}${recorded.length?'<span class="calendar-record-dot" aria-label="有成长记录">·</span>':''}</span>${items.slice(0,2).map(e=>`<span class="calendar-event calendar-color-${e.color} ${e.done===e.total?'finished':''}"><b>${e.done===e.total?'✓ ':''}W${String(e.index+1).padStart(2,'0')}</b> ${esc(current?e.title:e.name)}</span>`).join('')}${items.length>2?`<span class="calendar-more">另 ${items.length-2} 项</span>`:''}</button>`;
    }).join('');
    const selectedEvents=onDay(shown,selected),selectedLogs=logs.filter(l=>l.day===selected);
    $('#calendar-agenda').innerHTML=`<h3>${esc(selected)} · 训练概括</h3>`+(selectedEvents.length?selectedEvents.map(e=>`<article class="calendar-agenda-card calendar-color-${e.color}"><span class="tag">${esc(e.name)} · W${String(e.index+1).padStart(2,'0')}</span><h3>${esc(e.title)}</h3><p class="quiet">${esc(e.start)} — ${esc(e.end)} · 本周 ${e.hours} 小时 · 自报完成 ${e.done}/${e.total} · ${esc(e.status)}</p><ul>${e.tasks.map(t=>`<li>${e.completed[t.id]?'✓ ':'○ '}${esc(t.title)}</li>`).join('')}</ul>${e.focus?`<p>本周改进重点：${esc(e.focus.title)}</p>`:''}<a href="/competitions/${encodeURIComponent(e.id)}#plan">查看计划与验收 ↗</a></article>`).join(''):'<p class="quiet">这一天没有已安排的训练周。</p>')+(selectedLogs.length?`<div class="calendar-daily-log"><strong>当日成长记录</strong>${selectedLogs.map(l=>`<p>${esc(catalog.find(c=>c.id===l.contest_id)?.short||l.contest_id)} · 实际 ${esc(l.actual_hours)} 小时：${esc(l.progress)}</p>`).join('')}</div>`:'');
  }
  function refresh(){collect();render();}
  api.setPlan=(id,plan,completed,reviews=[])=>{overrides.set(id,{plan,completed,reviews});refresh();};
  $('#calendar-prev').addEventListener('click',()=>{if(month>'1900-01'){month=moveMonth(month,-1);selected=month+'-01';render();}});
  $('#calendar-next').addEventListener('click',()=>{if(month<'2100-12'){month=moveMonth(month,1);selected=month+'-01';render();}});
  $('#calendar-today').addEventListener('click',()=>{selected=today();month=selected.slice(0,7);render();});
  $('#calendar-start').addEventListener('click',()=>{const first=events.filter(e=>!filter||e.id===filter).map(e=>e.start).sort()[0];if(first){selected=first;month=first.slice(0,7);render();}});
  $('#calendar-filter').addEventListener('change',()=>{filter=$('#calendar-filter').value;render();});
  $('#calendar-grid').addEventListener('click',event=>{const day=event.target.closest('[data-calendar-day]')?.dataset.calendarDay;if(day){selected=day;month=day.slice(0,7);render();}});
  root.addEventListener('growth-memory-change',refresh);
  root.addEventListener('contest-library-change',refresh);
  root.addEventListener('storage',event=>{if(event.key===null||event.key?.startsWith('jingxu-v2-')||['jingxu-growth-v1','jingxu-v1'].includes(event.key)){if(event.key===null)overrides.clear();else if(event.key?.startsWith('jingxu-v2-'))overrides.delete(event.key.slice('jingxu-v2-'.length));refresh();}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  refresh();
  fetch('/api/contests').then(r=>{if(!r.ok)throw new Error('竞赛列表加载失败');return r.json();}).then(data=>{catalog=data.contests;refresh();}).catch(()=>{$('#calendar-summary').textContent='竞赛列表暂时无法加载，日历仅显示已读取的当前计划。';});
})(typeof window!=='undefined'?window:globalThis);

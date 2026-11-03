(function(root){
  const DRAFT='jingxu-growth-drafts-v1';
  const KEY='jingxu-growth-v1',PREF='jingxu-growth-enabled-v1';
  const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function load(){
    const raw=JSON.parse(localStorage.getItem(KEY)||'{"logs":[]}');
    if(!raw||!Array.isArray(raw.logs))throw new Error('成长记录格式异常，请先导出备份，再检查浏览器存储。');
    return raw.logs;
  }
  function valid(log,today){
    if(!log||!/^\d{4}-\d{2}-\d{2}$/.test(log.day)||new Date(log.day+'T00:00:00Z').toISOString().slice(0,10)!==log.day||log.day>today)throw new Error('请选择今天或过去的有效日期。');
    if(!log.contest_id||log.contest_id.length>50)throw new Error('请选择竞赛。');
    for(const k of ['actual_hours','planned_hours'])if(typeof log[k]!=='number'||!Number.isFinite(log[k])||log[k]<0||log[k]>24)throw new Error('每日用时需要在0—24小时之间。');
    if(!['done','partial','blocked','rest'].includes(log.status))throw new Error('请选择完成情况。');
    if(log.status==='rest'&&(log.actual_hours||log.planned_hours))throw new Error('休息日的计划与实际用时请填写0。');
    for(const [k,max] of [['goal',250],['progress',1000],['blocker',500],['skills',200]]){
      if(typeof log[k]!=='string'||log[k].length>max||(['goal','progress'].includes(k)&&!log[k].trim()))throw new Error('请完整填写目标、实际进展，并遵守字数限制。');
    }
    return log;
  }
  function saveLog(log,today){
    valid(log,today);
    const logs=load().filter(l=>!(l.day===log.day&&l.contest_id===log.contest_id));
    const total=logs.filter(l=>l.day===log.day).reduce((n,l)=>n+l.actual_hours,0)+log.actual_hours;
    if(total>24)throw new Error('同一天跨竞赛累计用时不能超过24小时。');
    logs.push(log);logs.sort((a,b)=>a.day.localeCompare(b.day)||a.contest_id.localeCompare(b.contest_id));
    if(logs.length>500)throw new Error('已达到500条记录，请先导出并删除不需要的旧记录。');
    localStorage.setItem(KEY,JSON.stringify({logs}));
    return logs;
  }
  function removeLog(contest,day){const logs=load().filter(l=>!(l.contest_id===contest&&l.day===day));localStorage.setItem(KEY,JSON.stringify({logs}));return logs;}
  function forPlanning(){
    const checkbox=typeof document!=='undefined'?document.querySelector('#use-growth-memory'):null;
    if(checkbox&&!checkbox.checked)return [];
    if(localStorage.getItem(PREF)==='false')return [];
    return load().slice(-120);
  }
  function loadDrafts(){const drafts=JSON.parse(localStorage.getItem(DRAFT)||'{}');if(!drafts||typeof drafts!=='object'||Array.isArray(drafts))throw new Error('每日草稿无法读取，请先备份。');return drafts;}
  function saveDraft(contest,day,fields){const drafts=loadDrafts();drafts[contest+'|'+day]=fields;localStorage.setItem(DRAFT,JSON.stringify(drafts));}
  function clearDraft(contest,day){const drafts=loadDrafts();delete drafts[contest+'|'+day];localStorage.setItem(DRAFT,JSON.stringify(drafts));}
  const api={load,saveLog,removeLog,forPlanning,valid,loadDrafts,saveDraft,clearDraft};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.GrowthMemory=api;
  if(typeof document==='undefined')return;
  const mount=document.querySelector('#growth-memory');if(!mount)return;
  let catalog=[],summaryVersion=0;
  const $=s=>mount.querySelector(s),status=s=>{$('#growth-status').textContent=s;};
  mount.innerHTML=`<div class="section-heading"><div><span class="eyebrow">CROSS-COMPETITION MEMORY</span><h2>我的成长记录</h2></div><button type="button" class="text-button" id="growth-export">导出记录</button></div>
    <p class="quiet">每天记录真实投入与进展，下次参加其他竞赛也能参考。每个竞赛每天一条，可修改；没有训练的日期也可记录休息。</p>
    <div id="growth-stat-line" class="growth-summary" aria-live="polite"></div>
    <details class="resource-fold" open><summary>记录今天 / 补记进度</summary><form id="growth-form"><div class="form-grid">
      <label>竞赛<select id="growth-contest" required></select></label><label>日期<input id="growth-day" type="date" required></label>
      <label>实际用时（小时）<input id="growth-actual" type="number" min="0" max="24" step="0.25" placeholder="例如：0.5" required></label>
      <label>今天完成情况<select id="growth-completion"><option value="done">完成当天安排</option><option value="partial">部分完成</option><option value="blocked">未完成 / 卡住</option><option value="rest">休息 / 未安排训练</option></select></label>
      <label class="wide">今天做了什么<textarea id="growth-progress" maxlength="1000" rows="3" required placeholder="写实际成果、结果，或卡住的地方"></textarea></label>
      </div><details class="resource-fold"><summary>补充目标、卡点和标签（选填）</summary><div class="form-grid"><label>原计划用时（小时）<input id="growth-planned" type="number" min="0" max="24" step="0.25" value="0"></label><label>练习标签<input id="growth-skills" maxlength="200" placeholder="例如：Python,数据审计"></label><label class="wide">当天目标<input id="growth-goal" maxlength="250" placeholder="未填写时不推断具体目标"></label><label class="wide">卡点与下一步<textarea id="growth-blocker" maxlength="500" rows="2" placeholder="例如：下次先做一个分组填补小例子"></textarea></label></div></details><p class="quiet">输入会自动保存为草稿，切换日期或离开页面后可继续；点击保存后才计入成长记录。</p><div class="form-actions"><button class="primary" type="submit">保存当天记录</button></div></form></details>
    <p id="growth-status" role="status" aria-live="polite"></p><details class="resource-fold"><summary>查看与修改最近记录</summary><label for="growth-history-limit">查看范围</label><select id="growth-history-limit"><option value="30">最近30条</option><option value="90">最近90条</option><option value="500">全部记录</option></select><div id="growth-history"></div></details>
    <p class="quiet">记录保存在当前浏览器，不随重新生成计划清空。计划开启“参考成长记录”时，会发送最近最多120条记录用于统计，摘要与近期8条用于AI计划；自报进度不等于验收或能力认证。</p>`;
  function currentContest(){return document.querySelector('#contest-title')?location.pathname.split('/').filter(Boolean).pop():$('#growth-contest').value||catalog[0]?.id;}
  function budget(){const n=Number(document.querySelector('#weekly-hours')?.value);return n>=1&&n<=40?n:6;}
  const fields=[['growth-planned','planned_hours',0],['growth-actual','actual_hours',''],['growth-completion','status','done'],['growth-skills','skills',''],['growth-goal','goal',''],['growth-progress','progress',''],['growth-blocker','blocker','']];
  function populate(){
    const contest=$('#growth-contest').value,day=$('#growth-day').value;
    const log=loadDrafts()[contest+'|'+day]||load().find(l=>l.contest_id===contest&&l.day===day);
    for(const [id,key,fallback]of fields)$('#'+id).value=log?.[key]??fallback;
  }
  async function render(){
    const version=++summaryVersion;
    try{
      const logs=load();
      $('#growth-history').innerHTML=logs.slice(-Number($('#growth-history-limit').value||30)).reverse().map(log=>`<article class="growth-entry"><strong>${escape(log.day)} · ${escape(catalog.find(c=>c.id===log.contest_id)?.short||log.contest_id)}</strong><p>计划 ${escape(log.planned_hours)}h / 实际 ${escape(log.actual_hours)}h · ${escape({done:'完成',partial:'部分完成',blocked:'卡住',rest:'休息'}[log.status])}</p><p>${escape(log.goal)}</p><p>${escape(log.progress)}</p><p class="quiet">${escape(log.blocker)}</p><button type="button" class="text-button" data-growth-edit="${escape(log.contest_id)}" data-day="${escape(log.day)}">修改</button><button type="button" class="text-button" data-growth-delete="${escape(log.contest_id)}" data-day="${escape(log.day)}">删除</button></article>`).join('')||'<p class="quiet">还没有记录，先记下今天的实际进展。</p>';
      const total=logs.reduce((n,l)=>n+l.actual_hours,0),sources=new Set(logs.map(l=>l.contest_id)).size;
      $('#growth-stat-line').textContent=`累计 ${logs.length} 条记录 · ${sources} 个竞赛 · 实际投入 ${Math.round(total*100)/100} 小时`;
      const response=await fetch('/api/growth/summary',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({contest_id:currentContest(),weekly_hours:budget(),logs:logs.slice(-120)})});
      const result=await response.json();if(version!==summaryVersion)return;
      if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'成长记录暂时无法分析。');
      $('#growth-stat-line').textContent+=`。${result.reason}${result.entries?` 若参考记录，下次计划建议每周不超过 ${result.recommended_hours} 小时。`:''}`;
      const overview=document.querySelector('#growth-overview');
      if(overview){
        const blockers=[...new Set(logs.slice().reverse().map(l=>l.blocker).filter(Boolean))].slice(0,5);
        overview.innerHTML=`<div class="growth-stat-grid"><article><strong>${sources}</strong><span>累计记录的竞赛</span></article><article><strong>${logs.length}</strong><span>每日记录</span></article><article><strong>${Math.round(total*100)/100}h</strong><span>累计实际投入</span></article><article><strong>${result.logged_days}</strong><span>近28天已记录日期</span></article></div><h3>训练节奏</h3><p>${escape(result.reason)}</p><p class="quiet">参考预算为每周 ${escape(result.requested_hours)} 小时。自报完成指数：${result.goal_completion_index===null?'暂无足够记录':Math.round(result.goal_completion_index*100)+'%'}，不代表成果验收通过率。</p><h3>练习过的内容</h3><div class="practice-topics">${result.practice_topics.length?result.practice_topics.map(t=>`<span class="tag">${escape(t.topic)} · ${t.recorded_days}天</span>`).join(''):'<p class="quiet">记录练习标签后可在这里回看。</p>'}</div><h3>近期卡点与下一步</h3>${blockers.length?'<ul>'+blockers.map(b=>`<li>${escape(b)}</li>`).join('')+'</ul>':'<p class="quiet">还没有记录卡点。</p>'}<p class="quiet">练习记录不代表已经掌握能力。下次生成计划时，可选择参考这些经历。</p>`;
      }
    }catch(e){if(version===summaryVersion)status(e.message);}
  }
  api.refresh=()=>{if(catalog.length)render();};
  $('#growth-form').addEventListener('submit',event=>{
    event.preventDefault();if(!$('#growth-form').reportValidity())return;
    try{saveLog({contest_id:$('#growth-contest').value,day:$('#growth-day').value,planned_hours:Number($('#growth-planned').value),actual_hours:Number($('#growth-actual').value),status:$('#growth-completion').value,goal:$('#growth-goal').value.trim()||'未单独填写当天目标',progress:$('#growth-progress').value.trim(),blocker:$('#growth-blocker').value.trim(),skills:$('#growth-skills').value.trim()},ProfileStore.today());status('已保存。下次生成竞赛计划时可参考这条记录。');render();root.dispatchEvent(new Event('growth-memory-change'));}catch(e){status(e.message);}
  });
  mount.addEventListener('click',event=>{
    const edit=event.target.closest('[data-growth-edit]'),remove=event.target.closest('[data-growth-delete]');
    try{if(edit){$('#growth-contest').value=edit.dataset.growthEdit;$('#growth-day').value=edit.dataset.day;populate();$('#growth-goal').focus();}
      if(remove&&confirm('删除这条成长记录？')){removeLog(remove.dataset.growthDelete,remove.dataset.day);status('已删除。');render();root.dispatchEvent(new Event('growth-memory-change'));}}catch(e){status(e.message);}
  });
  $('#growth-history-limit').addEventListener('change',render);
  $('#growth-form').addEventListener('input',event=>{if(['growth-day','growth-contest'].includes(event.target.id))return;const contest=$('#growth-contest').value,day=$('#growth-day').value;if(!contest||!day)return;try{saveDraft(contest,day,Object.fromEntries(fields.map(([id,key])=>[key,$('#'+id).value])));status('草稿已自动保存，尚未计入正式记录。');}catch(e){status('草稿未保存：'+e.message);}});
  $('#growth-completion').addEventListener('change',()=>{if($('#growth-completion').value==='rest'){$('#growth-actual').value=0;$('#growth-planned').value=0;if(!$('#growth-progress').value)$('#growth-progress').value='今日未安排训练，休息。';}try{saveDraft($('#growth-contest').value,$('#growth-day').value,Object.fromEntries(fields.map(([id,key])=>[key,$('#'+id).value])));}catch(e){status(e.message);}});
  $('#growth-contest').addEventListener('change',()=>{try{populate();}catch(e){status(e.message);}});$('#growth-day').addEventListener('change',()=>{try{populate();}catch(e){status(e.message);}});
  $('#growth-export').addEventListener('click',()=>{try{const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,logs:load()},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='竞序-跨竞赛成长记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){status(e.message);}});
  const checkbox=document.querySelector('#use-growth-memory');
  if(checkbox){try{checkbox.checked=localStorage.getItem(PREF)!=='false';}catch(e){status(e.message);}checkbox.addEventListener('change',()=>{try{localStorage.setItem(PREF,String(checkbox.checked));root.dispatchEvent(new Event('growth-memory-change'));}catch(e){status(e.message);}});}
  document.querySelector('#weekly-hours')?.addEventListener('change',render);
  root.addEventListener('storage',event=>{if(event.key===KEY||event.key===PREF){if(checkbox)checkbox.checked=localStorage.getItem(PREF)!=='false';render();}});
  $('#growth-day').value=$('#growth-day').max=ProfileStore.today();
  fetch('/api/contests').then(r=>{if(!r.ok)throw new Error('无法加载成长记录的竞赛列表。');return r.json();}).then(data=>{catalog=data.contests;$('#growth-contest').innerHTML=catalog.map(c=>`<option value="${escape(c.id)}">${escape(c.short)}</option>`).join('');const selected=currentContest();if(catalog.some(c=>c.id===selected))$('#growth-contest').value=selected;populate();render();}).catch(e=>status(e.message));
})(typeof window!=='undefined'?window:globalThis);

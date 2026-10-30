(function(root){
 const allowed=key=>['jingxu-profile-v1','jingxu-library-v1','jingxu-growth-v1','jingxu-growth-drafts-v1','jingxu-growth-enabled-v1','jingxu-discipline-v1','jingxu-v1'].includes(key)||/^jingxu-v2-[a-z0-9-]{1,50}$/.test(key);
 const object=v=>v&&typeof v==='object'&&!Array.isArray(v);
 const text=(v,max=24000)=>typeof v==='string'&&v.length<=max;
 const day=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!Number.isNaN(new Date(v+'T00:00:00Z').valueOf())&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
 function assert(ok,message){if(!ok)throw new Error(message);}
 function validTask(t){assert(object(t)&&text(t.id,100)&&t.id&&text(t.title,150)&&text(t.deliverable,500)&&Number.isFinite(t.hours)&&t.hours>0&&t.hours<=40,'备份包含无效任务');assert(t.resource_ids===undefined||(Array.isArray(t.resource_ids)&&t.resource_ids.every(x=>text(x,100))),'任务资源格式错误');}
 function validWeek(w){assert(object(w)&&text(w.title,150)&&day(w.start)&&day(w.end)&&w.start<=w.end&&Array.isArray(w.tasks)&&w.tasks.length<=200,'备份包含无效训练周');w.tasks.forEach(validTask);}
 function validState(state,version=false){
  assert(object(state),'计划存档格式错误');
  if(state.plan!=null){assert(object(state.plan)&&text(state.plan.summary,3000)&&Array.isArray(state.plan.weeks)&&state.plan.weeks.length>0&&state.plan.weeks.length<=64,'计划格式错误');state.plan.weeks.forEach(validWeek);const ids=state.plan.weeks.flatMap(w=>w.tasks.map(t=>t.id));assert(new Set(ids).size===ids.length,'计划任务标识重复');}
  if(state.completed!==undefined)assert(object(state.completed)&&Object.values(state.completed).every(v=>typeof v==='boolean'),'完成状态格式错误');
  if(state.messages!==undefined)assert(Array.isArray(state.messages)&&state.messages.every(m=>object(m)&&['user','assistant'].includes(m.role)&&text(m.content)),'聊天记录格式错误');
  if(state.submissionDrafts!==undefined)assert(object(state.submissionDrafts)&&Object.values(state.submissionDrafts).every(v=>text(v)),'成果草稿格式错误');
  if(state.reviews!==undefined){assert(Array.isArray(state.reviews),'评价记录格式错误');for(const r of state.reviews){assert(object(r)&&object(r.review)&&['passed','needs_revision','insufficient_evidence','review_incomplete'].includes(r.review.verdict)&&text(r.review.summary)&&Array.isArray(r.review.criteria),'评价记录格式错误');if(r.week)validWeek(r.week);else assert(object(r.task)&&text(r.task.title),'评价缺少对应成果');for(const c of r.review.criteria)assert(object(c)&&text(c.criterion)&&text(c.feedback)&&text(c.evidence)&&['met','partial','missing'].includes(c.status),'评价条目格式错误');}}
  if(state.versions!==undefined){assert(!version&&Array.isArray(state.versions),'历史版本格式错误');for(const entry of state.versions){assert(object(entry)&&text(entry.id,100)&&text(entry.label,300)&&object(entry.state),'历史版本格式错误');validState(entry.state,true);}}
 }
 function validateEntry(key,value){
  assert(allowed(key),'备份包含不允许的数据项：'+key);
  if(key.startsWith('jingxu-v2-')||key==='jingxu-v1')return validState(value);
  if(key==='jingxu-profile-v1')assert(object(value)&&['major','grade','skills'].every(k=>text(value[k],500)&&value[k].trim()),'画像格式错误');
  if(key==='jingxu-library-v1')assert(object(value)&&['favorites','participating','archived'].every(k=>value[k]===undefined||(Array.isArray(value[k])&&value[k].every(id=>typeof id==='string'&&/^[a-z0-9-]{1,50}$/.test(id)))),'赛事列表格式错误');
  if(key==='jingxu-growth-v1'){assert(object(value)&&Array.isArray(value.logs)&&value.logs.length<=500,'成长记录格式错误');const seen=new Set();for(const l of value.logs){assert(object(l)&&text(l.contest_id,50)&&day(l.day)&&['done','partial','blocked','rest'].includes(l.status)&&[['goal',250],['progress',1000],['blocker',500],['skills',200]].every(([k,max])=>text(l[k],max))&&l.goal.trim()&&l.progress.trim()&&!(l.status==='rest'&&(l.actual_hours||l.planned_hours))&&['actual_hours','planned_hours'].every(k=>Number.isFinite(l[k])&&l[k]>=0&&l[k]<=24),'每日记录格式错误');assert(!seen.has(l.contest_id+'|'+l.day),'每日记录重复');seen.add(l.contest_id+'|'+l.day);}}
  if(key==='jingxu-growth-drafts-v1')assert(object(value)&&Object.values(value).every(d=>object(d)&&Object.values(d).every(v=>typeof v==='string'||(typeof v==='number'&&Number.isFinite(v)))),'每日草稿格式错误');
  if(key==='jingxu-growth-enabled-v1')assert(typeof value==='boolean','成长偏好格式错误');
  if(key==='jingxu-discipline-v1')assert(value===null||object(value),'筛选偏好格式错误');
 }
 function exportData(storage=localStorage){const entries={},unreadable={};for(let i=0;i<storage.length;i++){const key=storage.key(i);if(allowed(key)){const raw=storage.getItem(key);try{entries[key]=JSON.parse(raw);}catch{unreadable[key]=raw;}}}return {format:'jingxu-workspace',version:1,exported_at:new Date().toISOString(),entries,unreadable};}
 function normalize(data){if(object(data)&&data.version===1&&Array.isArray(data.logs)&&!data.format)return {format:'jingxu-workspace',version:1,entries:{'jingxu-growth-v1':{logs:data.logs}}};return data;}
 function inspect(data){data=normalize(data);assert(object(data)&&data.format==='jingxu-workspace'&&data.version===1&&object(data.entries),'请选择竞序统一备份文件（JSON）');const entries=Object.entries(data.entries);assert(entries.length>0&&entries.length<=100,'备份数据项数量异常');entries.forEach(([k,v])=>validateEntry(k,v));return {keys:entries.map(([k])=>k),plans:entries.filter(([k,v])=>(k.startsWith('jingxu-v2-')||k==='jingxu-v1')&&v.plan).length,logs:data.entries['jingxu-growth-v1']?.logs.length||0};}
 function restoreData(data,storage=localStorage,overwrite=false){
  data=normalize(data);const result=inspect(data),writes=Object.entries(data.entries).filter(([key])=>overwrite||storage.getItem(key)===null),before=new Map(writes.map(([key])=>[key,storage.getItem(key)]));
  const written=[];
  try{for(const [key,value]of writes){storage.setItem(key,JSON.stringify(value));written.push(key);}}
  catch(error){for(const key of written)storage.removeItem(key);for(const key of written){const old=before.get(key);if(old!==null)storage.setItem(key,old);}throw new Error('恢复失败，已撤回本次写入，请检查存储空间。');}
  return {...result,imported:writes.length,skipped:result.keys.length-writes.length};
 }
 function signature(week){return JSON.stringify(week.tasks.map(t=>[t.id,t.title,t.deliverable]).sort((a,b)=>String(a[0]).localeCompare(String(b[0]))));}
 function weekStatus(week,completed={},reviews=[]){
  const latest=reviews.slice().reverse().find(r=>r.week&&signature(r.week)===signature(week));
  const all=week.tasks.length>0&&week.tasks.every(t=>completed[t.id]);
  if(latest?.review.verdict==='passed')return latest.applied&&all?'验收通过':'验收通过 · 待应用/同步进度';
  if(latest?.review.verdict==='needs_revision')return '需改进后复验';
  if(latest?.review.verdict==='insufficient_evidence')return '待补充证据';
  if(latest?.review.verdict==='review_incomplete')return '待重新评价';
  return all?'自报完成 · 待验收':'进行中';
 }
 function weeklyJournal(logs,contestId,week){
  const found=logs.filter(l=>l.contest_id===contestId&&l.day>=week.start&&l.day<=week.end).sort((a,b)=>a.day.localeCompare(b.day));
  if(!found.length)return '';
  const clip=(s,n)=>s.length>n?s.slice(0,n)+'（节选，全文见每日记录）':s;
  return `本周每日记录汇总（${found.length}天；实际用时${Math.round(found.reduce((n,l)=>n+l.actual_hours,0)*100)/100}小时）\n以下为本人日常自报记录，尚不等于成果验收；文件、代码与验证证据请继续补充。\n\n`+found.map(l=>`${l.day}｜${{done:'完成当天目标',partial:'部分完成',blocked:'卡住',rest:'休息'}[l.status]}｜实际${l.actual_hours}小时\n目标：${clip(l.goal,150)}\n进展：${clip(l.progress,600)}${l.blocker?'\n卡点与下一步：'+clip(l.blocker,200):''}`).join('\n\n');
 }
 const api={exportData,inspect,restoreData,validState,weekStatus,weeklyJournal,normalize};root.WorkspaceData=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(typeof document==='undefined')return;
 const mount=document.querySelector('#workspace-backup');if(!mount)return;
 let pending=null,fileVersion=0;
 mount.innerHTML='<details class="resource-fold"><summary>统一备份与恢复</summary><p class="quiet">备份包含画像、参赛与归档列表、计划历史版本、成果评价、每日记录及草稿。导入前会检查文件；覆盖恢复前会下载当前数据备份。</p><button id="backup-export" class="secondary" type="button">下载完整备份</button><label for="backup-file">导入竞序备份（JSON）</label><input id="backup-file" type="file" accept=".json"><p id="backup-status" role="status"></p><div id="backup-preview" hidden><label><input type="checkbox" id="backup-overwrite"> 替换备份中与本机同名的数据（默认保留本机冲突项）</label><button id="backup-apply" class="primary" type="button">确认恢复</button></div></details>';
 const $=s=>mount.querySelector(s),message=s=>{$('#backup-status').textContent=s;};
 function download(data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='竞序-完整备份-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 $('#backup-export').addEventListener('click',()=>{try{const backup=exportData();download(backup);message(Object.keys(backup.unreadable).length?'已下载备份；无法解析的数据项已单独保留原文，不会自动导入。':'已下载完整备份。');}catch(e){message(e.message);}});
 $('#backup-file').addEventListener('change',async event=>{const version=++fileVersion;pending=null;$('#backup-preview').hidden=true;const file=event.target.files?.[0];if(!file)return;try{if(file.size>10000000)throw new Error('备份文件超过10MB，请检查是否选择了正确文件。');const data=normalize(JSON.parse(await file.text()));if(version!==fileVersion)return;const summary=inspect(data);pending=data;$('#backup-overwrite').checked=false;message(`已检查：${summary.plans}份计划、${summary.logs}条每日记录、${summary.keys.length}项数据。确认后恢复。`);$('#backup-preview').hidden=false;}catch(e){message(e.message);}});
 $('#backup-apply').addEventListener('click',()=>{if(!pending)return;try{download(exportData());const result=restoreData(pending,localStorage,$('#backup-overwrite').checked);message(`已恢复${result.imported}项，保留本机冲突项${result.skipped}项。正在重新载入…`);location.reload();}catch(e){message(e.message);}});
})(typeof window!=='undefined'?window:globalThis);

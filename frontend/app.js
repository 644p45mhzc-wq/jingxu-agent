// Escape all raw HTML; only explicitly supported Markdown produces markup.
window.ChatMarkdown = (() => {
  const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function inline(s) {
    const tokens = [];
    let text = escape(s).replace(/`([^`]+)`/g, (_, code) => { tokens.push(`<code>${code}</code>`); return `\u0000${tokens.length-1}\u0000`; });
    text = text.replace(/\[([^\]]+)\]\(([^\s)]+)\)/g, (_, label, href) => {
      if (!/^https?:\/\//i.test(href)) return label;
      tokens.push(`<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`);
      return `\u0000${tokens.length-1}\u0000`;
    }).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/__(.+?)__/g,'<strong>$1</strong>').replace(/\*([^*\n]+)\*/g,'<em>$1</em>').replace(/~~(.+?)~~/g,'<del>$1</del>');
    return text.replace(/\u0000(\d+)\u0000/g, (_, i) => tokens[+i]);
  }
  function render(raw) {
    const lines = String(raw).replace(/\r\n?/g,'\n').split('\n'), out = [];
    let paragraph = [], list = null, code = null;
    const flush = () => { if(paragraph.length) {out.push(`<p>${paragraph.map(inline).join('<br>')}</p>`); paragraph=[];} };
    const closeList = () => {if(list) {out.push(`</${list}>`); list=null;}};
    for(let i=0;i<lines.length;i++) {
      const line=lines[i];
      if(code !== null) {if(/^\s*```/.test(line)) {out.push(`<pre><code>${escape(code.join('\n'))}</code></pre>`); code=null;} else code.push(line); continue;}
      if(/^\s*```/.test(line)) {flush();closeList();code=[];continue;}
      if(!line.trim()) {flush();closeList();continue;}
      const heading=line.match(/^\s*(#{1,6})\s+(.+)$/), item=line.match(/^\s*(?:([-+*])|\d+[.)])\s+(.+)$/);
      if(heading) {flush();closeList();const level=Math.min(heading[1].length+1,6);out.push(`<h${level}>${inline(heading[2])}</h${level}>`);continue;}
      if(item) {flush(); const kind=item[1]?'ul':'ol';if(list!==kind) {closeList();out.push(`<${kind}>`);list=kind;}out.push(`<li>${inline(item[2])}</li>`);continue;}
      if(/^\s*(?:---+|\*\*\*+)\s*$/.test(line)) {flush();closeList();out.push('<hr>');continue;}
      if(/^\s*>/.test(line)) {flush();closeList();out.push(`<blockquote>${inline(line.replace(/^\s*>\s?/,''))}</blockquote>`);continue;}
      if(line.includes('|') && i+1<lines.length && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i+1])) {
        flush();closeList();const cells=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(v=>inline(v.trim()));
        out.push('<div class="md-table"><table><thead><tr>'+cells(line).map(v=>`<th>${v}</th>`).join('')+'</tr></thead><tbody>');i++;
        while(i+1<lines.length && lines[i+1].includes('|') && lines[i+1].trim()) {i++;out.push('<tr>'+cells(lines[i]).map(v=>`<td>${v}</td>`).join('')+'</tr>');}
        out.push('</tbody></table></div>');continue;
      }
      closeList();paragraph.push(line);
    }
    flush();closeList();if(code!==null)out.push(`<pre><code>${escape(code.join('\n'))}</code></pre>`);
    return out.join('');
  }
  return {render};
})();

const $ = (s) => document.querySelector(s);
let sharedProfile = null;
let versions = [], generatedPreview = null;
let reviews = [], submissionDrafts = {}, reviewPreview = null, reviewController = null, reviewCancelled = false;
const verdictLabel = {passed:'验收通过', needs_revision:'需要修改', insufficient_evidence:'证据不足', review_incomplete:'AI评价未完成'};
let data, plan = null, completed = {}, messages = [], busy = false, adjustmentPreview = null;
const contestId = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || 'cumcm');
const storageKey = `jingxu-v2-${contestId}`;
const esc = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function notify(text) { const box = $('#notice'); box.textContent = text; box.hidden = false; clearTimeout(notify.timer); notify.timer = setTimeout(() => box.hidden = true, 6500); }
function profile() { return sharedProfile; }
function refreshProfile() {
  try { sharedProfile = ProfileStore.load(); } catch { sharedProfile = null; }
  $('#profile-summary').textContent = sharedProfile ? `${sharedProfile.grade} · ${sharedProfile.major}\n能力：${sharedProfile.skills}` : '还没有填写画像，请先到首页填写并保存。';
  return Boolean(sharedProfile);
}
function requireProfile() { if(refreshProfile()) return true; notify('请先点击“修改画像”，在首页填写并保存画像。'); return false; }

function addDays(value,days){const d=new Date(value+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10);}
function restoreDateInputs(state){
 const saved=state.plan;
 $('#plan-start').value=state.planStart||saved?.schedule?.start||saved?.weeks?.[0]?.start||$('#plan-start').value||ProfileStore.today();
 $('#plan-end').value=state.planEnd||saved?.schedule?.end||saved?.weeks?.at(-1)?.end||(state.trainingWeeks?addDays($('#plan-start').value,state.trainingWeeks*7-1):$('#plan-end').value)||addDays($('#plan-start').value,6);
 $('#adjust-start').value=$('#plan-start').value<ProfileStore.today()?ProfileStore.today():$('#plan-start').value;
 $('#adjust-end').value=$('#plan-end').value;
}
function dateRangeValid(prefix,limit){
 const start=$('#'+prefix+'-start'),end=$('#'+prefix+'-end');
 start.setCustomValidity('');end.setCustomValidity('');
 const valid=value=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&!Number.isNaN(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
 if(!valid(start.value))start.setCustomValidity('请选择有效的开始日期。');
 else if(start.value<ProfileStore.today())start.setCustomValidity('开始日期不能早于今天。');
 if(!valid(end.value))end.setCustomValidity('请选择有效的结束日期。');
 else if(valid(start.value)){
  const days=Math.round((Date.parse(end.value+'T00:00:00Z')-Date.parse(start.value+'T00:00:00Z'))/86400000)+1;
  if(days<1)end.setCustomValidity('结束日期不能早于开始日期。');
  else if(days>limit)end.setCustomValidity('所选日期范围最多'+limit+'天（含首尾日期）。');
 }
 return start.reportValidity() && end.reportValidity();
}
function activeState() {return {plan,completed,reviews,submissionDrafts,messages:messages.slice(-100),planStart:$('#plan-start').value,planEnd:$('#plan-end').value,weeklyHours:Number($('#weekly-hours').value)};}
function save() {try{localStorage.setItem(storageKey,JSON.stringify({...activeState(),versions}));return true;}catch{notify('浏览器存储不可用，当前修改可能未保存，请先下载完整备份。');return false;}}
function archiveCurrent() {return {id:Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8),created_at:new Date().toISOString(),label:`${new Date().toLocaleString('zh-CN')} · ${plan?.weeks.length||0}周 · ${reviews.length}条评价`,state:JSON.parse(JSON.stringify({...activeState(),planStart:plan?.schedule?.start||plan?.weeks[0]?.start||$('#plan-start').value,planEnd:plan?.schedule?.end||plan?.weeks.at(-1)?.end||$('#plan-end').value,weeklyHours:plan?.schedule?.hours||Number($('#weekly-hours').value)}))};}
function commitState(next,history) {
  const stored={...next,versions:history};
  try{localStorage.setItem(storageKey,JSON.stringify(stored));}catch{notify('存储空间不足，未替换当前计划。请先下载完整备份并清理不需要的数据。');return false;}
  plan=stored.plan;completed=stored.completed||{};reviews=stored.reviews||[];submissionDrafts=stored.submissionDrafts||{};messages=stored.messages||[];versions=history;
  restoreDateInputs(stored);$('#weekly-hours').value=stored.weeklyHours||plan.schedule?.hours||6;
  clearAdjustment();renderPlan();renderReviewHistory();renderChatHistory();return true;
}
function renderVersions() {
  $('#plan-versions').hidden=!versions.length;
  $('#version-list').innerHTML=versions.length?'<label for="version-select">选择可恢复的旧版</label><select id="version-select">'+versions.slice().reverse().map(v=>`<option value="${esc(v.id)}">${esc(v.label)}</option>`).join('')+'</select><button type="button" class="secondary" id="restore-version">恢复此版本（当前版自动归档）</button> <button type="button" class="text-button" id="delete-version">删除选中旧版</button>':'';
  if(versions.length)$('#delete-version').addEventListener('click',()=>{if(busy)return;const id=$('#version-select').value;if(!versions.some(v=>v.id===id)||!confirm('删除这个旧版本及其成果快照？请先下载完整备份；当前版本保持不变。'))return;commitState(activeState(),versions.filter(v=>v.id!==id));});
  if(versions.length)$('#restore-version').addEventListener('click',()=>{if(busy)return;const selected=versions.find(v=>v.id===$('#version-select').value);if(!selected)return;const history=versions.filter(v=>v.id!==selected.id);if(plan)history.push(archiveCurrent());if(commitState(selected.state,history)){generatedPreview=null;$('#generation-preview').hidden=true;notify('已恢复旧版计划、成果草稿和评价，刚才的版本仍在历史中。');}});
}
function showGeneratedPreview(result) {
  generatedPreview=result;
  $('#generation-preview').innerHTML=`<h3>新计划预览 · ${result.weeks.length}周</h3><p>${esc(result.summary)}</p><p>${esc(result.schedule?.note||'')}</p>`+result.weeks.map((w,i)=>`<p><strong>W${String(i+1).padStart(2,'0')} · ${esc(w.title)}</strong><br><span class="quiet">${esc(w.start)} — ${esc(w.end)} · ${Math.round(w.tasks.reduce((n,t)=>n+t.hours,0)*100)/100}h</span></p>`).join('')+'<p class="quiet">应用后自动归档当前计划及成果，不会删除旧记录。</p><button type="button" class="primary" id="apply-generated">应用新计划</button> <button type="button" class="secondary" id="discard-generated">取消</button>';
  $('#generation-preview').hidden=false;
  $('#discard-generated').addEventListener('click',()=>{generatedPreview=null;$('#generation-preview').hidden=true;});
  $('#apply-generated').addEventListener('click',()=>{if(!generatedPreview||busy)return;if(generatedSettings!==null && generatedSettings!==generationSettings()){clearGeneratedPreview();notify('日期、预算或画像已变化，请重新生成。');return;}const next=generatedPreview,history=[...versions];if(plan)history.push(archiveCurrent());const state={plan:next,completed:{},reviews:[],submissionDrafts:{},messages:[...messages],planStart:next.schedule?.start||next.weeks[0].start,planEnd:next.schedule?.end||next.weeks.at(-1).end,weeklyHours:next.schedule?.hours||Number($('#weekly-hours').value)};if(commitState(state,history)){generatedPreview=null;$('#generation-preview').hidden=true;notify('新计划已应用，旧版及成果可在历史版本中恢复。');}});
}
function statusForWeek(week) {return window.WorkspaceData?window.WorkspaceData.weekStatus(week,completed,reviews):(week.tasks.every(t=>completed[t.id])?'自报完成 · 待验收':'进行中');}
function restore() {
  refreshProfile();
  try { const old = JSON.parse(localStorage.getItem(storageKey) || (contestId === 'cumcm' ? localStorage.getItem('jingxu-v1') : null) || 'null'); if (old) { if(old.plan?.weeks && Array.isArray(old.plan.weeks)) plan = old.plan; versions=Array.isArray(old.versions)?old.versions:[]; completed = old.completed || {}; reviews=Array.isArray(old.reviews)?old.reviews.slice(-50):[]; submissionDrafts=old.submissionDrafts&&typeof old.submissionDrafts==='object'?old.submissionDrafts:{}; messages=Array.isArray(old.messages)?old.messages.filter(m=>m && ['user','assistant'].includes(m.role) && typeof m.content==='string').slice(-100):[]; restoreDateInputs(old); if(old.weeklyHours || old.plan?.schedule?.hours) $('#weekly-hours').value = old.weeklyHours || old.plan.schedule.hours; } } catch { notify('保存的计划无法读取，请重新生成。'); }
}
async function api(url, body, externalController=null) {
  const controller = externalController || new AbortController(); const timer = setTimeout(() => controller.abort(), 135000);
  try { const response = await fetch(url, {method:body ? 'POST':'GET', headers:body ? {'Content-Type':'application/json'}:{}, body:body ? JSON.stringify(body):undefined, signal:controller.signal}); const result = await response.json(); if(!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : '提交的信息不完整或格式不正确，请检查档案。'); return result;
  } catch (e) { if(e.name === 'AbortError') throw new Error('请求超时，请稍后重试。'); if(e instanceof TypeError) throw new Error('无法连接后端，请确认服务正在运行。'); throw e; } finally { clearTimeout(timer); }
}
function resourceLink(r) { return `<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)} ↗</a>`; }
function renderPlan() {
  if(!plan) return;
  renderVersions();
  window.PlanCalendar?.setPlan?.(contestId,plan,completed,reviews);
  renderWeekFocus();
  renderSubmissionTasks();
  $('#adjust-panel').hidden = false;
  const growth=plan.schedule?.growth_memory;
  const growthNote=growth?`<div class="growth-summary"><strong>本次计划参考了成长记录</strong><p>${esc(growth.sources.map(s=>s.name).join('、'))} · 最近28天 ${growth.logged_days} 天记录</p><p>${esc(growth.reason)} 原预算 ${esc(growth.requested_hours)}h / 本计划 ${esc(growth.recommended_hours)}h 每周。</p><p class="quiet">练习记录用于安排训练，不代表已经掌握新竞赛的专项技能。</p></div>`:'';
  const expandedWeeks = new Set(Array.from(document.querySelectorAll('.week-fold[open]')).map(el=>el.dataset.week));
  const usedResourceUrls = new Set();
  const allTasks = plan.weeks.flatMap(w => w.tasks), done = allTasks.filter(t => completed[t.id]).length;
  $('#export').disabled = false;
  const timing = plan.schedule ? `${plan.schedule.start || plan.weeks[0].start} — ${plan.schedule.end || plan.weeks.at(-1).end} · ${plan.schedule.weeks} 周 · 每周 ${plan.schedule.hours} 小时` : '这是此前保存的计划；重新生成后将按当前竞赛时间安排。';
  $('#plan-content').innerHTML = `<span class="tag" style="background:#edf4e6">${plan.mode === 'ai' ? 'DeepSeek 个性化计划' : '通用模板 · 非 AI 生成'}</span><details class="plan-explanation"><summary>查看计划说明</summary><p class="plan-summary">${esc(plan.summary)}</p><p class="quiet">${esc(plan.schedule?.note || "")}</p></details><div class="plan-meta"><span class="date-chip">个人训练安排</span> ${esc(timing)}</div><div class="progress-head"><span>一步一步，走向完成</span><span>${done} / ${allTasks.length} 项自报完成</span></div><progress value="${done}" max="${allTasks.length}" aria-label="备赛任务完成进度"></progress>${growthNote}` + plan.weeks.map((w,i) => `<details class="week week-fold" data-week="${i}" ${(expandedWeeks.has(String(i)) || (!expandedWeeks.size && w.start<=ProfileStore.today() && w.end>=ProfileStore.today()))?'open':''}><summary class="week-head"><span class="week-num">W${String(i+1).padStart(2,'0')}</span><div><h3>${esc(w.title)}</h3><p>${esc(w.start)} — ${esc(w.end)} · ${Math.round(w.tasks.reduce((n,t) => n+t.hours,0)*100)/100} 小时 · ${esc(statusForWeek(w))}${w.history ? ' · 历史训练记录' : ''}</p></div></summary><button type="button" class="secondary week-submit" data-submit-week="${i}">提交本周成果 · 整周验收</button>${w.review_focus?`<div class="week-review-focus"><strong>本周改进重点：${esc(w.review_focus.title)}</strong><p>${esc(w.review_focus.deliverable)}</p><p class="quiet">在本周原有时间内优先完成，不额外增加工时。</p></div>`:''}${w.tasks.map(t => `<div class="task ${completed[t.id] ? 'done':''}"><input type="checkbox" id="${esc(t.id)}" data-task="${esc(t.id)}" ${completed[t.id] ? 'checked':''}><div><label for="${esc(t.id)}">${esc(t.title)} · ${esc(t.hours)}h</label><details class="task-details"><summary>完成标准</summary><p>${esc(t.deliverable)}</p><div class="task-links">${(t.resource_ids || []).map(id => data.resources.find(r => r.id === id)).filter(Boolean).filter(r => { if(usedResourceUrls.has(r.url)) return false; usedResourceUrls.add(r.url); return true; }).map(resourceLink).join('')}</div></details></div></div>`).join('')}</details>`).join('');
  document.querySelectorAll('[data-submit-week]').forEach(el=>el.addEventListener('click',()=>openWeekSubmission(Number(el.dataset.submitWeek))));
  
  document.querySelectorAll('[data-task]').forEach(el => el.addEventListener('change', () => { completed[el.dataset.task] = el.checked; clearAdjustment(); save(); renderPlan(); }));
}
let generationController=null, failedPlanMode=null, generationCancelled=false, generatedSettings=null;
function generationSettings(){return JSON.stringify({profile:profile(),start:$('#plan-start').value,end:$('#plan-end').value,hours:$('#weekly-hours').value,growth:$('#use-growth-memory').checked});}
function clearGeneratedPreview(){generatedPreview=null;generatedSettings=null;$('#generation-preview').hidden=true;}
async function generate(mode) {
  if(!requireProfile() || busy || !budgetValid() || !dateRangeValid('plan',84)) return;
  let growthLogs;try{growthLogs=window.GrowthMemory?window.GrowthMemory.forPlanning():[];}catch(e){notify('无法读取成长记录：'+e.message);return;}
  clearGeneratedPreview();const settings=generationSettings();
  generationController=new AbortController();generationCancelled=false;$('#cancel-generation').hidden=false;$('#retry-plan').hidden=true;
  busy = true; $('#generate').disabled = $('#template').disabled = true;
  const oldText = $('#generate').textContent; $('#generate').textContent = mode === 'ai' ? '正在拆解计划，请稍候…':'正在生成模板…';
  try {const result=await api(`/api/plan?mode=${mode}&contest_id=${encodeURIComponent(contestId)}`,{...profile(),growth_logs:growthLogs,start_date:$('#plan-start').value,end_date:$('#plan-end').value,weekly_hours:Number($('#weekly-hours').value)},generationController);failedPlanMode=null;if(settings!==generationSettings()){notify('日期、预算或画像已变化，请重新生成。');return;}generatedSettings=settings;showGeneratedPreview(result);$('#generation-preview').scrollIntoView({behavior:'smooth'});notify('新计划已生成，请预览后应用；当前计划未改变。');}
  catch(e) {failedPlanMode=mode;$('#retry-plan').hidden=false;notify(generationCancelled?'已停止生成，原计划保持不变。':e.message);} finally {generationController=null;$('#cancel-generation').hidden=true;busy=false;$('#generate').disabled=$('#template').disabled=false;$('#generate').textContent=oldText;}
}
function bubble(content, role) { const node = document.createElement('div'); node.className = `bubble ${role}`; node.textContent = content; $('#chat-log').appendChild(node); $('#chat-log').scrollTop = $('#chat-log').scrollHeight; return node; }

let chatController=null, chatCancelled=false;
function renderChatHistory() {
  $('#chat-log').innerHTML='';
  if(!messages.length) {bubble(`你好，我是你的${data.contest.short}备赛助手。可以聊能力差距、学习资源，或把卡住的任务发给我一起拆解。`,'assistant');return;}
  messages.forEach(m=>{const node=bubble(m.content,m.role);if(m.role==='assistant'){node.innerHTML=window.ChatMarkdown.render(m.content);node.classList.add('markdown-body');}});
}
async function streamChat(body, onDelta, signal) {
  const response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});
  if(!response.ok) {let error;try{error=await response.json()}catch{};throw new Error(typeof error?.detail==='string'?error.detail:'AI 请求失败，请重试。');}
  if(!response.body)throw new Error('浏览器未收到回复，请重试。');
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',complete=false;
  function process(line) {if(!line.startsWith('data:'))return;const event=JSON.parse(line.slice(5).trim());if(event.error)throw new Error(event.error);if(event.delta)onDelta(event.delta);if(event.done)complete=true;}
  try {while(true){const {done,value}=await reader.read();buffer+=done?decoder.decode():decoder.decode(value,{stream:true});let pos;while((pos=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,pos).replace(/\r$/,'');buffer=buffer.slice(pos+1);process(line);}if(done)break;}if(buffer.trim())process(buffer);if(!complete)throw new Error('回复中断，请重试。');}
  finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
}
async function sendChat(event) {
  event.preventDefault();if($('#send').disabled || !requireProfile() || !budgetValid())return;
  const input=$('#message'),text=input.value.trim();if(!text)return;
  const pendingMessages=[...messages,{role:'user',content:text}];
  input.value='';const userBubble=bubble(text,'user'),pending=bubble('正在连接 AI…','assistant');let answer='';
  chatController=new AbortController();chatCancelled=false;
  $('#send').disabled=true;$('#clear-chat').disabled=true;$('#cancel-chat').hidden=false;
  const timer=setTimeout(()=>chatController?.abort(),135000);
  try {
    const history=pendingMessages.slice(-18).map(m=>({...m,content:m.content.slice(0,6000)}));
    await streamChat({contest_id:contestId,profile:profile(),weekly_hours:Number($('#weekly-hours').value),plan,completed,messages:history},delta=>{answer+=delta;pending.innerHTML=window.ChatMarkdown.render(answer);pending.classList.add('markdown-body');$('#chat-log').scrollTop=$('#chat-log').scrollHeight;},chatController.signal);
    messages=[...pendingMessages,{role:'assistant',content:answer}].slice(-100);save();
  } catch(e) {
    userBubble.remove();input.value=text;
    pending.classList.add('error');pending.innerHTML=answer?window.ChatMarkdown.render(answer):'';
    const label=document.createElement('p');label.textContent=chatCancelled?'已停止回复，输入内容已保留。':e.name==='AbortError'?'回复超时，可重试。':e instanceof TypeError?'无法连接后端，请检查服务后重试。':e.message;pending.appendChild(label);
    const retry=document.createElement('button');retry.type='button';retry.className='secondary';retry.textContent='重新发送';retry.addEventListener('click',()=>{if($('#send').disabled)return;pending.remove();input.value=text;$('#chat-form').requestSubmit();});pending.appendChild(retry);
  } finally {clearTimeout(timer);chatController=null;$('#send').disabled=false;$('#clear-chat').disabled=false;$('#cancel-chat').hidden=true;$('#chat-log').scrollTop=$('#chat-log').scrollHeight;}
}
$('#cancel-chat').addEventListener('click',()=>{chatCancelled=true;chatController?.abort();});
$('#clear-chat').addEventListener('click',()=>{if(chatController || !confirm('清空当前竞赛的聊天记录？备赛计划和进度会保留。'))return;messages=[];save();renderChatHistory();});
$('#cancel-generation').addEventListener('click',()=>{generationCancelled=true;generationController?.abort();});
$('#retry-plan').addEventListener('click',()=>{if(failedPlanMode)generate(failedPlanMode);});
$('#generate').addEventListener('click', () => generate('ai'));
$('#template').addEventListener('click', () => generate('template'));
$('#chat-form').addEventListener('submit', sendChat);
$('#message').addEventListener('keydown', e => {if(e.key === 'Enter' && !e.shiftKey && !e.isComposing) {e.preventDefault(); $('#chat-form').requestSubmit();}});
document.querySelectorAll('[data-prompt]').forEach(b => b.addEventListener('click', () => {$('#message').value = b.dataset.prompt; $('#message').focus();}));
$('#export').addEventListener('click', () => {
  if(!plan) return;
  let text = `# ${data.contest.name} · 个人训练计划\n\n${plan.mode === 'ai' ? 'DeepSeek 个性化计划':'通用模板（非 AI 生成）'}\n\n${plan.summary}\n\n${plan.schedule ? plan.schedule.target_label + "；" + plan.schedule.note : "旧版计划"}\n\n` + plan.weeks.map((w,i) => `## 第 ${i+1} 周：${w.title}\n${w.start} 至 ${w.end}\n\n` + w.tasks.map(t => `- [${completed[t.id] ? 'x':' '}] ${t.title}（${t.hours} 小时）\n  交付物：${t.deliverable}\n` + (t.resource_ids||[]).map(id => data.resources.find(r => r.id === id)).filter(Boolean).map(r => `  资料：${r.title} ${r.url}\n`).join('')).join('\n')).join('\n');
  text += '\n\n# 成果与评价记录\n\n' + reviews.map(r=>`## ${reviewTitle(r)} · ${verdictLabel[r.review.verdict] || r.review.verdict}\n${r.reviewed_at} · ${r.applied?'已应用下一步':'未应用调整'}\n\n提交成果：\n${r.submission}\n\n评价：${r.review.summary}\n` + r.review.criteria.map(c=>`- ${c.criterion}（${c.status}）：${c.feedback}\n  证据：${c.evidence || '未提供'}\n`).join('')).join('\n');
  const url = URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'})); const a=document.createElement('a'); a.href=url; a.download=`${data.contest.name}备赛计划.md`; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
});
async function init() {
  $('#generate').disabled = $('#template').disabled = $('#send').disabled = true;
  try {
    data = await api(`/api/bootstrap?contest_id=${encodeURIComponent(contestId)}`);
    const c = data.contest;
    const schedule = data.schedule;
    $('#schedule-summary').textContent = schedule ? `系统建议 ${schedule.start || ProfileStore.today()} 至 ${schedule.end || "所选结束日期"} · 每周 ${schedule.hours} 小时。可修改开始和结束日期。` : '';
    $('#weekly-hours').value = schedule.hours;
    $('#plan-start').value = schedule.start || ProfileStore.today();
    $('#plan-end').value = schedule.end || addDays($('#plan-start').value, (schedule.weeks||1)*7-1);
    $('#plan-start').min = $('#adjust-start').min = ProfileStore.today();
    restoreDateInputs({});
    restore();
    window.GrowthMemory?.refresh?.();
    document.title = `${c.name} · 竞序`;
    if(window.ContestLibrary) $('#contest-library-actions').innerHTML=window.ContestLibrary.controls(contestId);
    $('#contest-title').textContent = c.name;
    $('#side-contest').textContent = c.name;
    $('#contest-short').textContent = c.short;
    $('#side-tags').textContent = c.tags.join(' / ');
    $('#contest-scope').textContent = '';
    if(c.registration_reference) {
      const ref = c.registration_reference;
      const note = document.createElement('p'); note.textContent = `报名参考：${ref.label} · 以当届通知为准`;
      const link = document.createElement('a'); link.href = ref.source; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = '依据与说明 ↗'; link.title = ref.note;
      $('#contest-scope').appendChild(note); $('#contest-scope').appendChild(link);
    }
    $('#contest-tags').innerHTML = [...(c.disciplines||[]).map(d=>d+'类'),...((c.disciplines||[]).length>1?['跨专业']:[]),...c.tags].map(t => `<span>${esc(t)}</span>`).join('');
    $('#contest-source').href = $('#timeline-source').href = c.source;
    $('#pending-note').textContent = c.pending;
    renderChatHistory();
    $('#status').textContent = data.configured ? 'DeepSeek 已配置' : '模板体验 · AI 待配置';
    $('#learning-path').innerHTML = (c.learning_path || []).map(step=>{const resource=data.resources.find(r=>r.id===step.resource_id);return `<li><strong>${esc(step.stage)}</strong><p>${esc(step.action)}</p><p class="quiet">验收：${esc(step.deliverable)}</p>${resource?resourceLink(resource):''}</li>`}).join('');
    $('#resource-list').innerHTML = data.resources.map(r => `<a class="resource-card" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer"><span>${esc(r.type)}${r.type === '精选教程' ? ' · 2026-10-11核对' : ''} ↗</span><h3>${esc(r.title)}</h3><p>${esc(r.note)}</p></a>`).join('');
    $('#timeline').innerHTML = c.timeline.map(t => `<div class="timeline-item"><span class="date-chip">${eventDateLabel(t)}</span><h3>${esc(t.label)}</h3><strong>${t.year} 年 · ${esc(t.date)}</strong><p>${esc(t.detail)}</p><a href="${esc(t.source)}" target="_blank" rel="noopener noreferrer">${esc(t.source_label)} ↗</a></div>`).join('');
    $('#verified-label').textContent = `赛事资料核验：${c.verified_at || '2026-10-09'} · 人工维护`;
    renderPlan();
    renderReviewHistory();
    $('#generate').disabled = $('#template').disabled = $('#send').disabled = false;
  } catch(e) {$('#status').textContent = '服务连接失败'; notify(e.message);}
}

function eventDateLabel(event) {
  const today=ProfileStore.today();
  const end=event.end || event.start;
  const past=end.length===7?end<today.slice(0,7):end<today;
  return (past?'历史节点':'已公布安排')+(event.precision==='month'?' · 月份精度':' · 日期记录');
}
function budgetValid() { return $('#weekly-hours').reportValidity(); }
function clearAdjustment() { clearReviewPreview(); adjustmentPreview=null; $('#adjust-preview').hidden=true; $('#adjust-preview').innerHTML=''; }
['#plan-start','#plan-end'].forEach(selector=>{$(selector).addEventListener('input',clearGeneratedPreview);$(selector).addEventListener('change',()=>{clearGeneratedPreview();if(dateRangeValid('plan',84))save();});});
$('#weekly-hours').addEventListener('input', ()=>{clearAdjustment();clearGeneratedPreview();});
$('#weekly-hours').addEventListener('change', ()=>{if(budgetValid())save();});
['#adjust-start','#adjust-end'].forEach(selector=>{for(const event of ['input','change'])$(selector).addEventListener(event,clearAdjustment);});
$('#preview-adjust').addEventListener('click', async ()=>{
  if(!plan || busy || !budgetValid() || !dateRangeValid('adjust',448)) return;
  const snapshot=JSON.stringify({plan,completed,hours:$('#weekly-hours').value,start:$('#adjust-start').value,end:$('#adjust-end').value});
  busy=true; $('#preview-adjust').disabled=true; $('#generate').disabled=$('#template').disabled=true;
  try {
    adjustmentPreview=await api('/api/plan/adjust',{contest_id:contestId,plan,completed,weekly_hours:Number($('#weekly-hours').value),start:$('#adjust-start').value,end:$('#adjust-end').value});
    if(snapshot!==JSON.stringify({plan,completed,hours:$('#weekly-hours').value,start:$('#adjust-start').value,end:$('#adjust-end').value})) {clearAdjustment();notify('预算或进度已变化，请重新预览。');return;}
    const next=adjustmentPreview.plan;
    $('#adjust-preview').innerHTML=`<h3>调整预览</h3><p>${esc(adjustmentPreview.summary)}</p><p class="quiet">新的训练结束日期：${esc(next.schedule.end)}。应用前原计划保持不变。</p>`+next.weeks.filter(w=>!w.history).map(w=>`<article class="preview-week"><strong>${esc(w.start)} — ${esc(w.end)}</strong><ul>${w.tasks.map(t=>`<li>${esc(t.title)} · ${Math.round(t.hours*100)/100}h<p class="quiet">${esc(t.deliverable)}</p></li>`).join('')}</ul></article>`).join('')+'<div class="form-actions"><button class="primary" id="apply-adjust" type="button">应用调整</button><button class="secondary" id="cancel-adjust" type="button">取消</button></div>';
    $('#adjust-preview').hidden=false;
    $('#apply-adjust').addEventListener('click',()=>{if(!adjustmentPreview)return;const next=adjustmentPreview.plan,history=[...versions,archiveCurrent()];const state={...activeState(),plan:next,completed:adjustmentPreview.completed,planStart:next.schedule.start,planEnd:next.schedule.end,weeklyHours:next.schedule.hours};if(commitState(state,history))notify('调整已应用，已完成任务已保留，原计划已归档。');});
    $('#cancel-adjust').addEventListener('click',clearAdjustment);
  } catch(e) {clearAdjustment();notify(e.message);} finally {busy=false;$('#preview-adjust').disabled=false;$('#generate').disabled=$('#template').disabled=false;}
});

init();

window.addEventListener('storage', e => { if(e.key === 'jingxu-profile-v1') refreshProfile(); });

function renderWeekFocus(){
 const root=$('#week-focus-list'); if(!root||!window.WeekFocus)return;
 const next=window.WeekFocus.tasks(plan,completed,ProfileStore.today());
 root.innerHTML=next.length?next.map(t=>`<article class="focus-task"><div><span class="tag">${esc(t.state)}</span><strong>${esc(t.title)}</strong><p class="quiet">${esc(t.week)} · ${esc(t.hours)} 小时</p><details><summary>完成标准</summary><p>${esc(t.deliverable)}</p></details></div></article>`).join('')+`<button type="button" class="secondary" data-submit-week="${plan.weeks.findIndex(w=>w.tasks.some(t=>t.id===next[0].id))}">提交本周成果 · 整周验收</button>`:(plan.weeks.some(w=>statusForWeek(w)!=='验收通过')?`<p class="quiet">任务已自报完成，还有训练周待验收。请提交成果或查看已有反馈。</p><button type="button" class="secondary" data-submit-week="${plan.weeks.findIndex(w=>statusForWeek(w)!=='验收通过')}">进入整周验收</button>`:'<p class="quiet">全部训练周已验收通过。</p>');
}



function reviewSnapshot() {
  return JSON.stringify({plan,completed,hours:$('#weekly-hours').value,profile:profile(),today:ProfileStore.today()});
}
function clearReviewPreview() {
  reviewPreview=null;
  const button=$('#apply-review'); if(button)button.disabled=true;
}
function weekKey(week) { return 'week:'+week.tasks.map(t=>t.id).join('|'); }
function selectedWeekIndex() { const value=$('#submission-task').value;return /^week-\d+$/.test(value)?Number(value.slice(5)):-1; }
function reviewTitle(record) { return record.week?`W${String(record.week_index+1).padStart(2,'0')} · ${record.week.title}`:record.task?.title||'历史评价'; }
function renderSubmissionTasks() {
  const select=$('#submission-task');if(!select)return;
  const previous=select.value,weeks=plan?.weeks||[];
  // Bring existing task drafts together without deleting the original drafts.
  weeks.forEach(w=>{const key=weekKey(w);if(submissionDrafts[key]===undefined){const parts=w.tasks.filter(t=>submissionDrafts[t.id]).map(t=>t.title+'：\n'+submissionDrafts[t.id]);if(parts.length)submissionDrafts[key]=parts.join('\n\n');}});
  select.innerHTML='<option value="">选择一周</option>'+weeks.map((w,i)=>`<option value="week-${i}">W${String(i+1).padStart(2,'0')} · ${esc(w.title)} · ${esc(statusForWeek(w))}</option>`).join('');
  const firstPending=weeks.findIndex(w=>w.tasks.some(t=>!completed[t.id]));
  select.value=weeks.some((w,i)=>previous===`week-${i}`)?previous:(weeks.length?`week-${Math.max(0,firstPending)}`:'');
  selectSubmission();
}
function selectSubmission() {
  const week=plan?.weeks?.[selectedWeekIndex()];
  $('#submission-standard').textContent=week?'本周整体验收要求：\n'+week.tasks.map((t,i)=>`${i+1}. ${t.title}\n${t.deliverable}`).join('\n\n')+(week.review_focus?`\n\n本周改进重点：${week.review_focus.title}\n${week.review_focus.deliverable}`:''):'请先生成计划，再选择一周。';
  $('#submission-text').value=week?submissionDrafts[weekKey(week)]||'':'';
  $('#submit-review').disabled=!week?.tasks.length||Boolean(reviewController);
}
function openWeekSubmission(index) {
  location.hash='#submission-panel';window.AppNavigation?.sync();
  $('#submission-task').value=`week-${index}`;selectSubmission();
  $('#submission-panel').scrollIntoView({behavior:'smooth'});$('#submission-text').focus();
}
function feedbackHTML(record) {
  const r=record.review;
  return `<h3>${esc(reviewTitle(record))} · ${esc(verdictLabel[r.verdict]||r.verdict)}</h3><p>${esc(r.summary)}</p><p class="quiet">${esc(record.reviewed_at)} · AI 根据提交文本给出的训练反馈，供学习参考。</p>`+
    r.criteria.map(c=>`<article class="review-criterion"><strong>${esc(c.criterion)} · ${esc((r.verdict==='review_incomplete'?{met:'已保留证据',partial:'部分反馈',missing:'待评价'}:{met:'已有证据',partial:'部分满足',missing:'缺少证据'})[c.status]||c.status)}</strong><p>${esc(c.feedback)}</p>${c.evidence?`<blockquote>提交证据：${esc(c.evidence)}</blockquote>`:''}</article>`).join('');
}
function matchingWeek(a,b) {return a&&b&&a.start===b.start&&a.end===b.end&&JSON.stringify(a.tasks)===JSON.stringify(b.tasks);}
function canApplySaved(record) {return !record.applied&&['passed','needs_revision'].includes(record.review.verdict)&&record.week&&plan?.weeks.some(w=>matchingWeek(w,record.week))&&reviews.slice().reverse().find(r=>matchingWeek(r.week,record.week))?.id===record.id;}
function renderReviewHistory() {
  $('#review-history').innerHTML=reviews.length?reviews.slice().reverse().map(r=>`<details class="resource-fold"><summary>${esc(reviewTitle(r))} · ${esc(verdictLabel[r.review.verdict]||r.review.verdict)}${r.applied?' · 已应用':''}</summary>${feedbackHTML(r)}${canApplySaved(r)?`<button type="button" class="secondary" data-apply-saved-review="${esc(r.id)}">应用这条本周反馈</button>`:''}<details><summary>查看提交原文</summary><pre class="submission-original">${esc(r.submission)}</pre></details></details>`).join(''):'<p class="quiet">还没有成果记录。</p>';
  document.querySelectorAll('[data-apply-saved-review]').forEach(button=>button.addEventListener('click',()=>{
    if(busy)return;const record=reviews.find(r=>r.id===button.dataset.applySavedReview);if(!record||!canApplySaved(record)){notify('该周计划或反馈已变化，请重新评价。');return;}
    const nextPlan=JSON.parse(JSON.stringify(plan)),index=nextPlan.weeks.findIndex(w=>matchingWeek(w,record.week)),nextCompleted={...completed};
    if(record.review.verdict==='passed'){for(const task of nextPlan.weeks[index].tasks)nextCompleted[task.id]=true;delete nextPlan.weeks[index].review_focus;}
    else{const focus=record.review.improvement;if(!focus||focus.hours>Number($('#weekly-hours').value)){notify('预算已变化，请重新评价后应用改进建议。');return;}nextPlan.weeks[index].review_focus=focus;}
    const nextReviews=reviews.map(r=>r.id===record.id?{...r,applied:true}:r);
    if(commitState({...activeState(),plan:nextPlan,completed:nextCompleted,reviews:nextReviews},versions))notify('已应用已保存的反馈，无需重复调用AI。');
  }));
}
$('#submission-task').addEventListener('change',selectSubmission);
$('#collect-week-logs').addEventListener('click',()=>{
  const week=plan?.weeks?.[selectedWeekIndex()];if(!week){notify('请先选择一周。');return;}
  try{const logs=window.GrowthMemory?.load()||[],summary=window.WorkspaceData?.weeklyJournal(logs,contestId,week)||'';if(!summary){notify('该周还没有当前竞赛的每日记录。可以先记录进度，或直接粘贴成果。');return;}
    const old=$('#submission-text').value;if(old&&!confirm('将本周记录追加到现有草稿后，原内容保留。是否继续？'))return;
    const next=(old?old+'\n\n':'')+summary;if(next.length>12000){notify('合并后超过12,000字符，请先精简当前草稿。原内容未改变。');return;}
    $('#submission-text').value=next;submissionDrafts[weekKey(week)]=next;save();notify('已汇总本周记录，请补充成果与验证证据后提交。');
  }catch(e){notify(e.message);}
});

$('#submission-text').addEventListener('input',()=>{
  const week=plan?.weeks?.[selectedWeekIndex()];if(week){submissionDrafts[weekKey(week)]=$('#submission-text').value;save();}
});
$('#submission-file').addEventListener('change',async event=>{
  const file=event.target.files?.[0];if(!file)return;
  const taskId=$('#submission-task').value,previous=$('#submission-text').value;
  if(!taskId){notify('请先选择一周。');event.target.value='';return;}
  try {
    if(file.size>64000)throw new Error('文件过大，请粘贴关键片段（最多12,000字符）。');
    const text=await file.text();
    if(text.length>12000||text.includes('\u0000'))throw new Error('请导入不超过12,000字符的文本文件。');
    if(taskId!==$('#submission-task').value||previous!==$('#submission-text').value){notify('周次或草稿已变化，请重新导入。');return;}
    if($('#submission-text').value&&!confirm('导入文件将替换当前成果草稿，是否继续？'))return;
    $('#submission-text').value=text;
    const week=plan?.weeks?.[selectedWeekIndex()];if(week){submissionDrafts[weekKey(week)]=text;save();}
    notify('已导入文本，检查内容后点击“提交并评价”。');
  } catch(e){notify(e.message);} finally {event.target.value='';}
});
$('#cancel-review').addEventListener('click',()=>{reviewCancelled=true;reviewController?.abort();});
$('#submission-form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(busy||reviewController||!plan||!requireProfile()||!budgetValid()||!$('#submission-form').reportValidity())return;
  const weekIndex=selectedWeekIndex(),text=$('#submission-text').value.trim();
  if(!plan.weeks[weekIndex]?.tasks.length||text.length<20){notify('请选择一周，并提交至少20字的本周成果。');return;}
  const snapshot=reviewSnapshot();
  reviewController=new AbortController();reviewCancelled=false;busy=true;clearReviewPreview();
  $('#submit-review').disabled=true;$('#generate').disabled=$('#template').disabled=true;
  $('#cancel-review').hidden=false;$('#review-status').textContent='正在综合检查本周全部成果…';$('#review-feedback').innerHTML='';
  try {
    const result=await api('/api/weeks/review',{contest_id:contestId,profile:profile(),plan,week_index:weekIndex,completed,submission:text,weekly_hours:Number($('#weekly-hours').value)},reviewController);
    reviews=[...reviews,result.record].slice(-50);save();renderReviewHistory();
    $('#review-feedback').innerHTML=feedbackHTML(result.record)+`<p>${esc(result.proposal_note)}</p>`;
    $('#review-status').textContent=result.record.review.verdict==='review_incomplete'?'AI评价未完整生成；成果与部分反馈已保存，点击提交可重新评价。':'评价已保存。计划和完成状态尚未改变。';
    if(result.proposal&&snapshot===reviewSnapshot()) {
      reviewPreview={...result,snapshot};
      const proposal=result.proposal;
      const reviewedWeek=proposal.plan.weeks[proposal.week_index];
      const focus=reviewedWeek?.review_focus;
      $('#review-feedback').innerHTML+=`<div class="week-review-focus"><h3>整周反馈应用预览</h3><p>${esc(proposal.summary)}</p>${focus?`<strong>${esc(focus.title)}</strong><p>${esc(focus.deliverable)}</p><p class="quiet">建议在本周预算内分配 ${esc(focus.hours)} 小时，不额外增加工时。</p>`:''}</div><button id="apply-review" class="primary" type="button">应用本周反馈</button>`;
      $('#apply-review').addEventListener('click',()=>{
        refreshProfile();
        if(!reviewPreview||reviewPreview.snapshot!==reviewSnapshot()){clearReviewPreview();notify('计划、画像或预算已变化，请重新评价后再应用。');return;}
        const next=reviewPreview.proposal,recordId=reviewPreview.record.id;
        plan=next.plan;completed=next.completed;
        if(reviewPreview.record.review.verdict==='passed'){const index=plan.weeks.findIndex(w=>w.tasks.some(t=>!completed[t.id]));if(index>=0)$('#submission-task').value=`week-${index}`;}
        reviews=reviews.map(r=>r.id===recordId?{...r,applied:true}:r);
        clearAdjustment();save();renderPlan();renderReviewHistory();
        $('#review-status').textContent='已应用本周反馈，查看周计划继续训练。';notify('已应用评价，查看本周待办继续训练。');
      });
    } else if(result.proposal) {
      $('#review-status').textContent='评价已保存；计划或预算已变化，本次调整预览已失效，请重新评价。';
    }
  } catch(e){$('#review-status').textContent=reviewCancelled?'评价已停止，成果草稿已保留。':e.message;}
  finally {reviewController=null;busy=false;$('#cancel-review').hidden=true;$('#generate').disabled=$('#template').disabled=false;selectSubmission();}
});

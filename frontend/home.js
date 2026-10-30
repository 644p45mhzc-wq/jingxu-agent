const esc = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $ = s => document.querySelector(s);
const form = $('#profile-form');
let contests = [];
let discipline='全部';
try { const saved=JSON.parse(localStorage.getItem('jingxu-discipline-v1')||'null'); const p=ProfileStore.load(); discipline=saved&&saved.major===p?.major?saved.filter:DisciplineFilters.infer(p); } catch { discipline=DisciplineFilters.infer(null); }
if(!['全部','文','理','医','工','跨专业'].includes(discipline))discipline='全部';
function filterControls(){document.querySelectorAll('[data-discipline]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.discipline===discipline));}); $('#discipline-note').textContent=`${discipline==='全部'?'全部方向':discipline==='跨专业'?'跨专业赛事':discipline+'类相关赛事'} · 可随时切换；相关方向不等于参赛资格。`;}
document.querySelectorAll('[data-discipline]').forEach(b=>b.addEventListener('click',()=>{discipline=b.dataset.discipline;try{localStorage.setItem('jingxu-discipline-v1',JSON.stringify({filter:discipline,major:ProfileStore.load()?.major}));}catch{} render();}));

function render() {
  filterControls();
  const query=$('#contest-search').value.trim().toLowerCase();
  const visible=contests.filter(c=>DisciplineFilters.matches(c,discipline)&&(!$('#favorite-only').checked||window.ContestLibrary?.isFavorite(c.id))&&(!query||[c.name,c.short,...c.tags,...(c.disciplines||[])].join(' ').toLowerCase().includes(query)));
  $('#contest-count').textContent=`${visible.length} / ${contests.length} 项赛事`;
  $('#all-contest-list').innerHTML=visible.map(c=>`<article class="recommend-card"><h3>${esc(c.name)}</h3><p>${esc(c.fit_reason||c.description||'')}</p><a href="/competitions/${encodeURIComponent(c.id)}">查看赛事 →</a>${window.ContestLibrary?.controls(c.id)||''}</article>`).join('')||'<p class="quiet">没有匹配的赛事，试试其他关键词或切换“全部”。</p>';

  const today = ProfileStore.today();
  const range = RegistrationTimeline.range(today);
  $('#date-range').textContent = `${range.start.replaceAll('-','.')} — ${range.end.replaceAll('-','.')}`;
  const entries = RegistrationTimeline.entries(contests.filter(c=>DisciplineFilters.matches(c,discipline) && (!$('#favorite-only').checked || window.ContestLibrary?.isFavorite(c.id))), today);
  $('#registration-line').innerHTML = entries.map(({contest:c,date,year,label}) => `<li class="registration-stop"><time datetime="${date}" title="${esc(c.registration_reference.note)}">${year}年 · ${esc(label)}</time><a href="/competitions/${encodeURIComponent(c.id)}"><h3>${esc(c.name)}</h3></a><div class="direction-tags">${(c.disciplines||[]).map(d=>`<span>${esc(d)}</span>`).join('')}${(c.disciplines||[]).length>1?'<span>跨专业</span>':''}</div><p class="fit-reason">${esc(c.fit_reason||'')}</p>${window.ContestLibrary?.controls(c.id)||''}</li>`).join('');
  $('#calendar-state').textContent = entries.length ? '' : '当前方向未来 12 个月暂无参考节点，试试“全部”或“跨专业”。';
  $('#calendar-state').hidden = entries.length > 0;
}
try { const p = ProfileStore.load(); if (p) for (const [k,v] of Object.entries(p)) if(form.elements[k]) form.elements[k].value = v; }
catch { $('#profile-status').textContent = '暂时无法读取保存的画像，请重新填写。'; }
form.addEventListener('submit', e => {
  e.preventDefault(); if(!form.reportValidity()) return;
  const p = Object.fromEntries(new FormData(form));
  try { ProfileStore.save(p); $('#profile-status').textContent = '画像已保存，适配推荐已更新。'; discipline=DisciplineFilters.infer(p); try{localStorage.removeItem('jingxu-discipline-v1');}catch{} render(); renderRecommendations(); }
  catch(e) { $('#profile-status').textContent = '保存失败：请检查填写内容或浏览器存储权限。'; }
});
async function init() {
  try {
    const response = await fetch('/api/contests'); if(!response.ok) throw new Error();
    contests = (await response.json()).contests;
    window.ContestLibrary?.setCatalog(contests);
    render();
    renderRecommendations();
  } catch { $('#calendar-state').textContent = '无法加载竞赛信息，请稍后刷新。'; }
}

const recommendationRules = {
  'cumcm': {keywords:['数学','高数','线代','概率','统计','建模','数据','python','matlab','物理','光电'], focus:'数学与数据分析', gap:'补齐模型验证、代码复现和建模论文写作。'},
  'electronics': {keywords:['电子','电路','光电','通信','自动化','嵌入式','单片机','stm32','硬件','信号','物理'],focus:'硬件与工程实践',gap:'确认实验设备与团队条件，从模块测试和系统联调开始。'},
  'lanqiao': {keywords:['计算机','软件','编程','算法','python','c++','java','程序','数据结构'],focus:'程序设计与算法',gap:'选定科目，补齐数据结构并进行限时真题训练。'},
  'computer-design': {keywords:['计算机','软件','设计','编程','前端','交互','数字媒体','人工智能','python','产品'],focus:'软件与作品设计',gap:'先选赛项，完成可演示作品和测试记录。'},
  'challenge-academic': {keywords:['科研','研究','实验','物理','光电','论文','调查','学术','创新','数学'],focus:'研究与科技创新',gap:'形成明确研究问题，补齐文献、实验记录与成果证据。'},
  'innovation': {keywords:['创新','创业','项目','产品','调研','设计','市场','原型','光电','技术'],focus:'创新项目与产品验证',gap:'从真实需求出发，积累用户反馈和原型验证证据。'},
  'challenge-business': {keywords:['创业','商业','管理','经济','财务','营销','市场','调研','计划书'],focus:'创业与商业分析',gap:'补齐市场验证、成本收入假设及实践证据。'}
};
function renderRecommendations() {
  const root=$('#recommend-list');let profile;
  try {profile=ProfileStore.load();} catch {profile=null;}
  if(!profile) {root.innerHTML='';$('#recommend-note').textContent='保存专业、年级和能力后，即可查看适配建议。';return;}
  if(!contests.length) {root.innerHTML='';$('#recommend-note').textContent='竞赛资料尚未加载，请刷新后再试。';return;}
  const major=String(profile.major||'').toLowerCase(),skills=String(profile.skills||'').toLowerCase();
  const ranked=contests.map(c=>{
    const rule=recommendationRules[c.id] || DisciplineFilters.rule(c);const matched=rule.keywords.filter(k=>major.includes(k)||skills.includes(k));
    const score=matched.reduce((sum,k)=>sum+(major.includes(k)?3:0)+(skills.includes(k)?2:0),0);
    return {c,rule,matched,score};
  }).sort((a,b)=>b.score-a.score);
  const selected=ranked.filter(r=>r.score>0).slice(0,5);
  $('#recommend-note').textContent=`${profile.grade} · ${profile.major}：${selected.length?'以下方向与你的画像有相关基础。':'暂未匹配到明确方向，以下竞赛可作为探索起点。'}`;
  const stage=['大一','大二'].includes(profile.grade)?'建议先完成一个基础训练项目，再逐步挑战正式作品。':'建议结合已有课程或项目成果，明确作品与答辩准备。';
  root.innerHTML=(selected.length?selected:ranked.slice(0,3)).map(({c,rule,matched,score},i)=>`<article class="recommend-card"><span class="tag">${score?`相关方向 ${i+1}`:'探索方向'} · ${esc(rule.focus)}</span><h3>${esc(c.name)}</h3><p>${score?`画像中的「${esc(matched.slice(0,3).join('、'))}」与该竞赛方向相关。`:'可从体验基础任务开始，判断自己是否感兴趣。'}</p><p class="quiet">${esc(rule.gap)} ${esc(stage)}</p><a href="/competitions/${encodeURIComponent(c.id)}">查看资料与训练计划 ↗</a>${window.ContestLibrary?.controls(c.id)||''}</article>`).join('');
}
window.addEventListener('storage', e=>{if(e.key==='jingxu-profile-v1'){discipline=DisciplineFilters.infer(ProfileStore.load());render();renderRecommendations();}});

init().finally(() => requestAnimationFrame(syncSectionNavigation));
document.addEventListener('visibilitychange', () => {if(!document.hidden && contests.length) {render();renderRecommendations();}});

function syncSectionNavigation(){window.AppNavigation?.sync();}
$('#favorite-only').addEventListener('change',render);
window.addEventListener('contest-library-change',render);

$('#contest-search').addEventListener('input',render);

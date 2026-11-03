(function(root){
 const sidebar=document.querySelector('#app-sidebar');if(!sidebar)return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const detail=location.pathname.startsWith('/competitions/'),current=detail?decodeURIComponent(location.pathname.split('/').filter(Boolean).pop()):null;
 let catalog=[],coach=false,knownJoined=0;
 function homeView(hash){if(['#plan-calendar'].includes(hash))return 'calendar';if(hash==='#participating')return 'participating';if(hash==='#profile')return 'profile';if(hash==='#growth-memory')return 'daily';if(hash==='#growth-summary')return 'summary';return 'discover';}
 function detailView(hash){if(hash==='#plan-calendar')return 'calendar';if(hash==='#submission-panel')return 'review';if(['#resources','#timeline'].includes(hash))return 'resources';if(hash==='#growth-memory')return 'daily';return 'plan';}
 function renderSidebar(){
  const active=detail?'preparation':['calendar','participating'].includes(homeView(location.hash))?'preparation':['profile','daily','summary'].includes(homeView(location.hash))?'growth':'discover';
  const joined=catalog.filter(c=>root.ContestLibrary?.isParticipating(c.id));
  const newlyJoined=joined.length>knownJoined;knownJoined=joined.length;
  sidebar.innerHTML=`<a class="brand" href="/">竞<span>序</span><small>备赛，有迹可循</small></a><nav class="app-nav" aria-label="主导航"><a class="app-nav-main ${active==='discover'?'active':''}" href="/" ${active==='discover'?'aria-current="page"':''}>发现适合你的竞赛</a><details class="app-nav-group" ${active==='preparation'||newlyJoined?'open':''}><summary class="${active==='preparation'?'active':''}">备赛</summary><div class="app-nav-sub"><a href="/#plan-calendar" ${!detail&&homeView(location.hash)==='calendar'?'class="active" aria-current="page"':''}>总日历</a><a href="/#participating" ${!detail&&homeView(location.hash)==='participating'?'class="active" aria-current="page"':''}>正在参加比赛</a><div class="joined-contests">${joined.length?joined.map(c=>`<a href="/competitions/${encodeURIComponent(c.id)}" class="${c.id===current?'active':''}" ${c.id===current?'aria-current="page"':''}>${esc(c.short)}</a>`).join(''):'<span class="quiet nav-empty">选择参加比赛后显示子目录</span>'}</div></div></details><details class="app-nav-group" ${active==='growth'?'open':''}><summary class="${active==='growth'?'active':''}">成长</summary><div class="app-nav-sub">${[['profile','我的画像'],['growth-memory','每日记录'],['growth-summary','成长总结']].map(([id,label])=>`<a href="/#${id}" ${!detail&&location.hash===`#${id}`?'class="active" aria-current="page"':''}>${label}</a>`).join('')}</div></details></nav><p class="sidebar-caption">从选择比赛，到记录成长。</p>`;
 }
 function setVisible(id,visible){const el=document.getElementById(id);if(el)el.hidden=!visible;}
 function sync(){
  renderSidebar();
  if(detail){
   const view=detailView(location.hash);
   for(const [id,views] of Object.entries({'week-focus':['plan'],'plan':['plan'],'plan-calendar':['calendar'],'submission-panel':['review'],'growth-memory':['daily'],'resources':['resources'],'contest-scope':['resources'],'official-schedule':['resources']}))setVisible(id,views.includes(view));
   document.querySelectorAll('[data-workspace-tab]').forEach(link=>{const active=link.dataset.workspaceTab===view;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
   const panel=document.querySelector('.chat-panel');if(panel)panel.hidden=!coach;
   const toggle=document.querySelector('#coach-toggle');if(toggle)toggle.setAttribute('aria-expanded',String(coach));
  }else{
   const view=homeView(location.hash);
   const discovery=['#annual-timeline','#recommendations','#my-contests'].includes(location.hash)?location.hash.slice(1):'all-contests';
   setVisible('discovery-tabs',view==='discover');setVisible('discovery-filters',view==='discover'&&['all-contests','annual-timeline'].includes(discovery));
   for(const [id,views] of Object.entries({'all-contests':['discover'],'annual-timeline':['discover'],'recommendations':['discover'],'my-contests':['discover'],'plan-calendar':['calendar'],'participating':['participating'],'profile':['profile'],'growth-memory':['daily'],'growth-summary':['summary']}))setVisible(id,views.includes(view)&&(!['all-contests','annual-timeline','recommendations','my-contests'].includes(id)||id===discovery));
   document.querySelectorAll('[data-discovery-tab]').forEach(link=>link.classList.toggle('active',link.dataset.discoveryTab===discovery));
   const headings={discover:['发现适合你的竞赛','浏览赛事、查看推荐，选择想参加的比赛。'],calendar:['总日历','查看正在参加比赛的训练安排。'],participating:['正在参加比赛','每个比赛都有独立的计划与验收记录。'],profile:['我的画像','记录基础能力，为所有竞赛提供参考。'],daily:['每日记录','记录实际投入、成果和卡点。'],summary:['成长总结','回看跨竞赛积累，了解下一阶段的训练依据。']};
   const title=document.querySelector('#page-title'),description=document.querySelector('#page-description');if(title)title.textContent=headings[view][0];if(description)description.textContent=headings[view][1];
  }
 }
 root.AppNavigation={sync,homeView,detailView};
 root.addEventListener('hashchange',()=>{sync();root.scrollTo?.({top:0,behavior:'smooth'});});
 root.addEventListener('contest-library-change',renderSidebar);
 document.querySelector('#coach-toggle')?.addEventListener('click',()=>{coach=!coach;sync();});
 document.querySelector('#coach-close')?.addEventListener('click',()=>{coach=false;sync();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&coach){coach=false;sync();document.querySelector('#coach-toggle')?.focus();}});
 sync();
 fetch('/api/contests').then(response=>{if(!response.ok)throw new Error('无法加载竞赛');return response.json();}).then(data=>{catalog=data.contests;root.ContestLibrary?.setCatalog(catalog);renderSidebar();}).catch(()=>{const note=document.querySelector('.sidebar-caption');if(note)note.textContent='竞赛列表暂时无法加载，请刷新重试。';});
})(window);

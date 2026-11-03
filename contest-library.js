(() => {
 const KEY='jingxu-library-v1';let catalog=[],favorites=[],participating=[],archived=[];
 const clean=items=>Array.isArray(items)?[...new Set(items.filter(x=>typeof x==='string'))]:[];
 function load(){const saved=JSON.parse(localStorage.getItem(KEY)||'{}');favorites=clean(saved.favorites);participating=clean(saved.participating);archived=clean(saved.archived).filter(id=>!participating.includes(id));}
 try{load();}catch{}
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const status=text=>{const el=document.querySelector('#library-status');if(el)el.textContent=text;};
 function save(){try{const old=JSON.parse(localStorage.getItem(KEY)||'{}');localStorage.setItem(KEY,JSON.stringify({...old,favorites,participating,archived}));return true;}catch{status('无法保存，请检查浏览器存储权限。');return false;}}
 function controls(id){return `<div class="contest-actions"><button type="button" class="participate-button" data-participate="${esc(id)}" aria-pressed="${participating.includes(id)}">${participating.includes(id)?'已参加':archived.includes(id)?'重新参加':'参加比赛'}</button><button type="button" data-favorite="${esc(id)}" aria-pressed="${favorites.includes(id)}">${favorites.includes(id)?'★ 已收藏':'☆ 收藏'}</button></div>`;}
 function render(){
  document.querySelectorAll('[data-favorite]').forEach(b=>{b.textContent=favorites.includes(b.dataset.favorite)?'★ 已收藏':'☆ 收藏';b.setAttribute('aria-pressed',String(favorites.includes(b.dataset.favorite)));});
  document.querySelectorAll('[data-participate]').forEach(b=>{b.textContent=participating.includes(b.dataset.participate)?'已参加':archived.includes(b.dataset.participate)?'重新参加':'参加比赛';b.setAttribute('aria-pressed',String(participating.includes(b.dataset.participate)));});
  const list=document.querySelector('#favorite-list');
  if(list)list.innerHTML=catalog.filter(c=>favorites.includes(c.id)).map(c=>`<article class="favorite-card"><a href="/competitions/${encodeURIComponent(c.id)}">${esc(c.short)}</a><p class="quiet">${esc(c.fit_reason||'')}</p>${controls(c.id)}</article>`).join('')||'<p class="quiet">收藏感兴趣的赛事，稍后再决定是否参加。</p>';
  const active=document.querySelector('#participating-list');
  if(active)active.innerHTML=catalog.filter(c=>participating.includes(c.id)).map(c=>`<article class="favorite-card"><h3>${esc(c.short)}</h3><p class="quiet">${esc(c.fit_reason||'')}</p><a href="/competitions/${encodeURIComponent(c.id)}">进入备赛 →</a><button class="text-button" type="button" data-archive="${esc(c.id)}">结束比赛并归档</button><button class="text-button" type="button" data-participate="${esc(c.id)}">移出正在参加列表</button></article>`).join('')||'<p class="quiet">还没有正在参加的比赛。到“竞赛”中点击“参加比赛”，它就会出现在这里和左侧子目录中。已有计划与成果仍保留。</p>';
  const archiveList=document.querySelector('#archived-list');
  if(archiveList)archiveList.innerHTML=catalog.filter(c=>archived.includes(c.id)).map(c=>`<article class="favorite-card"><h3>${esc(c.short)}</h3><p class="quiet">已结束 / 已归档 · 历史计划和成果保留</p><a href="/competitions/${encodeURIComponent(c.id)}">回看成果 →</a><button type="button" class="text-button" data-participate="${esc(c.id)}">重新参加</button></article>`).join('')||'<p class="quiet">还没有归档的比赛。</p>';
 }
 document.addEventListener('click',event=>{
  const favorite=event.target.closest('button[data-favorite]'),join=event.target.closest('button[data-participate]'),archive=event.target.closest('button[data-archive]');
  if(!favorite&&!join&&!archive)return;
  const oldFavorites=[...favorites],oldParticipating=[...participating],oldArchived=[...archived];
  if(favorite){const id=favorite.dataset.favorite;favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];}
  if(join){const id=join.dataset.participate;if(participating.includes(id)){if(!confirm('移出正在参加列表？已有计划、成果与成长记录会保留。'))return;participating=participating.filter(x=>x!==id);}else {participating.push(id);archived=archived.filter(x=>x!==id);}}
  if(archive){const id=archive.dataset.archive;participating=participating.filter(x=>x!==id);archived=[...new Set([...archived,id])];}
  if(!save()){favorites=oldFavorites;participating=oldParticipating;archived=oldArchived;return;}
  status(join||archive?'参赛列表已更新，已有训练记录保留。':'收藏已更新。');render();window.dispatchEvent(new Event('contest-library-change'));
 });
 window.addEventListener('storage',event=>{if(event.key===KEY||event.key===null){try{load();render();window.dispatchEvent(new Event('contest-library-change'));}catch{status('赛事列表无法读取，请检查浏览器存储。');}}});
 window.ContestLibrary={controls,isFavorite:id=>favorites.includes(id),isParticipating:id=>participating.includes(id),participating:()=>[...participating],archived:()=>[...archived],setCatalog(items){catalog=items;render();},render};
 render();
})();

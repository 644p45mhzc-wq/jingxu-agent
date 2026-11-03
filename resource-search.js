(() => {
 const form=document.querySelector('#resource-search-form'); if(!form)return;
 const query=document.querySelector('#resource-query'),kind=document.querySelector('#resource-kind'),button=document.querySelector('#resource-search-button'),status=document.querySelector('#resource-search-status'),results=document.querySelector('#resource-search-results');
 const safeUrl=url=>{try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)&&!u.username?u.href:null;}catch{return null;}};
 function externalLink(url,label){const a=document.createElement('a');a.href=url;a.textContent=label;a.target='_blank';a.rel='noopener noreferrer';return a;}
 form.addEventListener('submit',async e=>{
  e.preventDefault(); if(!form.reportValidity())return;
  const keyword=query.value.trim(); if(keyword.length<2)return;
  button.disabled=true;status.textContent='正在搜索…';results.replaceChildren();
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),22000);
  const suffix={all:'',course:' 课程 tutorial',tutorial:' 教程 documentation',paper:' 论文 research paper'}[kind.value];
  const fallback='https://www.bing.com/search?q='+encodeURIComponent(keyword+suffix);
  try{
   const params=new URLSearchParams({q:keyword,kind:kind.value,contest_id:location.pathname.split('/').filter(Boolean).pop()});
   const response=await fetch('/api/resources/search?'+params,{signal:controller.signal});
   if(!response.ok)throw new Error(response.status===404?'请重启后端以启用搜索。':'搜索暂时不可用，请稍后重试。');
   const payload=await response.json();let count=0;
   for(const item of payload.results||[]){const url=safeUrl(item.url);if(!url)continue;const card=document.createElement('article');card.className='resource-card';const a=externalLink(url,item.title);const p=document.createElement('p');p.textContent=item.description;const source=document.createElement('small');source.textContent=item.source;card.append(a,p,source);results.append(card);count++;}
   status.textContent=count?`找到 ${count} 条 · Bing · ${new Date(payload.searched_at).toLocaleTimeString()} · 未核验`:(payload.note||'暂无结果，换一个具体关键词试试。');
  }catch(error){status.textContent=error.name==='AbortError'?'搜索超时，请重试。':error.message;}
  finally{clearTimeout(timer);button.disabled=false;results.append(externalLink(fallback,'打开外部搜索 ↗'));}
 });
})();

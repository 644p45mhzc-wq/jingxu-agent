(function(root){
 function tasks(plan,completed,today,limit=3){
  const pending=(plan?.weeks||[]).flatMap(w=>(w.tasks||[]).filter(t=>!completed[t.id]).map(t=>({...t,start:w.start,end:w.end,week:w.title})));
  const due=pending.filter(t=>t.start<=today).sort((a,b)=>a.end.localeCompare(b.end));
  return (due.length?due:pending.sort((a,b)=>a.start.localeCompare(b.start))).slice(0,limit).map(t=>({...t,state:t.end<today?'逾期':t.start>today?'接下来':'本周'}));
 }
 const api={tasks}; if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.WeekFocus=api;
})(typeof window!=='undefined'?window:this);

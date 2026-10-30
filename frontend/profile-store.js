// One personal profile for all competitions; plans are stored independently.
window.ProfileStore = (() => {
  const key = 'jingxu-profile-v1';
  const ids = ['cumcm','innovation','challenge-academic','challenge-business','lanqiao','electronics','computer-design'];
  function today() {
    const parts = new Intl.DateTimeFormat('en-US', {timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const p = Object.fromEntries(parts.map(v => [v.type,v.value]));
    return `${p.year}-${p.month}-${p.day}`;
  }
  function valid(p) {
    return p && typeof p === 'object' && ['major','grade','skills'].every(k => typeof p[k] === 'string' && p[k].trim());
  }
  function clean(p) {return {major:p.major.trim(), grade:p.grade.trim(), skills:p.skills.trim()};}
  function load() {
    let current; try {current = JSON.parse(localStorage.getItem(key) || 'null');} catch {current=null;}
    if (valid(current)) return clean(current);
    for (const oldKey of [...ids.map(id => `jingxu-v2-${id}`), 'jingxu-v1']) {
      let old; try { old = JSON.parse(localStorage.getItem(oldKey) || 'null'); } catch { continue; }
      if (valid(old?.profile)) { save(old.profile); return clean(old.profile); }
    }
    return null;
  }
  function save(p) { if (!valid(p)) throw new Error('请完整填写专业、年级和能力。'); localStorage.setItem(key, JSON.stringify(clean(p))); }
  return {load, save, today};
})();

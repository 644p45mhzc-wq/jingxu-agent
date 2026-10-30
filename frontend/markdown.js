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

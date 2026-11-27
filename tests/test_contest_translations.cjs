const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ids = ['cumcm','innovation','challenge-academic','challenge-business','lanqiao','electronics','computer-design','fltrp','advertising','mathematics','physics-experiment','mechanical-design','biomedical-design','life-science','medical-innovation'];
const context = {window:{}};
vm.runInNewContext(fs.readFileSync('frontend/contest-translations.js','utf8'),context);
const translations=context.window.ContestTranslations;
assert.equal(Object.keys(translations.byId).length,15);
for (const id of ids) {
  const entry=translations.byId[id];
  assert(entry,`Missing English name for ${id}`);
  assert(entry.source.startsWith('https://'),`Missing naming reference: ${id}`);
  assert.equal(translations.translate(entry.zhName),entry.name);
  assert.equal(translations.translate(entry.zhShort),entry.short);
  assert.equal(translations.translate(entry.zhReason),entry.reason);
  assert(!/[\u3400-\u9fff]/.test(entry.name+entry.short+entry.reason),`Chinese remained: ${id}`);
  assert(translations.searchText(id).includes(entry.name));
}
assert.equal(translations.translate('未收录赛事'),undefined);
console.log('All 15 competition names, short labels, descriptions and search text have English equivalents.');

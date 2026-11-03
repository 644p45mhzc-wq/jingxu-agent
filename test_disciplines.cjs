const assert=require('node:assert/strict');
const filters=require('../frontend/disciplines.js');
for(const [major,expected] of [['临床医学','医'],['护理学','医'],['计算机科学与技术','工'],['光电信息科学与工程','工'],['法学','文'],['英语','文'],['数学与应用数学','理'],['生物医学工程','医'],['未知专业','全部']])assert.equal(filters.infer({major}),expected,major);
const cross={disciplines:['医','工']},single={disciplines:['文']};
assert(filters.matches(cross,'医'));assert(filters.matches(cross,'工'));assert(filters.matches(cross,'跨专业'));assert(!filters.matches(single,'跨专业'));assert(!filters.matches(single,'理'));assert(filters.matches(single,'全部'));assert.equal(filters.infer(null),'全部');
console.log('Profile defaults, category filters, and interdisciplinary matching passed.');

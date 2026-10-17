const assert=require('node:assert/strict');
const fs=require('node:fs');
const Core=require('../src/core.js');
const Q=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../dist/questions.json'),'utf8'));
const state=Core.fresh(), today=new Date('2026-10-17T10:00:00Z');
const rng=()=>0.317;
for(const n of [5,10,20,'all']){
  const selected=Core.select(Q,state,{count:n},rng),size=n==='all'?600:n;
  assert.equal(selected.length,size);
  assert.equal(new Set(selected.map(q=>q.id)).size,size);
  assert.equal(selected.filter(q=>q.category==='言語').length,size*.4);
}
for(const topic of new Set(Q.map(q=>q.topic))){
  const selected=Core.select(Q,state,{count:10,topic},rng);
  assert.equal(selected.length,10);assert(selected.every(q=>q.topic===topic));
  assert.equal(Core.select(Q,state,{count:'all',topic},rng).length,40);
}
assert.equal(Core.select(Q,state,{mode:'review'}).length,0);
Core.record(state,'q001',false,false,today);
Core.record(state,'q121',false,true,new Date('2026-10-16T10:00:00Z'));
assert.equal(Core.reviewPool(Q,state).length,2);
assert.deepEqual(Core.select(Q,state,{mode:'review',count:5},rng).map(q=>q.id),['q121','q001']);
assert(Core.select(Q,state,{count:5},rng).some(q=>Core.needsReview(state.records[q.id])));
assert(Core.select(Q,state,{count:10},rng).some(q=>q.id==='q001'));
Core.record(state,'q001',true,true,today);
assert(Core.needsReview(state.records.q001));
Core.record(state,'q001',true,false,today);
assert(!Core.needsReview(state.records.q001));
assert.deepEqual(Core.totals(state),{attempts:4,correct:2,seen:2,review:1});
assert.equal(state.days[Core.dayKey(today)].attempts,3);
assert.deepEqual(Core.validate(JSON.parse(JSON.stringify(state)),Q),state);
for(const bad of [null,[],{}, {version:2,records:{},days:{}}, {...state,records:{bad:state.records.q001}}, {...state,days:{}}, {...state,days:{'2026-02-30':{attempts:4,correct:2}}}])assert.throws(()=>Core.validate(bad,Q));
const evil=JSON.parse(JSON.stringify(state));evil.records.q001.correct=999;assert.throws(()=>Core.validate(evil,Q));
const seen=Core.fresh();for(const q of Q.slice(0,60))Core.record(seen,q.id,true,false,today);
assert(Core.select(Q,seen,{count:20},rng).every(q=>!seen.records[q.id]));
// Exhaust a question bank, then verify that subsequent sessions still work.
const full=Core.fresh();for(const q of Q)Core.record(full,q.id,true,false,today);
assert.equal(Core.select(Q,full,{count:20},rng).length,20);
assert.equal(Core.select(Q,full,{count:'all'},rng).length,600);
// Daily statistics use the host's local day, including at a UTC boundary.
assert.equal(Core.dayKey(new Date(2026,0,2,0,1)),'2026-01-02');
assert.equal(Core.dayKey(new Date(2026,11,31,23,59)),'2026-12-31');
console.log('Core: selection, review, totals, validation and local dates passed.');

const legacy=Core.fresh();for(const q of Q.slice(0,300))Core.record(legacy,q.id,Number(q.id.slice(1))%2===0,false,today);
assert.deepEqual(Core.validate(JSON.parse(JSON.stringify(legacy)),Q),legacy);
assert.equal(Core.totals(legacy).seen,300);
console.log('Legacy import: records for all 300 original IDs remain valid in the 600-question bank.');

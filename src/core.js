'use strict';
const Core = (() => {
  const VERSION = 1;
  const fresh = () => ({version: VERSION, records: {}, days: {}});
  const dayKey = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const shuffle = (items, random = Math.random) => {
    const out = [...items];
    for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(random()*(i+1)); [out[i],out[j]]=[out[j],out[i]]; }
    return out;
  };
  const needsReview = r => !!r && (!r.lastCorrect || r.unsure);
  const reviewPool = (questions, state) => questions.filter(q => needsReview(state.records[q.id]));
  function varied(pool, count, records, random) {
    const out=[], rest=shuffle(pool,random).sort((a,b)=>(records[a.id]?.attempts||0)-(records[b.id]?.attempts||0));
    const used=new Set();
    while(rest.length && out.length<count) {
      let i=rest.findIndex(q=>!used.has(q.topic));
      if(i<0) { used.clear(); i=0; }
      const [q]=rest.splice(i,1); used.add(q.topic); out.push(q);
    }
    return out;
  }
  function select(questions, state, {count=10, topic=null, mode='normal', ids=null}={}, random=Math.random) {
    let pool=topic ? questions.filter(q=>q.topic===topic) : [...questions];
    if(ids) { const set=new Set(ids); pool=pool.filter(q=>set.has(q.id)); }
    const n=count==='all'?pool.length:Math.min(Number(count),pool.length);
    if(mode==='review') return shuffle(reviewPool(pool,state),random).sort((a,b)=>(state.records[a.id].lastAt.localeCompare(state.records[b.id].lastAt))).slice(0,n);
    function choose(p,k) {
      const review=shuffle(reviewPool(p,state),random).sort((a,b)=>state.records[a.id].lastAt.localeCompare(state.records[b.id].lastAt));
      const chosen=review.slice(0,Math.min(Math.max(k>=3?1:0,Math.floor(k*.2)),review.length));
      const picked=new Set(chosen.map(q=>q.id));
      const unseen=p.filter(q=>!state.records[q.id]);
      chosen.push(...varied(unseen,k-chosen.length,state.records,random));
      chosen.forEach(q=>picked.add(q.id));
      chosen.push(...varied(p.filter(q=>!picked.has(q.id)),k-chosen.length,state.records,random));
      return chosen;
    }
    if(topic || ids) return shuffle(choose(pool,n),random);
    const verbal=pool.filter(q=>q.category==='言語'), math=pool.filter(q=>q.category==='非言語');
    const vn=Math.min(Math.round(n*.4),verbal.length), mn=Math.min(n-vn,math.length);
    const result=[...choose(verbal,vn),...choose(math,mn)];
    if(result.length<n) { const picked=new Set(result.map(q=>q.id)); result.push(...choose(pool.filter(q=>!picked.has(q.id)),n-result.length)); }
    return shuffle(result,random);
  }
  function record(state, id, correct, unsure, date=new Date()) {
    const old=state.records[id]||{attempts:0,correct:0};
    state.records[id]={attempts:old.attempts+1,correct:old.correct+(correct?1:0),lastCorrect:correct,unsure:!!unsure,lastAt:date.toISOString()};
    const key=dayKey(date), day=state.days[key]||{attempts:0,correct:0};
    state.days[key]={attempts:day.attempts+1,correct:day.correct+(correct?1:0)};
  }
  function totals(state, questions=null) {
    const keys=questions?questions.map(q=>q.id):Object.keys(state.records);
    return keys.reduce((a,id)=>{const r=state.records[id];if(r){a.attempts+=r.attempts;a.correct+=r.correct;a.seen++;if(needsReview(r))a.review++;}return a;},{attempts:0,correct:0,seen:0,review:0});
  }
  function validate(input, questions) {
    const isObject=x=>x!==null && typeof x==='object' && !Array.isArray(x);
    if(!isObject(input)||input.version!==VERSION||!isObject(input.records)||!isObject(input.days)) throw new Error('対応していない記録ファイルです。');
    const clean=fresh(), known=new Set(questions.map(q=>q.id));
    const int=n=>Number.isSafeInteger(n)&&n>=0&&n<=1e9;
    for(const [id,r] of Object.entries(input.records)) {
      if(!known.has(id)||!isObject(r)||!int(r.attempts)||r.attempts<1||!int(r.correct)||r.correct>r.attempts||typeof r.lastCorrect!=='boolean'||typeof r.unsure!=='boolean'||typeof r.lastAt!=='string'||!Number.isFinite(Date.parse(r.lastAt))) throw new Error('問題ごとの記録に不正な値があります。');
      if((r.lastCorrect && r.correct===0)||(!r.lastCorrect && r.correct===r.attempts)) throw new Error('正誤の記録が一致しません。');
      clean.records[id]={attempts:r.attempts,correct:r.correct,lastCorrect:r.lastCorrect,unsure:r.unsure,lastAt:r.lastAt};
    }
    for(const [day,r] of Object.entries(input.days)) {
      const d=new Date(day+'T12:00:00');
      if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||!Number.isFinite(d.getTime())||dayKey(d)!==day||!isObject(r)||!int(r.attempts)||r.attempts<1||!int(r.correct)||r.correct>r.attempts) throw new Error('日ごとの記録に不正な値があります。');
      clean.days[day]={attempts:r.attempts,correct:r.correct};
    }
    const total=totals(clean), days=Object.values(clean.days).reduce((a,r)=>({attempts:a.attempts+r.attempts,correct:a.correct+r.correct}),{attempts:0,correct:0});
    if(total.attempts!==days.attempts||total.correct!==days.correct) throw new Error('問題別と日別の合計が一致しません。');
    return clean;
  }
  return {fresh,dayKey,shuffle,needsReview,reviewPool,select,record,totals,validate};
})();
if(typeof module!=='undefined' && module.exports) module.exports=Core;

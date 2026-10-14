import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DATA} from '../content.js';
import {Lesson,KEYS,CATEGORIES,RATIO_KEYS,calculateRatios,resultsFromSubmissions,reflectionFlags,
  validateSnapshot,newState,encodeState,decodeState,encodeDraft,decodeDraft,decodeNumbers,encodeNumbers,
  validateDraft,ratioCorrect,pyFixed,currency,parseNumber,canonicalJSON} from '../engine.js';
const oracle=JSON.parse(readFileSync(new URL('./python-oracles.json',import.meta.url)));
const legacy=JSON.parse(readFileSync(new URL('./legacy-links.json',import.meta.url)));
const python=(code,args=[])=>{
  const result=spawnSync(process.env.PYTHON??'python3',['-c',code,...args],{cwd:new URL('../../',import.meta.url),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);return JSON.parse(result.stdout);
};
const at=stage=>new Lesson({...legacy[stage].payload,o:[[...legacy[stage].payload.o[0]].reverse(),[2,0,3,1]]});
function fill(lesson,perfect=true) {
  const stage=lesson.state.p;
  if(stage===1)DATA.accounts.forEach((account,i)=>lesson.setDraft('class_'+i,perfect?account.category:DATA.categories.find(value=>value!==account.category)));
  if(stage===2) {
    lesson.setDraft('liquidity_order',perfect?DATA.liquidityOrder:[...DATA.liquidityOrder].reverse());
    DATA.context.forEach(q=>lesson.setDraft('context_'+q.id,perfect?q.correct:q.options.find(value=>value!==q.correct)));
  }
  if(stage===3) {
    const values=calculateRatios(DATA.current);RATIO_KEYS.forEach(key=>lesson.setNumber(key,String(perfect?values[key]:0)));
  }
  if(stage===4) {
    DATA.analysis.forEach(q=>lesson.setDraft('analysis_'+q.id,perfect?q.correct:q.options.find(value=>value!==q.correct)));
    DATA.comparisons.forEach(q=>lesson.setDraft('comparison_'+q.id,perfect?q.correct:DATA.comparisonOptions.find(value=>value!==q.correct)));
  }
  if(stage===5) {
    DATA.diagnoses.forEach(q=>lesson.setDraft('diagnosis_'+q.id,perfect?q.correct:q.options.find(value=>value!==q.correct)));
    lesson.setDraft('diagnosis_evidence',perfect?DATA.correctEvidence:DATA.evidence.slice(4));
    lesson.setRationale(perfect?'Recommend approval with conditions; monitor liquidity and debt.':'This statement is long enough but contains none of the rubric words.');
  }
}
test('all original scoring structures match 84 independent Python submission cases',()=>{
  assert.equal(oracle.submissions.length,84);
  for(const fixture of oracle.submissions) {
    assert.deepEqual(validateSnapshot(fixture.payload),fixture.payload);
    assert.deepEqual(resultsFromSubmissions(fixture.payload.s),fixture.results);
  }
});
test('current/prior ratios, tolerance boundaries and exact Python display rounding',()=>{
  for(const fixture of oracle.ratios)assert.deepEqual(calculateRatios(fixture.input),fixture.output);
  for(const fixture of oracle.format) {
    assert.equal(currency(fixture.value),fixture.currency);
    for(const [digits,expected] of Object.entries(fixture.fixed))assert.equal(pyFixed(fixture.value,Number(digits)),expected);
  }
  assert.equal(pyFixed(1.125,2),'1.12');assert.equal(pyFixed(1.815,2),'1.81');
  assert.equal(ratioCorrect(260100,260000,100),true);assert.equal(ratioCorrect(260100.001,260000,100),false);
  assert.throws(()=>calculateRatios({...DATA.current,current_liabilities:0}));
});
test('legacy progress and draft tokens retain display orders, answered gates and Python compatibility',async()=>{
  for(const fixture of legacy) {
    const state=await decodeState(fixture.token);assert.deepEqual(state,fixture.payload);
    assert.deepEqual(await decodeState(await encodeState(state)),state);
  }
  const lesson=at(3);fill(lesson);
  const draft=await encodeDraft(lesson.draft,3);
  assert.deepEqual(await decodeDraft(draft,3),lesson.draft);
  const token=await encodeState(lesson.state);
  assert.deepEqual(python('import json,sys;from diagnosing_dollars.progress import decode_snapshot;print(json.dumps(decode_snapshot(sys.argv[1])))',[token]),lesson.state);
  const savedDraft=python('import base64,json,sys,zlib;t=sys.argv[1];print(zlib.decompress(base64.urlsafe_b64decode(t+\"=\"*(-len(t)%4))).decode())',[draft]);
  assert.deepEqual(savedDraft,lesson.draft);
});
test('full perfect and deliberately wrong routes preserve 39-point grading and original submission-only gates',()=>{
  for(const perfect of [true,false]) {
    const lesson=new Lesson();assert.equal(lesson.advance(),true);
    for(let stage=1;stage<=5;stage++) {
      assert.equal(lesson.advance(),false);assert.equal(lesson.submit(),false);
      fill(lesson,perfect);assert.equal(lesson.submit(),true);
      const before=canonicalJSON(lesson.state);
      assert.equal(lesson.submit(),false);assert.equal(lesson.setDraft('class_0',DATA.categories[0]),false);
      assert.equal(canonicalJSON(lesson.state),before);
      assert.equal(lesson.advance(),true);
    }
    assert.equal(lesson.state.c,true);
    const total=Object.values(lesson.results).reduce((sum,result)=>sum+result.score,0);
    assert.equal(total,perfect?39:0);
    assert.equal(lesson.advance(),false);
  }
});
test('evidence deductions, reflection substring rubric, raw-text session-only rules and 20-character validation',async()=>{
  for(const fixture of oracle.reflections) {
    const flags=reflectionFlags(fixture.text);
    assert.equal(flags.filter(Boolean).length,fixture.result[0]);
    assert.deepEqual(flags,fixture.result[1].map(item=>item.met));
  }
  const lesson=at(5);fill(lesson);lesson.setRationale('😀'.repeat(19));assert.equal(lesson.submit(),false);
  lesson.setRationale('😀'.repeat(20));assert.equal(lesson.submit(),true);assert.equal(lesson.results.diagnosis.reflection_score,0);
  const token=await encodeState(lesson.state),draft=await encodeDraft(lesson.draft,5);
  const restored=new Lesson(await decodeState(token),undefined,await decodeDraft(draft,5));
  assert.equal(restored.rationale,'');assert.equal(restored.results.diagnosis.reflection_score,0);
  assert.equal(Object.hasOwn(restored.draft,'diagnosis_reflection'),false);
});
test('number entry and unfinished native numeric drafts restore without changing original typed draft compatibility',async()=>{
  for(const [raw,expected] of [['260,000',260000],['$260,000',260000],['1.81',1.81],['54.5',54.5],['-12.5',-12.5],['1e3',1000],['0',0]])
    assert.equal(parseNumber(raw),expected);
  for(const raw of ['', ' ', '1,20','1e','-','Infinity','NaN','1000000000001'])assert.equal(parseNumber(raw),null);
  const lesson=at(3);lesson.setNumber('current_ratio','1e');assert.equal(lesson.submit(),false);
  const numbers=await encodeNumbers(lesson.numbers);
  const restored=new Lesson(lesson.state,undefined,await decodeDraft(await encodeDraft(lesson.draft,3),3),await decodeNumbers(numbers));
  assert.equal(restored.numbers.current_ratio,'1e');assert.equal(restored.draft.ratio_current_ratio,null);
  assert.deepEqual(await decodeNumbers(await encodeNumbers({current_ratio:'secret student name'})),{});
});
test('every review stage independently rejects edits, submissions, rationale, reset and future advancement',()=>{
  const lesson=new Lesson(legacy[6].payload),before=canonicalJSON(lesson.state);
  for(let view=5;view>=0;view--) {
    assert.equal(lesson.move(-1),true);assert.equal(lesson.view,view);
    assert.equal(lesson.setDraft('class_0',DATA.categories[0]),false);
    assert.equal(lesson.setNumber('current_ratio','0'),false);
    assert.equal(lesson.setRationale('Recommend approval based on liquidity and debt.'),false);
    for(const method of ['submit','advance','reset'])assert.equal(lesson[method](),false);
    assert.equal(canonicalJSON(lesson.state),before);
  }
  for(let view=1;view<=6;view++){assert.equal(lesson.move(1),true);assert.equal(lesson.view,view);}
  assert.equal(lesson.move(1),false);assert.equal(canonicalJSON(lesson.state),before);
});
test('malformed schema, duplicate orders, future drafts, unknown choices and future views are rejected',async()=>{
  for(const token of [undefined,'','bad!','a'.repeat(4097)])assert.equal(await decodeState(token),null);
  assert.throws(()=>validateSnapshot({...newState(),p:6,c:true}));
  const duplicate=newState();duplicate.o[1]=[0,0,2,3];assert.throws(()=>validateSnapshot(duplicate));
  assert.throws(()=>validateDraft({ratio_current_ratio:1},2));
  assert.throws(()=>validateDraft({class_0:'unknown'},1));
  assert.throws(()=>validateDraft({liquidity_order:['Cash','Cash']},2));
  for(const view of ['999','-1','2.4','bad'])assert.equal(new Lesson(legacy[3].payload,view).view,3);
});
test('reset preserves copied completed links and isolates native case instances',async()=>{
  const first=new Lesson(legacy[6].payload),second=new Lesson(),token=await encodeState(first.state);
  assert.equal(first.reset(),true);assert.equal(first.state.p,0);assert.equal(second.state.p,0);
  assert.equal((await decodeState(token)).c,true);assert.equal(first.rationale,'');
});
test('all captured variants, feedback, help and metadata contain no provisional app branding',()=>{
  const walk=value=>{
    if(Array.isArray(value))return value.forEach(walk);
    if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){
      if(['text','label','help'].includes(key)&&typeof item==='string')assert.doesNotMatch(item,/\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b/i);
      else walk(item);
    }
  };
  walk(DATA.screens);walk(DATA.sidebar);walk(DATA.hero);assert.equal(DATA.title,'Diagnosing Dollars');
  assert.equal(CATEGORIES.length,5);assert.equal(KEYS.length,5);
});

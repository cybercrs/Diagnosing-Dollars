/** Original clinical scoring and gates with legacy-compatible native saves. */
import {DATA} from './content.js';
import {assert,copy,object,exact,int,finite,shuffled,encodeJSON,decodeJSON,parseNumber,numericText} from './shared.js';
export {currency,pyFixed,canonicalJSON,copy,parseNumber} from './shared.js';
export const KEYS=['cl','li','ra','an','di'];
export const CATEGORIES=['classification','liquidity','ratios','analysis','diagnosis'];
export const RATIO_KEYS=['working_capital','current_ratio','debt_to_assets','debt_to_equity'];
const indexes=(value,lengths)=>{
  assert(Array.isArray(value)&&value.length===lengths.length&&value.every((n,i)=>int(n,0,lengths[i]-1)),'Invalid answer indexes');
  return [...value];
};
const permutation=(value,size)=>{const list=indexes(value,Array(size).fill(size));assert(new Set(list).size===size,'Invalid display order');return list;};
export function newState() {
  return {v:1,p:0,o:[shuffled(DATA.accounts.map((_,i)=>i)),shuffled(DATA.liquidityOrder.map((_,i)=>i))],s:{},c:false};
}
export function validateSnapshot(raw) {
  assert(exact(raw,['v','p','o','s','c'])&&raw.v===1&&int(raw.p,0,6),'Unsupported saved case');
  assert(Array.isArray(raw.o)&&raw.o.length===2,'Invalid display orders');
  const orders=[permutation(raw.o[0],DATA.accounts.length),permutation(raw.o[1],DATA.liquidityOrder.length)];
  assert(object(raw.s),'Invalid submissions');
  const count=Object.keys(raw.s).length;
  assert(count<=5&&Object.keys(raw.s).every(key=>KEYS.slice(0,count).includes(key)),'Invalid submission prefix');
  assert(count>=Math.max(0,raw.p-1)&&count<=Math.min(raw.p,5),'Inconsistent saved stage');
  const answers={};
  if(Object.hasOwn(raw.s,'cl'))answers.cl=indexes(raw.s.cl,DATA.accounts.map(()=>DATA.categories.length));
  if(Object.hasOwn(raw.s,'li')) {
    assert(Array.isArray(raw.s.li)&&raw.s.li.length===2,'Invalid liquidity submission');
    answers.li=[permutation(raw.s.li[0],4),indexes(raw.s.li[1],DATA.context.map(q=>q.options.length))];
  }
  if(Object.hasOwn(raw.s,'ra')) {
    assert(Array.isArray(raw.s.ra)&&raw.s.ra.length===4&&raw.s.ra.every(finite),'Invalid ratio values');
    answers.ra=[...raw.s.ra];
  }
  if(Object.hasOwn(raw.s,'an')) {
    assert(Array.isArray(raw.s.an)&&raw.s.an.length===2,'Invalid analysis submission');
    answers.an=[indexes(raw.s.an[0],DATA.analysis.map(q=>q.options.length)),indexes(raw.s.an[1],DATA.comparisons.map(()=>DATA.comparisonOptions.length))];
  }
  if(Object.hasOwn(raw.s,'di')) {
    assert(Array.isArray(raw.s.di)&&raw.s.di.length===3,'Invalid diagnosis submission');
    assert(int(raw.s.di[1],1,(1<<DATA.evidence.length)-1)&&int(raw.s.di[2],0,7),'Invalid evidence/rubric flags');
    answers.di=[indexes(raw.s.di[0],DATA.diagnoses.map(q=>q.options.length)),raw.s.di[1],raw.s.di[2]];
  }
  assert(typeof raw.c==='boolean'&&raw.c===(raw.p===6&&count===5),'Inconsistent completion');
  return {v:1,p:raw.p,o:orders,s:answers,c:raw.c};
}
export const encodeState=state=>encodeJSON(validateSnapshot(state));
export async function decodeState(token){try{return validateSnapshot(await decodeJSON(token));}catch{return null;}}
export function calculateRatios(values) {
  assert(values.current_liabilities!==0&&values.total_assets!==0&&values.total_equity!==0,'Ratio denominators must be nonzero');
  return {working_capital:values.current_assets-values.current_liabilities,
    current_ratio:values.current_assets/values.current_liabilities,
    debt_to_assets:values.total_liabilities/values.total_assets*100,
    debt_to_equity:values.total_liabilities/values.total_equity*100};
}
export const ratioCorrect=(value,expected,tolerance)=>value!==null&&Number.isFinite(value)&&Math.abs(value-expected)<=Math.max(tolerance,1e-9*Math.max(Math.abs(value),Math.abs(expected)));
const questionFeedback=(questions,selected,options)=>questions.map((question,index)=>{
  const chosen=(options??question.options)[selected[index]];
  return {id:question.id,name:question.prompt??question.label??'',chosen,correct:question.correct,is_correct:chosen===question.correct,why:question.why??''};
});
const score=items=>items.filter(item=>item.is_correct).length;
export function reflectionFlags(text) {
  const normalized=text.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  return DATA.rubric.map(criterion=>criterion.patterns.some(pattern=>normalized.includes(pattern)));
}
export function reflectionFeedback(flags) {return DATA.rubric.map((criterion,i)=>({label:criterion.label,met:Boolean(flags[i]),guidance:criterion.guidance}));}
export function resultsFromSubmissions(answers) {
  const results={};
  if(answers.cl) {
    const feedback=DATA.accounts.map((account,i)=>({name:account.name,chosen:DATA.categories[answers.cl[i]],correct:account.category,
      is_correct:DATA.categories[answers.cl[i]]===account.category,why:account.why}));
    results.classification={score:score(feedback),max:DATA.accounts.length,feedback};
  }
  if(answers.li) {
    const submitted_order=answers.li[0].map(i=>DATA.liquidityOrder[i]),order_correct=answers.li[0].every((n,i)=>n===i);
    const feedback=questionFeedback(DATA.context,answers.li[1]);
    results.liquidity={score:score(feedback)+Number(order_correct),max:4,order_correct,submitted_order,feedback};
  }
  if(answers.ra) {
    const expected=calculateRatios(DATA.current),tolerances=[100,.01,.1,.1];
    const entries=Object.fromEntries(RATIO_KEYS.map((key,i)=>[key,answers.ra[i]]));
    const checks=Object.fromEntries(RATIO_KEYS.map((key,i)=>[key,ratioCorrect(entries[key],expected[key],tolerances[i])]));
    results.ratios={score:Object.values(checks).filter(Boolean).length,max:4,checks,entries};
  }
  if(answers.an) {
    const feedback=questionFeedback(DATA.analysis,answers.an[0]),comparison_feedback=questionFeedback(DATA.comparisons,answers.an[1],DATA.comparisonOptions);
    const comparison_score=score(comparison_feedback);
    results.analysis={score:score(feedback)+comparison_score,max:6,feedback,comparison_score,comparison_feedback};
  }
  if(answers.di) {
    const feedback=questionFeedback(DATA.diagnoses,answers.di[0]),selected=DATA.evidence.filter((_,i)=>answers.di[1]&(1<<i));
    const good=selected.filter(value=>DATA.correctEvidence.includes(value)).length,bad=selected.length-good;
    const evidence_feedback=DATA.evidence.map(option=>{
      const wasSelected=selected.includes(option),should_select=DATA.correctEvidence.includes(option);
      return {option,selected:wasSelected,should_select,is_correct:wasSelected===should_select};
    });
    const flags=DATA.rubric.map((_,i)=>Boolean(answers.di[2]&(1<<i))),reflection_score=flags.filter(Boolean).length;
    const evidence_score=Math.max(0,good-bad),reflection_feedback=reflectionFeedback(flags);
    results.diagnosis={score:score(feedback)+evidence_score+reflection_score,max:10,feedback,evidence_score,evidence_feedback,reflection_score,reflection_feedback};
  }
  return results;
}
export function draftSchema(stage) {
  const fields={};
  if(stage>=1)DATA.accounts.forEach((_,i)=>{fields['class_'+i]=['choice',['Select a section',...DATA.categories]];});
  if(stage>=2) {
    fields.liquidity_order=['many',DATA.liquidityOrder];
    DATA.context.forEach(q=>{fields['context_'+q.id]=['choice',['Select an answer',...q.options]];});
  }
  if(stage>=3)RATIO_KEYS.forEach(key=>{fields['ratio_'+key]=['number',[]];});
  if(stage>=4) {
    DATA.analysis.forEach(q=>{fields['analysis_'+q.id]=['choice',q.options];});
    DATA.comparisons.forEach(q=>{fields['comparison_'+q.id]=['choice',['Select a comparison',...DATA.comparisonOptions]];});
  }
  if(stage>=5) {
    DATA.diagnoses.forEach(q=>{fields['diagnosis_'+q.id]=['choice',q.options];});
    fields.diagnosis_evidence=['many',DATA.evidence];
  }
  return fields;
}
function validDraft(value,[kind,options]) {
  if(value===null)return true;
  if(kind==='choice')return typeof value==='string'&&options.includes(value);
  if(kind==='many')return Array.isArray(value)&&value.length<=options.length&&new Set(value).size===value.length&&value.every(item=>typeof item==='string'&&options.includes(item));
  return finite(value);
}
export function validateDraft(raw,stage) {
  const fields=draftSchema(stage);
  assert(object(raw)&&Object.keys(raw).every(key=>Object.hasOwn(fields,key)&&validDraft(raw[key],fields[key])),'Invalid saved drafts');
  return copy(raw);
}
export const encodeDraft=(raw,stage)=>encodeJSON(validateDraft(raw,stage),32000,16000);
export async function decodeDraft(token,stage){try{return validateDraft(await decodeJSON(token,32000,16000),stage);}catch{return {};}}
export const rawNumbers=raw=>Object.fromEntries(Object.entries(raw).filter(([key,value])=>RATIO_KEYS.includes(key)&&numericText(value)));
export const encodeNumbers=raw=>encodeJSON(rawNumbers(raw),1000,2000);
export async function decodeNumbers(token){try{const raw=await decodeJSON(token,1000,2000);return object(raw)?rawNumbers(raw):{};}catch{return {};}}
export class Lesson {
  constructor(state=newState(),view,draft={},numbers={}) {
    this.state=validateSnapshot(state);this.draft=validateDraft(draft,this.state.p);
    const number=typeof view==='string'&&/^-?\d+$/.test(view)?Number(view):view;
    this.view=int(number,0,this.state.p)?number:this.state.p;
    this.numbers=this.state.p>=3?rawNumbers(numbers):{};this.rationale='';this.error='';
  }
  get reviewing(){return this.view<this.state.p;}
  get results(){return resultsFromSubmissions(this.state.s);}
  get submitted(){return this.state.p>=1&&this.state.p<=5&&Object.hasOwn(this.state.s,KEYS[this.state.p-1]);}
  move(direction) {
    if(![-1,1].includes(direction)||!int(this.view+direction,0,this.state.p))return false;
    this.view+=direction;this.error='';return true;
  }
  setDraft(key,value) {
    if(this.reviewing||this.submitted)return false;
    const fields=draftSchema(this.state.p);
    const stagePrefix={1:'class_',2:'context_',3:'ratio_',4:'analysis_',5:'diagnosis_'}[this.state.p];
    const current=stagePrefix&&key.startsWith(stagePrefix)||this.state.p===2&&key==='liquidity_order'||this.state.p===4&&key.startsWith('comparison_');
    if(!current||!Object.hasOwn(fields,key)||!validDraft(value,fields[key]))return false;
    this.draft[key]=copy(value);this.error='';return true;
  }
  setNumber(key,text) {
    if(this.reviewing||this.submitted||this.state.p!==3||!RATIO_KEYS.includes(key)||typeof text!=='string'||text.length>64)return false;
    this.numbers[key]=text;this.draft['ratio_'+key]=parseNumber(text);this.error='';return true;
  }
  setRationale(text) {
    if(this.reviewing||this.submitted||this.state.p!==5||typeof text!=='string'||text.length>500)return false;
    this.rationale=text;this.error='';return true;
  }
  submit() {
    if(this.reviewing||this.submitted||this.state.p<1||this.state.p>5)return false;
    const stage=this.state.p,draft=this.draft;let packed;
    if(stage===1) {
      packed=DATA.accounts.map((_,i)=>DATA.categories.indexOf(draft['class_'+i]));
      if(packed.includes(-1)){this.error=DATA.errors.classification;return false;}
    } else if(stage===2) {
      const order=draft.liquidity_order??[],answers=DATA.context.map(q=>q.options.indexOf(draft['context_'+q.id]));
      if(order.length!==4||answers.includes(-1)){this.error=DATA.errors.liquidity;return false;}
      packed=[order.map(item=>DATA.liquidityOrder.indexOf(item)),answers];
    } else if(stage===3) {
      packed=RATIO_KEYS.map(key=>Object.hasOwn(this.numbers,key)?parseNumber(this.numbers[key]):draft['ratio_'+key]??null);
      if(packed.some(value=>!finite(value))){this.error=DATA.errors.ratios??'Enter all four financial vital signs before submitting.';return false;}
    } else if(stage===4) {
      const answers=DATA.analysis.map(q=>q.options.indexOf(draft['analysis_'+q.id]));
      const comparisons=DATA.comparisons.map(q=>DATA.comparisonOptions.indexOf(draft['comparison_'+q.id]));
      if(answers.includes(-1)||comparisons.includes(-1)){this.error=DATA.errors.analysis;return false;}
      packed=[answers,comparisons];
    } else {
      const answers=DATA.diagnoses.map(q=>q.options.indexOf(draft['diagnosis_'+q.id])),evidence=draft.diagnosis_evidence??[];
      if(answers.includes(-1)||!evidence.length||[...this.rationale.trim()].length<20){this.error=DATA.errors.diagnosis;return false;}
      packed=[answers,evidence.reduce((mask,value)=>mask|(1<<DATA.evidence.indexOf(value)),0),
        reflectionFlags(this.rationale).reduce((mask,value,i)=>mask|(Number(value)<<i),0)];
    }
    this.state.s[KEYS[stage-1]]=packed;this.state.c=false;this.error='';validateSnapshot(this.state);return true;
  }
  advance() {
    if(this.reviewing||this.state.p>=6||this.state.p>0&&!this.submitted)return false;
    this.state.p++;this.view=this.state.p;this.state.c=this.state.p===6&&Object.keys(this.state.s).length===5;
    this.error='';validateSnapshot(this.state);return true;
  }
  reset() {
    if(this.reviewing)return false;
    this.state=newState();this.view=0;this.draft={};this.numbers={};this.rationale='';this.error='';return true;
  }
}

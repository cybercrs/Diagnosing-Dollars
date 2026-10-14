/** Native clinical controls around the unchanged teaching screens. */
import {DATA} from './content.js';
import {Lesson,CATEGORIES,RATIO_KEYS,calculateRatios,resultsFromSubmissions,
  decodeState,encodeState,decodeDraft,encodeDraft,decodeNumbers,encodeNumbers,currency,pyFixed,parseNumber} from './engine.js';
import {copy} from './shared.js';

const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
const escapeHTML=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let lesson,sequence=0,progressIndex=0;
async function save() {
  const current=++sequence,state=copy(lesson.state),draft=copy(lesson.draft),numbers=copy(lesson.numbers),view=lesson.view;
  document.documentElement.dataset.saving='true';
  try {
    const [progress,savedDraft,savedNumbers]=await Promise.all([encodeState(state),encodeDraft(draft,state.p),encodeNumbers(numbers)]);
    if(current!==sequence)return;
    const url=new URL(location.href);url.searchParams.set('progress',progress);url.searchParams.set('draft',savedDraft);url.searchParams.set('view',String(view));
    if(Object.keys(numbers).length)url.searchParams.set('numbers',savedNumbers);else url.searchParams.delete('numbers');
    history.replaceState(null,'',url);$('save-error').hidden=true;
  } catch(error) {
    if(current!==sequence)return;
    $('save-error').textContent='Your address could not be updated. Keep this tab open; refreshing may not preserve the latest input.';
    $('save-error').hidden=false;console.error(error);
  } finally {if(current===sequence)document.documentElement.dataset.saving='false';}
}
function scrollTop(){window.scrollTo({top:0,left:0,behavior:'instant'});$('lesson').focus({preventScroll:true});}
function update(scroll=false,focus){render();save();if(scroll)scrollTop();else if(focus)document.getElementById(focus)?.focus({preventScroll:true});}
function markdown(text) {
  const fragment=document.createDocumentFragment();let list;
  for(const line of text.replace(/\\\$/g,'$').split('\n').map(x=>x.trim()).filter(Boolean)) {
    const bullet=/^[-*]\s+(.+)/.exec(line),heading=/^(#{1,6})\s+(.+)/.exec(line);
    const item=el(bullet?'li':heading?'h'+heading[1].length:'p');
    item.innerHTML=escapeHTML(bullet?bullet[1]:heading?heading[2]:line).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    if(bullet){if(!list){list=el('ul');fragment.append(list);}list.append(item);}else{list=null;fragment.append(item);}
  }
  return fragment;
}
function draftValue(node) {
  if(!Object.hasOwn(lesson.draft,node.key)&&!lesson.reviewing&&!lesson.submitted) {
    const value=node.kind==='many'?[]:node.kind==='select'?node.options[0]:null;
    lesson.setDraft(node.key,value);
  }
  return lesson.draft[node.key]??(node.kind==='many'?[]:null);
}
function choice(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const value=draftValue(node);
  if(node.kind==='select') {
    const box=el('div'),label=el('label',node.label,'select-label'),select=el('select');
    select.id=node.key;label.htmlFor=node.key;
    node.options.forEach(option=>{const item=el('option',option);item.value=option;item.selected=value===option;select.append(item);});
    select.addEventListener('change',()=>{if(lesson.setDraft(node.key,select.value))save();});box.append(label,select);return box;
  }
  const fieldset=el('fieldset');fieldset.append(el('legend',node.label));
  node.options.forEach((option,index)=>{
    const label=el('label',undefined,'choice'),input=el('input');input.type='radio';input.id=node.key+'_'+index;input.name=node.key;
    input.value=option;input.checked=value===option;
    input.addEventListener('change',()=>{if(lesson.setDraft(node.key,option))save();});
    label.append(input,el('span',option));fieldset.append(label);
  });return fieldset;
}
function many(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const fieldset=el('fieldset'),value=draftValue(node);fieldset.append(el('legend',node.label));
  if(node.help)fieldset.append(el('p',node.help,'caption'));
  const options=node.key==='liquidity_order'?lesson.state.o[1].map(i=>DATA.liquidityOrder[i]):node.options;
  options.forEach((option,index)=>{
    const label=el('label',undefined,'choice'),input=el('input');input.type='checkbox';input.id=node.key+'_'+index;
    input.checked=value.includes(option);input.value=option;
    input.addEventListener('change',()=>{
      const selected=lesson.draft[node.key]??[],next=input.checked?[...selected,option]:selected.filter(item=>item!==option);
      if(lesson.setDraft(node.key,next))update(false,input.id);
    });
    label.append(input,el('span',option));fieldset.append(label);
  });
  if(node.key==='liquidity_order'&&value.length) {
    const list=el('ol',undefined,'selected-order');
    value.forEach((option,index)=>{
      const item=el('li'),row=el('div',undefined,'order-row');row.append(el('span',option));
      for(const [label,direction] of [['↑',-1],['↓',1]]) {
        const button=el('button',label);button.type='button';
        button.id='order-'+index+'-'+(direction<0?'up':'down');button.setAttribute('aria-label','Move '+option+(direction<0?' earlier':' later'));
        button.disabled=index+direction<0||index+direction>=value.length;
        button.addEventListener('click',()=>{
          const next=[...value];[next[index],next[index+direction]]=[next[index+direction],next[index]];
          if(lesson.setDraft(node.key,next))update(false,'order-'+(index+direction)+'-'+(direction<0?'up':'down'));
        });row.append(button);
      }
      item.append(row);list.append(item);
    });fieldset.append(el('p','Your order, from most liquid to least liquid:','caption'),list);
  }
  return fieldset;
}
function number(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  draftValue(node);
  const key=node.key.replace('ratio_',''),box=el('div',undefined,'amount'),label=el('label',node.label,'select-label'),input=el('input');
  label.htmlFor=node.key;input.id=node.key;input.name=node.key;input.type='text';input.inputMode='decimal';input.maxLength=64;
  input.placeholder=node.placeholder;input.value=lesson.numbers[key]??(lesson.draft[node.key]===null?'':String(lesson.draft[node.key]??''));
  input.setAttribute('aria-invalid',String(input.value!==''&&parseNumber(input.value)===null));
  input.addEventListener('input',()=>{if(lesson.setNumber(key,input.value)){input.setAttribute('aria-invalid',String(input.value!==''&&parseNumber(input.value)===null));save();}});
  box.append(label,input);return box;
}
function textArea(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const box=el('div'),label=el('label',node.label,'select-label'),textarea=el('textarea');
  label.htmlFor=node.key;textarea.id=node.key;textarea.name=node.key;textarea.value=lesson.rationale;
  textarea.maxLength=node.maxLength;textarea.rows=4;textarea.placeholder=node.placeholder??'';
  textarea.addEventListener('input',()=>lesson.setRationale(textarea.value));box.append(label,textarea);
  if(node.help)box.append(el('p',node.help,'caption'));return box;
}
function feedbackRows(items,showName=false) {
  const fragment=document.createDocumentFragment();
  for(const item of items) {
    const box=el('div',undefined,'feedback-row');
    if(showName){box.append(el('strong',item.name),el('br'));}
    const answer=item.is_correct?'✓ Correct':'↺ Your answer: '+(item.chosen||'No answer')+' · Correct: '+item.correct;
    box.append(el('span',answer,item.is_correct?'feedback-good':'feedback-fix'),el('br'),el('small',item.why));fragment.append(box);
  }
  return fragment;
}
function ratioFeedback() {
  const result=lesson.results.ratios,expected=calculateRatios(DATA.current),labels=['Working capital','Current ratio','Debt-to-assets ratio','Debt-to-equity ratio'];
  const format=(key,value)=>key==='working_capital'?currency(value):key==='current_ratio'?pyFixed(value,2)+':1':pyFixed(value,1)+'%';
  const fragment=document.createDocumentFragment();
  RATIO_KEYS.forEach((key,index)=>{
    const correct=result.checks[key],box=el('div',undefined,'feedback-row');
    const detail='Your answer: '+format(key,result.entries[key])+(correct?'':' · Correct answer: '+format(key,expected[key]));
    box.append(el('strong',labels[index]),el('br'),el('span',(correct?'✓ Correct':'↺ Incorrect'),correct?'feedback-good':'feedback-fix'),
      el('br'),el('small',detail));fragment.append(box);
  });return fragment;
}
function evidenceFeedback() {
  const result=lesson.results.diagnosis,fragment=document.createDocumentFragment();
  const heading=el('p');heading.append(el('strong','Evidence selection: '+result.evidence_score+' of 4 points'));fragment.append(heading);
  for(const item of result.evidence_feedback) {
    const good=item.selected===item.should_select,message=item.selected?(item.should_select?'Correctly selected':'This statement does not support the diagnosis'):
      item.should_select?'Supporting evidence was missed':'Correctly left unselected';
    const box=el('div',undefined,'feedback-row');box.append(el('span',(good?'✓ ':'↺ ')+message,good?'feedback-good':'feedback-fix'),el('br'),el('small',item.option));fragment.append(box);
  }return fragment;
}
function reflectionFeedback() {
  const result=lesson.results.diagnosis,fragment=document.createDocumentFragment(),heading=el('p');
  heading.append(el('strong','Written rationale: '+result.reflection_score+' of 3 points'));fragment.append(heading);
  for(const item of result.reflection_feedback) {
    const box=el('div',undefined,'feedback-row');
    box.append(el('span',(item.met?'✓ ':'↺ ')+item.label+': '+(item.met?'Criterion met':'Add this element'),item.met?'feedback-good':'feedback-fix'),
      el('br'),el('small',item.guidance));fragment.append(box);
  }fragment.append(el('p',DATA.modelResponse,'notice info'));return fragment;
}
function csv(rows,columns){return [columns,...rows.map(row=>columns.map(key=>row[key]))].map(row=>row.map(value=>'"'+String(value).replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';}
function table(node) {
  const section=el('section'),wrap=el('div',undefined,'table-wrap'),table=el('table'),columns=Object.keys(node.rows[0]);
  wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Financial vital signs and comparisons; scroll horizontally to see all columns');
  const caption=el('caption','Financial Vital Signs and Comparisons'),head=el('thead'),line=el('tr'),body=el('tbody');
  table.append(caption);let rows=[...node.rows],sort=null,descending=false;
  const draw=()=>{body.replaceChildren(...rows.map(row=>{const tr=el('tr');columns.forEach((key,index)=>{const cell=el(index===0?'th':'td',row[key]);if(index===0)cell.scope='row';tr.append(cell);});return tr;}));};
  columns.forEach(key=>{
    const th=el('th'),button=el('button',key);th.scope='col';button.type='button';
    button.addEventListener('click',()=>{descending=sort===key?!descending:false;sort=key;rows=[...node.rows].sort((a,b)=>String(a[key]).localeCompare(String(b[key]),'en')*(descending?-1:1));
      [...line.children].forEach(cell=>cell.removeAttribute('aria-sort'));th.setAttribute('aria-sort',descending?'descending':'ascending');draw();});
    th.append(button);line.append(th);
  });head.append(line);table.append(head,body);draw();wrap.append(table);section.append(wrap);
  const tools=el('div',undefined,'table-tools'),download=el('button','Download table as CSV'),expand=el('button','Expand table');
  download.type=expand.type='button';
  download.addEventListener('click',()=>{const blob=new Blob([csv(rows,columns)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=el('a');
    link.href=url;link.download='diagnosing-dollars-comparisons.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  expand.addEventListener('click',()=>{const dialog=el('dialog',undefined,'expanded-table'),close=el('button','Close table'),placeholder=document.createComment('table position');
    close.type='button';wrap.before(placeholder);dialog.append(el('h2',caption.textContent),close,wrap);document.body.append(dialog);
    close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>{placeholder.replaceWith(wrap);dialog.remove();expand.focus();},{once:true});dialog.showModal();});
  tools.append(expand,download);section.append(tools);return section;
}
function action(node,scope) {
  const reset=node.action==='reset_case';
  if(lesson.reviewing&&!reset)return document.createDocumentFragment();
  const button=el('button',node.label,scope==='sidebar'?'':'primary');button.type='button';button.disabled=lesson.reviewing;
  if(reset&&scope==='sidebar')button.id='reset';
  button.addEventListener('click',()=>{
    let changed=false,scroll=false;
    if(reset){changed=lesson.reset();scroll=true;}
    else if(node.action==='advance'){changed=lesson.advance();scroll=true;}
    else if(node.action?.startsWith('submit_'))changed=lesson.submit();
    if(changed||lesson.error)update(scroll);
  });return button;
}
function renderNode(node,scope='lesson') {
  if(node.kind==='sidebar') {const fragment=document.createDocumentFragment();node.children.forEach(child=>fragment.append(renderNode(child,'sidebar')));return fragment;}
  if(node.kind==='radio'||node.kind==='select')return choice(node);
  if(node.kind==='many')return many(node);
  if(node.kind==='number')return number(node);
  if(node.kind==='text')return textArea(node);
  if(node.kind==='button')return action(node,scope);
  if(node.kind==='table')return table(node);
  if(node.kind==='feedback')return feedbackRows(lesson.results[node.path[0]][node.path[1]],node.showName);
  if(node.kind==='ratio-feedback')return ratioFeedback();
  if(node.kind==='evidence-feedback')return evidenceFeedback();
  if(node.kind==='reflection-feedback')return reflectionFeedback();
  if(node.kind==='result-banner') {
    const result=lesson.results[CATEGORIES[lesson.view-1]],good=result.score===result.max,medium=result.score>=result.max*.7;
    const text=good?'Vital signs recorded: '+result.score+' of '+result.max+' correct.':medium?'Good clinical progress: '+result.score+' of '+result.max+' correct. Review the notes below.':
      'This section needs another look: '+result.score+' of '+result.max+' correct. Review the notes below before continuing.';
    const message=el('p',text,'notice '+(good?'success':medium?'info':'warning'));message.setAttribute('role','status');return message;
  }
  if(node.kind==='html') {
    const template=document.createElement('template');template.innerHTML=node.text;
    const brand=template.content.querySelector('.brand-title');
    if(brand){const heading=el('h1',brand.textContent,'brand-title');brand.replaceWith(heading);}
    if(lesson.view===6) {
      const card=template.content.querySelector('.clinical-card');
      if(card?.querySelector('.clinical-label')?.textContent==='Case status') {
        const total=Object.values(lesson.results).reduce((sum,item)=>sum+item.score,0),tier=DATA.performance.find(tier=>total/39*100>=tier.minimum);
        card.querySelector('.clinical-title').textContent=tier.label;card.querySelector('.clinical-copy').textContent=tier.message;
      }
    }return template.content;
  }
  if(['columns','column','form'].includes(node.kind)) {
    const box=el('div',undefined,node.kind==='columns'?'columns':null);if(node.kind==='columns')box.style.setProperty('--columns',node.children.length);
    let children=node.children;
    if(node.kind==='form'&&node.key==='classification_form') {
      const rows=node.children.filter(child=>child.kind==='columns');
      children=[...lesson.state.o[0].map(i=>rows[i]),...node.children.filter(child=>child.kind!=='columns')];
    }
    children.forEach(child=>box.append(renderNode(child,scope)));return box;
  }
  if(node.kind==='details') {
    if(scope==='sidebar'&&lesson.reviewing)return document.createDocumentFragment();
    const details=el('details');details.open=Boolean(node.expanded);details.append(el('summary',node.label));
    node.children.forEach(child=>details.append(renderNode(child,scope)));return details;
  }
  if(node.kind==='divider')return el('hr');
  if(node.kind==='metric') {
    const total=Object.values(lesson.results).reduce((sum,item)=>sum+item.score,0),box=el('div',undefined,'metric');
    const value=lesson.view===6?(node.label==='Total score'?total+' / 39':pyFixed(total/39*100,0)+'%'):node.value;
    box.append(el('span',node.label),el('strong',value));return box;
  }
  if(node.kind==='progress') {
    const progress=el('progress');progress.max=1;
    const category=scope==='lesson'&&lesson.view===6?CATEGORIES[progressIndex++]:null;
    progress.value=category?lesson.results[category].score/lesson.results[category].max:scope==='sidebar'?lesson.state.p/6:node.value;
    progress.setAttribute('aria-label',category?category+' score':'Case progress');return progress;
  }
  let text=node.text;
  if(node.kind==='markdown'||node.kind==='write') {
    if(lesson.view===4&&text.startsWith('**Comparison vocabulary:'))text='**Comparison vocabulary:** '+lesson.results.analysis.comparison_score+' of 3 correct.  \nPrior year = intracompany · Peer average = industry-average · Competitor = intercompany';
    if(lesson.view===6&&node.kind==='write') {
      const labels=['Account classification','Liquidity and context','Ratio calculations','Comparisons and trends','Financial diagnosis'];
      const index=labels.findIndex(label=>text.startsWith('**'+label+':'));
      if(index>=0){const result=lesson.results[CATEGORIES[index]];text='**'+labels[index]+':** '+result.score+' of '+result.max;}
    }
    return markdown(text);
  }
  const item=el(['title','header'].includes(node.kind)?'h2':node.kind==='subheader'?'h3':'p',text,
    ['success','warning','info','error'].includes(node.kind)?'notice '+(node.kind==='error'?'warning':node.kind):node.kind==='caption'?'caption':null);
  if(['success','warning','info','error'].includes(node.kind))item.setAttribute('role',node.kind==='error'?'alert':'status');return item;
}
function render() {
  progressIndex=0;
  $('hero').replaceChildren(...DATA.hero.map(node=>renderNode(node)));
  $('sidebar').replaceChildren(...DATA.sidebar.map(node=>renderNode(node,'sidebar')));
  $('back').disabled=lesson.view===0;$('forward').disabled=lesson.view>=lesson.state.p;
  $('page-counter').textContent='Stage '+(lesson.view+1)+' of 7';
  $('stage-line').replaceChildren(el('span',DATA.stages[lesson.view]),el('span',(lesson.view+1)+' of 7'));
  $('stage-progress').value=lesson.view;
  $('review-message').replaceChildren(...(lesson.reviewing?[el('p','Review only. Return to your current stage to continue the case.','notice info')]:[]));
  const hasResult=lesson.view>=1&&lesson.view<=5&&Object.hasOwn(lesson.state.s,['cl','li','ra','an','di'][lesson.view-1]);
  const nodes=DATA.screens[lesson.view][hasResult?'wrong':'unanswered'];
  $('lesson').replaceChildren(...nodes.map(node=>renderNode(node)));
  if(lesson.error){const error=el('p',lesson.error,'notice warning');error.setAttribute('role','alert');$('lesson').append(error);}
  $('lesson').setAttribute('aria-busy','false');document.documentElement.dataset.view=String(lesson.view);document.documentElement.dataset.reached=String(lesson.state.p);
}
async function initialize() {
  const query=new URL(location.href).searchParams,token=query.get('progress'),state=token?await decodeState(token):null;
  const draft=await decodeDraft(query.get('draft'),state?.p??0),numbers=await decodeNumbers(query.get('numbers'));
  lesson=new Lesson(state??undefined,query.get('view')??undefined,draft,numbers);
  render();if(token&&!state)$('lesson').prepend(el('p','This saved link could not be restored. A new patient case has been opened.','notice warning'));
  await save();document.documentElement.dataset.ready='true';performance.mark('diagnosing-ready');
}
$('back').addEventListener('click',()=>{if(lesson.move(-1))update(true);});
$('forward').addEventListener('click',()=>{if(lesson.move(1))update(true);});
window.addEventListener('popstate',()=>{document.documentElement.dataset.ready='false';initialize();});
initialize().catch(error=>{$('lesson').replaceChildren(el('p','This browser could not open the case. Use a current browser with JavaScript and Compression Streams enabled.','notice warning'));$('lesson').setAttribute('aria-busy','false');console.error(error);});

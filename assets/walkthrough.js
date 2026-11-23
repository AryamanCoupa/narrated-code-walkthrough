'use strict';
const DATA=JSON.parse(document.getElementById('data').textContent);
const $=selector=>document.querySelector(selector);
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const prose=text=>esc(text).split('\n').filter(Boolean).map(p=>'<p>'+p+'</p>').join('');
const files=new Map(DATA.files.map(file=>[file.path,file]));
const time=seconds=>{const n=Math.round(seconds);return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');};
const smooth=()=>matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth';
let current=0,cueIndex=-1,started=false,selectedFile=DATA.files[0].path,returnFocus=null;
let reviewed=new Set();try{reviewed=new Set(JSON.parse(localStorage.getItem('code-guide:'+DATA.id)||'[]'));}catch{}
const audio=$('#audio');
function codeLines(source,start=1,first=0,last=first,diff=false){return source.split('\n').map((line,i)=>`<div class="line${start+i>=first&&start+i<=last?' selected':''}${diff&&line.startsWith('+')&&!line.startsWith('+++')?' added':''}${diff&&line.startsWith('-')&&!line.startsWith('---')?' removed':''}" data-line="${start+i}"><span class="ln" aria-hidden="true">${start+i}</span><span class="src">${esc(line)||' '}</span></div>`).join('');}
function codeCard(file,start,end,explanation='',context=false){const source=files.get(file).source.split('\n');const top=context?Math.max(1,start-7):start;const bottom=context?Math.min(source.length,Math.max(top+35,end+7)):end;return `<section class="code-card" data-file="${esc(file)}" data-start="${top}" data-end="${bottom}"><div class="code-bar"><span>${esc(file)} · L${start}${end!==start?'–'+end:''}</span><button data-open-file="${esc(file)}" data-line="${start}" data-end-line="${end}">Inspect full file</button></div><div class="code-scroll" tabindex="0">${codeLines(source.slice(top-1,bottom).join('\n'),top,start,end)}</div>${explanation?'<div class="code-caption">'+esc(explanation)+'</div>':''}</section>`;}
function flowDetail(node){return prose(node.text)+(node.file?'<button class="file-link" data-open-file="'+esc(node.file)+'" data-line="'+node.line+'" data-end-line="'+node.end_line+'">Inspect related source</button>':'');}
function renderBlock(block){let body='';const title=block.title?'<h2>'+esc(block.title)+'</h2>':'';
  if(block.type==='text')body=prose(block.text);
  if(block.type==='code')body=codeCard(block.file,block.line,block.end_line,block.explanation);
  if(block.type==='cards')body='<div class="grid2">'+block.items.map(item=>'<div class="card"><h3>'+esc(item.title)+'</h3>'+prose(item.text)+'</div>').join('')+'</div>';
  if(block.type==='flow')body='<div class="flow">'+block.items.map((item,i)=>`<button class="flow-node" data-flow-block="${block.id}" data-node="${item.id}" aria-pressed="${i===0}"><span class="number">${i+1}</span><b>${esc(item.title)}</b></button>`).join('')+`</div><div class="flow-detail" data-flow-detail="${block.id}">${flowDetail(block.items[0])}</div>`;
  return `<section class="block" data-block="${block.id}">${title}${body}</section>`;
}
function renderNav(){
  $('#nav').innerHTML=DATA.chapters.map((chapter,i)=>`<button class="lesson-nav" data-chapter="${i}"${i===current?' aria-current="step"':''}><span class="nav-num">${reviewed.has(i)?'✓':String(i+1).padStart(2,'0')}</span><span>${esc(chapter.title)}</span><span class="nav-time">${chapter.minutes}m</span></button>`).join('');
  $('#progress').textContent=reviewed.size+' of '+DATA.chapters.length+' chapters reviewed';
}
function persist(){try{localStorage.setItem('code-guide:'+DATA.id,JSON.stringify([...reviewed]));}catch{}renderNav();}
function render(index,scroll=true){
  audio.pause();current=index;cueIndex=-1;started=false;
  const chapter=DATA.chapters[current];const quiz=chapter.quiz;
  $('#main').innerHTML=`<div class="eyebrow">Chapter ${current+1} of ${DATA.chapters.length}<span>${chapter.minutes} minute reading budget</span></div><h1>${esc(chapter.title)}</h1><p class="intro">${esc(chapter.summary)}</p><section id="stage" class="narration-stage" hidden aria-label="Code being explained"></section><article>${chapter.blocks.map(renderBlock).join('')}</article>${quiz?`<section class="quiz"><div class="quiz-label">Quick check</div><h3>${esc(quiz.question)}</h3><div class="quiz-options">${quiz.choices.map((choice,i)=>`<button data-answer="${i}">${esc(choice)}</button>`).join('')}</div><div class="feedback" id="feedback" role="status"></div></section>`:''}<footer class="footer-nav"><button class="btn" data-previous${current===0?' disabled':''}>← Previous</button><button class="btn primary" data-next>${current===DATA.chapters.length-1?'Finish walkthrough ✓':'Mark reviewed & continue →'}</button></footer>`;
  renderNav();$('#player').hidden=!chapter.audio;$('#player').style.display=chapter.audio?'':'none';document.body.classList.toggle('no-audio',!chapter.audio);
  $('#track-title').textContent=(current+1)+'. '+chapter.title;$('#follow-label').textContent='Follow narration highlights the current lines';
  if(chapter.audio){audio.src=chapter.audio;audio.playbackRate=+$('#speed').value;updateTime();}else audio.removeAttribute('src');
  $('#transcript-title').textContent=chapter.title;
  $('#transcript-body').innerHTML=(chapter.narration||[]).map((cue,i)=>`<button class="transcript-cue" data-seek="${i}"><time>${time(cue.start||0)}</time><span>${esc(cue.text)}</span></button>`).join('');
  $('#audio-status').textContent='';history.replaceState(null,'','#chapter='+chapter.id);
  if(scroll){window.scrollTo({top:0,behavior:'instant'});$('#main').focus({preventScroll:true});}
}
function updateTime(){const chapter=DATA.chapters[current],rate=+$('#speed').value;$('#track-time').textContent=time(chapter.seconds/rate)+' this chapter · '+time(DATA.chapters.reduce((n,c)=>n+(c.seconds||0),0)/rate)+' total at this speed';}
function scrollCode(pane,line,end=line){const row=pane.querySelector('[data-line="'+line+'"]');if(!row)return;const r=row.getBoundingClientRect(),p=pane.getBoundingClientRect(),last=pane.querySelector('[data-line="'+end+'"]')?.getBoundingClientRect()||r;if(r.top<p.top+18||last.bottom>p.bottom-18)pane.scrollTo({top:pane.scrollTop+r.top-p.top-45,behavior:smooth()});}
function focusCode(reference,label){
  const stage=$('#stage'),file=files.get(reference.file),first=reference.line,last=reference.end_line;
  const existing=stage.querySelector('.code-card');const reuse=existing?.dataset.file===reference.file&&first>=+existing.dataset.start&&last<=+existing.dataset.end;
  stage.hidden=false;
  if(!reuse)stage.innerHTML='<div class="eyebrow">Now explaining <span></span></div>'+codeCard(reference.file,first,last,file.purpose,true);
  stage.querySelector('.eyebrow span').textContent=label;
  stage.querySelector('.code-bar span').textContent=reference.file+' · L'+first+(last!==first?'–'+last:'');
  const button=stage.querySelector('[data-open-file]');button.dataset.line=first;button.dataset.endLine=last;
  stage.querySelectorAll('.line').forEach(row=>row.classList.toggle('selected',+row.dataset.line>=first&&+row.dataset.line<=last));
  scrollCode(stage.querySelector('.code-scroll'),first,last);return stage;
}
function selectNode(blockId,nodeId){
  const block=DATA.chapters[current].blocks.find(block=>block.id===blockId);const node=block.items.find(node=>node.id===nodeId);
  const container=document.querySelector('[data-block="'+blockId+'"]');container.querySelectorAll('[data-node]').forEach(button=>button.setAttribute('aria-pressed',button.dataset.node===nodeId));
  container.querySelector('[data-flow-detail]').innerHTML=flowDetail(node);
}
function follow(force=false){
  const chapter=DATA.chapters[current];if(!chapter.audio||(!started&&!force))return;
  const cues=chapter.narration;let index=0;for(let i=0;i<cues.length;i++){if(cues[i].start<=audio.currentTime+.02)index=i;else break;}
  if(index===cueIndex&&!force)return;cueIndex=index;const cue=cues[index];
  $('#follow-label').textContent=($('#follow').checked?'Following: ':'Now explaining: ')+cue.label;
  document.querySelectorAll('[data-seek]').forEach(node=>node.classList.toggle('active',+node.dataset.seek===index));
  if(!$('#follow').checked)return;
  if($('#transcript-dialog').open){$('#transcript-body .active')?.scrollIntoView({block:'center',behavior:smooth()});return;}
  if($('#source-dialog').open)return;
  const previous=document.querySelector('.narration-active');document.querySelectorAll('.narration-active').forEach(node=>node.classList.remove('narration-active'));
  let target;
  if(cue.file)target=focusCode(cue,cue.label);
  else{$('#stage').hidden=true;target=document.querySelector('[data-block="'+cue.target+'"]');if(cue.node)selectNode(cue.target,cue.node);}
  if(target){target.classList.add('narration-active');const r=target.getBoundingClientRect();if(previous!==target||r.top<8||r.top>innerHeight*.4)target.scrollIntoView({block:'start',behavior:smooth()});}
}
async function play(){try{await audio.play();$('#audio-status').textContent='';}catch{$('#audio-status').textContent='Press Play to start this chapter.';}}
function fileList(){const query=$('#search').value.toLowerCase();$('#files').innerHTML=DATA.files.filter(file=>(file.path+' '+file.purpose+' '+(file.details||'')).toLowerCase().includes(query)).map(file=>`<button class="file-item${file.path===selectedFile?' active':''}" data-file-select="${esc(file.path)}"><span>${esc(file.path)}</span>${file.deleted?'<b class="file-status">Removed</b>':''}</button>`).join('')||'<p class="empty">No matching files</p>';}
function sourceFile(path,line=1,end=line,diff=false){selectedFile=path;const file=files.get(path);$('#file-explanation').innerHTML='<h3>'+esc(path)+'</h3><p><b>'+esc(file.purpose)+'</b></p>'+prose(file.details||'')+(file.deleted?'<p class="subtle">Removed file: source shown from the selected base.</p>':'');$('#diff').disabled=!file.diff;$('#source').innerHTML=codeLines(diff?file.diff:file.source,1,diff?0:line,diff?0:end,diff);$('#source').scrollTop=0;if(!diff)scrollCode($('#source'),line);fileList();}
function openSource(path,line=1,end=line){audio.pause();returnFocus=document.activeElement;$('#source-dialog').showModal();sourceFile(path,line,end);}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.chapter!==undefined)render(+button.dataset.chapter);
  else if(button.dataset.openFile)openSource(button.dataset.openFile,+button.dataset.line||1,+button.dataset.endLine||+button.dataset.line||1);
  else if(button.dataset.fileSelect)sourceFile(button.dataset.fileSelect);
  else if(button.dataset.node)selectNode(button.dataset.flowBlock,button.dataset.node);
  else if(button.dataset.answer!==undefined){const quiz=DATA.chapters[current].quiz;const correct=+button.dataset.answer===quiz.answer;document.querySelectorAll('[data-answer]').forEach(node=>node.classList.remove('correct','wrong'));button.classList.add(correct?'correct':'wrong');$('#feedback').textContent=(correct?'Correct. ':'Try again. ')+quiz.explanation;}
  else if(button.hasAttribute('data-next')){reviewed.add(current);persist();if(current<DATA.chapters.length-1)render(current+1);else button.textContent='Walkthrough reviewed ✓';}
  else if(button.hasAttribute('data-previous')&&current>0)render(current-1);
  else if(button.dataset.seek!==undefined){audio.currentTime=DATA.chapters[current].narration[+button.dataset.seek].start;started=true;follow(true);play();}
});
$('#browse').onclick=()=>openSource(selectedFile);$('#close-source').onclick=()=>$('#source-dialog').close();$('#source-dialog').onclose=()=>returnFocus?.focus();
$('#full-source').onclick=()=>sourceFile(selectedFile);$('#diff').onclick=()=>sourceFile(selectedFile,1,1,true);$('#search').oninput=fileList;
$('#theme').onclick=()=>{const dark=document.documentElement.dataset.theme!=='dark';document.documentElement.dataset.theme=dark?'dark':'light';$('#theme').textContent=dark?'Light mode':'Dark mode';};
$('#reset').onclick=()=>{reviewed.clear();persist();};
$('#replay').onclick=()=>{audio.currentTime=0;play();};$('#speed').onchange=()=>{audio.playbackRate=+$('#speed').value;updateTime();};
$('#transcript').onclick=()=>{$('#transcript-dialog').showModal();if(started)follow(true);};$('#close-transcript').onclick=()=>$('#transcript-dialog').close();$('#transcript-dialog').onclose=()=>{if(started)follow(true);$('#transcript').focus();};
$('#follow').onchange=()=>{if($('#follow').checked&&started)follow(true);else document.querySelectorAll('.narration-active').forEach(node=>node.classList.remove('narration-active'));};
audio.onplay=()=>{started=true;follow(true);};audio.ontimeupdate=()=>follow();audio.onseeked=()=>{started=true;follow(true);};
audio.onended=()=>{if($('#auto-next').checked){reviewed.add(current);persist();if(current<DATA.chapters.length-1){render(current+1);play();}else $('#audio-status').textContent='Narration complete.';}};
document.title=DATA.title;$('#guide-title').textContent=DATA.title;$('#audience').textContent=DATA.audience+' · '+DATA.minutes+' minute path';$('#snapshot').textContent=DATA.revision.startsWith('working tree')?DATA.revision.slice(0,24):'Source '+DATA.revision.slice(0,8);
const initial=new URLSearchParams(location.hash.slice(1)).get('chapter');render(Math.max(0,DATA.chapters.findIndex(chapter=>chapter.id===initial)),false);

(function(){
const MONTHS=['Tishrei','Cheshvan','Kislev','Teves','Shevat','Adar','Adar-I','Adar-II','Nisan','Iyar','Sivan','Tammuz','Av','Elul'];
const MHE={Tishrei:'תשרי',Cheshvan:'חשון',Kislev:'כסלו',Teves:'טבת',Shevat:'שבט',Adar:'אדר','Adar-I':'אדר א׳','Adar-II':'אדר ב׳',Nisan:'ניסן',Iyar:'אייר',Sivan:'סיון',Tammuz:'תמוז',Av:'אב',Elul:'אלול'};
const MDAYS={Tishrei:30,Cheshvan:30,Kislev:30,Teves:29,Shevat:30,Adar:29,'Adar-I':30,'Adar-II':29,Nisan:30,Iyar:29,Sivan:30,Tammuz:29,Av:30,Elul:29};
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const get=u=>fetch(u,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(u+' '+r.status);return r.json()});
function iso(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function srcs(x){if(!x.sources||!x.sources.length)return'';return '<details><summary>Sources ('+x.sources.length+')</summary>'+x.sources.map(s=>'<div>'+(s.url?'<a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.name)+'</a>':esc(s.name))+'</div>').join('')+'</details>'}
function person(p){
  const yrs=[p.year_heb,p.year].filter(Boolean).join(' / ');
  return '<div class="card"><div class="n">'+esc(p.name_en||'')+'</div>'+(p.name_he?'<div class="nh">'+esc(p.name_he)+'</div>':'')+
   (p.father_en||p.father_he?'<div class="f">Son of '+esc(p.father_en||'')+(p.father_he?' · <span dir="rtl">'+esc(p.father_he)+'</span>':'')+'</div>':'')+
   (yrs?'<div class="y">Niftar '+esc(yrs)+(p.adar?' · Adar '+esc(p.adar):'')+'</div>':'')+(p.who?'<div class="w">'+esc(p.who)+'</div>':'')+
   (p.burial&&p.burial.en?'<div class="y">Buried: '+(p.burial.map?'<a href="'+esc(p.burial.map)+'" target="_blank" rel="noopener">'+esc(p.burial.en)+'</a>':esc(p.burial.en))+'</div>':'')+srcs(p)+'</div>'}
function event(e){const yrs=[e.year_heb||e.year_note,e.year].filter(Boolean).join(' / ');
  return '<div class="card ev"><span class="yr">'+esc(yrs)+'</span>'+esc(e.en||'')+(e.he?'<div class="nh">'+esc(e.he)+'</div>':'')+srcs(e)+'</div>'}
function lists(y,h){return '<h2>Yahrzeits ('+y.length+')</h2>'+(y.length?y.map(person).join(''):'<p class="muted">No confirmed yahrzeits on file for this date yet.</p>')+
  (h&&h.length?'<h2>Jewish history</h2>'+h.map(event).join(''):'')}
function dayView(el,d,label){
  return get('api/day/'+iso(d)+'.json').catch(()=>get('api/'+label+'.json')).then(doc=>{
    const begins=new Date(doc.begins_evening_of+'T12:00:00');
    el.innerHTML='<div class="datehead"><div class="he" dir="rtl">'+esc(doc.hebrew_date_he)+'</div><div class="en">'+esc(doc.hebrew_date_en)+'</div><div class="civ">'+esc(doc.weekday)+', '+esc(doc.civil_date)+' · begins '+begins.toLocaleDateString('en-US',{weekday:'long'})+' evening</div></div>'+lists(doc.yahrzeits,doc.history);
  }).catch(e=>{el.innerHTML='<p class="muted">Could not load: '+esc(e.message)+'</p>'})}
const now=new Date(); const tmr=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1);
dayView($('#today'),now,'today'); let tLoaded=false;
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on',x===b));
  document.querySelectorAll('main section').forEach(s=>s.hidden=s.id!==b.dataset.tab);
  if(b.dataset.tab==='tomorrow'&&!tLoaded){tLoaded=true;dayView($('#tomorrow'),tmr,'tomorrow')}
  if(b.dataset.tab==='browse'&&!$('#month').options.length)initBrowse();
  if(b.dataset.tab==='search')$('#q').focus();
  history.replaceState(null,'','#'+b.dataset.tab);
});
const monthCache={};
function loadMonth(m){return monthCache[m]||(monthCache[m]=get('api/month/'+m+'.json'))}
function initBrowse(){const sel=$('#month');MONTHS.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m.replace('-',' ')+'  '+MHE[m];sel.appendChild(o)});
  sel.onchange=()=>showMonth(sel.value,1);
  get('api/today.json').then(t=>{const d=parseInt(t.hebrew_date_key),m=t.hebrew_date_key.split('-').slice(1).join('-');sel.value=m;showMonth(m,d)}).catch(()=>showMonth('Tishrei',1))}
function showMonth(m,day){loadMonth(m).then(doc=>{const box=$('#days');box.innerHTML='';
  for(let i=1;i<=MDAYS[m];i++){const k=i+'-'+m,b=document.createElement('button');b.textContent=i;
    if((doc.yahrzeits[k]||[]).length)b.classList.add('has');b.onclick=()=>showDay(m,i);box.appendChild(b)}
  showDay(m,day||1)})}
function showDay(m,i){loadMonth(m).then(doc=>{const k=i+'-'+m;
  document.querySelectorAll('#days button').forEach((b,j)=>b.classList.toggle('on',j+1===i));
  $('#browseOut').innerHTML='<div class="datehead"><div class="he" dir="rtl">'+esc(i)+' '+esc(MHE[m])+'</div><div class="en">'+esc(i+' '+m.replace('-',' '))+'</div>'+
   (m==='Adar'?'<div class="civ">In a leap year these are kept in Adar I, except names marked Adar II.</div>':'')+'</div>'+lists(doc.yahrzeits[k]||[],doc.history[k]||[])})}
let idx=null;const norm=s=>String(s||'').toLowerCase().normalize('NFKD').replace(/[\u0591-\u05C7]/g,'').replace(/[׳״'"`.,()\-]/g,' ').replace(/\s+/g,' ');
$('#q').oninput=()=>{const q=norm($('#q').value).trim();if(q.length<2){$('#searchOut').innerHTML='<span class="muted">Type at least 2 letters.</span>';return}
  (idx?Promise.resolve(idx):get('api/search.json').then(r=>idx=r.map(x=>({r:x,t:norm(x.slice(2).join(' '))})))).then(I=>{
   const words=q.split(' ');const hits=I.filter(x=>words.every(w=>x.t.includes(w))).slice(0,80);
   $('#searchOut').innerHTML=hits.length?hits.map(h=>{const x=h.r;const[d,...mm]=x[1].split('-');const m=mm.join('-');
     return '<div class="card hit" data-m="'+esc(m)+'" data-d="'+esc(d)+'"><div class="k">'+(x[0]==='y'?'YAHRZEIT':'HISTORY')+' · '+esc(d+' '+m.replace('-',' '))+' · <span dir="rtl">'+esc(d)+' '+esc(MHE[m])+'</span></div><div class="n">'+esc(x[2])+'</div>'+(x[3]?'<div class="nh">'+esc(x[3])+'</div>':'')+(x[5]||x[6]?'<div class="y">'+esc([x[5],x[6]].filter(Boolean).join(' / '))+'</div>':'')+'</div>'}).join(''):'<span class="muted">No match.</span>';
   document.querySelectorAll('.hit').forEach(el=>el.onclick=()=>{document.querySelector('nav button[data-tab=browse]').click();const go=()=>{$('#month').value=el.dataset.m;showMonth(el.dataset.m,parseInt(el.dataset.d))};$('#month').options.length?go():setTimeout(go,400)})})};
get('api/status.json').then(s=>{$('#built').textContent='Updated '+new Date(s.generated).toLocaleString('en-US')}).catch(()=>{});
$('#dayLink').href='api/day/'+iso(now)+'.json';
const h=location.hash.slice(1);if(h){const b=document.querySelector('nav button[data-tab="'+h+'"]');if(b)b.click()}
})();

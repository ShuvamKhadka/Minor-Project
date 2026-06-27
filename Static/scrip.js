
let files=[], jdFile=null;

function setJdFile(inp){
  jdFile=inp.files[0]||null;
  document.getElementById('jd-fname').textContent=jdFile?'📄 '+jdFile.name:'';
}

const drop=document.getElementById('drop');
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over')});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{
  e.preventDefault();drop.classList.remove('over');
  addFiles([...e.dataTransfer.files].filter(f=>/\.(pdf|docx)$/i.test(f.name)));
});

function addFiles(list){
  [...list].forEach(f=>{
    if(!files.find(x=>x.name===f.name&&x.size===f.size)) files.push(f);
  });
  renderChips();
}
function removeFile(i){files.splice(i,1);renderChips()}
function renderChips(){
  document.getElementById('chips').innerHTML=files.map((f,i)=>`
    <div class="chip">
      <span>📄</span>
      <span class="cn">${f.name}</span>
      <span style="color:var(--mute);font-size:.68rem">${(f.size/1024).toFixed(0)}kb</span>
      <button onclick="removeFile(${i})" title="Remove">✕</button>
    </div>`).join('');
}

async function submit(){
  const jdText=document.getElementById('jd').value.trim();
  const topK=document.getElementById('top-k').value;
  const btn=document.getElementById('sbtn');
  
  if(!jdText&&!jdFile){toast('Enter or upload a job description.');return}
  if(files.length===0){toast('Upload at least one resume.');return}
  if(!topK || topK < 1){toast('Please select a valid shortlist value (K >= 1).');return}
  
  btn.classList.add('loading');btn.disabled=true;
  clearResults();
  
  const fd=new FormData();
  if(jdText) fd.append('job_description',jdText);
  if(jdFile) fd.append('jd_file',jdFile);
  fd.append('top_k', topK); // Appending dynamic selection field
  files.forEach(f=>fd.append('resumes',f));
  
  try{
    const r=await fetch('/rank',{method:'POST',body:fd});
    const d=await r.json();
    if(!r.ok||d.error){toast(d.error||'Server error.');return}
    render(d.results);
  }catch{toast('Cannot reach Flask server — is it running?')}
  finally{btn.classList.remove('loading');btn.disabled=false}
}

function clearResults(){
  document.getElementById('grid').innerHTML='';
  document.getElementById('emp').style.display='flex';
  document.getElementById('cnt').textContent='0 resumes';
  ['st','sp','sa'].forEach(id=>document.getElementById(id).textContent='—');
}

function color(s){return s>=75?'var(--grn)':s>=55?'var(--sky)':s>=35?'var(--ylw)':'var(--red)'}
function lcls(l){return{Excellent:'le',Good:'lg',Potential:'lp',Low:'ll'}[l]||'ll'}
function rbcls(r){return r===1?'g':r===2?'s':r===3?'b':''}

function render(res){
  if(!res||!res.length){toast('No results returned matching your filter configurations.');return}
  document.getElementById('emp').style.display='none';
  document.getElementById('cnt').textContent=res.length+' resume'+(res.length!==1?'s':'');
  const sc=res.map(r=>r.score);
  document.getElementById('st').textContent=res.length;
  document.getElementById('sp').textContent=Math.max(...sc).toFixed(1)+'%';
  document.getElementById('sa').textContent=(sc.reduce((a,b)=>a+b)/sc.length).toFixed(1)+'%';
  const grid=document.getElementById('grid');
  grid.innerHTML='';
  res.forEach((r,i)=>{
    const d=document.createElement('div');
    d.innerHTML=card(r,i);
    const el=d.firstElementChild;
    el.style.animationDelay=i*.04+'s';
    grid.appendChild(el);
    setTimeout(()=>{const f=el.querySelector('.fill');if(f)f.style.width=r.score+'%'},60+i*35);
  });
}

function card(r,i){
  return`<div class="card r${r.rank}">
  <div class="ct">
    <div class="rb ${rbcls(r.rank)}">#${r.rank}</div>
    <div class="ci">
      <div class="cn2" title="${r.name}">${r.name}</div>
      <div class="cm"><span>📧 ${r.email}</span><span>📄 ${r.filename}</span></div>
    </div>
    <div class="csb">
      <div class="cv" style="color:${color(r.score)}">${r.score}<span style="font-size:.75rem;color:var(--mute)">%</span></div>
      <div class="cl">Match</div>
    </div>
  </div>
  <div class="meter"><div class="fill" style="background:${color(r.score)}"></div></div>
  <div class="cb">
    <span class="lbl ${lcls(r.label)}">${r.label}</span>
    <div class="acts">
      <button class="ic" id="pb${i}" onclick="togglePreview(${i})">👁 Preview</button>
      <a class="ic" href="/download/${encodeURIComponent(r.filename)}" download>⬇ Download</a>
    </div>
  </div>
  <div class="ss">
    <span>AI Semantic Match (KNN Distance): <strong>${r.score}%</strong></span>
  </div>
  <div class="pv" id="pv${i}">
    <h4>📄 Resume Preview</h4>
    <div class="pvt">${esc(r.preview)}</div>
  </div>
</div>`;
}

function togglePreview(i){
  document.getElementById('pv'+i).classList.toggle('open');
  document.getElementById('pb'+i).classList.toggle('on');
}

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function toast(m){
  const t=document.getElementById('toast');t.textContent=m;t.classList.add('on');
  setTimeout(()=>t.classList.remove('on'),3500);
}
document.getElementById('jd').addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter')submit()});

One-line summary: add a `popup=edit` popup mode that shows only the finished-video editor, replace the main-page finished view with an “Edit in popup” card, post a `vsEdited` message back to the opener after a successful apply, and add a port-based TEST pill.

---

## Edit 1 — header: add TEST pill, popup title, Close button

**Old text**
```html
<header><h1>Video Studio</h1><a href="/make" style="color:var(--acc);font-weight:600">Describe a video →</a><span class="mut">YouTube, NotebookLM audio or notes → explainer + Short</span><span style="flex:1"></span>
<span id="pw" class="pill">WanGP …</span><span id="pk" class="pill">API key …</span><button class="sec" onclick="toggleSettings()">Settings</button></header>
```

**New text**
```html
<header><h1>Video Studio</h1><a href="/make" style="color:var(--acc);font-weight:600">Describe a video →</a><span class="mut">YouTube, NotebookLM audio or notes → explainer + Short</span><span style="flex:1"></span>
<span id="testpill" class="pill test" style="display:none">TEST</span><span id="popTitle" style="display:none"></span><span id="pw" class="pill">WanGP …</span><span id="pk" class="pill">API key …</span><button class="sec" onclick="toggleSettings()">Settings</button><button id="popClose" class="sec" style="display:none" onclick="window.close()">Close</button></header>
```

---

## Edit 2 — CSS: popup layout + TEST pill

**Old text**
```css
html.embed main{grid-template-columns:1fr;padding:0;max-width:none}html.embed body{background:var(--panel)}html.embed #newvideo{border:0;margin:0}
</style></head><body>
```

**New text**
```css
html.embed main{grid-template-columns:1fr;padding:0;max-width:none}html.embed body{background:var(--panel)}html.embed #newvideo{border:0;margin:0}
html.popup body{background:var(--panel)}
html.popup header h1,html.popup header a,html.popup header span.mut,html.popup header #pw,html.popup header #pk,html.popup header button:not(#popClose),html.popup header > span[style*="flex:1"]{display:none}
html.popup #popTitle{display:inline;font-weight:600;font-size:16px}
html.popup #popClose{display:inline-block}
html.popup main{grid-template-columns:1fr;padding:0;max-width:none}
html.popup main>section:first-child{display:none}
html.popup #detail{max-width:1280px;margin:16px auto;background:transparent;border:0;padding:0}
html.popup #detail > :not(video):not(#scrub):not(#edbar):not(#edp){display:none}
.pill.test{background:#f8d7da;color:#a94442;border-color:#f1b0b7;font-size:11px;padding:2px 8px;animation:testpulse 2.4s ease-in-out infinite}
@keyframes testpulse{0%,100%{opacity:.55}50%{opacity:1}}
</style></head><body>
```

---

## Edit 3 — script start: popup flag, TEST pill show, opener listener

**Old text**
```js
let sel=null, stages=[], planCache=null, editing=false;
const EMBED=new URLSearchParams(location.search).has('embed');
{const qj=new URLSearchParams(location.search).get('job');if(qj)sel=qj;}
if(EMBED)document.documentElement.classList.add('embed');
const $=id=>document.getElementById(id);
```

**New text**
```js
let sel=null, stages=[], planCache=null, editing=false;
const EMBED=new URLSearchParams(location.search).has('embed');
const POPUP=new URLSearchParams(location.search).get('popup')==='edit';
{const qj=new URLSearchParams(location.search).get('job');if(qj)sel=qj;}
if(EMBED)document.documentElement.classList.add('embed');
if(POPUP)document.documentElement.classList.add('popup');
const $=id=>document.getElementById(id);
if(location.port!=='42021'){const tp=$('testpill');if(tp)tp.style.display='';}
function openEditPopup(id){window.open('/?job='+encodeURIComponent(id)+'&popup=edit','vsedit','width=1280,height=900');}
window.addEventListener('message',(e)=>{if(e.data&&e.data.vsEdited){sel=e.data.vsEdited;editing=false;planCache=null;lastKey='';loadJobs();}});
```

---

## Edit 4 — `loadDetail`: popup branch + finished-job card on main page

**Old text**
```js
 lastKey=key;
 const mtxt={both:`long ${s.minutes} min + Short ${fmt(Math.round(s.short_secs||165))}`,short:`${s.smoke?'Smoke test · ':''}Short ${fmt(Math.round(s.short_secs||165))}`,long:`long ${s.minutes} min`}[s.mode||'long'];
 let h=`<h2>${esc(s.title||s.url)}</h2><div class="mut">${mtxt} · <b data-testid="job-status" data-status="${esc(s.status)}" data-stage="${esc(s.stage)}">${statusText(s)}</b>${s.error?` · <span style="color:var(--bad)">${esc(s.error)}</span>`:''}</div>${outputsHtml(s)}${(s.length_warnings||[]).map(w=>`<div data-testid="length-warning" style="color:var(--bad);font-size:13px">Length miss: ${esc(w)}</div>`).join('')}`;
```

**New text**
```js
 lastKey=key;
 const fin=(s.output||s.short_output)&&!['running','queued','paused','awaiting_visuals','awaiting_review'].includes(s.status);
 if(POPUP){if(fin){$('popTitle').textContent=s.title||s.url;const useShort=s.short_output&&!(s.output&&s.edit_target=='long');const relSrc=useShort?s.short_output:s.output;if(relSrc){const rel=relSrc.replace(/\\/g,'/').split('/').slice(-2).join('/');$('detail').innerHTML=`<video id="ov" controls src="/files/${sel}/${rel}?t=${Date.now()}" ontimeupdate="edTick()" onloadedmetadata="scDraw()" onplay="scTick()" onpause="scTick()"></video><div id="scrub"></div><div id="edbar"></div><div id="edp"></div>`;edInit();return}}else{$('detail').innerHTML='<p class="mut">This job is not finished yet.</p>';return}}
 if(!POPUP&&fin){const mode=s.mode||'long';const cardMt={both:`long ${s.minutes} min + Short ${fmt(Math.round(s.short_secs||165))}`,short:`${s.smoke?'Smoke test · ':''}Short ${fmt(Math.round(s.short_secs||165))}`,long:`long ${s.minutes} min`}[mode];const kindTxt={both:'Long + Short',short:'Short',long:'Explainer'}[mode];$('detail').innerHTML=`<div class="job" style="display:flex;gap:16px;align-items:center"><div style="flex:1;min-width:0"><b>${esc(s.title||s.url)}</b><div class="mut" style="font-size:12px">${kindTxt} · ${cardMt}</div><button style="margin-top:10px" onclick="openEditPopup('${sel}')">Edit in popup ↗</button></div><div id="thumbp" style="width:180px;flex:0 0 auto"></div></div>`;if(s.thumbnail)showThumb(s);return}
 const mtxt={both:`long ${s.minutes} min + Short ${fmt(Math.round(s.short_secs||165))}`,short:`${s.smoke?'Smoke test · ':''}Short ${fmt(Math.round(s.short_secs||165))}`,long:`long ${s.minutes} min`}[s.mode||'long'];
 let h=`<h2>${esc(s.title||s.url)}</h2><div class="mut">${mtxt} · <b data-testid="job-status" data-status="${esc(s.status)}" data-stage="${esc(s.stage)}">${statusText(s)}</b>${s.error?` · <span style="color:var(--bad)">${esc(s.error)}</span>`:''}</div>${outputsHtml(s)}${(s.length_warnings||[]).map(w=>`<div data-testid="length-warning" style="color:var(--bad);font-size:13px">Length miss: ${esc(w)}</div>`).join('')}`;
```

---

## Edit 5 — `edWait`: notify opener after successful apply

**Old text**
```js
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.';}}
```

**New text**
```js
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
 if(POPUP&&window.opener){try{window.opener.postMessage({vsEdited:sel},'*')}catch(e){}}
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.';}}
```

---

## How Claude should test

1. Serve the app on a non-42021 port, e.g. `http://127.0.0.1:8080/?job=<finished_job_id>`.
   - Header should show the small pulsing **TEST** pill.
2. On the same non-42021 port, open the main Video Studio page and select a finished job.
   - The detail pane should now show the compact card: title, kind/duration, thumbnail if available, and **Edit in popup ↗**.
   - Running/unfinished jobs should still show the existing inline progress view unchanged.
3. Click **Edit in popup ↗**.
   - A `vsedit` popup should open at `/?job=<id>&popup=edit`.
   - The popup should show only: slim header with job title + Close, the video, the scrubber/beat strip, and the beat editor panel.
4. Make an edit in the popup and apply it.
   - The popup’s log should say **Applied**.
   - The opener/main page should receive the `vsEdited` message and reload that job’s card.
5. Repeat on the live port `42021` to confirm the TEST pill is hidden.

---

## Unsure / needed

- The excerpt did not include `showThumb()`; I kept the existing `if(s.thumbnail)showThumb(s)` call and added a `#thumbp` container in the main card, assuming the existing function writes into `#thumbp`. If `showThumb()` expects a different target, point me at its body and I’ll adjust.
- The popup branch only renders the editor when the job has an output file; for a non-finished `popup=edit` URL it shows “This job is not finished yet.” That should be fine since the main page only opens popups for finished jobs, but flag it if you expected the full progress view there.
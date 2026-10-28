# Task: Video Studio — beat editor in a POPUP window + port-based TEST pill (branch feature/unified-ui)

Tariq wants the Newsroom pattern in Video Studio: the scrubber/video and EVERY editing control in a popup window,
not inline on the main page. Video Studio's UI is one file: `app/static/index.html` (inline CSS + JS, excerpts
below; the light theme is already applied). Keep every existing API call and editor function working.

## Design (please follow it; it keeps the change small)
1. POPUP MODE of the same page: `/?job=<id>&popup=edit` (window name `vsedit`, reused). In popup mode the page shows
   ONLY: a slim header (job title + Close), the finished video `#ov` with its scrubber and beat strip (`#edbar`),
   and the beat editor panel `#edp` (all six panes: candidates, fit, actions, preview, chat, log) — i.e. everything
   loadDetail()/edInit()/edOpen()/edDraw() render today for a finished job. Hide the job list, the New-video form,
   settings and everything else (a body class `popup` + CSS is fine).
2. MAIN PAGE: where loadDetail() renders the finished video and editor for a finished job, render instead a compact
   card (title, kind, duration, thumbnail if available) with a button "Edit in popup ↗" that does
   `window.open('/?job='+sel+'&popup=edit','vsedit','width=1280,height=900')`. Running/unfinished jobs keep today's
   inline progress view unchanged.
3. After an edit is applied in the popup (where edWait()/edApply finish with "Applied"), `window.opener.postMessage
   ({vsEdited: sel}, '*')`; the main page listens and reloads that job's card. Popup keeps a Close button
   (window.close()).
4. TEST pill: if `location.port !== '42021'` (the live port), show a small, slowly pulsing pill "TEST" in the header
   (both modes), same look as the Newsroom/Publisher one: rounded, pale pink background, dark-pink text, 11px, gentle
   opacity pulse. Not loud.
5. Larger type only where Tariq edits (already: narration 16.5px, chat 15.5px, text boxes 16px) — keep.

## Answer format
Exact search/replace edits against index.html: for each edit, the EXACT old text (copied from the excerpts, unique in
the file) and the new text. Plus any new CSS block and new functions as complete code. Then how to test.
Do not rewrite unrelated functions.

## Excerpts of app/static/index.html
### CSS (lines 4-66)
```html
<style>
:root{--bg:#f3f0e9;--panel:#ffffff;--line:#ccd3da;--fg:#1d2733;--mut:#5d6b7a;--acc:#e8930c;--ok:#1a9e6b;--bad:#d93a3a;--blue:#2f7fe0;--inset:#f8f5ef}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
header{display:flex;align-items:center;gap:16px;padding:14px 24px;border-bottom:1px solid var(--line)}
h1{font-size:20px;margin:0}h2{font-size:16px;margin:0 0 12px}.mut{color:var(--mut)}
.pill{padding:3px 10px;border-radius:99px;font-size:12px;border:1px solid var(--line)}.pill.ok{color:var(--ok);border-color:var(--ok)}.pill.bad{color:var(--bad);border-color:var(--bad)}
main{display:grid;grid-template-columns:380px 1fr;gap:20px;padding:20px 24px;max-width:1500px;margin:auto}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
label{display:block;font-size:13px;color:var(--mut);margin:10px 0 4px}
input[type=text],input[type=password],textarea,select{width:100%;background:var(--inset);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:9px 10px;font:inherit}
textarea{min-height:90px;resize:vertical}
button{background:var(--acc);color:#111;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer}
button.sec{background:transparent;color:var(--fg);border:1px solid var(--line)}button:disabled{opacity:.5;cursor:default}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.job{padding:10px;border:1px solid var(--line);border-radius:8px;margin-bottom:8px;cursor:pointer}.job.sel{border-color:var(--acc)}
.stages{display:flex;gap:4px;flex-wrap:wrap;margin:10px 0}.st{font-size:12px;padding:3px 8px;border-radius:6px;background:var(--inset);border:1px solid var(--line);color:var(--mut)}
.st.done{color:#fff;background:#1a9e6b;border-color:#1a9e6b}.st.cur{color:#111;background:var(--acc);border-color:var(--acc);font-weight:700}
pre{background:var(--inset);border:1px solid var(--line);border-radius:8px;padding:10px;max-height:320px;overflow:auto;font-size:12.5px;white-space:pre-wrap}
.sc button.on{background:var(--acc);color:#111;border-color:var(--acc)}.sc{border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin:8px 0}.sc-strip{position:relative;height:22px;margin-top:4px}
.sc-seg{position:absolute;top:0;height:20px;box-sizing:border-box;border:1px solid var(--line);border-radius:4px;font-size:11px;line-height:18px;text-align:center;overflow:hidden;cursor:pointer;background:rgba(127,127,127,.12)}
.sc-seg.off{opacity:.45;cursor:default}.sc-seg.cur{background:var(--acc);color:#111;font-weight:700}
.sec-edit{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}.sec-edit input{font-weight:600}
video{width:100%;border-radius:8px;margin-top:10px}
details summary{cursor:pointer;color:var(--mut);font-size:13px;margin-top:10px}
.script-doc{margin-top:18px;background:var(--inset);border:1px solid var(--line);border-radius:10px;padding:22px 26px;max-height:none}.script-doc h1{font-size:22px;margin:6px 0 4px}.script-doc .sub{color:var(--mut,#9aa4b2);margin:0 0 14px;font-style:italic}.script-doc h3{font-size:16px;margin:20px 0 6px}.script-doc p{line-height:1.65;margin:0;font-size:15.5px}
main>section{min-width:0}
.rv-beat{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0;background:var(--inset)}.rv-beat.unsure{border-color:#d29922}.rv-beat.done{opacity:.8}
.dbg{border-color:#d29922!important}.dbg-chain{font-size:12.5px;margin:4px 0 0 0;padding-left:18px}.dbg-chat{max-height:260px;overflow:auto;font-size:13px;margin:6px 0}
.dbg-chat .you{color:var(--fg);margin-top:6px}.dbg-chat .ai{color:#4a5a6a;white-space:pre-wrap}.dbg-bp{display:inline-block;border:1px solid var(--line);border-radius:12px;padding:1px 8px;margin:2px 4px 2px 0;font-size:12.5px}
.rv-row{display:flex;gap:10px;overflow-x:auto;padding:8px 0}.rv-c{flex:0 0 120px;font-size:11.5px;line-height:1.3}
.rv-c img{width:120px;height:213px;object-fit:cover;border-radius:6px;border:2px solid var(--line);cursor:pointer;display:block;background:#000}
.rv-c.sel img{border-color:var(--acc)}.rv-c.auto img{box-shadow:0 0 0 2px var(--blue)}.rv-c .bad{color:var(--bad)}.rv-c .ok{color:var(--ok)}
.rv-c .wrn{position:relative}.rv-c .wrn:after{content:"⚠";position:absolute;top:6px;right:8px;font-size:22px;color:#ffcc00;text-shadow:0 0 4px #000}
.rv-badge{font-size:12px;padding:2px 8px;border-radius:6px;border:1px solid var(--line)}.rv-prev{margin:6px 0}.rv-prev video,.rv-prev img{max-height:420px;width:auto;border-radius:8px}
.rv-note{font-size:12.5px;color:var(--mut);border-left:2px solid var(--line);padding-left:8px;margin:4px 0}
.edp-card{padding:14px}.edp-head{display:flex;align-items:flex-start;gap:10px}.edp-meta{font-size:12px;color:var(--mut);margin-top:2px}
.edp-vo{font-size:16.5px;line-height:1.5;margin:10px 0;padding:8px 10px;border-left:3px solid var(--acc);background:rgba(245,165,36,.06);border-radius:4px}
.edp-lab{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin-bottom:2px}
.edp-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:12px}@media(max-width:1000px){.edp-grid{grid-template-columns:1fr}}
.edp-col{display:flex;flex-direction:column;gap:12px;min-width:0}
.edp{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:14px}.edp-t{font-size:15px;font-weight:700;margin:0 0 8px;letter-spacing:.01em}
.edp-sub{font-size:11.5px;font-weight:400;color:var(--mut);margin-left:6px}.edp-help{font-size:12px;color:var(--mut);margin-bottom:6px;line-height:1.45}.edp-empty{font-size:12.5px;color:var(--mut);font-style:italic;padding:6px 0}
.p-cand{background:#e9f1fd}.p-fit{background:#f1eafd}.p-act{background:#e7f5ec}.p-prev{background:#fdf3d8;border-color:#d9c58a}.p-chat{background:#fdeee2}.p-log{background:#eef0f2}
.edp-user{color:var(--ok)}
.edc .edc-name{font-weight:700;font-size:12.5px;margin-top:4px}.edc .edc-meta{font-size:11px;color:var(--mut);line-height:1.3}.edc .edc-rej{font-size:11px;color:var(--bad);line-height:1.3}
.edc-src{position:absolute;left:6px;top:6px;font-size:10.5px;font-weight:800;letter-spacing:.06em;padding:2px 6px;border-radius:4px;color:#111}
.src-file{background:#5bd68a}.src-ai{background:#c49bff}.src-generated{background:#7fc4ff}
.edc-use{display:flex!important;align-items:center;gap:6px;margin:6px 0 0!important;padding:4px 8px;border:1px solid var(--line);border-radius:6px;color:var(--fg)!important;font-size:12.5px!important;font-weight:600;cursor:pointer;background:var(--inset)}
.edc-use input{width:17px;height:17px;accent-color:var(--acc);margin:0}.edc.sel .edc-use{border-color:var(--acc);background:rgba(245,165,36,.12)}
.edp-chat{max-height:320px;display:flex;flex-direction:column;gap:6px}.cm{max-width:88%}.cm-b{padding:7px 10px;border-radius:10px;white-space:pre-wrap;font-size:15.5px;line-height:1.45}
.cm-m{font-size:10.5px;color:var(--mut);margin:2px 4px 0}.cm-you{align-self:flex-end;text-align:right}.cm-you .cm-b{background:#1f4b7a;color:#fff;border-bottom-right-radius:3px;text-align:left}
.cm-ai{align-self:flex-start}.cm-ai .cm-b{background:#eceff2;color:var(--fg);border-bottom-left-radius:3px}
.cm-sys{align-self:center;max-width:95%;font-size:11.5px;color:#7a5d00;background:rgba(227,179,65,.14);border:1px dashed rgba(180,140,40,.45);border-radius:6px;padding:3px 8px;font-family:ui-monospace,Consolas,monospace}
.edp-log .lg{font-size:12.5px;padding:3px 0;border-bottom:1px solid rgba(0,0,0,.07)}.edp-log .lg:empty{display:none}.lg-ok{color:var(--ok)}.lg-bad{color:var(--bad)}.lg-busy{color:var(--acc)}.lg-meta{font-size:11.5px;color:var(--mut)}
.ed-last{font-size:12.5px}
.ed-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}.ed-fit button{padding:5px 10px;font-size:12.5px}.ed-fit button.on{background:var(--acc);color:#111;border-color:var(--acc)}
.src-note{font-size:13.5px;color:var(--mut);border-left:3px solid var(--blue);background:rgba(47,127,224,.07);padding:5px 9px;margin:2px 0 6px;border-radius:4px}
.edp-card textarea,.edp-card input[type=text]{font-size:16px}
.sec-edit textarea{font-size:17px;line-height:1.5}.sec-edit input{font-size:16px}
html.embed header,html.embed #settings,html.embed main>section:last-child,html.embed main>section>.card:not(#newvideo){display:none!important}
html.embed main{grid-template-columns:1fr;padding:0;max-width:none}html.embed body{background:var(--panel)}html.embed #newvideo{border:0;margin:0}
</style></head><body>
```
### header + main markup (lines 67-125)
```html
<header><h1>Video Studio</h1><a href="/make" style="color:var(--acc);font-weight:600">Describe a video →</a><span class="mut">YouTube, NotebookLM audio or notes → explainer + Short</span><span style="flex:1"></span>
<span id="pw" class="pill">WanGP …</span><span id="pk" class="pill">API key …</span><button class="sec" onclick="toggleSettings()">Settings</button></header>
<main>
<section>
 <div class="card" id="settings" style="display:none"><h2>Settings</h2>
  <label>Script AI</label><select id="sp"><option value="zai">z.ai GLM (cheap API)</option><option value="deepseek">DeepSeek (cheap API)</option><option value="claude">Claude API (best quality)</option><option value="local">Local AI via Ollama (free, no key)</option></select>
  <label>Image check AI</label><select id="qp"><option value="zai">z.ai GLM vision</option><option value="deepseek">DeepSeek</option><option value="claude">Claude</option><option value="off">Off</option></select>
  <p class="mut" style="font-size:12px;margin:6px 0 0">Keys are saved in the Windows Credential Manager vault (entry "ExplainerStudio"), encrypted to your Windows login, never in a file. Type delete in a key box and Save to remove it.</p>
  <label>z.ai API key</label><input id="zk" type="password" placeholder="z.ai key">
  <label>z.ai model</label><input id="zm" type="text"><label>z.ai vision model</label><input id="zv" type="text">
  <label>z.ai Anthropic-compatible URL</label><input id="zu" type="text"><label>z.ai OpenAI-compatible URL (for vision)</label><input id="zo" type="text">
  <label>DeepSeek API key</label><input id="dk" type="password" placeholder="sk-...">
  <label>DeepSeek model</label><input id="dm" type="text">
  <label>Anthropic API key</label><input id="k" type="password" placeholder="sk-ant-...">
  <label>Claude script model</label><input id="sm" type="text"><label>Claude image-check model</label><input id="qm" type="text">
  <label>Target narration speed (words per minute)</label><input id="wpm" type="text">
  <label>Motion share (0–0.3; lower = faster renders)</label><input id="ms" type="text">
  <label><input id="iqa" type="checkbox"> Automatic image QA (catches deformed people/robots)</label>
  <label>Stock-clip vetting AI (for Shorts)</label><select id="vp"><option value="local">Local vision model via Ollama (free)</option><option value="zai">z.ai GLM vision</option><option value="claude">Claude</option><option value="off">Off (take Pexels' top results unchecked)</option></select>
  <label>Local vetting model (Ollama)</label><input id="vm" type="text">
  <label>WanGP MCP URL (leave blank to find it automatically)</label><input id="wu" type="text" placeholder="e.g. http://127.0.0.1:8000/mcp">
  <label><input id="poq" type="checkbox"> When review is skipped, still pause if the fact-check raises questions</label>
  <label>Channel name (shown on the Short's 9:16 thumbnail; blank = none)</label><input id="chn" type="text">
  <div class="row" style="margin-top:12px"><button onclick="saveSettings()">Save</button><button class="sec" onclick="testKey()">Test saved keys</button><button class="sec" onclick="smoke()" aria-label="Run smoke test">Run smoke test (30-second Short)</button><span id="ssaved" class="mut"></span></div>
 </div>
 <div class="card" id="newvideo" data-testid="new-video-form"><h2>New video</h2>
  <label>Source</label><select id="srck" data-testid="input-type" aria-label="Source" onchange="srcUI()"><option value="yt">YouTube link</option><option value="file">Upload a file (NotebookLM audio, .mp3/.m4a/.wav, or .pdf/.docx/.txt/.md)</option><option value="text">Paste text (notes, briefing doc)</option></select>
  <div id="s_yt"><label>YouTube link</label><input id="url" data-testid="youtube-url" aria-label="YouTube link" type="text" placeholder="https://www.youtube.com/watch?v=...">
   <details><summary>Paste a transcript too (if the video has no captions)</summary><textarea id="tx" data-testid="transcript-text"></textarea></details></div>
  <div id="s_file" style="display:none"><label>File</label><input id="upf" data-testid="file-upload" type="file" accept=".mp3,.m4a,.wav,.aac,.ogg,.flac,.opus,.webm,.mp4,.txt,.md,.pdf,.docx">
   <label>…or a file path on this PC</label><input id="upp" data-testid="file-path" aria-label="File path on this PC" type="text" placeholder="F:\notebooklm\briefing.m4a"></div>
  <div id="s_text" style="display:none"><label>Text</label><textarea id="ptx" data-testid="source-text" aria-label="Source text" rows="8" placeholder="Paste NotebookLM notes, a briefing doc, an article..."></textarea></div>
  <div id="s_meta" style="display:none"><label>Title of the source (shown in credits)</label><input id="stt" data-testid="source-title" aria-label="Source title" type="text" placeholder="e.g. The economics of AI agents">
   <label>Credit (who made it)</label><input id="scr" data-testid="source-credit" aria-label="Source credit" type="text" placeholder="e.g. NotebookLM, or the author's name"></div>
  <label>Make</label><select id="mode" data-testid="output-mode" aria-label="Make" onchange="srcUI()"><option value="both">Long explainer + Short</option><option value="short">Short only</option><option value="long">Long explainer only</option><option value="smoke">Smoke test (30-second Short, pipeline check)</option></select>
  <div id="s_clips" style="display:none"><details data-testid="provide-clips"><summary>Provide clips (your own footage, mixed with generated visuals)</summary>
   <label>Video clips (one or more)</label><input id="clipf" data-testid="clip-upload" type="file" multiple accept=".mp4,.mov,.m4v,.mkv,.webm,.avi,.mts">
   <label>…or clip paths on this PC (one per line)</label><textarea id="clipp" data-testid="clip-paths" rows="2" placeholder="F:\footage\church_outside.mp4"></textarea>
   <label>Which clip goes where (optional)</label><textarea id="cliph" data-testid="clip-hints" rows="2" placeholder="clip 1 is the church exterior, clip 2 is the interior through bars   — or —   clip1=beat3, clip2=beat5,6"></textarea>
   <div class="mut" style="font-size:12.5px">Clips are numbered in the order chosen (uploads first, then paths). Beats your footage doesn't cover get the usual generated visuals; you can move clips in the timeline editor.</div></details></div>
  <div id="m_short"><label>Short length: <b id="sv">2:45</b> (YouTube Shorts max is 3:00)</label><input id="ssec" data-testid="short-length" aria-label="Short length" type="range" min="120" max="176" step="5" value="165" oninput="sv.textContent=fmt(+this.value)" onchange="sv.textContent=fmt(+this.value)" style="width:100%"></div>
  <div id="m_long"><label>Long video length: <b id="mv">15</b> minutes</label><input id="min" data-testid="long-length" aria-label="Long video length" type="range" min="3" max="20" value="15" oninput="mv.textContent=this.value" onchange="mv.textContent=this.value" style="width:100%">
   <label><input id="caps" data-testid="toggle-captions" type="checkbox" checked> Animated captions with icons</label>
   <label><input id="pres" data-testid="toggle-presenter" type="checkbox"> On-screen presenter (small corner window, experimental)</label></div>
  <label>Narration</label><select id="ttse" data-testid="narration-engine" aria-label="Narration"><option value="">Settings default (Kokoro, falls back to WanGP)</option><option value="kokoro">Kokoro (fast preset voice)</option><option value="wanGP">WanGP cloned voice (slow)</option></select>
  <label>Audience</label><select id="aud" data-testid="audience" aria-label="Audience"><option value="">Settings default (Common)</option><option value="common">Common: plain language, jargon explained on first use</option><option value="beginner">Beginner</option><option value="informed">Informed: technical terms used freely</option><option value="expert">Expert: jargon throughout, no hand-holding</option></select>
  <label>Script AI for this video</label><select id="jp" data-testid="script-ai" aria-label="Script AI"><option value="">Use Settings default</option><option value="zai">z.ai GLM</option><option value="deepseek">DeepSeek</option><option value="claude">Claude</option><option value="local">Local AI (Ollama)</option></select>
  <div id="m_vr"><label>Visuals (Shorts)</label><select id="vrev" data-testid="visuals-mode" aria-label="Visuals (Shorts)"><option value="never" selected>Decide everything: never pause, make the best call when unsure</option><option value="auto">Auto: pick automatically, pause only when unsure</option><option value="every">Review every beat: make every treatment, pause to choose</option></select></div>
  <label><input id="auto" data-testid="toggle-skip-script-review" type="checkbox" checked> Skip script review (render straight away; untick to read and edit the script first)</label>
  <details id="dbgd" data-testid="debug-options" style="margin-top:8px"><summary>Debug (breakpoints)</summary>
   <label style="color:var(--fg)"><input type="checkbox" id="dbgon" data-testid="toggle-debug" aria-label="Debug mode"> Debug mode: pause when a breakpoint matches (off = runs as normal)</label>
   <label for="dbgbps">Breakpoints, one per line (checked after each beat's visuals are decided)</label>
   <textarea id="dbgbps" data-testid="debug-breakpoints" aria-label="Breakpoints" rows="3" placeholder="stock_found == 0&#10;beat == 3&#10;treatment == stock|photo|still|animate|parallax|3d|card&#10;escalated_past == stock&#10;narration contains &quot;word&quot;"></textarea></details>
  <div class="row" style="margin-top:12px"><button data-testid="make-video" id="makebtn" aria-label="Make video" onclick="createJob()">Make video</button><button class="sec" id="stopbtn" data-testid="stop-video" aria-label="Stop video" style="display:none;border-color:var(--bad);color:var(--bad)" onclick="stopVideo()">Stop video</button><span id="jobrun" data-testid="job-running" style="font-weight:600"></span><span id="cmsg" data-testid="make-message" class="mut"></span></div>
 </div>
 <div class="card"><h2>Jobs</h2><div class="row" id="openrow" style="margin-bottom:6px;display:none"><input type="text" id="openid" data-testid="open-job-id" placeholder="Open a job by ID (e.g. 20261011_192216)" style="flex:1" onkeydown="if(event.key=='Enter')openJob()"><button class="sec" data-testid="open-job" onclick="openJob()">Open</button></div><div id="jobs" class="mut">No jobs yet.</div></div>
</section>
<section><div class="card" id="detail"><span class="mut">Select a job to see progress.</span></div></section>
</main>
```
### script start, job list and loadDetail (lines 126-200)
```js
<script>
let sel=null, stages=[], planCache=null, editing=false;
const EMBED=new URLSearchParams(location.search).has('embed');
{const qj=new URLSearchParams(location.search).get('job');if(qj)sel=qj;}
if(EMBED)document.documentElement.classList.add('embed');
const $=id=>document.getElementById(id);
async function j(u,o){const r=await fetch(u,o);if(!r.ok)throw new Error(await r.text());return r.json()}
function toggleSettings(){const s=$('settings');s.style.display=s.style.display=='none'?'block':'none';loadSettings()}
async function flagsUI(){try{const s=await j('/api/settings');if($('s_clips'))$('s_clips').style.display=s.own_clips?'':'none';if($('openrow'))$('openrow').style.display=s.post_edit_v2?'':'none'}catch(e){}}
async function loadSettings(){const s=await j('/api/settings');$('k').value=s.anthropic_api_key;$('sm').value=s.script_model;$('qm').value=s.qa_model;$('wpm').value=s.wpm;$('ms').value=s.motion_share;$('iqa').checked=s.image_qa;$('sp').value=s.script_provider;$('qp').value=s.qa_provider;$('zk').value=s.zai_api_key;$('zm').value=s.zai_model;$('zv').value=s.zai_vision_model;$('zu').value=s.zai_base_url;$('zo').value=s.zai_openai_url;$('dk').value=s.deepseek_api_key;$('dm').value=s.deepseek_model;$('vp').value=s.vet_provider;$('vm').value=s.vet_model;$('poq').checked=!!s.pause_on_questions;$('wu').value=s.wangp_mcp||'';$('chn').value=s.channel_name||'';if($('s_clips'))$('s_clips').style.display=s.own_clips?'':'none';if($('openrow'))$('openrow').style.display=s.post_edit_v2?'':'none'}
async function testKey(){$('ssaved').textContent='Testing...';const st=await j('/api/status');const ps=[['zai',st.zai_key],['deepseek',st.deepseek_key],['claude',st.api_key]].filter(x=>x[1]).map(x=>x[0]);if(!ps.length){$('ssaved').textContent='No keys saved yet';return}let out=[];for(const p of ps){const r=await j('/api/test_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:p})});out.push((r.ok?'✓ ':'✗ ')+r.msg)}$('ssaved').innerHTML=out.map(esc).join('<br>')}
async function saveSettings(){await j('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({anthropic_api_key:$('k').value,script_model:$('sm').value,qa_model:$('qm').value,wpm:+$('wpm').value,motion_share:+$('ms').value,image_qa:$('iqa').checked,script_provider:$('sp').value,qa_provider:$('qp').value,zai_api_key:$('zk').value,zai_model:$('zm').value,zai_vision_model:$('zv').value,zai_base_url:$('zu').value,zai_openai_url:$('zo').value,deepseek_api_key:$('dk').value,deepseek_model:$('dm').value,vet_provider:$('vp').value,vet_model:$('vm').value,pause_on_questions:$('poq').checked,wangp_mcp:$('wu').value.trim(),channel_name:$('chn').value.trim()})});$('ssaved').textContent='Saved';status()}
async function status(){try{const s=await j('/api/status');stages=s.stages;$('pw').textContent=s.wangp?'WanGP running':(s.wangp_on_demand?'WanGP: starts on demand':'WanGP not available');$('pw').className='pill '+(s.wangp||s.wangp_on_demand?'ok':'bad');const pn={deepseek:'DeepSeek',zai:'z.ai',claude:'Claude',local:'Local AI'}[s.provider]||s.provider;const rdy=s.provider=='local'||(s.provider=='zai'?s.zai_key:s.provider=='deepseek'?s.deepseek_key:s.api_key);$('pk').textContent='Script: '+pn+(rdy?'':' (no key)');$('pk').className='pill '+(rdy?'ok':'bad')}catch(e){}}
function fmt(x){return Math.floor(x/60)+':'+String(x%60).padStart(2,'0')}
function srcUI(){const k=$('srck').value,m=$('mode').value;$('s_yt').style.display=k=='yt'?'':'none';$('s_file').style.display=k=='file'?'':'none';$('s_text').style.display=k=='text'?'':'none';$('s_meta').style.display=k=='yt'?'none':'';$('m_short').style.display=m=='long'||m=='smoke'?'none':'';$('m_long').style.display=m=='short'||m=='smoke'?'none':'';$('m_vr').style.display=m=='long'?'none':''}
let RUNJOB=null,STARTING=false;
const BUSY=['running','queued','paused','awaiting_visuals','awaiting_review'];
function runUI(js){const r=(js||[]).find(x=>BUSY.includes(x.status));RUNJOB=r?r.id:null;const busy=!!r||STARTING;
 $('makebtn').disabled=busy;$('makebtn').title=busy?'A job is running: stop it or wait for it to finish':'';$('stopbtn').style.display=r?'':'none';
 $('jobrun').textContent=r?('● '+({running:'Job running',queued:'Job queued',paused:'Job paused',awaiting_visuals:'Job waiting for your visual choices',awaiting_review:'Job waiting for script review'}[r.status]||'Job active')+': '+(r.title||r.id).slice(0,60)+(r.cancel_req?' · stopping at the next safe point…':'')):'';$('jobrun').style.color=r?'var(--acc)':''}
async function stopVideo(){if(!RUNJOB)return;$('stopbtn').disabled=true;try{const d=await j(`/api/jobs/${RUNJOB}/stop`,{method:'POST'});$('cmsg').textContent=d.state=='stopping'?'Stopping at the next safe point (never mid-render)…':'Stopped.'}catch(e){$('cmsg').textContent=e.message}$('stopbtn').disabled=false;loadJobs()}
async function createJob(){if(RUNJOB||STARTING)return;STARTING=true;$('makebtn').disabled=true;$('cmsg').textContent='Starting...';const k=$('srck').value;const fd=new FormData();
 const f={mode:$('mode').value,short_secs:$('ssec').value,minutes:$('min').value,presenter:$('pres').checked,captions:$('caps').checked,auto_approve:$('auto').checked,provider:$('jp').value,visual_review:$('vrev').value,tts_engine:$('ttse').value,audience:$('aud').value,debug:$('dbgon').checked,breakpoints:$('dbgbps').value,src_title:$('stt').value,src_credit:$('scr').value,
  url:k=='yt'?$('url').value.trim():'',transcript:k=='yt'?$('tx').value:k=='text'?$('ptx').value:''};
 for(const x in f)fd.append(x,f[x]);
 if($('s_clips')&&$('s_clips').style.display!='none'){for(const cf of $('clipf').files)fd.append('clips',cf);fd.append('clip_paths',$('clipp').value);fd.append('clip_hints',$('cliph').value)}
 if(k=='file'){if($('upf').files.length)fd.append('file',$('upf').files[0]);else if($('upp').value.trim())fd.append('src_path',$('upp').value.trim());else{$('cmsg').textContent='Choose a file (or type its path) first.';STARTING=false;$('makebtn').disabled=false;return}}
 try{const r=await fetch('/api/jobs',{method:'POST',body:fd});const d=await r.json();if(!r.ok)throw new Error(d.error||'failed');sel=d.id;if(EMBED)parent.postMessage({vsJob:d.id},'*');$('url').value='';$('upp').value='';$('ptx').value='';$('upf').value='';if($('clipf')){$('clipf').value='';$('clipp').value='';$('cliph').value=''}$('cmsg').textContent='';STARTING=false;loadJobs()}catch(e){$('cmsg').textContent=e.message;STARTING=false;$('makebtn').disabled=false}}
async function openJob(){const id=($('openid').value||'').trim();if(!id)return;try{await j(`/api/jobs/${id}`)}catch(e){alert('No job '+id);return}sel=id;editing=false;planCache=null;lastKey='';loadJobs()}
async function loadJobs(){const js=await j('/api/jobs');runUI(js);$('jobs').innerHTML=js.length?js.map(x=>`<div class="job ${x.id==sel?'sel':''}" onclick="sel='${x.id}';editing=false;planCache=null;loadJobs()"><b>${esc(x.title||x.url||x.id)}</b><div class="mut" style="font-size:12px">${x.id} · ${x.cancelled&&x.status=='stopped'?'cancelled':x.status} · ${x.stage}</div></div>`).join(''):'No jobs yet.';if(sel)loadDetail()}
function esc(s){return String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
let lastKey='';
// one status line per output (Short / Explainer): finished (with file), working (stage, beat n of N), or waiting
const STAGE_NAME={transcript:'transcript',script:'script',short_script:'script',review:'script review',short_stock:'stock footage',short_voice:'narration',
 short_fallback:'visuals',short_review:'visual review',short_render:'rendering',charts:'charts',voice:'narration',captions:'captions',broll:'stock footage',
 presenter:'presenter',motion:'motion clips',stills:'stills',assemble:'rendering'};
function outputsHtml(s){const p=s.prog||{},m=s.mode||'long',rows=[],busy=['running','queued','paused','awaiting_visuals','awaiting_review'].includes(s.status);
 const one=(name,key,file)=>{let t;
  if(file)t=`✓ Finished <code style="font-size:12px">${esc(file.replace(/\\/g,'/').split('/').slice(-1)[0])}</code>`;
  else if(busy&&(p.out===key||p.out==='both'))t=`<b>${s.status=='running'?'Working':esc(statusText(s))}</b> — ${esc(STAGE_NAME[p.stage||s.stage]||p.stage||s.stage||'')}${p.of?` · ${key=='short'?'Beat':'Section'} ${p.n} of ${p.of}`:''}`;
  else if(s.status=='finished')t='—';else t=busy?'Waiting':esc(s.status||'');
  rows.push(`<div data-testid="output-${key}" style="font-size:13.5px">${name}: ${t}</div>`)};
 if(m=='short'||m=='both')one('Short','short',s.short_output);
 if(m=='long'||m=='both')one('Explainer','explainer',s.output);
 return rows.length?`<div style="margin:6px 0">${rows.join('')}</div>`:''}
function hk(x){let h=0;x=String(x||'');for(let i=0;i<x.length;i++)h=(h*31+x.charCodeAt(i))|0;return (h>>>0).toString(36)}   // thumbnail cache key
function tq(c){return '?v='+hk((c.key||'')+'|'+(c.thumb||''))}
async function loadDetail(){if(editing)return;const s=await j('/api/jobs/'+sel);const done=s.done||[];
 const key=sel+'|'+s.status+'|'+s.stage+'|'+((s.prog||{}).n||0);
 if((s.status=='awaiting_review'||s.status=='awaiting_visuals'||s.status=='paused'||s.status=='finished'||(s.status=='error'&&s.stage=='transcript'))&&key==lastKey)return;   // don't redraw while you read/paste
 lastKey=key;
 const mtxt={both:`long ${s.minutes} min + Short ${fmt(Math.round(s.short_secs||165))}`,short:`${s.smoke?'Smoke test · ':''}Short ${fmt(Math.round(s.short_secs||165))}`,long:`long ${s.minutes} min`}[s.mode||'long'];
 let h=`<h2>${esc(s.title||s.url)}</h2><div class="mut">${mtxt} · <b data-testid="job-status" data-status="${esc(s.status)}" data-stage="${esc(s.stage)}">${statusText(s)}</b>${s.error?` · <span style="color:var(--bad)">${esc(s.error)}</span>`:''}</div>${outputsHtml(s)}${(s.length_warnings||[]).map(w=>`<div data-testid="length-warning" style="color:var(--bad);font-size:13px">Length miss: ${esc(w)}</div>`).join('')}`;
 h+=`<div class="stages">${(s.stages||stages).map(t=>`<span class="st ${done.includes(t)?'done':(s.stage==t?'cur':'')}">${t}</span>`).join('')}</div>`;
 h+=`<div class="row">`;
 if(s.status=='awaiting_review'){h+=`<button onclick="act('approve')">Approve & render</button>`;if(s.plan_summary)h+=`<button class="sec" onclick="editPlan()">Edit long script</button>`;if(s.short_summary)h+=`<button class="sec" onclick="editShort()">Edit Short script</button>`}
 if(['running','queued'].includes(s.status)){h+=`<button class="sec" onclick="act('stop')">Stop</button>`;h+=s.pause_req?`<span class="mut" data-testid="job-pausing">Pausing at the next safe point…</span>`:`<button class="sec" data-testid="job-pause" onclick="act('pause')">Pause now</button>`}
 if(['error','stopped'].includes(s.status))h+=`<button onclick="act('resume')">Resume</button>`;
 h+=`</div>`;
 if(s.status=='error'&&s.stage=='transcript')h+=`<details open style="margin-top:12px"><summary>Paste transcript (continues without YouTube)</summary><textarea id="jptx" rows="8" style="width:100%" placeholder="Paste the video's transcript here"></textarea><button onclick="pasteTx()">Use this transcript and continue</button> <span id="jptxm" class="mut"></span></details>`;
 if(s.short_output&&!(s.output&&s.edit_target=='long')){const rel=s.short_output.replace(/\\/g,'/').split('/').slice(-2).join('/');h+=`<p>Finished Short: <code>${esc(s.short_output)}</code><br><span class="mut">YouTube description with credits: output/youtube_short_description.txt</span></p><div class="row" style="align-items:flex-start"><div><video id="ov" controls style="max-width:360px" src="/files/${sel}/${rel}?t=${Date.now()}" ontimeupdate="edTick()" onloadedmetadata="scDraw()" onplay="scTick()" onpause="scTick()"></video><div id="scrub"></div><div id="edbar"></div></div><div id="thumbp" style="flex:1;min-width:260px"></div></div><div id="edp"></div>`}
 if(s.output&&(!s.short_output||s.edit_target=='long')){const rel=s.output.replace(/\\/g,'/').split('/').slice(-2).join('/');h+=`<p>Finished video: <code>${esc(s.output)}</code></p><video id="ov" controls src="/files/${sel}/${rel}?t=${Date.now()}" ontimeupdate="edTick()" onloadedmetadata="scDraw()" onplay="scTick()" onpause="scTick()"></video><div id="scrub"></div><div id="edbar"></div><div id="edp"></div>`}
 if(s.trace)h+=`<p class="mut" style="font-size:13px">Debug trace: <a data-testid="debug-trace" href="/files/${sel}/trace.md?t=${Date.now()}" target="_blank">trace.md</a> (in the job folder)</p>`;
 h+=`<div id="dbp"></div><div id="rvp"></div><div id="sdoc"></div><div id="doc"></div><div id="ed"></div>`;
 h+=`<details ${s.status=='error'?'open':''} style="margin-top:18px"><summary class="mut">Technical log</summary><pre id="log">${esc((s.log||[]).join('\n'))}</pre></details>`;
 $('detail').innerHTML=h;const l=$('log');if(l)l.scrollTop=l.scrollHeight;
 DBG_PAUSED=s.status=='paused';if(s.status=='paused'||s.status=='awaiting_visuals')showReview().then(showDebug);if(s.thumbnail)showThumb(s);if(s.status=='finished'&&(s.short_output||s.output))edInit();
 if(s.status!='awaiting_visuals'){if(s.plan_summary&&done.includes('script'))showScript(s);if(s.short_summary&&done.includes('short_script'))showShort(s)}}
// fact-check questions: a to-do while the job waits for review; just notes once review was skipped
function qbox(qs,st){const waiting=st&&st.status=='awaiting_review';
 return `<div style="border:1px solid ${waiting?'#d29922':'var(--line)'};border-radius:8px;padding:10px 14px;margin:10px 0"><b>${waiting?'Please check before approving:':'Fact-check notes (review was skipped, so the video was made without pausing):'}</b><ul>${qs.map(q=>`<li>${esc(q)}</li>`).join('')}</ul><span class="mut" style="font-size:13px">${waiting?"Fix with Edit script, or approve if it's fine.":"To fix these before rendering next time, untick Skip script review."}</span></div>`}
async function showShort(st){const p=await j(`/api/jobs/${sel}/short_plan`);const w=p.sections.reduce((a,x)=>a+x.vo.split(/\s+/).length,0);
 let h=`<div class="script-doc"><div class="mut" style="font-size:13px">SHORT · ${p.sections.length} beats · ${w} words · about ${fmt(Math.round(w/155*60+p.sections.length*0.35+2))}</div>`;
 if(p.questions&&p.questions.length)h+=qbox(p.questions,st);else if(p.checked)h+=`<div class="mut" style="font-size:13px;margin-top:4px">✓ Checked against the source</div>`;
 h+=`<h1>${esc(p.title)}</h1><p class="sub">${esc(p.tag||'')}</p>`;
```
### editor functions (lines 286-430)
```js

// ---------------- post-render editing (every output type)
let ED={beats:[],kind:null,cur:null,open:null,space:'short',rv:null,sel:[],fit:'auto',timer:null};
const FITS=[['auto','Auto'],['freeze','Freeze'],['slow','Slow down'],['loop','Loop'],['trim','Trim'],['speed','Speed up'],['still','Add still']];   // + Segment for your own files (edDraw)
function fmtT(x){return Math.floor(x/60)+':'+String(Math.floor(x%60)).padStart(2,'0')}
async function edInit(){try{const d=await j(`/api/jobs/${sel}/edit/beats`);ED.beats=d.beats||[];ED.kind=d.kind;edBar(d)}catch(e){}}
function edJump(id){const v=$('ov'),b=ED.beats.find(x=>x.id==id);if(!v||!b)return;v.pause();v.currentTime=b.start+Math.min(0.5,b.dur/2);ED.cur=b.id;edBar()}
function edAt(t){return ED.beats.find(b=>t>=b.start&&t<b.start+b.dur)}
function edTick(){scTick();const v=$('ov');if(!v||!ED.beats.length)return;const b=edAt(v.currentTime);const k=b?b.id:'';if(k!==ED.cur){ED.cur=k;edBar()}}
function edBar(d){const el=$('edbar');if(!el)return;const v=$('ov');const b=v?edAt(v.currentTime):null;d=d||ED.last||{};ED.last=d;scDraw();
 let h=`<div class="ed-bar">`;
 if(d.busy)h+=`<span class="rv-badge" style="color:var(--acc)">${esc(d.busy)}</span>`;
 else if(b&&b.editable)h+=`<button data-testid="edit-at" data-beat="${b.id}" onclick="edOpen('${b.id}')">Edit at ${fmtT(v.currentTime)} (${esc(b.label)}${ED.kind!='short'?' · '+b.id:''})</button>`;
 else if(b)h+=`<span class="mut" style="font-size:13px">${esc(b.label)}: not editable (title/end card)</span>`;
 else h+=`<span class="mut" style="font-size:13px">Play or scrub to a beat to edit it</span>`;
 if(!d.busy&&ED.beats.some(x=>x.editable))h+=`<select data-testid="edit-jump" aria-label="Jump to beat" style="width:auto" onchange="edJump(this.value)"><option value="">Jump to beat…</option>${ED.beats.filter(x=>x.editable).map(x=>`<option value="${x.id}" ${b&&b.id==x.id?'selected':''}>${esc(x.label)}${ED.kind!='short'?' · '+x.id:''} (${fmtT(x.start)})${x.own?' · your footage':''}</option>`).join('')}</select>`;
 if(d.undo&&!d.busy){const hs=d.history||[];const last=hs.length?hs[hs.length-1]:null;h+=`<button class="sec" data-testid="edit-undo" title="${hs.length?esc(hs.length+' edit(s) can be undone, newest first'):''}" onclick="edAll('undo')">Undo ${last?esc(last.label||last.beat):'last edit'}${hs.length>1?' ('+hs.length+')':''}</button>`}
 if(!d.busy&&(d.outputs||[]).length>1)h+=`<span class="mut" style="font-size:13px">Editing:</span><button class="sec ${d.target=='short'?'on':''}" data-testid="edit-target-short" onclick="edTarget('short')">Short</button><button class="sec ${d.target!='short'?'on':''}" data-testid="edit-target-long" onclick="edTarget('long')">Explainer</button>`;
 h+=`<button class="sec" onclick="if(confirm('Re-render the whole video? Your edits are kept.'))edAll('rerender')">Full re-render</button><button class="sec" onclick="edAll('cleanup')" title="Deletes previews and unused treatment files; thumbnails stay">Done editing (clean up)</button>`;
 if(ED.beats.some(x=>x.own))h+=`<span class="mut" data-testid="edit-own-coverage" style="font-size:12.5px">Your footage: ${ED.beats.filter(x=>x.own).map(x=>esc(x.label)+(ED.kind!='short'?' · '+x.id:'')).join(', ')}</span>`;
 const L=d.last;if(L&&!d.busy)h+=`<span class="ed-last" data-testid="edit-last-status" style="color:var(${L.ok?'--ok':'--bad'})">Last edit (${esc(L.beat)}): ${L.ok?'applied':'NOT applied — '+esc(L.msg)}</span>`;
 else if(d.error&&!d.busy)h+=`<span style="color:var(--bad);font-size:13px">Last edit NOT applied: ${esc(d.error)}</span>`;
 if(d.edits&&d.edits.length)h+=`<span class="mut" style="font-size:12px">${d.edits.length} edit(s) in the video</span>`;
 el.innerHTML=h+`</div>`}
// ---------------- timeline scrubber: find a beat by scrubbing the video, then open it in the edit panel below
// Short / Explainer selector (edit/target), player scrubber with the beat strip, timestamp, beat at that time, Play / Stop,
// "Edit this beat" -> edOpen(beat). Stop pauses and keeps the position, so the beat stays selected for editing.
function fmtTs(x){x=Math.max(0,x||0);return Math.floor(x/60)+':'+(x%60).toFixed(1).padStart(4,'0')}
function scDraw(){const el=$('scrub'),v=$('ov');if(!el||!v)return;const d=ED.last||{},lb=ED.beats.length?ED.beats[ED.beats.length-1]:null,D=(isFinite(v.duration)&&v.duration)||(lb?lb.start+lb.dur:0);
 const outs=d.outputs||[],tgt=d.target||(ED.kind=='short'?'short':'long');
 const has=k=>!outs.length?(k==(ED.kind=='short'?'short':'long')):outs.includes(k);
 let h=`<div class="sc" data-testid="scrubber"><div class="row" style="align-items:center;gap:6px;margin:0 0 6px">
  <span class="mut" style="font-size:13px">Video:</span>
  <button class="sec ${tgt=='short'?'on':''}" data-testid="scrub-pick-short" aria-pressed="${tgt=='short'}" ${has('short')&&!d.busy?'':'disabled'} onclick="${tgt=='short'?'':"edTarget('short')"}">Short</button>
  <button class="sec ${tgt!='short'?'on':''}" data-testid="scrub-pick-long" aria-pressed="${tgt!='short'}" ${has('long')&&!d.busy?'':'disabled'} onclick="${tgt!='short'?'':"edTarget('long')"}">Explainer</button></div>`;
 h+=`<input type="range" id="scr_r" data-testid="scrub-range" aria-label="Scrub the video" min="0" max="${D.toFixed(2)}" step="0.05" value="${(v.currentTime||0).toFixed(2)}" oninput="scSeek(this.value)" style="width:100%;margin:0">`;
 if(D>0&&ED.beats.length)h+=`<div class="sc-strip">${ED.beats.map(b=>`<div class="sc-seg ${b.editable?'':'off'}" data-beat="${b.id}" title="${esc(b.label)} (${fmtT(b.start)})" style="left:${(b.start/D*100).toFixed(3)}%;width:${(b.dur/D*100).toFixed(3)}%" onclick="scSeek(${(b.start+Math.min(0.5,b.dur/2)).toFixed(2)})">${ED.kind=='short'?(b.label||'').replace(/^Beat /,''):b.id}</div>`).join('')}</div>`;
 h+=`<div class="row" style="align-items:center;gap:8px;margin-top:6px">
  <button class="sec" data-testid="scrub-play" onclick="$('ov').play()">▶ Play</button><button class="sec" data-testid="scrub-stop" onclick="$('ov').pause()">■ Stop</button>
  <span data-testid="scrub-time" id="scr_t" style="font-variant-numeric:tabular-nums;font-weight:600">0:00.0</span><span class="mut" style="font-size:13px">/ ${fmtTs(D)}</span>
  <span data-testid="scrub-beat" id="scr_b" class="rv-badge">—</span>
  <button data-testid="scrub-edit" id="scr_e" onclick="scEdit()" disabled>Edit this beat</button></div></div>`;
 el.innerHTML=h;scTick()}
function scSeek(t){const v=$('ov');if(!v)return;v.currentTime=+t;scTick()}
function scTick(){const v=$('ov'),r=$('scr_r');if(!v||!r)return;const t=v.currentTime||0;
 if(document.activeElement!==r)r.value=t.toFixed(2);if(isFinite(v.duration)&&+r.max<v.duration)r.max=v.duration.toFixed(2);
 $('scr_t').textContent=fmtTs(t);const b=edAt(t),busy=(ED.last||{}).busy;
 $('scr_b').textContent=b?(b.label+(ED.kind!='short'?' · '+b.id:'')+(b.editable?'':' (not editable)')):(ED.beats.length?'between beats':'beats not loaded');
 $('scr_b').dataset.beat=b?b.id:'';
 const e=$('scr_e');e.disabled=!(b&&b.editable)||!!busy||!v.paused;e.title=!v.paused?'Stop the video first':busy?String(busy):'';
 document.querySelectorAll('.sc-seg').forEach(x=>x.classList.toggle('cur',!!b&&x.dataset.beat==b.id))}
function scEdit(){const v=$('ov');if(!v)return;v.pause();const b=edAt(v.currentTime);if(b&&b.editable)edOpen(b.id)}

async function edTarget(t){try{await rvPost(`/api/jobs/${sel}/edit/target`,{target:t});ED.open=null;lastKey='';loadJobs()}catch(e){alert(e.message)}}
async function edAll(a){try{await rvPost(`/api/jobs/${sel}/edit_all/${a}`);if(a=='undo'){edReload()}else{lastKey='';loadJobs()}}catch(e){alert(e.message)}}
function edReload(){const v=$('ov');if(v){const base=(v.getAttribute('src')||ED.ovSrc||'').split('?')[0];const t=v.getAttribute('src')?v.currentTime:(ED.ovT||0);if(base){v.src=base+'?t='+Date.now();v.currentTime=t}ED.ovSrc=null}edInit()}
const edQ=()=>ED.space=='long'?'?space=long':'';const edBase=()=>`/files/${sel}/${ED.space=='long'?'longedit/':''}short/`;
async function edOpen(bid){const v=$('ov');if(v)v.pause();$('edp').innerHTML='<p class="mut">Opening the beat…</p>';
 try{const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.error);
  ED.open=bid;ED.space=d.space;ED.rv=d.rv;const b=ED.rv.beats[bid];ED.sel=[...(b.current||[])];ED.fit='auto';ED.draft='';ED.chat=(await j(`/api/jobs/${sel}/edit/chat?beat=${bid}`)).chat;edDraw()}catch(e){$('edp').innerHTML=`<p style="color:var(--bad)">${esc(e.message)}</p>`}}
// ---- beat-edit panel: six labelled panes (Candidates, Fit options, Actions | Preview, Chat, Log), each with its own tint
const SRC_OF=(c)=>{const r=c.rung,it=c.item||{};if(it.user||r=='supplied'||r=='own')return['FILE','your file'];
 if(['still','animate','parallax','parallax (fill)','cloud','reconstruction'].includes(r))return['AI','AI-made picture or motion'];
 if(['stock','photo'].includes(r))return['FILE','real footage / photo'];
 if(r=='current'){if(it.type=='graphic')return['GENERATED','drawn by the studio'];if(/GENERATED|RECON/.test(it.tag||''))return['AI','AI-made'];return['FILE','media file']}
 return['GENERATED','drawn by the studio (graphic, simulation, map, card)']};
const edUserSel=()=>ED.sel.length&&ED.sel.every(c=>{const x=ED.rv.cands[c];return x&&(x.item.user||x.item.own_n||x.rung=='supplied'||x.rung=='own')});
function edPane(cls,title,sub,body,tid){return`<section class="edp ${cls}" data-testid="edit-pane-${tid}"><h3 class="edp-t">${title}${sub?` <span class="edp-sub">${sub}</span>`:''}</h3>${body}</section>`}
function edDraw(){if($('edchat'))ED.draft=$('edchat').value;const pv=$('edpv'),pvKeep=pv&&!pv.querySelector('.edp-empty')&&pv.innerHTML.trim()?pv.innerHTML:'';const bid=ED.open,b=ED.rv.beats[bid],bt=ED.beats.find(x=>x.id==bid)||{};
 const head=`<div class="edp-head"><div><h2 style="margin:0">Edit ${esc(bt.label||bid)}</h2><div class="edp-meta">${fmtT(bt.start||0)}–${fmtT((bt.start||0)+(bt.dur||0))} · ${(bt.dur||0).toFixed(1)}s slot${ED.kind!='short'?' · '+esc(bid):''}</div></div><span style="flex:1"></span><button class="sec" onclick="ED.open=null;$('edp').innerHTML=''">Close</button></div>
 <div class="edp-vo"><span class="edp-lab">Narration</span>${esc(b.vo)}</div>${bt.source?`<div class="src-note">Picture source: ${esc(bt.source)}</div>`:``}`;
 // Candidates
 let cands=`<div class="edp-help">Tick <b>Use</b> on the ones to show (they play in the order ticked). Click a thumbnail to preview it on the right. Blue outline = in the video now.</div><div class="rv-row">`;
 for(const cid of b.cands){const c=ED.rv.cands[cid];if(c.missing)continue;const i=ED.sel.indexOf(cid);const [src,srcT]=SRC_OF(c);
  const name=RUNG[c.rung]||(c.rung=='current'?((b.current||[]).includes(cid)?'In the video now':'Before your edit'):c.rung);
  const why=c.rung=='current'&&!(b.current||[]).includes(cid)?'was in the video':c.why;
  cands+=`<div class="rv-c edc ${i>=0?'sel':''} ${(b.current||[]).includes(cid)?'auto':''}" data-testid="edit-treatment" data-cand="${cid}" data-rung="${c.rung}" data-index="${b.cands.indexOf(cid)}"><div class="${c.worst?'wrn':''}" style="position:relative"><img data-testid="edit-treatment-thumb" loading="lazy" src="${c.thumb?edBase()+c.thumb+tq(c):''}" onclick="edCand('${cid}')" style="${ED.space=='long'?'width:213px;height:120px':''}"><span class="edc-src src-${src.toLowerCase()}" data-testid="edit-source-tag" title="${esc(srcT)}">${src}</span></div>
  <div class="edc-name">${esc(name)}</div>${c.item.tag?`<div class="edc-meta">on screen: ${esc(c.item.tag)}</div>`:''}
  ${c.ok?`<div class="edc-meta">${esc(why)}</div>`:`<div class="edc-rej" data-testid="edit-reject-reason">✗ ${esc(why)}</div>`}
  <label class="edc-use"><input type="checkbox" data-testid="edit-choose" data-cand="${cid}" ${i>=0?'checked':''} onchange="edTickC('${cid}',this.checked)"> Use${i>=0&&ED.sel.length>1?' #'+(i+1):''}</label></div>`}
 cands+=`</div>`;
 // Fit options
 const user=edUserSel();const fits=user?FITS.filter(([k])=>k!='still').concat([['segment','Segment (2–3 chunks)']]):FITS;
 const fit=`<div class="edp-help">${user?'<b class="edp-user">Your file — fit-and-render.</b> Used exactly as supplied: no vision check, no AI animation, no substitution, no pan/zoom. Only fitted to the slot (trim, loop, freeze, speed ≤1.5×, segment), then rendered.':'How the picked treatment is fitted to the slot.'} Slot: ${(bt.dur||0).toFixed(1)}s.</div>
  <div class="row ed-fit">${fits.map(([k,n])=>`<button class="sec ${ED.fit==k?'on':''}" data-testid="edit-fit-${k}" onclick="ED.fit='${k}';edDraw()">${n}</button>`).join('')}</div>`;
 // Actions
 const acts=`<div class="row"><button data-testid="edit-preview" onclick="edPreview()" ${ED.sel.length?'':'disabled'}>Preview in the video</button><button data-testid="edit-apply" onclick="edApply()" ${ED.sel.length?'':'disabled'}>Apply to video</button></div>
  <div class="row" style="margin-top:6px"><button class="sec" data-testid="edit-skip" onclick="edSkip()">Skip (headline card)</button><button class="sec" data-testid="edit-show-all" onclick="edRv('expand')" ${b.busy?'disabled':''}>Show all options</button><button class="sec" data-testid="edit-add-animation" onclick="edRv('animate')" ${b.busy?'disabled':''}>Add animation</button></div>
  <label>Your own file (path on this PC or a URL) — used as-is, fitted to the slot</label><div class="row"><input type="text" id="edsp" data-testid="edit-supply-path" style="flex:1"><select id="edst" data-testid="edit-supply-label" style="width:auto"><option value="">label: auto (YOUR FOOTAGE / FILE)</option><option>FILE</option><option>YOUR FOOTAGE</option><option>ILLUSTRATIVE</option><option>GENERATED</option></select><button class="sec" data-testid="edit-supply" onclick="edSupply()">Add</button></div>
  <label>Regenerate with a change (e.g. "nose down, storm clouds")</label><div class="row"><textarea id="edrf" data-testid="edit-refine-text" rows="2" style="flex:1"></textarea><button class="sec" data-testid="edit-refine" onclick="edRv('refine')" ${b.busy?'disabled':''}>Regenerate</button></div>`;
 // Preview
 const prev=`<div id="edpv" class="rv-prev" data-testid="edit-preview-area"><div class="edp-empty">Nothing previewed yet. Click a thumbnail, or <b>Preview in the video</b> to see this beat as it will look.</div></div>`;
 // Chat: you right, assistant left, pipeline status lines (in brackets) separate
 const msgs=(ED.chat||[]).map(x=>{const parts=String(x.reply||'').split(/\n(?=\()/);const main=parts[0],st=parts.slice(1);
  return`<div class="cm cm-you" data-testid="chat-you"><div class="cm-b">${esc(x.you)}</div><div class="cm-m">you${x.t?' · '+esc(x.t):''}</div></div>
  <div class="cm cm-ai" data-testid="chat-ai"><div class="cm-b">${esc(main)}${x.handoff?` <button class="sec" style="padding:2px 8px;font-size:12px" data-h="${esc(x.handoff)}" onclick="navigator.clipboard.writeText(this.dataset.h);this.textContent='Copied — paste it in the Claude chat'">Copy for Claude</button>`:''}</div><div class="cm-m">assistant · ${esc(x.backend||'')}${x.action&&x.action!='none'?' · action: '+esc(x.action):''}</div></div>
  ${st.map(z=>`<div class="cm cm-sys" data-testid="chat-status">⚙ ${esc(z.replace(/^\(|\)$/g,''))}</div>`).join('')}`}).join('')||'<div class="edp-empty">Ask why, refine, more stock, simulate, use option N — then "apply it".</div>';
 const chat=`<div class="dbg-chat edp-chat" data-testid="edit-chat-log">${msgs}</div>
  <div class="row"><textarea id="edchat" data-testid="edit-chat-text" rows="2" style="flex:1" placeholder="e.g. simulate the descent with real physics / use option 3 / apply it">${esc(ED.draft||'')}</textarea><button data-testid="edit-chat-send" onclick="edChat()" ${ED.chatBusy?'disabled':''}>${ED.chatBusy?'Thinking…':'Send'}</button></div>`;
 // Log: pipeline status for this beat
 const last=(ED.last||{}).last;
 const log=`<div class="edp-log" data-testid="edit-log">${b.busy?`<div class="lg lg-busy">⏳ ${esc(b.busy)}</div>`:''}<div id="edmsg" data-testid="edit-message" class="lg"></div>
  ${b.msg&&!(last&&last.beat==bid&&/^(Applied|Not applied)/.test(b.msg))?`<div class="lg ${/^Not applied/.test(b.msg)?'lg-bad':''}">${esc(b.msg)}</div>`:''}
  ${last&&last.beat==bid?`<div class="lg ${last.ok?'lg-ok':'lg-bad'}" data-testid="edit-last">${last.ok?'✓ '+esc(last.msg||'Applied.'):'✗ Not applied: '+esc(last.msg||'')}</div>`:''}
  ${(b.notes||[]).map(x=>`<div class="lg lg-meta">${esc(x.t)} you: “${esc(x.you)}” → <b>${esc(x.intent)}</b>: ${esc(x.understood)} [${esc(x.backend)}]</div>`).join('')}</div>`;
 let h=`<div class="card edp-card" style="margin-top:12px">${head}<div class="edp-grid"><div class="edp-col">${edPane('p-cand','Candidates',`${b.cands.filter(c=>!ED.rv.cands[c].missing).length} options`,cands,'candidates')}${edPane('p-fit','Fit options','',fit,'fit')}${edPane('p-act','Actions','',acts,'actions')}</div>
  <div class="edp-col">${edPane('p-prev','Preview of this beat','',prev,'preview')}${edPane('p-chat','Chat','about this beat',chat,'chat')}${edPane('p-log','Log','status of this beat',log,'log')}</div></div></div>`;
 $('edp').innerHTML=h;if(pvKeep)$('edpv').innerHTML=pvKeep;clearTimeout(ED.timer);if(b.busy)ED.timer=setTimeout(edRefresh,4000)}
async function edChat(){const t=$('edchat').value.trim();if(!t||ED.chatBusy)return;ED.chatBusy=1;ED.draft=t;edDraw();const bid=ED.open;
 try{const x=await rvPost(`/api/jobs/${sel}/edit/chat`,{beat:bid,text:t});ED.draft='';if($('edchat'))$('edchat').value='';ED.chat=(await j(`/api/jobs/${sel}/edit/chat?beat=${bid}`)).chat;
  ED.chatBusy=0;if(ED.open!=bid)return;const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const d=await r.json();if(r.ok)ED.rv=d.rv;
  if(x.select)ED.sel=[...x.select];edDraw();if(x.action=='apply'&&!/Couldn't do it/.test(x.reply)){$('edmsg').textContent='Applying…';edWait()}}
 catch(e){ED.chatBusy=0;edDraw();alert(e.message)}}
async function edRefresh(){if(!ED.open)return;try{ED.rv=await j(`/api/jobs/${sel}/review${edQ()}`);const r=await fetch(`/api/jobs/${sel}/edit/open/${ED.open}`,{method:'POST'});const d=await r.json();if(r.ok)ED.rv=d.rv;edDraw()}catch(e){}}
function edTickC(cid,on){const i=ED.sel.indexOf(cid);if(on&&i<0)ED.sel.push(cid);if(!on&&i>=0)ED.sel.splice(i,1);edDraw()}
async function edCand(cid){const el=$('edpv');el.innerHTML='<span class="mut">Rendering a 2-second preview…</span>';
 try{const d=await rvPost(`/api/jobs/${sel}/preview/${cid}${edQ()}`);el.innerHTML=(d.video?pvVideo(`${edBase()}${d.video}`):`<img src="${edBase()}${d.image}">`)+` <button class="sec" onclick="this.parentElement.innerHTML=''">Close</button>`}catch(e){el.innerHTML=`<span style="color:var(--bad)">${esc(e.message)}</span>`}}
async function edPreview(){const el=$('edpv');el.innerHTML='<span class="mut">Rendering the beat as it will look in the video (half resolution)…</span>';
 try{const d=await rvPost(`/api/jobs/${sel}/edit/preview/${ED.open}`,{cands:ED.sel,fit:ED.fit});el.innerHTML=`<div class="mut" style="font-size:13px">Fit: <b>${esc(d.fit)}</b> — ${esc(d.why)}</div><video controls autoplay playsinline src="/files/${sel}/${d.video}" style="max-height:480px"></video> <button class="sec" onclick="this.parentElement.innerHTML=''">Close</button>`}catch(e){el.innerHTML=`<span style="color:var(--bad)">${esc(e.message)}</span>`}}
// let go of the video file before it is replaced (Windows won't replace a file a player has open): pause + unload the players
function edRelease(){const v=$('ov');if(v&&v.getAttribute('src')){ED.ovSrc=v.getAttribute('src');ED.ovT=v.currentTime;v.pause();v.removeAttribute('src');v.load()}
 document.querySelectorAll('#edpv video').forEach(x=>{x.pause();x.removeAttribute('src');x.load()})}
async function edApply(){if(!ED.sel.length)return;$('edmsg').textContent='Applying…';edRelease();try{await rvPost(`/api/jobs/${sel}/edit/apply/${ED.open}`,{cands:ED.sel,fit:ED.fit});edWait()}catch(e){$('edmsg').textContent='';edReload();alert(e.message)}}
async function edSkip(){const b=ED.rv.beats[ED.open];const cid=b.cands.find(c=>ED.rv.cands[c].rung=='headline');if(!cid){alert('No headline card for this beat');return}ED.sel=[cid];ED.fit='auto';edApply()}
async function edWait(){const d=await j(`/api/jobs/${sel}/edit/beats`);edBar(d);if(d.busy){setTimeout(edWait,3000);if($('edmsg'))$('edmsg').textContent=d.busy;return}
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.'}}}
async function edRv(a){const body={action:a};if(a=='refine'){body.text=$('edrf').value.trim();if(!body.text)return}
 try{ED.rv=await rvPost(`/api/jobs/${sel}/review/${ED.open}${edQ()}`,body);edDraw();setTimeout(edRefresh,1500)}catch(e){alert(e.message)}}
async function edSupply(){const t=$('edsp').value.trim();if(!t)return;$('edmsg').textContent='Adding your file…';
 try{ED.rv=await rvPost(`/api/jobs/${sel}/review/${ED.open}${edQ()}`,{action:'supply',src:t,tag:$('edst').value});ED.sel=[...ED.rv.beats[ED.open].chosen];$('edmsg').textContent='';edDraw()}catch(e){$('edmsg').textContent='';alert(e.message)}}

// ---- debugger: the shared pause panel (manual pause, breakpoint, or the auto review pause with debug on)
let D=null,DBG_PAUSED=false,dbgBeat=null,dbgBusy='',dbgKey='';
async function showDebug(){try{D=await j(`/api/jobs/${sel}/debug`)}catch(e){return}
 const ks=Object.keys(D.chains||{});
 const pk=sel+'|'+(D.pause&&D.pause.t||D.status);if(pk!==dbgKey){dbgKey=pk;dbgBeat=D.pause&&D.pause.beat||null}
 if(!dbgBeat||!ks.includes(dbgBeat)){const u=RV&&Object.entries(RV.beats).find(([k,b])=>b.uncertain&&!b.decision);dbgBeat=u?u[0]:(ks[0]||null)}
 drawDebug()}
function dbgLabel(){if(!D)return'';if(D.status=='paused')return D.pause&&D.pause.label||'Paused';return 'Paused: uncertain about this beat'}
function drawDebug(){const el=$('dbp');if(!el||!D)return;const on=D.debug&&D.debug.on,paused=D.status=='paused',p=D.pause||{};
 const ks=Object.keys(D.chains||{}).sort((a,b)=>+a.slice(1)-+b.slice(1));const c=(D.chains||{})[dbgBeat]||{};
 let h=`<div class="card dbg" data-testid="debug-panel" style="margin-top:14px"><div class="row" style="align-items:center"><b data-testid="debug-label">${esc(dbgLabel())}</b>`+
  (paused?`<span class="mut" style="font-size:13px">${p.n?'at Beat '+p.n:'before '+esc(p.where||D.stage||'')}</span>`:'')+`</div>
  <label style="color:var(--fg);margin-top:6px"><input type="checkbox" data-testid="debug-toggle" aria-label="Debug mode for the rest of this run" ${on?'checked':''} onchange="dbgSet({on:this.checked})"> Debug mode for the rest of this run</label>`;
```

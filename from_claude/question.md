# Task: give the YouTube Publisher the Newsroom's look and its popup-player pattern (branch feature/unified-ui)

Tariq likes the Newsroom's new design: light theme, each panel a different soft colour, larger type only where he
edits, and "Watch / decide" opening a POPUP WINDOW that holds the player, scrubber and EVERY control and dialog for
that video. Apply the same look and pattern to the YouTube Publisher (Flask; files: templates/base.html,
templates/publish.html, static/css/style.css, static/js/publish.js, app.py). Do not change publish logic or endpoints.

## Wanted
1. Theme: same palette, fonts and panel tints as the Newsroom (its CSS is below). No dark background.
2. Main page = lists only, no player: panels "Ready to publish" (finished jobs from GET /api/jobs) and "Published"
   (GET /api/published), each its own tint, with Prev/Next + "n of N" + title/channel/kind like the Newsroom rotators.
3. "Open" on an item opens ONE shared popup window (window name `pubplayer`, reused for every pick) at a new page
   `templates/player.html` served by a new GET route `/player?job=<job>&kind=<kind>&channel=<channel>`.
   The popup carries everything that is on the publish page today for that video: preview player with scrubber,
   thumbnail tools (regenerate-from-frame dialog, custom upload), title/description/tags/category, visibility,
   made-for-kids, language, chapters, end-screen link, Publish / Publish both / Save draft / Retry / Restart, and the
   live publishing-activity log with screenshots. After a successful publish it tells the opener to refresh
   (postMessage) and closes itself; a Close button too. For a Published item it shows the YouTube link(s), no
   publish buttons.
   Move the existing publish.js logic into the popup page (split into player.js if cleaner); keep every existing API call.
4. TEST indicator, decided by the PORT, never by the branch: if the server's port is not the live port (config
   `port`, 42030), every page shows a small, slowly pulsing "TEST" pill in the header (tiny, not loud, like a broker's
   simulation marker). Pass it from Flask to the templates (e.g. a context processor reading the port the app was
   started on; app.py starts with `app.run(host='127.0.0.1', port=int(cfg['port']), ...)` - add an env override
   `PUBLISHER_PORT` so a test copy can run on 42031).
5. SAFETY in test mode (server side, not just disabled buttons): when not on the live port, every non-GET request is
   refused with 403 {"error": "TEST copy: actions are disabled"} (it shares the real Chrome profile and channels, so a
   test publish would be real). The popup's action buttons show disabled with a tooltip in test mode.
6. Keep the larger edit-box type the Newsroom uses (title/description inputs about 16px).

## Answer format
Full file contents for every file you change or add (they are small enough), each preceded by its path. Then how to
test. Keep the HTML plain (no framework), as the existing files are.

## Newsroom reference (the look to copy)

### newsroom static/player.html
```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Newsroom player</title>
<style>
:root{--bg:#f3f0e9;--panel:#ffffff;--line:#ccd3da;--text:#1d2733;--dim:#5d6b7a;--acc:#d99400;--ok:#1a9e6b;--bad:#d93a3a;--blue:#2f7fe0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 Inter,Segoe UI,system-ui,sans-serif;padding:16px}
h2{font-size:18px;margin:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
video{width:100%;max-height:56vh;background:#000;border-radius:8px;margin:10px 0}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}
button{background:#ffffff;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:8px 14px;cursor:pointer;font:inherit}
button.primary{background:var(--acc);color:#111;border-color:var(--acc);font-weight:700}
button.go{background:#2e7d32;color:#fff;border-color:#2e7d32;font-weight:700}
button:disabled{opacity:.45;cursor:default}
select{background:#ffffff;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:8px 9px;font:inherit}
textarea{flex:1;min-width:240px;background:#ffffff;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:8px 9px;font:inherit;font-size:16px}
.status{font-size:13px;color:var(--acc)}
.err{color:var(--bad);font-size:13px;white-space:pre-wrap}
.muted{color:var(--dim);font-size:13px}
.pubtag{background:#2e7d32;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
.newtag{background:#f5c542;color:#111;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
.rejtag{background:#b3261e;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
a{color:var(--blue)}
</style>
</head>
<body>
<div class="card" id="app"><p class="muted">Loading…</p></div>
<script>
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, body) {
  const r = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const j = await r.json().catch(() => ({error: 'HTTP ' + r.status}));
  if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}
const qs = new URLSearchParams(location.search);
const ID = qs.get('id') || '';
let kind = qs.get('kind') || '';
let channels = [], visibility = 'Private', it = null;

function done(action) {
  try { if (window.opener && !window.opener.closed) window.opener.postMessage({type: 'nr-action', action}, '*'); } catch (e) {}
  document.body.innerHTML = '<div class="card"><h2>Done.</h2><p class="muted">This window will close itself…</p></div>';
  setTimeout(() => window.close(), 600);
}

async function load() {
  try {
    const [st, s] = await Promise.all([api('/api/staged?all=1'), api('/api/status')]);
    channels = s.channels || []; visibility = s.visibility || 'Private';
    it = (st.items || []).find(x => x.id === ID);
    if (!it) { $('app').innerHTML = '<div class="err">That video is no longer in the Newsroom lists.</div>'; return; }
    const kinds = it.kinds || ['short'];
    if (!kinds.includes(kind)) kind = kinds[kinds.length - 1];
    render();
  } catch (e) { $('app').innerHTML = `<div class="err">${esc(e.message)}</div>`; }
}

function render() {
  const kinds = it.kinds || ['short'];
  const pubs = it.published || {};
  const remaining = kinds.filter(k => !pubs[k]);
  const prog = it.publish_progress || {};
  const rejected = it.status === 'rejected';
  const tag = rejected ? '<span class="rejtag">REJECTED</span>' : !remaining.length ? '<span class="pubtag">PUBLISHED</span>' : (it.status === 'published' ? '<span class="pubtag">PARTLY PUBLISHED</span>' : '<span class="newtag">TO REVIEW</span>');
  const pcs = it.pub_channels || {};
  const onChans = Object.keys(pcs).length ? Object.keys(pcs) : (it.channel && Object.keys(pubs).length ? [it.channel] : []);
  const pubKinds = kinds.filter(k => pubs[k]);
  const rsKinds = it.status === 'rejected' ? kinds : pubKinds;
  const otherChans = channels.filter(c => !onChans.includes(c));
  const canAct = !rejected && remaining.length > 0;
  const busy = ['queued','researching','rendering'].includes(it.long_status);
  const pubEnabled = canAct && (['staged','publish_failed'].includes(it.status) || (it.status === 'published' && remaining.length)) && !busy;
  $('app').innerHTML = `
    <div class="row" style="justify-content:space-between"><h2>${tag} ${esc(it.vs_title || it.headline)}</h2><button onclick="window.close()">Close ✕</button></div>
    <div class="status">${esc(it.status)}${it.channel ? ' · ' + esc(it.channel) : ''} · job ${esc(it.job)}</div>
    ${it.error ? `<div class="err">${esc(it.error)}</div>` : ''}
    ${kinds.length > 1 ? `<div class="row">${kinds.map(k => `<button data-kind="${k}" ${k === kind ? 'class="primary"' : ''}>${k === 'long' ? 'Explainer' : 'Short'}</button>`).join('')}</div>` : ''}
    <video controls autoplay preload="metadata" src="/media/${encodeURIComponent(it.id)}/${kind}"></video>
    ${Object.entries(prog).map(([k, v]) => `<div class="muted">${esc(k)}: ${esc(v.status)} ${esc((v.last || {}).message || '')}</div>`).join('')}
    ${Object.entries(pubs).map(([k, u]) => u ? `<div><a href="${esc(u)}" target="_blank" rel="noopener">${esc(k)}: ${esc(u)}</a></div>` : '').join('')}
    ${onChans.length ? `<div class="muted">On YouTube: ${onChans.map(esc).join(', ')}</div>` : ''}
    ${it.presenter_note ? `<div class="muted">Presenter ${esc(it.presenter_note)}</div>` : ''}
    ${it.long_status && it.long_status !== 'done' ? `<div class="${it.long_status === 'failed' ? 'err' : 'muted'}">Explainer: ${esc(it.long_status)}${it.long_stage ? ' – ' + esc(it.long_stage) : ''}${it.long_error ? ' – ' + esc(it.long_error) : ''}</div>` : ''}
    ${canAct ? `<div class="row">
      <select id="chan">${channels.map(c => `<option value="${esc(c)}" ${c === it.channel ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>
      <select id="vis">${['Private','Unlisted','Public'].map(v => `<option ${v === (it.visibility || visibility) ? 'selected' : ''}>${v}</option>`).join('')}</select>
      ${remaining.length > 1 ? `<select id="kinds"><option value="long,short">Both (explainer, then Short with its link)</option><option value="short">Short only</option><option value="long">Explainer only</option></select>` : ''}
    </div>
    <div class="row">
      <button class="primary" id="pub" ${pubEnabled ? '' : 'disabled'}>${it.status === 'publish_failed' ? 'Retry upload (same video)' : 'Publish to YouTube'}</button>
      ${it.approved ? `<button class="go" id="unappr">✓ Approved (${esc(it.approved.channel)}, ${esc(it.approved.visibility)}) — undo</button>` : `<button id="appr">Approve for publish</button>`}
      ${['staged','publish_failed'].includes(it.status) ? '<button id="rej">Reject</button>' : ''}
    </div>` : ''}
    ${it.move_pending ? `<div class="card" style="background:#fde8e8;border-color:#b3261e;margin:10px 0">
      <b>Move waiting:</b> this video is uploaded to <b>${esc(it.move_pending.to)}</b> and still live on <b>${esc(it.move_pending.from)}</b>.<br>
      Deleting it from ${esc(it.move_pending.from)} is permanent — YouTube has no true move: the old link, views and comments go away for good.
      <div class="row"><button class="primary" id="mdel">Delete from ${esc(it.move_pending.from)} now</button>
      <button id="mcancel">Cancel move — keep it on both</button></div></div>` : ''}
    ${!it.move_pending && (it.status === 'published' || it.status === 'rejected') && rsKinds.length ? `<div style="margin-top:12px"><h3 style="margin:0 0 6px">${it.status === 'rejected' ? 'Publish to a channel' : 'Submit again / move'}</h3>
      <div class="row">
      <select id="rchan">${otherChans.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('')}</select>
      <select id="rvis">${['Private','Unlisted','Public'].map(v => `<option ${v === (it.visibility || visibility) ? 'selected' : ''}>${v}</option>`).join('')}</select>
      ${rsKinds.length > 1 ? `<select id="rkinds"><option value="long,short">Both (explainer, then Short)</option><option value="short">Short only</option><option value="long">Explainer only</option></select>` : ''}
      </div>
      ${otherChans.length ? `<div class="row"><button id="rsub">${it.status === 'rejected' ? 'Publish to this channel' : 'Submit again to this channel'}</button>
      ${it.status === 'published' && it.channel ? '<button id="rmove">Move to this channel instead</button>' : ''}</div>
      <div class="muted">Submit again: the video ends up on both channels. Move: it uploads there first; deleting it from ${esc(it.channel || 'the old channel')} happens only after that upload succeeds, and only when you confirm it separately.</div>`
      : '<div class="muted">This video is already on every channel.</div>'}
      </div>` : ''}
    ${!kinds.includes('long') && !busy && ['staged','publish_failed'].includes(it.status) ? '<div class="row"><button id="mklong">Make explainer too</button></div>' : ''}
    <div class="row" style="align-items:flex-start"><textarea id="fbnote" rows="2" placeholder="Feedback (what to do differently from now on — becomes a house-style rule)"></textarea>
      <button id="fbsend">Teach</button></div>
    <div class="muted" id="fbmsg">${(it.feedback || []).length ? (it.feedback.length + ' note(s) given on this video') : 'Your notes become house-style rules for every later video.'}</div>`;
  document.querySelectorAll('[data-kind]').forEach(b => b.onclick = () => { kind = b.dataset.kind; render(); });
  if ($('pub')) $('pub').onclick = async () => {
    const ch = $('chan').value, vis = $('vis').value;
    if (!confirm(`Publish "${it.vs_title || it.headline}" to ${ch} as ${vis}?`)) return;
    $('pub').disabled = true;
    const ks = $('kinds') ? $('kinds').value.split(',') : remaining;
    try { await api('/api/publish', {id: it.id, channel: ch, visibility: vis, kinds: ks}); done('publish'); } catch (e) { alert(e.message); $('pub').disabled = false; }
  };
  if ($('appr')) $('appr').onclick = async () => {
    const ks = $('kinds') ? $('kinds').value.split(',') : null;
    try { await api('/api/approve', {id: it.id, on: true, channel: $('chan').value, visibility: $('vis').value, kinds: ks}); done('approve'); } catch (e) { alert(e.message); }
  };
  if ($('unappr')) $('unappr').onclick = async () => {
    try { await api('/api/approve', {id: it.id, on: false}); done('approve'); } catch (e) { alert(e.message); }
  };
  if ($('rej')) $('rej').onclick = async () => {
    const reason = prompt(`Reject "${it.vs_title || it.headline}"? It leaves the review list.\nWhy? (optional: the reason teaches the house style)`, $('fbnote').value || '');
    if (reason === null) return;
    try { await api('/api/reject', {id: it.id, reason}); done('reject'); } catch (e) { alert(e.message); }
  };
  if ($('mklong')) $('mklong').onclick = async () => {
    try { await api('/api/explainer', {id: it.id}); load(); } catch (e) { alert(e.message); }
  };
  if ($('mdel')) $('mdel').onclick = async () => {
    if (!confirm(`Delete "${it.vs_title || it.headline}" from ${it.move_pending.from} permanently?\n\nYouTube has no true move: the old link, its views and comments are gone for good. The copy on ${it.move_pending.to} stays.`)) return;
    try { await api('/api/move/delete', {id: it.id}); done('move'); } catch (e) { alert(e.message); }
  };
  if ($('mcancel')) $('mcancel').onclick = async () => {
    try { await api('/api/move/cancel', {id: it.id}); done('move-cancel'); } catch (e) { alert(e.message); }
  };
  const rsGo = async (move) => {
    const ch = $('rchan').value, vis = $('rvis').value;
    const rk = $('rkinds') ? $('rkinds').value.split(',') : rsKinds;
    if (move && !confirm(`Move "${it.vs_title || it.headline}" to ${ch}?\n\nStep 1: upload it to ${ch}. Step 2: deleting it from ${it.channel} — only after the upload succeeds, and only when you confirm it separately.`)) return;
    if (!move && !confirm(`${it.status === 'rejected' ? 'Publish' : 'Submit again'} "${it.vs_title || it.headline}" to ${ch} as ${vis}?`)) return;
    try { await api('/api/resubmit', {id: it.id, channel: ch, visibility: vis, kinds: rk, move}); done(move ? 'move' : 'resubmit'); } catch (e) { alert(e.message); }
  };
  if ($('rsub')) $('rsub').onclick = () => rsGo(false);
  if ($('rmove')) $('rmove').onclick = () => rsGo(true);
  $('fbsend').onclick = async () => {
    const note = $('fbnote').value.trim(); if (!note) return;
    $('fbsend').disabled = true; $('fbmsg').textContent = 'Learning...';
    try {
      const r = await api('/api/feedback', {id: it.id, note});
      $('fbnote').value = '';
      $('fbmsg').textContent = r.added.length ? 'Learned: ' + r.added.map(x => x.rule).join(' | ') : 'Noted (nothing general to learn from it).';
    } catch (e) { $('fbmsg').textContent = e.message; }
    $('fbsend').disabled = false;
  };
}
load();
</script>
</body>
</html>
```

### newsroom static/index.html (CSS + panel markup; script trimmed)
```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Newsroom</title>
<style>
  :root { --bg:#f3f0e9; --panel:#ffffff; --line:#ccd3da; --text:#1d2733; --dim:#5d6b7a; --acc:#d99400; --ok:#1a9e6b; --bad:#d93a3a; --blue:#2f7fe0; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 Inter, Segoe UI, system-ui, sans-serif; }
  header { display:flex; align-items:center; flex-wrap:wrap; gap:8px 12px; padding:12px 18px; border-bottom:1px solid var(--line); }
  header h1 { white-space:nowrap; }
  header h1 { font-size:17px; margin:0; letter-spacing:.5px; }
  header h1 span { color:var(--acc); }
  .pill { font-size:12px; padding:3px 9px; border-radius:99px; border:1px solid var(--line); color:var(--dim); }
  .pill.ok { color:var(--ok); border-color:#2a5a35; } .pill.bad { color:var(--bad); border-color:#d9a0a0; }
  main { display:grid; grid-template-columns: 340px 1fr 420px; gap:14px; padding:14px; height:calc(100vh - 54px); }
  section { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; overflow:auto; min-height:0; }
  main>section:nth-child(1) { background:#e9f1fd; } main>section:nth-child(2) { background:#fdf3d8; } main>section:nth-child(3) { background:#e7f5ec; }
  h2 { font-size:12px; text-transform:uppercase; letter-spacing:1.5px; color:var(--dim); margin:0 0 10px; display:flex; justify-content:space-between; align-items:center; }
  .card { border:1px solid var(--line); border-radius:8px; padding:10px; margin-bottom:10px; background:#ffffff; }
  .card h3 { font-size:14px; margin:0 0 4px; }
  .card a { color:var(--blue); font-size:12px; word-break:break-all; }
  .card p { margin:6px 0; color:var(--dim); font-size:13px; }
  button { background:#ffffff; color:var(--text); border:1px solid var(--line); border-radius:7px; padding:7px 12px; cursor:pointer; font:inherit; }
  button:hover:not(:disabled) { border-color:var(--acc); }
  button:disabled { opacity:.45; cursor:default; }
  button.primary { background:var(--acc); color:#111; border-color:var(--acc); font-weight:700; }
  input, select { background:#ffffff; color:var(--text); border:1px solid var(--line); border-radius:7px; padding:7px 9px; font:inherit; }
  .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .status { font-size:12px; color:var(--acc); }
  .err { color:var(--bad); font-size:12px; margin:6px 0; white-space:pre-wrap; }
  .muted { color:var(--dim); font-size:12px; }
  .bar { height:6px; background:#e3ded2; border-radius:3px; overflow:hidden; margin:8px 0; }
  .bar i { display:block; height:100%; background:var(--acc); width:0; transition:width .4s; }
  .stages { display:flex; flex-wrap:wrap; gap:4px; margin:6px 0; }
  .stages span { font-size:11px; padding:2px 6px; border-radius:4px; background:#ffffff; color:var(--dim); }
  .stages span.done { color:var(--ok); } .stages span.now { color:#111; background:var(--acc); }
  .beat { border-left:3px solid var(--acc); padding:4px 10px; margin:8px 0; }
  .beat b { font-size:11px; color:var(--dim); display:block; }
  pre.log { font:11px/1.4 Consolas, monospace; color:var(--dim); white-space:pre-wrap; margin:0; max-height:160px; overflow:auto; }
  video { width:100%; max-height:62vh; background:#000; border-radius:8px; }
  .nav { display:flex; justify-content:space-between; align-items:center; margin:8px 0; }
  hr { border:0; border-top:1px solid var(--line); margin:14px 0; }
  @media (max-width: 1100px) { main { grid-template-columns:1fr; height:auto; } }
.pubtag{background:#2e7d32;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
.newtag{background:#f5c542;color:#111;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
button.done{background:#2e7d32;color:#fff;border-color:#2e7d32;opacity:.85}
label.approve{display:flex;gap:8px;align-items:center;margin:8px 0;font-weight:600}
label.approve input{width:20px;height:20px}
button.go{background:#2e7d32;color:#fff;border-color:#2e7d32;font-weight:700}
.fb{margin-top:10px;display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap}.fb textarea{flex:1;min-width:240px}
.rules{list-style:none;padding:0;margin:0}.rules li{padding:4px 0;border-bottom:1px solid rgba(128,128,128,.2)}
.rules .tag{font-size:11px;padding:1px 6px;border-radius:8px;background:rgba(128,128,128,.25);margin-right:6px}.rules .x{float:right;padding:0 6px}
.fb textarea{font-size:16px;line-height:1.5}
.panel{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:12px}
.panel h3{font-size:14px}
.panel-review{background:#fdf3d8}.panel-published{background:#e7f5ec}.panel-rejected{background:#fde8e8}
.rejtag{background:#b3261e;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;vertical-align:middle}
</style>
</head>
<body>
<header>
  <h1>THE <span>NEWSROOM</span></h1>
  <span id="pvs" class="pill">Video Studio …</span>
  <span id="ppub" class="pill">Publisher …</span>
  <span id="pdoc" class="pill">Inbox …</span>
  <span id="pauto" class="pill"></span><span class="pill" id="pcount"></span>
  <span id="pq" class="pill" style="display:none"></span>
</header>
<main>
  <!-- Left: inbox -->
  <section>
    <h2>Inbox <button id="refresh" title="Read the Newsroom Inbox doc again">Refresh</button></h2>
    <div id="inboxerr" class="err"></div>
    <div id="inbox"><p class="muted">Loading…</p></div>
    <div class="row"><button id="more" style="display:none">More…</button></div>
    <div class="row" style="margin-top:8px"><span class="muted">Generate makes</span>
      <select id="genmode"><option value="short">a Short</option><option value="smoke">a 30-second smoke test</option>
        <option value="long">an explainer</option><option value="both">explainer + Short</option></select></div>
    <hr>
    <h2>Add an item by hand</h2>
    <input id="addh" placeholder="Headline" style="width:100%;margin-bottom:6px">
    <input id="addu" placeholder="https://source-url" style="width:100%;margin-bottom:6px">
    <div class="row"><input id="addp" placeholder="Pitch (optional)" style="flex:1"><button id="addbtn">Add</button></div>
    <div id="addmsg" class="muted"></div>
    <hr>
    <h2>Set up a Google Alert</h2>
    <div class="row"><input id="topic" placeholder="e.g. Latest AI News" style="flex:1"><button id="alertbtn">Create alert</button></div>
    <div id="alertmsg" class="muted"></div>
  </section>

  <!-- Center: the active job -->
  <section>
    <h2>Active job <span id="mode" class="muted"></span></h2>
    <div id="active"><p class="muted">Loading…</p></div>
    <hr>
    <h2>Newsroom log</h2>
    <pre id="log" class="log"></pre>
  </section>

  <!-- Right: review panels (lists only; one shared player pops up) -->
  <section>
    <h2>Review <span class="muted" style="font-weight:normal;text-transform:none;letter-spacing:0">— pick a video; the player pops up</span></h2>
    <div id="panels"><p class="muted">Loading…</p></div>
  </section>
  <section>
    <h2>House style <span class="muted" style="font-size:12px;font-weight:normal">learned from your feedback; every new script and visual follows these</span></h2>
    <div id="style"><p class="muted">No rules yet. Give feedback on a staged video.</p></div>
    <div class="row" style="margin-top:8px"><select id="starea"><option>script</option><option>humor</option><option>visuals</option><option>voice</option><option selected>general</option></select>
      <input id="strule" placeholder="Add a rule by hand" style="flex:1"><button id="stadd">Add</button></div>
  </section>
</main>
<!-- page script trimmed -->
```

## Publisher files today

### templates/base.html
```
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>YouTube Publisher</title><link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}"></head><body>
<header><a class="brand" href="/">◉ <strong>YouTube Publisher</strong></a><span class="badge">LOCAL STUDIO</span><span class="muted">Finished videos. Ready for their audience.</span><span class="status-dot">●</span><span>Ready</span></header>
{% block content %}{% endblock %}<script src="{{ url_for('static', filename='js/publish.js') }}" defer></script></body></html>
```

### templates/publish.html
```
{% extends 'base.html' %}{% block content %}
<div class="page-heading"><div class="eyebrow">YOUR PUBLISHING DESK</div><h1>Give your video its next chapter.</h1><p class="muted">Choose a finished video, fine-tune the details, and publish to your channel.</p></div>
<main><section class="details"><form id="publish-form">
<div class="card"><div class="section-title"><span class="step">01</span><h2>Choose your video</h2></div><div class="two"><label>Channel<select id="channel">{% for c in channels %}<option value="{{c.key}}">{{c.name}}</option>{% endfor %}</select></label><label>Finished job<select id="job"><option>Loading jobs…</option></select></label></div>
<div class="tabs" role="tablist" aria-label="Video type"><button type="button" id="tab-short" role="tab" data-kind="short">Short <span>9:16</span></button><button type="button" id="tab-long" role="tab" data-kind="long">Explainer <span>16:9</span></button></div><p id="job-error" class="error" role="alert"></p></div>
<div class="card"><div class="section-title"><span class="step">02</span><h2>Make the first impression</h2></div><div class="thumb-layout"><img id="thumbnail" alt="Selected thumbnail"><div><h3>Thumbnail</h3><p class="muted small">The first frame of your story.</p><button type="button" class="secondary" id="frame-open">Regenerate from frame</button><button type="button" class="secondary" id="custom-open">Upload custom</button><button type="button" class="text-button" id="generated">Use generated</button><input type="file" id="custom-file" accept="image/png,image/jpeg,image/webp" hidden></div></div>
<div class="field-head"><label for="title">Title</label><button type="button" class="text-button regenerate" data-field="title">↻ Regenerate</button></div><input id="title" maxlength="100" required placeholder="A title that makes the story clear"><div class="count" id="title-count">0 / 100</div>
<div class="field-head"><label for="description">Description</label><button type="button" class="text-button regenerate" data-field="description">↻ Regenerate</button></div><textarea id="description" maxlength="5000" rows="8" required></textarea><div id="hook-preview" class="hook-preview"></div><div class="count" id="description-count">0 / 5000</div>
<div class="field-head"><label for="tag-entry">Tags</label><button type="button" class="text-button regenerate" data-field="tags">↻ Regenerate</button></div><div id="tags" class="chips"></div><input id="tag-entry" placeholder="Add a tag, then press Enter"><div class="count" id="tags-count">0 / 500</div>
<label>Category<select id="category">{% for c in categories %}<option>{{c}}</option>{% endfor %}</select></label></div>
<div class="card"><div class="section-title"><span class="step">03</span><h2>Set the destination</h2></div><fieldset><legend>Visibility</legend><div class="radio-row"><label><input type="radio" name="visibility" value="Private" checked> Private</label><label><input type="radio" name="visibility" value="Unlisted"> Unlisted</label><label><input type="radio" name="visibility" value="Public"> Public</label></div></fieldset>
<fieldset><legend>Made for kids</legend><div class="radio-row"><label><input type="radio" name="kids" value="no" checked> No</label><label><input type="radio" name="kids" value="yes"> Yes</label></div></fieldset><label>Video language<select id="language">{% for l in ['English','Spanish','French','German','Arabic','Hindi','Urdu'] %}<option>{{l}}</option>{% endfor %}</select></label>
<div id="chapter-section"><div class="field-head"><label>Chapters</label><button type="button" class="text-button regenerate" data-field="chapters">↻ Regenerate</button></div><div id="chapters"></div><button type="button" class="secondary" id="add-chapter">+ Add chapter</button><p class="small muted">Start at 0:00. Add at least three chapters, or leave empty.</p></div>
<label id="link-label" for="link-search">End screen link (optional)</label><input id="link-search" placeholder="Search published videos by title, channel or ID"><select id="link-target"><option value="">None — publish without a link</option></select><p class="small muted">Only previously published videos appear here.</p></div>
<div class="actions"><button type="submit" id="publish-button">Publish to YouTube <span>↗</span></button><button type="button" class="secondary" id="publish-both" hidden title="Explainer first; its link then goes into the Short">Publish both ↗</button><button type="button" class="secondary" id="save-draft">Save draft</button><button type="button" class="text-button" id="reset">Reset</button><button type="button" class="text-button" id="cancel">Cancel</button></div><p id="form-message" role="status"></p></form></section>
<aside><div class="preview card"><div class="field-head"><h2>Video preview</h2><span class="badge" id="preview-kind">EXPLAINER</span></div><div class="video-stage"><video id="player" controls preload="metadata"></video></div><h3 id="filename">Choose a finished job</h3><div id="file-info" class="media-facts"></div><p class="small muted">Preview only · Your video stays exactly as rendered.</p></div>
<div class="card progress"><div class="field-head"><h2>Publishing activity</h2><span id="task-status" class="badge">IDLE</span></div><div id="progress-empty"><span class="orbit">↗</span><h3>Your next upload starts here.</h3><p class="muted small">Follow each step and see Studio screenshots as your video uploads.</p></div><div id="progress-log" aria-live="polite"></div><div id="result"></div><div id="recovery" hidden><button type="button" id="retry" class="secondary">Retry from this step</button><button type="button" id="restart" class="secondary">Restart upload</button></div></div></aside></main>
<dialog id="frame-dialog"><h2>Pick your thumbnail frame</h2><video id="frame-player" controls preload="metadata"></video><label>Frame position <input id="frame-time" type="range" min="0" max="1" step="0.1" value="0"></label><span id="frame-position">0:00</span><div class="actions"><button id="frame-save">Use this frame</button><button class="secondary" id="frame-close">Cancel</button></div></dialog>
{% endblock %}
```

### static/css/style.css
```
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mut:#8b949e;--acc:#f5a524;--ok:#3ecf8e;--bad:#ff5c5c}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,Segoe UI,sans-serif}header{display:flex;align-items:center;gap:18px;border-bottom:1px solid var(--line);padding:20px 4vw}.brand{color:var(--fg);text-decoration:none;font-size:18px}.brand:first-letter{color:var(--acc)}header .muted{flex:1}.badge{font-size:10px;letter-spacing:.1em;border:1px solid var(--line);border-radius:5px;padding:4px 8px;color:var(--mut);white-space:nowrap}.status-dot{color:var(--ok)}.muted{color:var(--mut)}.small{font-size:12px}.page-heading{max-width:1430px;margin:38px auto 28px;padding:0 28px}.eyebrow{font-size:11px;color:var(--acc);letter-spacing:.16em;font-weight:700}h1{font-size:32px;letter-spacing:-.04em;margin:9px 0}h2{font-size:16px;margin:0}h3{font-size:14px;margin:8px 0}p{margin:5px 0 12px}main{display:grid;grid-template-columns:minmax(420px,1fr) minmax(420px,1.05fr);gap:26px;max-width:1430px;margin:auto;padding:0 28px 60px}section,aside{min-width:0}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:18px}.section-title{display:flex;align-items:center;gap:12px;margin-bottom:18px}.step{color:var(--acc);font-size:11px;border:1px solid #665027;padding:4px 7px;border-radius:6px}.two{display:grid;grid-template-columns:1fr 1.2fr;gap:14px}label,legend{display:block;font-size:12px;color:var(--mut);margin:12px 0 6px}input,select,textarea{width:100%;background:#0d1117;border:1px solid var(--line);border-radius:7px;padding:10px 12px;color:var(--fg);font:inherit}textarea{resize:vertical}input:focus,select:focus,textarea:focus{outline:1px solid var(--acc)}button{border:0;border-radius:7px;background:var(--acc);color:#16120a;padding:10px 15px;font-weight:650;cursor:pointer}button:disabled{opacity:.32;cursor:not-allowed}.secondary{border:1px solid var(--line);background:transparent;color:var(--fg)}.text-button{background:none;color:var(--mut);padding:5px;font-size:12px}.text-button:hover{color:var(--acc)}.tabs{display:flex;background:#0d1117;padding:5px;border:1px solid var(--line);border-radius:8px;margin-top:18px;gap:5px}.tabs button{flex:1;background:none;color:var(--mut)}.tabs button.active{background:#302617;color:var(--acc)}.tabs span{font-size:10px;margin-left:6px;opacity:.7}.field-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px}.count{font-size:11px;text-align:right;color:var(--mut);margin:4px 0}.thumb-layout{display:grid;grid-template-columns:150px 1fr;gap:20px;align-items:center;margin-bottom:16px}.thumb-layout img{width:150px;aspect-ratio:16/9;object-fit:contain;background:#0d1117;border:1px solid var(--line);border-radius:8px}.thumb-layout button{display:block;margin:7px 0;font-size:12px}.chips{display:flex;flex-wrap:wrap;gap:6px;margin:5px 0}.chip{padding:4px 7px;background:#252c36;border:1px solid var(--line);border-radius:5px;font-size:11px}.chip button{padding:0 0 0 6px;background:none;color:var(--mut)}fieldset{border:0;padding:0;margin:0 0 14px}.radio-row{display:flex;gap:24px}.radio-row label{display:flex;align-items:center;gap:7px;margin:0;color:var(--fg)}input[type=radio]{width:auto;accent-color:var(--acc)}.chapter-row{display:flex;gap:6px;margin-bottom:6px}.chapter-row input:first-child{width:85px}.chapter-row button{padding:5px 9px}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:18px}.actions button:first-child{flex:1}.actions span{margin-left:12px}.preview{position:sticky;top:18px}.video-stage{background:#080b10;border-radius:8px;margin-top:16px;display:flex;justify-content:center;min-height:220px}video{max-width:100%;max-height:450px;width:100%;border-radius:8px}video.short{aspect-ratio:9/16;width:auto;height:450px}.media-facts{display:flex;gap:15px;flex-wrap:wrap;color:var(--mut);font-size:11px;margin:9px 0 14px}.progress{margin-top:18px}#progress-empty{text-align:center;padding:25px 0}.orbit{font-size:30px;color:var(--mut);display:inline-block;border:1px solid var(--line);border-radius:50%;width:58px;height:58px;line-height:54px;margin-bottom:12px}#progress-log{max-height:550px;overflow-y:auto}.event{font-size:12px;border-bottom:1px solid #242a34;padding:9px 0}.event time{color:var(--mut);margin-right:9px}.event img{width:100%;border-radius:6px;margin-top:8px}.error,#form-message.error{color:var(--bad)}.success{color:var(--ok)}.hook-preview{border-left:2px solid var(--acc);padding:6px 10px;background:#241f16;white-space:pre-wrap;font-size:11px;color:#d9bc87;margin-top:5px;max-height:85px;overflow:auto}dialog{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:12px;width:min(700px,90vw);padding:25px}dialog::backdrop{background:#000a}a{color:var(--acc)}#result a{display:block;margin:12px 0;overflow-wrap:anywhere}@media(max-width:950px){main{grid-template-columns:1fr}.preview{position:static}aside{grid-row:1}header .muted{display:none}.page-heading{margin-top:24px}h1{font-size:26px}}@media(max-width:500px){main{padding:0 14px 40px}.two{grid-template-columns:1fr}.thumb-layout{grid-template-columns:100px 1fr}.thumb-layout img{width:100px}header{gap:10px}.card{padding:16px}}
```

### static/js/publish.js
```
const $ = id => document.getElementById(id);
let jobs=[], records=[], kind='long', tags=[], thumb='', currentTask=null, generation=0, busy=false;
async function api(url, data, method='POST') { const r=await fetch(url, data===undefined?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); const j=await r.json(); if(!r.ok)throw Error(j.error||r.statusText); return j; }
function message(text,error=false){$('form-message').textContent=text;$('form-message').className=error?'error':'success';}
function renderTags(){ $('tags').replaceChildren(); tags.forEach((tag,i)=>{const s=document.createElement('span');s.className='chip';s.append(document.createTextNode(tag));const b=document.createElement('button');b.type='button';b.textContent='×';b.onclick=()=>{tags.splice(i,1);renderTags();};s.append(b);$('tags').append(s);});$('tags-count').textContent=(tags.reduce((n,t)=>n+t.length+(t.includes(' ')?2:0),0)+Math.max(tags.length-1,0))+' / 500'; }
function chapter(seconds=0,title=''){ const row=document.createElement('div');row.className='chapter-row';const stamp=document.createElement('input');stamp.value=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');stamp.placeholder='0:00';stamp.setAttribute('aria-label','Chapter timestamp');const name=document.createElement('input');name.value=title;name.placeholder='Chapter title';name.setAttribute('aria-label','Chapter title');const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent='×';remove.onclick=()=>row.remove();row.append(stamp,name,remove);$('chapters').append(row); }
function form(){const chapters=[...$('chapters').children].map(r=>{const [stamp,title]=r.querySelectorAll('input');if(!/^\d+:[0-5]\d(?::[0-5]\d)?$/.test(stamp.value))throw Error('Use valid chapter timestamps, such as 0:00.');return {seconds:stamp.value.split(':').reduce((a,n)=>a*60+Number(n),0),title:title.value};});return {job:$('job').value,kind,channel:$('channel').value,title:$('title').value,description:$('description').value,tags,category:$('category').value,visibility:document.querySelector('[name=visibility]:checked').value,made_for_kids:document.querySelector('[name=kids]:checked').value==='yes',language:$('language').value,chapters:kind==='long'?chapters:[],thumbnail:thumb,link_target:$('link-target').value};}
function counts(){ $('title-count').textContent=$('title').value.length+' / 100';$('description-count').textContent=$('description').value.length+' / 5000';$('hook-preview').textContent=$('description').value.split('\n').slice(0,3).join('\n'); }
function previewThumb(){ $('thumbnail').src=thumb?`/api/thumbnail/${$('channel').value}/${$('job').value}/${kind}/${thumb}?v=${Date.now()}`:'';$('thumbnail').style.aspectRatio=kind==='short'?'9/16':'16/9'; }
function linkOptions(){const search=$('link-search').value.toLowerCase(),selected=$('link-target').value;$('link-target').replaceChildren(new Option('None — publish without a link',''));records.filter(r=>!(r.job===$('job').value&&r.kind===kind&&r.channel===$('channel').value)&&`${r.title} ${r.channel} ${r.video_id}`.toLowerCase().includes(search)).forEach(r=>$('link-target').add(new Option(`${r.title} · ${r.channel} · ${r.video_id}`,r.video_id)));$('link-target').value=selected;}
async function load(){$('publish-button').disabled=true;const seq=++generation,job=jobs.find(j=>j.id===$('job').value);$('job-error').textContent='';for(const k of ['short','long']){$('tab-'+k).disabled=!job?.types[k];$('tab-'+k).classList.toggle('active',kind===k);$('tab-'+k).setAttribute('aria-selected',kind===k);}if(!job||!Object.keys(job.types).length){$('job-error').textContent='No video found in this job folder.';$('publish-button').disabled=true;$('player').removeAttribute('src');$('player').load();$('thumbnail').removeAttribute('src');$('filename').textContent='No video found in this job folder.';$('file-info').textContent='';return;}if(!job.types[kind]){kind=job.types.long?'long':'short';return load();}try{const j=await api(`/api/defaults/${job.id}/${kind}/${$('channel').value}`);if(seq!==generation)return;const d=j.data;$('title').value=d.title;$('description').value=d.description;tags=d.tags;thumb=d.thumbnail;$('category').value=d.category;$('language').value=d.language;document.querySelector('[name=visibility][value=Private]').checked=true;document.querySelector('[name=kids][value=no]').checked=true;$('chapters').replaceChildren();d.chapters.forEach(c=>chapter(c.seconds,c.title));$('chapter-section').hidden=kind==='short';$('link-label').textContent=kind==='short'?'Link this Short to (optional):':'End screen link (optional):';$('link-target').value='';$('player').src=`/api/video/${job.id}/${kind}`;$('player').classList.toggle('short',kind==='short');$('preview-kind').textContent=kind==='short'?'SHORT · 9:16':'EXPLAINER · 16:9';$('filename').textContent=j.media.filename;const m=j.media;$('file-info').textContent=`${(m.size/1024/1024).toFixed(1)} MB · ${Math.floor(m.duration/60)}:${String(Math.floor(m.duration%60)).padStart(2,'0')} · ${m.width} × ${m.height} · ${m.fps} fps`;renderTags();previewThumb();counts();linkOptions();$('publish-button').disabled=busy;$('publish-both').hidden=!(job.types.long&&job.types.short);$('publish-both').disabled=busy;}catch(e){message(e.message,true);}}
async function start(mode='new'){try{const data=form();if(!data.thumbnail||!data.title.trim()||!data.description.trim())throw Error('Choose a thumbnail and fill title and description.');if(mode==='restart'){if(!confirm('An existing upload may already exist. Restart can create a duplicate. Check Studio first. Continue?'))return;data.confirm_restart=true;}data.mode=mode;const result=await api('/publish',data);currentTask=result.task_id;localStorage.setItem('publisherTask',currentTask);busy=true;$('publish-button').disabled=true;$('recovery').hidden=true;$('progress-empty').hidden=true;$('progress-log').replaceChildren();message('Publishing started.');poll();}catch(e){message(e.message,true);$('recovery').hidden=false;}}
let shown=0;
let pairNext=null;async function startPair(){try{const job=$('job').value,ch=$('channel').value,cur=form();if(!cur.thumbnail||!cur.title.trim()||!cur.description.trim())throw Error('Choose a thumbnail and fill title and description.');const other=kind==='long'?'short':'long',o=(await api(`/api/defaults/${job}/${other}/${ch}`)).data;const body={};body[kind]=cur;body[other]=o;if(!confirm('Publish the explainer first, then the Short with the explainer link (both Private unless chosen otherwise)?'))return;const r=await api('/publish/pair',body);currentTask=r.long_task;pairNext=r.short_task;localStorage.setItem('publisherTask',currentTask);busy=true;$('publish-button').disabled=true;$('publish-both').disabled=true;$('progress-empty').hidden=true;$('progress-log').replaceChildren();message('Publishing the explainer, then the Short.');poll();}catch(e){message(e.message,true);}}
async function poll(){try{const t=await api('/publish/status/'+currentTask);$('task-status').textContent=t.status.toUpperCase();if(shown>$('progress-log').childElementCount)shown=0;t.events.slice(shown).forEach(e=>{const div=document.createElement('div');div.className='event';const time=document.createElement('time');time.textContent=e.time;div.append(time,document.createTextNode(e.message));if(e.screenshot){const img=document.createElement('img');img.loading='lazy';img.alt=e.message;img.src=`/publish/screenshot/${currentTask}/${e.screenshot}`;div.append(img);}$('progress-log').append(div);});shown=t.events.length;if(t.status==='complete'&&pairNext){const nx=pairNext;pairNext=null;currentTask=nx;shown=0;localStorage.setItem('publisherTask',nx);$('progress-log').replaceChildren();message('Explainer done: '+t.result.url+' — publishing the Short.');setTimeout(poll,1000);return;}if(t.status==='complete'){$('result').replaceChildren();const a=document.createElement('a');a.href=t.result.url;a.target='_blank';a.rel='noopener';a.textContent='Open on YouTube ↗';$('result').append(a);if(t.result.link_error){const p=document.createElement('p');p.className='error';p.textContent=t.result.link_error;$('result').append(p);$('recovery').hidden=false;}records=await api('/api/published');linkOptions();busy=false;$('publish-button').disabled=false;}else if(['error','cancelled'].includes(t.status)){message(t.error||'Cancelled',true);$('recovery').hidden=false;busy=false;$('publish-button').disabled=false;}else setTimeout(poll,1000);}catch(e){message(e.message,true);busy=false;$('publish-button').disabled=false;}}
document.addEventListener('DOMContentLoaded',async()=>{$('publish-form').onsubmit=e=>{e.preventDefault();shown=0;start();};$('job').onchange=load;$('channel').onchange=load;['short','long'].forEach(k=>$('tab-'+k).onclick=()=>{kind=k;load();});$('title').oninput=counts;$('description').oninput=counts;$('tag-entry').onkeydown=e=>{if(e.key==='Enter'||e.key===','){e.preventDefault();const t=e.target.value.trim();if(t&&!tags.some(x=>x.toLowerCase()===t.toLowerCase()))tags.push(t);e.target.value='';renderTags();}};$('add-chapter').onclick=()=>chapter();$('link-search').oninput=linkOptions;$('publish-both').onclick=startPair;$('save-draft').onclick=async()=>{try{await api('/api/draft',form());message('Draft saved.');}catch(e){message(e.message,true);}};$('reset').onclick=load;$('cancel').onclick=async()=>{if(currentTask&&busy)await api('/publish/cancel/'+currentTask,{});else{message('Cancelled.');load();}};$('retry').onclick=()=>{shown=0;start('resume');};$('restart').onclick=()=>{shown=0;start('restart');};document.querySelectorAll('.regenerate').forEach(b=>b.onclick=async()=>{b.disabled=true;message('Regenerating '+b.dataset.field+'…');try{const snapshot=form();const j=await api('/api/regenerate',{...snapshot,field:b.dataset.field});if(snapshot.job!==$('job').value||snapshot.kind!==kind||snapshot.channel!==$('channel').value)return;if(b.dataset.field==='tags'){tags=j.value;renderTags();}else if(b.dataset.field==='chapters'){$('chapters').replaceChildren();j.value.forEach(c=>chapter(c.seconds,c.title));}else $(b.dataset.field).value=j.value;counts();message('Updated '+b.dataset.field+'.');}catch(e){message(e.message,true);}finally{b.disabled=false;}});
async function uploadThumb(file,seconds){try{const data=new FormData();data.set('job',$('job').value);data.set('channel',$('channel').value);data.set('kind',kind);if(file)data.set('file',file);else data.set('seconds',seconds);const r=await fetch('/api/thumbnail',{method:'POST',body:data});const j=await r.json();if(!r.ok)throw Error(j.error);thumb=j.thumbnail;previewThumb();$('frame-dialog').close();message('Thumbnail updated.');}catch(e){message(e.message,true);}}
$('custom-open').onclick=()=>$('custom-file').click();$('custom-file').onchange=e=>{if(e.target.files[0])uploadThumb(e.target.files[0]);};$('generated').onclick=()=>{thumb='generated';previewThumb();};$('frame-open').onclick=()=>{$('frame-player').src=$('player').src;$('frame-dialog').showModal();};$('frame-player').onloadedmetadata=()=>{$('frame-time').max=Math.max(0,$('frame-player').duration-.1);};$('frame-time').oninput=e=>{$('frame-player').currentTime=Number(e.target.value);$('frame-position').textContent=Math.floor(e.target.value/60)+':'+String(Math.floor(e.target.value%60)).padStart(2,'0');};$('frame-save').onclick=()=>uploadThumb(null,$('frame-player').currentTime);$('frame-close').onclick=()=>{$('frame-player').pause();$('frame-dialog').close();};
try{jobs=await api('/api/jobs');records=await api('/api/published');$('job').replaceChildren();jobs.forEach(j=>$('job').add(new Option(j.id,j.id)));const selected=new URLSearchParams(location.search).get('job');if(jobs.some(j=>j.id===selected))$('job').value=selected;await load();const previous=new URLSearchParams(location.search).get('task')||localStorage.getItem('publisherTask');if(previous){currentTask=previous;$('progress-empty').hidden=true;poll();}}catch(e){message(e.message,true);}});
```

### app.py (routes and startup excerpts)
```python
"""Local, independent publishing UI. Run only on loopback."""
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image
import publisher_logic as logic
import youtube_publisher as backend

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
tasks = {}
task_lock = threading.Lock()
browser_lock = threading.Lock()

@app.before_request
def local_requests():
    # Prevent a remote site from submitting publish requests to localhost.
    if request.method != 'GET':
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='Cross-origin requests are not allowed.'), 403
    if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
        return jsonify(error='Local access only.'), 403

@app.errorhandler(ValueError)
@app.errorhandler(FileNotFoundError)
def input_error(error):
    return jsonify(error=str(error)), 400

@app.get('/')
def home():
    channels = []
    for path in (ROOT / 'channel_configs').glob('*.json'):
        channels.append({'key': path.stem, 'name': backend.read_json(path)['youtube_channel_name']})
    return render_template('publish.html', channels=channels, categories=backend.CATEGORIES)

@app.get('/health')
def health():
    return jsonify(service='youtube-publisher', port=logic.config()['port'])

@app.get('/api/jobs')
def jobs():
    return jsonify(logic.jobs())

@app.get('/api/published')
def published():
    return jsonify(logic.records())

@app.get('/api/video/<job>/<kind>')
def video(job, kind):
    return send_file(logic.assets(job, kind)[0], conditional=True)

@app.get('/api/defaults/<job>/<kind>/<channel>')
def defaults(job, kind, channel):
    data = logic.defaults(job, kind, channel)
    video, thumb, _ = logic.assets(job, kind)
    return jsonify(data=data, media=dict(filename=video.name, size=video.stat().st_size, **logic.probe(video)))

@app.get('/api/thumbnail/<channel>/<job>/<kind>/<name>')
def thumbnail(channel, job, kind, name):
    return send_file(logic.thumbnail_path(dict(channel=channel, job=job, kind=kind, thumbnail=name)), conditional=True)
...
@app.post('/publish/cancel/<task_id>')
def cancel(task_id):
    if task_id in tasks:
        tasks[task_id]['cancel_requested'] = True
    return jsonify(cancelled=True)

if __name__ == '__main__':
    cfg = logic.config()
    Path(cfg['log_dir']).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=Path(cfg['log_dir']) / 'publisher.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    app.run(host='127.0.0.1', port=int(cfg['port']), debug=False, threaded=True, use_reloader=False)
```

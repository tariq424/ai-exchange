## Summary
Switches the YouTube Publisher to the Newsroom light theme and panel/rotator list pattern, adds the shared `pubplayer` popup page with the full publishing desk, and adds a server-side TEST guard based on the actual port.

---

### `templates/base.html`
```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Publisher</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body data-test-mode="{{ 'true' if test_mode else 'false' }}" data-default-channel="{{ default_channel }}" data-actual-port="{{ actual_port }}" data-live-port="{{ live_port }}">
<header>
  <a class="brand" href="/">◉ <strong>YouTube Publisher</strong></a>
  {% if test_mode %}<span class="test-pill" title="TEST copy on port {{ actual_port }} — non-GET actions are disabled server-side">TEST</span>{% endif %}
  <span class="muted">Finished videos. Ready for their audience.</span>
  <span class="status-dot">●</span><span>Ready</span>
</header>
{% block content %}{% endblock %}
{% block scripts %}{% endblock %}
</body>
</html>
```

---

### `templates/publish.html`
```html
{% extends 'base.html' %}
{% block content %}
<div class="page-heading">
  <div class="eyebrow">YOUR PUBLISHING DESK</div>
  <h1>Give your video its next chapter.</h1>
  <p class="muted">Choose a finished video or a published one; the full publishing desk opens in a popup.</p>
</div>
<main class="lists">
  <section class="panel ready-panel">
    <h2>Ready to publish <span class="muted normal">— pick a video; the publisher pops up</span></h2>
    <div id="ready"><p class="muted">Loading…</p></div>
  </section>

  <section class="panel published-panel">
    <h2>Published <span class="muted normal">— open to see links</span></h2>
    <div id="published"><p class="muted">Loading…</p></div>
  </section>
</main>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/publish.js') }}" defer></script>
{% endblock %}
```

---

### `templates/player.html`
```html
{% extends 'base.html' %}
{% block content %}
<div class="player-shell">
  <div class="card player-card">
    <div class="row spread">
      <div>
        <div class="eyebrow">PUBLISHING DESK</div>
        <h1 id="player-title">{{ 'Published video' if published else 'Fine-tune and publish' }}</h1>
      </div>
      <button type="button" class="secondary" onclick="window.close()">Close ✕</button>
    </div>

    <div id="job-error" class="error" role="alert"></div>

    <div class="row channel-row">
      <label>Channel
        <select id="channel">
          {% for c in channels %}
          <option value="{{ c.key }}" {% if c.key == channel %}selected{% endif %}>{{ c.name }}</option>
          {% endfor %}
        </select>
      </label>
      <input type="hidden" id="job" value="{{ job }}">
    </div>

    <div class="tabs" role="tablist" aria-label="Video type">
      <button type="button" id="tab-short" role="tab" data-kind="short">Short <span>9:16</span></button>
      <button type="button" id="tab-long" role="tab" data-kind="long">Explainer <span>16:9</span></button>
    </div>

    <div id="published-links" class="card section-card" hidden></div>

    <div class="video-preview-card card section-card">
      <div class="section-title"><span class="step">01</span><h2>Preview</h2><span class="badge" id="preview-kind">EXPLAINER</span></div>
      <div class="video-stage"><video id="player" controls preload="metadata"></video></div>
      <h3 id="filename">Choose a finished job</h3>
      <div id="file-info" class="media-facts"></div>
      <p class="small muted">Preview only · Your video stays exactly as rendered.</p>
    </div>

    <form id="publish-form">
      <div class="player-grid">
        <div class="player-main edit-only">
          <div class="card section-card">
            <div class="section-title"><span class="step">02</span><h2>Make the first impression</h2></div>
            <div class="thumb-layout">
              <img id="thumbnail" alt="Selected thumbnail">
              <div>
                <h3>Thumbnail</h3>
                <p class="muted small">The first frame of your story.</p>
                <button type="button" class="secondary js-action" id="frame-open">Regenerate from frame</button>
                <button type="button" class="secondary js-action" id="custom-open">Upload custom</button>
                <button type="button" class="text-button js-action" id="generated">Use generated</button>
                <input type="file" id="custom-file" accept="image/png,image/jpeg,image/webp" hidden>
              </div>
            </div>

            <div class="field-head"><label for="title">Title</label><button type="button" class="text-button regenerate js-action" data-field="title">↻ Regenerate</button></div>
            <input id="title" maxlength="100" required placeholder="A title that makes the story clear">
            <div class="count" id="title-count">0 / 100</div>

            <div class="field-head"><label for="description">Description</label><button type="button" class="text-button regenerate js-action" data-field="description">↻ Regenerate</button></div>
            <textarea id="description" maxlength="5000" rows="8" required></textarea>
            <div id="hook-preview" class="hook-preview"></div>
            <div class="count" id="description-count">0 / 5000</div>

            <div class="field-head"><label for="tag-entry">Tags</label><button type="button" class="text-button regenerate js-action" data-field="tags">↻ Regenerate</button></div>
            <div id="tags" class="chips"></div>
            <input id="tag-entry" placeholder="Add a tag, then press Enter">
            <div class="count" id="tags-count">0 / 500</div>

            <label>Category
              <select id="category">
                {% for c in categories %}<option>{{ c }}</option>{% endfor %}
              </select>
            </label>
          </div>

          <div class="card section-card">
            <div class="section-title"><span class="step">03</span><h2>Set the destination</h2></div>
            <fieldset>
              <legend>Visibility</legend>
              <div class="radio-row">
                <label><input type="radio" name="visibility" value="Private" checked> Private</label>
                <label><input type="radio" name="visibility" value="Unlisted"> Unlisted</label>
                <label><input type="radio" name="visibility" value="Public"> Public</label>
              </div>
            </fieldset>
            <fieldset>
              <legend>Made for kids</legend>
              <div class="radio-row">
                <label><input type="radio" name="kids" value="no" checked> No</label>
                <label><input type="radio" name="kids" value="yes"> Yes</label>
              </div>
            </fieldset>
            <label>Video language
              <select id="language">
                {% for l in ['English','Spanish','French','German','Arabic','Hindi','Urdu'] %}<option>{{ l }}</option>{% endfor %}
              </select>
            </label>
            <div id="chapter-section">
              <div class="field-head"><label>Chapters</label><button type="button" class="text-button regenerate js-action" data-field="chapters">↻ Regenerate</button></div>
              <div id="chapters"></div>
              <button type="button" class="secondary" id="add-chapter">+ Add chapter</button>
              <p class="small muted">Start at 0:00. Add at least three chapters, or leave empty.</p>
            </div>
            <label id="link-label" for="link-search">End screen link (optional)</label>
            <input id="link-search" placeholder="Search published videos by title, channel or ID">
            <select id="link-target">
              <option value="">None — publish without a link</option>
            </select>
            <p class="small muted">Only previously published videos appear here.</p>
          </div>
        </div>

        <aside class="player-side edit-only">
          <div class="card progress">
            <div class="field-head"><h2>Publishing activity</h2><span id="task-status" class="badge">IDLE</span></div>
            <div id="progress-empty">
              <span class="orbit">↗</span>
              <h3>Your next upload starts here.</h3>
              <p class="muted small">Follow each step and see Studio screenshots as your video uploads.</p>
            </div>
            <div id="progress-log" aria-live="polite"></div>
            <div id="result"></div>
            <div id="recovery" hidden>
              <button type="button" id="retry" class="secondary js-action">Retry from this step</button>
              <button type="button" id="restart" class="secondary js-action">Restart upload</button>
            </div>
          </div>

          <div class="actions">
            <button type="submit" id="publish-button" class="primary js-action">Publish to YouTube <span>↗</span></button>
            <button type="button" class="secondary js-action" id="publish-both" hidden title="Explainer first; its link then goes into the Short">Publish both ↗</button>
            <button type="button" class="secondary js-action" id="save-draft">Save draft</button>
            <button type="button" class="text-button" id="reset">Reset</button>
            <button type="button" class="text-button" id="cancel">Cancel</button>
          </div>
          <p id="form-message" role="status"></p>
        </aside>
      </div>
    </form>
  </div>
</div>

<dialog id="frame-dialog">
  <h2>Pick your thumbnail frame</h2>
  <video id="frame-player" controls preload="metadata"></video>
  <label>Frame position <input id="frame-time" type="range" min="0" max="1" step="0.1" value="0"></label>
  <span id="frame-position">0:00</span>
  <div class="actions">
    <button id="frame-save" class="js-action">Use this frame</button>
    <button class="secondary" id="frame-close">Cancel</button>
  </div>
</dialog>
{% endblock %}

{% block scripts %}
<script>
window.PLAYER_JOB = {{ job|tojson }};
window.PLAYER_KIND = {{ kind|tojson }};
window.PLAYER_CHANNEL = {{ channel|tojson }};
window.PLAYER_PUBLISHED = {{ 'true' if published else 'false' }};
</script>
<script src="{{ url_for('static', filename='js/player.js') }}" defer></script>
{% endblock %}
```

---

### `static/css/style.css`
```css
:root{
  --bg:#f3f0e9;
  --panel:#ffffff;
  --line:#ccd3da;
  --text:#1d2733;
  --dim:#5d6b7a;
  --acc:#d99400;
  --ok:#1a9e6b;
  --bad:#d93a3a;
  --blue:#2f7fe0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 Inter,Segoe UI,system-ui,sans-serif}

header{display:flex;align-items:center;gap:18px;border-bottom:1px solid var(--line);padding:12px 18px;background:var(--panel)}
.brand{color:var(--text);text-decoration:none;font-size:17px;font-weight:700;white-space:nowrap}
.brand:first-letter{color:var(--acc)}
header .muted{flex:1;font-size:13px}
.status-dot{color:var(--ok)}
.badge{font-size:10px;letter-spacing:.08em;border:1px solid var(--line);border-radius:99px;padding:3px 8px;color:var(--dim);white-space:nowrap}
.test-pill{font-size:11px;padding:3px 9px;border-radius:99px;border:1px solid #d9a0a0;color:var(--bad);background:#fde8e8;animation:testPulse 2.2s ease-in-out infinite}
@keyframes testPulse{0%,100%{opacity:.45}50%{opacity:1}}

.muted{color:var(--dim)}
.small{font-size:12px}
.error{color:var(--bad)}
.success{color:var(--ok)}

.page-heading{max-width:1200px;margin:28px auto 18px;padding:0 18px}
.eyebrow{font-size:11px;color:var(--acc);letter-spacing:.14em;font-weight:700}
h1{font-size:26px;letter-spacing:-.03em;margin:6px 0}
h2{font-size:16px;margin:0}
h3{font-size:14px;margin:6px 0}
p{margin:5px 0 12px}

main.lists{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:1200px;margin:auto;padding:0 18px 40px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-height:240px}
.ready-panel{background:#fdf3d8}
.published-panel{background:#e7f5ec}
.panel h2{font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:var(--dim);margin:0 0 12px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.panel h2 .normal{font-weight:normal;text-transform:none;letter-spacing:0;font-size:12px}

.card{background:#ffffff;border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px}
.rotator-card h3{font-size:15px;margin:0 0 4px}
.rotator-top{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}
.counter{font-size:12px;color:var(--dim)}
.nav{display:flex;justify-content:space-between;align-items:center;margin-top:10px}
.nav button{font-size:13px}

.player-shell{max-width:1180px;margin:18px auto 40px;padding:0 16px}
.player-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.spread{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.channel-row{margin:12px 0 4px}
.player-grid{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:18px;margin-top:16px}
.player-main{min-width:0}
.player-side{min-width:0}
.section-card{margin-bottom:14px}
.section-title{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.step{color:var(--acc);font-size:11px;border:1px solid #d6b56b;padding:3px 7px;border-radius:6px}

input,select,textarea{width:100%;background:#ffffff;border:1px solid var(--line);border-radius:7px;padding:9px 10px;color:var(--text);font:inherit}
textarea{resize:vertical;font-size:16px;line-height:1.5}
#title{font-size:16px}
input:focus,select:focus,textarea:focus{outline:1px solid var(--acc)}

button{background:#ffffff;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:8px 12px;cursor:pointer;font:inherit}
button:hover:not(:disabled){border-color:var(--acc)}
button:disabled{opacity:.45;cursor:not-allowed}
button.primary{background:var(--acc);color:#111;border-color:var(--acc);font-weight:700}
button.go{background:#2e7d32;color:#fff;border-color:#2e7d32;font-weight:700}
.secondary{border:1px solid var(--line);background:transparent;color:var(--text)}
.text-button{background:none;border:none;color:var(--dim);padding:5px;font-size:13px}
.text-button:hover{color:var(--acc)}

.tabs{display:flex;background:#ffffff;padding:5px;border:1px solid var(--line);border-radius:8px;margin-top:14px;gap:5px}
.tabs button{flex:1;background:none;color:var(--dim);border:1px solid transparent}
.tabs button.active{background:#fdf3d8;color:var(--text);border-color:var(--line);font-weight:700}
.tabs span{font-size:10px;margin-left:6px;opacity:.7}

.field-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:12px}
.count{font-size:11px;text-align:right;color:var(--dim);margin:4px 0}
.thumb-layout{display:grid;grid-template-columns:150px 1fr;gap:18px;align-items:center;margin-bottom:14px}
.thumb-layout img{width:150px;aspect-ratio:16/9;object-fit:contain;background:#f3f0e9;border:1px solid var(--line);border-radius:8px}
.thumb-layout button{display:block;margin:6px 0;font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:5px 0}
.chip{padding:4px 8px;background:#f3f0e9;border:1px solid var(--line);border-radius:5px;font-size:12px}
.chip button{padding:0 0 0 6px;background:none;border:none;color:var(--dim);font:inherit}

fieldset{border:0;padding:0;margin:0 0 14px}
legend{font-size:12px;color:var(--dim);margin:0 0 6px}
.radio-row{display:flex;gap:22px;flex-wrap:wrap}
.radio-row label{display:flex;align-items:center;gap:7px;margin:0;color:var(--text);font-size:14px}
input[type=radio]{width:auto;accent-color:var(--acc)}

.chapter-row{display:flex;gap:6px;margin-bottom:6px}
.chapter-row input:first-child{width:85px}
.chapter-row input:last-child{flex:1}
.chapter-row button{padding:5px 9px;flex:0 0 auto}

.video-stage{background:#e8e4da;border-radius:8px;margin-top:14px;display:flex;justify-content:center;min-height:220px}
video{max-width:100%;max-height:460px;width:100%;border-radius:8px}
video.short{aspect-ratio:9/16;width:auto;height:420px}
.media-facts{display:flex;gap:15px;flex-wrap:wrap;color:var(--dim);font-size:12px;margin:8px 0 12px}

.progress{margin-bottom:14px}
#progress-empty{text-align:center;padding:24px 0}
.orbit{font-size:30px;color:var(--dim);display:inline-block;border:1px solid var(--line);border-radius:50%;width:58px;height:58px;line-height:54px;margin-bottom:12px}
#progress-log{max-height:520px;overflow-y:auto}
.event{font-size:12px;border-bottom:1px solid #e3ded2;padding:9px 0}
.event time{color:var(--dim);margin-right:9px;font-size:11px}
.event img{width:100%;border-radius:6px;margin-top:8px}
#form-message{font-size:13px;margin:8px 0;white-space:pre-wrap}
.hook-preview{border-left:2px solid var(--acc);padding:6px 10px;background:#fdf3d8;white-space:pre-wrap;font-size:12px;color:#5d4a10;margin-top:5px;max-height:85px;overflow:auto}

.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:18px}
.actions button:first-child{flex:1}
.actions span{margin-left:12px}

dialog{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:12px;width:min(700px,90vw);padding:22px}
dialog::backdrop{background:rgba(29,39,51,.45)}

a{color:var(--blue)}
#result a{display:block;margin:10px 0;overflow-wrap:anywhere;color:var(--blue)}

@media(max-width:950px){
  main.lists{grid-template-columns:1fr}
  .player-grid{grid-template-columns:1fr}
  .player-side{grid-row:1}
}
@media(max-width:500px){
  .thumb-layout{grid-template-columns:100px 1fr}
  .thumb-layout img{width:100px}
  .two{grid-template-columns:1fr}
  header .muted{display:none}
}
```

---

### `static/js/publish.js`
```javascript
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(url, data) {
  const r = await fetch(url, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const j = await r.json().catch(() => ({error: 'HTTP ' + r.status}));
  if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}

const DEFAULT_CHANNEL = document.body.dataset.defaultChannel || '';
const TEST_MODE = document.body.dataset.testMode === 'true';

function openItem(item, published = false) {
  const params = new URLSearchParams({
    job: item.job,
    kind: item.kind,
    channel: item.channel || DEFAULT_CHANNEL
  });
  if (published) params.set('published', '1');
  window.open('/player?' + params.toString(), 'pubplayer', 'width=1200,height=850');
}

function kindLabel(types) {
  if (types && types.long && types.short) return 'Explainer + Short';
  if (types && types.long) return 'Explainer';
  if (types && types.short) return 'Short';
  return 'Unknown';
}

function makeRotator(container, items, render) {
  let idx = 0;

  function paint() {
    container.replaceChildren();
    if (!items.length) {
      container.innerHTML = '<div class="card muted">Nothing here.</div>';
      return;
    }

    const item = items[idx];
    const card = document.createElement('div');
    card.className = 'rotator-card card';
    card.innerHTML = `
      <div class="rotator-top">
        <div class="tags muted">${render.tags ? esc(render.tags(item)) : ''}</div>
        <span class="counter">${idx + 1} of ${items.length}</span>
      </div>
      <div class="field-head">
        <h3>${esc(render.title(item))}</h3>
        <button class="primary open-btn" data-action="open">Open ↗</button>
      </div>
      <p class="muted">${esc(render.subtitle(item))}</p>`;

    card.querySelector('[data-action="open"]').onclick = () => render.open(item);
    container.append(card);

    if (items.length > 1) {
      const nav = document.createElement('div');
      nav.className = 'nav';

      const prev = document.createElement('button');
      prev.type = 'button';
      prev.className = 'secondary';
      prev.textContent = '← Prev';
      prev.onclick = () => { idx = (idx - 1 + items.length) % items.length; paint(); };

      const next = document.createElement('button');
      next.type = 'button';
      next.className = 'secondary';
      next.textContent = 'Next →';
      next.onclick = () => { idx = (idx + 1) % items.length; paint(); };

      nav.append(prev, next);
      container.append(nav);
    }
  }

  paint();
}

async function load() {
  try {
    const [jobs, published] = await Promise.all([
      api('/api/jobs'),
      api('/api/published')
    ]);

    const jobItems = jobs.map(j => ({
      job: j.id,
      kind: j.types && j.types.long ? 'long' : (j.types && j.types.short ? 'short' : 'long'),
      channel: j.channel || DEFAULT_CHANNEL,
      title: j.title || j.id,
      types: j.types || {}
    }));

    makeRotator($('ready'), jobItems, {
      tags: item => kindLabel(item.types),
      title: item => item.title,
      subtitle: item => `${item.channel || 'unknown channel'} · ${kindLabel(item.types)}`,
      open: item => openItem(item, false)
    });

    const pubItems = published.map(r => ({
      job: r.job,
      kind: r.kind === 'short' ? 'short' : 'long',
      channel: r.channel || DEFAULT_CHANNEL,
      title: r.title || r.job,
      video_id: r.video_id || ''
    }));

    makeRotator($('published'), pubItems, {
      tags: item => item.kind === 'short' ? 'Short' : 'Explainer',
      title: item => item.title,
      subtitle: item => `${item.channel || 'unknown channel'} · ${item.kind === 'short' ? 'Short' : 'Explainer'}${item.video_id ? ' · ' + item.video_id : ''}`,
      open: item => openItem(item, true)
    });
  } catch (e) {
    $('ready').innerHTML = `<div class="error">${esc(e.message)}</div>`;
    $('published').innerHTML = `<div class="error">${esc(e.message)}</div>`;
  }
}

window.addEventListener('message', e => {
  if (e.data && e.data.type === 'pub-action') load();
});

document.addEventListener('DOMContentLoaded', load);
```

---

### `static/js/player.js`
```javascript
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

let jobs = [], records = [], kind = window.PLAYER_KIND || 'long', tags = [], thumb = '';
let currentTask = null, generation = 0, busy = false;
let shown = 0, pairNext = null;

const TEST_MODE = document.body.dataset.testMode === 'true';
const DEFAULT_CHANNEL = document.body.dataset.defaultChannel || '';
const PUBLISHED_VIEW = window.PLAYER_PUBLISHED === true;

async function api(url, data, method = 'POST') {
  const r = await fetch(url, data === undefined ? {} : {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const j = await r.json().catch(() => ({error: 'HTTP ' + r.status}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

function message(text, error = false) {
  const el = $('form-message');
  if (!el) return;
  el.textContent = text;
  el.className = error ? 'error' : 'success';
}

function renderTags() {
  $('tags').replaceChildren();
  tags.forEach((tag, i) => {
    const s = document.createElement('span');
    s.className = 'chip';
    s.append(document.createTextNode(tag));
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = '×';
    b.onclick = () => { tags.splice(i, 1); renderTags(); };
    s.append(b);
    $('tags').append(s);
  });
  $('tags-count').textContent = (tags.reduce((n, t) => n + t.length + (t.includes(' ') ? 2 : 0), 0) + Math.max(tags.length - 1, 0)) + ' / 500';
}

function chapter(seconds = 0, title = '') {
  const row = document.createElement('div');
  row.className = 'chapter-row';

  const stamp = document.createElement('input');
  stamp.value = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
  stamp.placeholder = '0:00';
  stamp.setAttribute('aria-label', 'Chapter timestamp');

  const name = document.createElement('input');
  name.value = title;
  name.placeholder = 'Chapter title';
  name.setAttribute('aria-label', 'Chapter title');

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'secondary';
  remove.textContent = '×';
  remove.onclick = () => row.remove();

  row.append(stamp, name, remove);
  $('chapters').append(row);
}

function form() {
  const chapters = [...$('chapters').children].map(r => {
    const [stamp, title] = r.querySelectorAll('input');
    if (!/^\d+:[0-5]\d(?::[0-5]\d)?$/.test(stamp.value)) throw Error('Use valid chapter timestamps, such as 0:00.');
    return {seconds: stamp.value.split(':').reduce((a, n) => a * 60 + Number(n), 0), title: title.value};
  });
  return {
    job: $('job').value,
    kind,
    channel: $('channel').value,
    title: $('title').value,
    description: $('description').value,
    tags,
    category: $('category').value,
    visibility: document.querySelector('[name=visibility]:checked').value,
    made_for_kids: document.querySelector('[name=kids]:checked').value === 'yes',
    language: $('language').value,
    chapters: kind === 'long' ? chapters : [],
    thumbnail: thumb,
    link_target: $('link-target').value
  };
}

function counts() {
  $('title-count').textContent = $('title').value.length + ' / 100';
  $('description-count').textContent = $('description').value.length + ' / 5000';
  $('hook-preview').textContent = $('description').value.split('\n').slice(0, 3).join('\n');
}

function previewThumb() {
  $('thumbnail').src = thumb ? `/api/thumbnail/${$('channel').value}/${$('job').value}/${kind}/${thumb}?v=${Date.now()}` : '';
  $('thumbnail').style.aspectRatio = kind === 'short' ? '9/16' : '16/9';
}

function linkOptions() {
  const search = $('link-search').value.toLowerCase();
  const selected = $('link-target').value;
  $('link-target').replaceChildren(new Option('None — publish without a link', ''));
  records
    .filter(r => !(String(r.job) === String($('job').value) && r.kind === kind && r.channel === $('channel').value) &&
      `${r.title} ${r.channel} ${r.video_id}`.toLowerCase().includes(search))
    .forEach(r => $('link-target').add(new Option(`${r.title} · ${r.channel} · ${r.video_id}`, r.video_id)));
  $('link-target').value = selected;
}

function applyTestMode() {
  if (!TEST_MODE) return;
  document.querySelectorAll('.js-action').forEach(b => {
    b.disabled = true;
    if (!b.dataset.testTitled) {
      b.dataset.testTitled = '1';
      b.title = b.title ? b.title + ' — TEST copy: actions are disabled' : 'TEST copy: actions are disabled';
    }
  });
  const file = $('custom-file');
  if (file) file.disabled = true;
}

function publishedLink(record) {
  const href = record.url || (record.video_id ? 'https://youtu.be/' + encodeURIComponent(String(record.video_id)) : '');
  const label = (record.kind === 'short' ? 'Short' : 'Explainer') + (record.title ? ': ' + record.title : '');
  return href
    ? `<div class="row"><a href="${esc(href)}" target="_blank" rel="noopener">${esc(label)} ↗</a></div>`
    : `<div class="muted">${esc(label)} (no link recorded)</div>`;
}

function renderPublishedLinks() {
  const job = String($('job').value || '');
  const channel = String($('channel').value || '');
  const matches = records.filter(r =>
    String(r.job || '') === job &&
    String(r.channel || '') === channel &&
    String(r.kind || 'long') === kind
  );
  const links = matches.map(publishedLink).join('');
  $('published-links').innerHTML = '<h2>Published on YouTube</h2>' +
    (links || '<p class="muted">No published link was recorded for this job/channel/kind.</p>');
}

async function load() {
  $('publish-button').disabled = true;
  const seq = ++generation;
  const job = jobs.find(j => j.id === $('job').value);
  $('job-error').textContent = '';

  for (const k of ['short', 'long']) {
    $('tab-' + k).disabled = !job?.types[k];
    $('tab-' + k).classList.toggle('active', kind === k);
    $('tab-' + k).setAttribute('aria-selected', kind === k);
  }

  if (!job || !Object.keys(job.types).length) {
    $('job-error').textContent = 'No video found in this job folder.';
    $('publish-button').disabled = true;
    $('player').removeAttribute('src');
    $('player').load();
    $('thumbnail').removeAttribute('src');
    $('filename').textContent = 'No video found in this job folder.';
    $('file-info').textContent = '';
    applyTestMode();
    return;
  }

  if (!job.types[kind]) {
    kind = job.types.long ? 'long' : 'short';
    return load();
  }

  try {
    const j = await api(`/api/defaults/${job.id}/${kind}/${$('channel').value}`);
    if (seq !== generation) return;

    const d = j.data;
    $('title').value = d.title;
    $('description').value = d.description;
    tags = d.tags;
    thumb = d.thumbnail;
    $('category').value = d.category;
    $('language').value = d.language;
    document.querySelector('[name=visibility][value=Private]').checked = true;
    document.querySelector('[name=kids][value=no]').checked = true;
    $('chapters').replaceChildren();
    d.chapters.forEach(c => chapter(c.seconds, c.title));
    $('chapter-section').hidden = kind === 'short';
    $('link-label').textContent = kind === 'short' ? 'Link this Short to (optional):' : 'End screen link (optional):';
    $('link-target').value = '';
    $('player').src = `/api/video/${job.id}/${kind}`;
    $('player').classList.toggle('short', kind === 'short');
    $('preview-kind').textContent = kind === 'short' ? 'SHORT · 9:16' : 'EXPLAINER · 16:9';
    $('filename').textContent = j.media.filename;
    const m = j.media;
    $('file-info').textContent = `${(m.size / 1024 / 1024).toFixed(1)} MB · ${Math.floor(m.duration / 60)}:${String(Math.floor(m.duration % 60)).padStart(2, '0')} · ${m.width} × ${m.height} · ${m.fps} fps`;

    renderTags();
    previewThumb();
    counts();
    linkOptions();
    $('publish-button').disabled = busy;
    $('publish-both').hidden = !(job.types.long && job.types.short);
    $('publish-both').disabled = busy;
    applyTestMode();
  } catch (e) {
    message(e.message, true);
    applyTestMode();
  }
}

async function start(mode = 'new') {
  if (TEST_MODE) throw Error('TEST copy: actions are disabled');
  try {
    const data = form();
    if (!data.thumbnail || !data.title.trim() || !data.description.trim()) throw Error('Choose a thumbnail and fill title and description.');
    if (mode === 'restart') {
      if (!confirm('An existing upload may already exist. Restart can create a duplicate. Check Studio first. Continue?')) return;
      data.confirm_restart = true;
    }
    data.mode = mode;
    const result = await api('/publish', data);
    currentTask = result.task_id;
    localStorage.setItem('publisherTask', currentTask);
    busy = true;
    $('publish-button').disabled = true;
    $('recovery').hidden = true;
    $('progress-empty').hidden = true;
    $('progress-log').replaceChildren();
    message('Publishing started.');
    applyTestMode();
    poll();
  } catch (e) {
    message(e.message, true);
    $('recovery').hidden = false;
    applyTestMode();
  }
}

async function startPair() {
  if (TEST_MODE) throw Error('TEST copy: actions are disabled');
  try {
    const job = $('job').value, ch = $('channel').value, cur = form();
    if (!cur.thumbnail || !cur.title.trim() || !cur.description.trim()) throw Error('Choose a thumbnail and fill title and description.');
    const other = kind === 'long' ? 'short' : 'long';
    const o = (await api(`/api/defaults/${job}/${other}/${ch}`)).data;
    const body = {};
    body[kind] = cur;
    body[other] = o;
    if (!confirm('Publish the explainer first, then the Short with the explainer link (both Private unless chosen otherwise)?')) return;

    const r = await api('/publish/pair', body);
    currentTask = r.long_task;
    pairNext = r.short_task;
    localStorage.setItem('publisherTask', currentTask);
    busy = true;
    $('publish-button').disabled = true;
    $('publish-both').disabled = true;
    $('progress-empty').hidden = true;
    $('progress-log').replaceChildren();
    message('Publishing the explainer, then the Short.');
    applyTestMode();
    poll();
  } catch (e) {
    message(e.message, true);
    applyTestMode();
  }
}

async function poll() {
  try {
    const t = await api('/publish/status/' + currentTask);
    $('task-status').textContent = t.status.toUpperCase();
    if (shown > $('progress-log').childElementCount) shown = 0;
    t.events.slice(shown).forEach(e => {
      const div = document.createElement('div');
      div.className = 'event';
      const time = document.createElement('time');
      time.textContent = e.time;
      div.append(time, document.createTextNode(e.message));
      if (e.screenshot) {
        const img = document.createElement('img');
        img.loading = 'lazy';
        img.alt = e.message;
        img.src = `/publish/screenshot/${currentTask}/${e.screenshot}`;
        div.append(img);
      }
      $('progress-log').append(div);
    });
    shown = t.events.length;

    if (t.status === 'complete' && pairNext) {
      const nx = pairNext;
      pairNext = null;
      currentTask = nx;
      shown = 0;
      localStorage.setItem('publisherTask', nx);
      $('progress-log').replaceChildren();
      message('Explainer done: ' + t.result.url + ' — publishing the Short.');
      setTimeout(poll, 1000);
      return;
    }

    if (t.status === 'complete') {
      $('result').replaceChildren();
      const a = document.createElement('a');
      a.href = t.result.url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = 'Open on YouTube ↗';
      $('result').append(a);
      if (t.result.link_error) {
        const p = document.createElement('p');
        p.className = 'error';
        p.textContent = t.result.link_error;
        $('result').append(p);
        $('recovery').hidden = false;
      }
      records = await api('/api/published');
      linkOptions();
      busy = false;
      $('publish-button').disabled = false;
      applyTestMode();
      message('Published. Closing…');
      try {
        if (window.opener && !window.opener.closed) {
          window.opener.postMessage({type:'pub-action', action:'publish'}, '*');
        }
      } catch (e) {}
      setTimeout(() => window.close(), 900);
    } else if (['error', 'cancelled'].includes(t.status)) {
      message(t.error || 'Cancelled', true);
      $('recovery').hidden = false;
      busy = false;
      $('publish-button').disabled = false;
      applyTestMode();
    } else {
      setTimeout(poll, 1000);
    }
  } catch (e) {
    message(e.message, true);
    busy = false;
    $('publish-button').disabled = false;
    applyTestMode();
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  $('publish-form').onsubmit = e => { e.preventDefault(); shown = 0; start(); };
  $('job').onchange = load;
  $('channel').onchange = load;

  ['short', 'long'].forEach(k => {
    $('tab-' + k).onclick = () => { if (kind !== k) { kind = k; load(); } };
  });

  $('title').oninput = counts;
  $('description').oninput = counts;

  $('tag-entry').onkeydown = e => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const t = e.target.value.trim();
      if (t && !tags.some(x => x.toLowerCase() === t.toLowerCase())) tags.push(t);
      e.target.value = '';
      renderTags();
    }
  };

  $('add-chapter').onclick = () => chapter();
  $('link-search').oninput = linkOptions;

  $('publish-both').onclick = async () => {
    try { await startPair(); } catch (e) { message(e.message, true); }
  };

  $('save-draft').onclick = async () => {
    try {
      if (TEST_MODE) throw Error('TEST copy: actions are disabled');
      await api('/api/draft', form());
      message('Draft saved.');
    } catch (e) { message(e.message, true); }
  };

  $('reset').onclick = load;

  $('cancel').onclick = async () => {
    if (currentTask && busy) {
      if (TEST_MODE) { message('TEST copy: actions are disabled', true); return; }
      try {
        await api('/publish/cancel/' + currentTask, {});
      } catch (e) { message(e.message, true); }
    } else {
      message('Cancelled.');
      load();
    }
  };

  $('retry').onclick = () => { shown = 0; start('resume').catch(e => message(e.message, true)); };
  $('restart').onclick = () => { shown = 0; start('restart').catch(e => message(e.message, true)); };

  document.querySelectorAll('.regenerate').forEach(b => {
    b.onclick = async () => {
      b.disabled = true;
      message('Regenerating ' + b.dataset.field + '…');
      try {
        if (TEST_MODE) throw Error('TEST copy: actions are disabled');
        const snapshot = form();
        const j = await api('/api/regenerate', {...snapshot, field: b.dataset.field});
        if (snapshot.job !== $('job').value || snapshot.kind !== kind || snapshot.channel !== $('channel').value) return;
        if (b.dataset.field === 'tags') {
          tags = j.value;
          renderTags();
        } else if (b.dataset.field === 'chapters') {
          $('chapters').replaceChildren();
          j.value.forEach(c => chapter(c.seconds, c.title));
        } else {
          $(b.dataset.field).value = j.value;
        }
        counts();
        message('Updated ' + b.dataset.field + '.');
      } catch (e) {
        message(e.message, true);
      } finally {
        b.disabled = false;
        applyTestMode();
      }
    };
  });

  async function uploadThumb(file, seconds) {
    if (TEST_MODE) throw Error('TEST copy: actions are disabled');
    try {
      const data = new FormData();
      data.set('job', $('job').value);
      data.set('channel', $('channel').value);
      data.set('kind', kind);
      if (file) data.set('file', file);
      else data.set('seconds', seconds);

      const r = await fetch('/api/thumbnail', {method:'POST', body:data});
      const j = await r.json();
      if (!r.ok) throw Error(j.error);
      thumb = j.thumbnail;
      previewThumb();
      $('frame-dialog').close();
      message('Thumbnail updated.');
    } catch (e) {
      message(e.message, true);
    }
  }

  $('custom-open').onclick = () => $('custom-file').click();
  $('custom-file').onchange = e => {
    if (e.target.files[0]) uploadThumb(e.target.files[0]);
  };
  $('generated').onclick = () => { thumb = 'generated'; previewThumb(); };

  $('frame-open').onclick = () => {
    $('frame-player').src = $('player').src;
    $('frame-dialog').showModal();
  };
  $('frame-player').onloadedmetadata = () => {
    $('frame-time').max = Math.max(0, $('frame-player').duration - .1);
  };
  $('frame-time').oninput = e => {
    $('frame-player').currentTime = Number(e.target.value);
    $('frame-position').textContent = Math.floor(e.target.value / 60) + ':' + String(Math.floor(e.target.value % 60)).padStart(2, '0');
  };
  $('frame-save').onclick = () => uploadThumb(null, $('frame-player').currentTime);
  $('frame-close').onclick = () => {
    $('frame-player').pause();
    $('frame-dialog').close();
  };

  try {
    records = await api('/api/published');
    const params = new URLSearchParams(location.search);

    if (params.get('job')) $('job').value = params.get('job');
    if (params.get('channel')) $('channel').value = params.get('channel');
    if (params.get('kind') === 'short' || params.get('kind') === 'long') kind = params.get('kind');

    if (PUBLISHED_VIEW) {
      document.querySelectorAll('.edit-only, .video-preview-card, .channel-row, .tabs').forEach(el => el.hidden = true);
      $('published-links').hidden = false;
      renderPublishedLinks();
      applyTestMode();
      return;
    }

    jobs = await api('/api/jobs');
    await load();

    const previous = params.get('task') || localStorage.getItem('publisherTask');
    if (previous) {
      currentTask = previous;
      $('progress-empty').hidden = true;
      poll();
    }
    applyTestMode();
  } catch (e) {
    message(e.message, true);
    applyTestMode();
  }
});
```

---

### `app.py` patch

```diff
--- a/app.py
+++ b/app.py
@@ -1,6 +1,8 @@
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
+ACTUAL_PORT = int(os.environ.get('PUBLISHER_PORT', logic.config()['port']))
+
 app = Flask(__name__)
 app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
 tasks = {}
 task_lock = threading.Lock()
 browser_lock = threading.Lock()
 
+
+def channel_options():
+    channels = []
+    for path in (ROOT / 'channel_configs').glob('*.json'):
+        channels.append({'key': path.stem, 'name': backend.read_json(path)['youtube_channel_name']})
+    return channels
+
+
+@app.context_processor
+def inject_ui():
+    live_port = int(logic.config()['port'])
+    channels = channel_options()
+    return dict(
+        test_mode=ACTUAL_PORT != live_port,
+        actual_port=ACTUAL_PORT,
+        live_port=live_port,
+        default_channel=channels[0]['key'] if channels else ''
+    )
+
+
 @app.before_request
 def local_requests():
     # Prevent a remote site from submitting publish requests to localhost.
     if request.method != 'GET':
         origin = request.headers.get('Origin')
         if origin and origin != request.host_url.rstrip('/'):
             return jsonify(error='Cross-origin requests are not allowed.'), 403
     if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
         return jsonify(error='Local access only.'), 403
 
+
+@app.before_request
+def test_copy_writes():
+    live_port = int(logic.config()['port'])
+    if ACTUAL_PORT != live_port and request.method != 'GET':
+        return jsonify(error='TEST copy: actions are disabled'), 403
+
+
 @app.errorhandler(ValueError)
 @app.errorhandler(FileNotFoundError)
 def input_error(error):
     return jsonify(error=str(error)), 400
 
 @app.get('/')
 def home():
-    channels = []
-    for path in (ROOT / 'channel_configs').glob('*.json'):
-        channels.append({'key': path.stem, 'name': backend.read_json(path)['youtube_channel_name']})
-    return render_template('publish.html', channels=channels, categories=backend.CATEGORIES)
+    return render_template('publish.html', channels=channel_options(), categories=backend.CATEGORIES)
+
+
+@app.get('/player')
+def player():
+    channels = channel_options()
+    keys = {c['key'] for c in channels}
+    job = request.args.get('job', '').strip()
+    kind = request.args.get('kind', 'long').strip()
+    channel = request.args.get('channel', '').strip()
+    published = request.args.get('published') == '1'
+
+    if kind not in ('short', 'long'):
+        kind = 'long'
+    if not channel or channel not in keys:
+        channel = channels[0]['key'] if channels else ''
+
+    return render_template(
+        'player.html',
+        channels=channels,
+        categories=backend.CATEGORIES,
+        job=job,
+        kind=kind,
+        channel=channel,
+        published=published
+    )
@@ -XXX,7 +XXX,8 @@
 if __name__ == '__main__':
     cfg = logic.config()
     Path(cfg['log_dir']).mkdir(parents=True, exist_ok=True)
     logging.basicConfig(filename=Path(cfg['log_dir']) / 'publisher.log', level=logging.INFO,
                         format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
-    app.run(host='127.0.0.1', port=int(cfg['port']), debug=False, threaded=True, use_reloader=False)
+    ACTUAL_PORT = int(os.environ.get('PUBLISHER_PORT', cfg['port']))
+    app.run(host='127.0.0.1', port=ACTUAL_PORT, debug=False, threaded=True, use_reloader=False)
```

---

## How to test

1. **Live copy**
   - Run normally: `python app.py` (uses config `port`, normally `42030`).
   - Open `http://127.0.0.1:42030`.
   - You should see the light Newsroom-style two-panel list with Ready to publish and Published rotators.
   - There should be **no TEST pill**.
   - Clicking **Open** should open one shared popup window named `pubplayer`, reused for every pick.
   - Publish controls and activity log should work exactly as before.
   - Successful publish should post a message to the opener, refresh the lists, then close the popup.

2. **TEST copy**
   - Set an override port and run:
     - Windows PowerShell:
       ```powershell
       $env:PUBLISHER_PORT=42031
       python app.py
       ```
     - CMD:
       ```cmd
       set PUBLISHER_PORT=42031
       python app.py
       ```
   - Open `http://127.0.0.1:42031`.
   - A small slowly pulsing **TEST** pill should appear in the header.
   - Open the popup; every server-mutating action button should be disabled and show a tooltip like:
     `TEST copy: actions are disabled`.
   - Confirm the server guard:
     ```bash
     curl -X POST http://127.0.0.1:42031/publish -H "Content-Type: application/json" -d "{}"
     ```
     Expected:
     ```json
     {"error":"TEST copy: actions are disabled"}
     ```
   - Also confirm any POST `/api/...` action is refused the same way.

3. **Published popup**
   - From a Published panel item, click **Open**.
   - The `/player?...&published=1` popup should show only YouTube link(s) and no publish buttons.
   - The opener should still refresh on successful publish from an edit popup.

4. **Regression**
   - Verify all existing publish endpoints still respond the same on the live port:
     `/api/jobs`, `/api/published`, `/api/defaults/...`, `/api/video/...`,
     `/api/thumbnail/...`, `/publish`, `/publish/pair`, `/publish/status/...`,
     `/publish/cancel/...`, `/api/draft`, `/api/regenerate`, `/publish/screenshot/...`.

---

## What I was unsure about

- I patched `app.py` as a diff because the full file was not supplied. The patch assumes the existing route names and `channel_configs` glob logic are exactly as shown.
- I assumed `/api/published` records have fields `job`, `kind`, `channel`, `title`, `video_id`, and `url`. The published popup falls back to `https://youtu.be/<video_id>` when `url` is missing.
- I assumed `/api/jobs` returns job objects with at least `id` and `types`, as the existing `publish.js` already expected.
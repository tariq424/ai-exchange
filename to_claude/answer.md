One-line summary: add per-job/tab editor sessions (`ED.sid`) with polling, heartbeats, close-on-pagehide and reservation/render banners, then add the two pytest files for `gpu_lock` and `editor_session`/`_StudioQueue`.

---

## 1. `app/static/index.html`

### Edit 1 — insert helper block after the existing `edInit` line

**Old**
```js
async function edInit(){try{const d=await j(`/api/jobs/${sel}/edit/beats`);ED.beats=d.beats||[];ED.kind=d.kind;edBar(d)}catch(e){}}
```

**New**
```js
async function edInit(){try{const d=await j(`/api/jobs/${sel}/edit/beats`);ED.beats=d.beats||[];ED.kind=d.kind;edBar(d)}catch(e){}}

// ---- editor GPU reservation / session helpers (round 2b) ----
function edSid(){
  const key='vsedit.sid.'+sel;
  let sid=sessionStorage.getItem(key);
  if(!sid){sid=(crypto.randomUUID&&crypto.randomUUID())||('sid-'+Date.now()+'-'+Math.random().toString(16).slice(2));sessionStorage.setItem(key,sid);}
  return sid;
}
function edStartTimers(){edStopTimers();ED.pollTimer=setInterval(edPoll,4000);ED.heartbeatTimer=setInterval(edHeartbeatIfActive,60000);}
function edStopTimers(){clearInterval(ED.pollTimer);clearInterval(ED.heartbeatTimer);ED.pollTimer=ED.heartbeatTimer=null;}
async function edPost(url,body){
  body=body||{};body.sid=ED.sid;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let d={};try{d=await r.json()}catch(_){}
  if(!r.ok){
    const e=new Error(d.error||r.statusText||('HTTP '+r.status));
    e.status=r.status;e.body=d;throw e;
  }
  return d;
}
function edSetApplyDisabled(disabled){
  ED.applyDisabled=disabled;
  document.querySelectorAll('#edp button').forEach(function(b){
    const t=(b.textContent||'').replace(/\s+/g,' ').toLowerCase();
    if(t.indexOf('apply')>=0||t.indexOf('skip')>=0)b.disabled=disabled;
  });
}
function edShowResume(msg){
  msg.textContent='';
  const b=document.createElement('button');
  b.type='button';b.textContent='Resume';b.className='ed-resume';
  b.onclick=function(){if(ED.open!==undefined&&ED.open!==null)edOpen(ED.open);};
  msg.append('Edit paused after 15 min — ',b);
  ED.bannerText='paused';
}
function edRenderBanners(d){
  let text='';let paused=false;let waiting=false;
  const lock=d.lock||{};
  if(lock.held&&!lock.mine){
    text='A render is on the runway — your edit starts at its next safe point ('+(lock.desc||'gpu')+', '+(lock.age!=null?lock.age+'s':'')+')';
  }else if(d.active===false&&!d.holder_jid){
    paused=true;
  }else if(d.owner===false&&d.holder_jid){
    waiting=true;text='Waiting: editor in use ('+d.holder_jid+')';
  }else if(d.waiting&&d.holder_jid){
    waiting=true;text='Waiting: editor in use ('+d.holder_jid+')';
  }
  ED.waiting=waiting;edSetApplyDisabled(waiting);
  const msg=$('edmsg');
  if(msg&&paused){edShowResume(msg);return;}
  if(msg&&!text&&ED.bannerText){msg.textContent='';ED.bannerText='';}
  if(msg&&text){msg.textContent=text;ED.bannerText=text;}
}
function edBanner(ed){
  if(!ed)return;
  edRenderBanners({active:true,owner:ed.ok,holder_jid:ed.holder_jid,waiting:ed.waiting,lock:{}});
}
async function edPoll(){
  if(!ED.sid)return;
  try{
    const r=await fetch(`/api/jobs/${sel}/editor?sid=${encodeURIComponent(ED.sid)}`,{cache:'no-store'});
    const d=await r.json();
    if(r.ok)edRenderBanners(d);
  }catch(_){}
}
function edHeartbeatIfActive(){
  if(!ED.sid||typeof sel==='undefined')return;
  if(Date.now()-(ED.lastActivity||0)>60000)return;
  fetch(`/api/jobs/${sel}/editor/heartbeat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:ED.sid})}).catch(function(){});
}
function edCloseSession(){
  if(!ED.sid||ED._closeSent)return;
  ED._closeSent=true;edStopTimers();
  const url=`/api/jobs/${sel}/editor/close`;
  const body=JSON.stringify({sid:ED.sid});
  try{
    if(navigator.sendBeacon){navigator.sendBeacon(url,new Blob([body],{type:'application/json'}));}
    else{fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:body,keepalive:true});}
  }catch(_){}
}
function edMarkActivity(){ED.lastActivity=Date.now();}
document.addEventListener('pointerdown',edMarkActivity,{passive:true});
document.addEventListener('keydown',edMarkActivity,{passive:true});
document.addEventListener('click',function(e){
  const el=e.target.closest?e.target.closest('button,.ed-close,[data-close]'):null;
  if(!el)return;
  const t=(el.textContent||'').replace(/\s+/g,' ').toLowerCase();
  if(t.indexOf('done editing')>=0||el.classList.contains('ed-close')||el.id==='edClose'||el.id==='edDone')edCloseSession();
});
window.addEventListener('pagehide',edCloseSession);
```

---

### Edit 2 — replace `edOpen`

**Old**
```js
async function edOpen(bid){const v=$('ov');if(v)v.pause();$('edp').innerHTML='<p class="mut">Opening the beat…</p>';
 try{const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.error);
  ED.open=bid;ED.space=d.space;ED.rv=d.rv;const b=ED.rv.beats[bid];ED.sel=[...(b.current||[])];ED.fit='auto';ED.draft='';ED.chat=(await j(`/api/jobs/${sel}/edit/chat?beat=${bid}`)).chat;edDraw()}catch(e){$('edp').innerHTML=`<p style="color:var(--bad)">${esc(e.message)}</p>`}}
```

**New**
```js
async function edOpen(bid){const v=$('ov');if(v)v.pause();$('edp').innerHTML='<p class="mut">Opening the beat…</p>';
 ED.sid=edSid();ED._closeSent=false;edStartTimers();
 try{const d=await edPost(`/api/jobs/${sel}/edit/open/${bid}`,{});
  ED.open=bid;ED.space=d.space;ED.rv=d.rv;const b=ED.rv.beats[bid];ED.sel=[...(b.current||[])];ED.fit='auto';ED.draft='';ED.chat=(await j(`/api/jobs/${sel}/edit/chat?beat=${bid}`)).chat;edDraw();edBanner(d.editor)}catch(e){if(e.status===409&&$('edmsg'))$('edmsg').textContent=e.message;$('edp').innerHTML=`<p style="color:var(--bad)">${esc(e.message)}</p>`}}
```

---

### Edit 3 — replace `edApply`

**Old**
```js
async function edApply(){if(!ED.sel.length)return;$('edmsg').textContent='Applying…';edRelease();try{await rvPost(`/api/jobs/${sel}/edit/apply/${ED.open}`,{cands:ED.sel,fit:ED.fit});edWait()}catch(e){$('edmsg').textContent='';edReload();alert(e.message)}}
```

**New**
```js
async function edApply(){if(!ED.sel.length||ED.waiting)return;$('edmsg').textContent='Applying…';edRelease();try{await edPost(`/api/jobs/${sel}/edit/apply/${ED.open}`,{cands:ED.sel,fit:ED.fit});edWait()}catch(e){$('edmsg').textContent='';edReload();if(e.status===409){if($('edmsg'))$('edmsg').textContent=e.message;return}alert(e.message)}}
```

---

### Edit 4a — replace the re-open inside the `edWait` error path

**Old**
```js
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
```

**New**
```js
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){try{const x=await edPost(`/api/jobs/${sel}/edit/open/${bid}`,{});if(x){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}catch(e){if(e.status===409&&$('edmsg'))$('edmsg').textContent=e.message}}return}
```

---

### Edit 4b — replace the re-open inside the `edWait` success path

**Old**
```js
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.'}}}
```

**New**
```js
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){try{const x=await edPost(`/api/jobs/${sel}/edit/open/${bid}`,{});if(x){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.'}}catch(e){if(e.status===409&&$('edmsg'))$('edmsg').textContent=e.message}}}
```

---

### Edit 5 — replace `edAll`

**Old**
```js
async function edAll(a){try{await rvPost(`/api/jobs/${sel}/edit_all/${a}`);if(a=='undo'){edReload()}else{lastKey='';loadJobs()}}catch(e){alert(e.message)}}
```

**New**
```js
async function edAll(a){try{await edPost(`/api/jobs/${sel}/edit_all/${a}`,{});if(a=='undo'){edReload()}else{lastKey='';loadJobs()}}catch(e){if(e.status===409&&$('edmsg'))$('edmsg').textContent=e.message;else alert(e.message)}}
```

---

## 2. `tests/test_gpu_lock.py`

```python
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for p in (str(APP), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from studio import gpu_lock


def _reset_lock():
    gpu_lock._fh = None
    gpu_lock._owner = None
    gpu_lock._depth = 0
    gpu_lock._desc = ""
    gpu_lock._since = 0.0


@pytest.fixture
def lock_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GPU_LOCK_FILE", str(tmp_path / "gpu.lock"))
    monkeypatch.setenv("GPU_RESERVATION_FILE", str(tmp_path / "gpu.reservation.json"))
    _reset_lock()
    yield tmp_path
    if gpu_lock.held_by_me():
        gpu_lock.release()
    _reset_lock()


def test_acquire_release(lock_env):
    assert gpu_lock.acquire("edit", timeout=1)
    assert gpu_lock.held_by_me()

    st = gpu_lock.status()
    assert st["held"] is True
    assert st["desc"] == "edit"

    assert gpu_lock.release()
    assert gpu_lock.status()["held"] is False


def test_second_process_cannot_acquire_while_held(lock_env):
    ready = lock_env / "ready.txt"

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(APP), str(ROOT)]
        + [p for p in sys.path if p not in (str(APP), str(ROOT))]
    )
    env["GPU_LOCK_FILE"] = str(lock_env / "gpu.lock")

    holder_code = f"""
import time
from studio import gpu_lock

gpu_lock.acquire("holder", timeout=2)
open({str(ready)!r}, "w").write("ok")
time.sleep(1.2)
gpu_lock.release()
"""
    holder = subprocess.Popen([sys.executable, "-c", holder_code], env=env)

    try:
        for _ in range(80):
            if ready.exists():
                break
            time.sleep(0.05)
        else:
            holder.kill()
            raise AssertionError("holder did not become ready")

        probe = subprocess.run(
            [sys.executable, "-c", "from studio import gpu_lock; print(gpu_lock.acquire('probe', timeout=0.3))"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert probe.returncode == 0
        assert probe.stdout.strip() == "False"
    finally:
        holder.wait(timeout=3)

    assert gpu_lock.acquire("after-holder-exit", timeout=1)
    gpu_lock.release()


def test_nested_acquire_release_keeps_lock_until_outer_release(lock_env):
    assert gpu_lock.acquire("outer")
    assert gpu_lock.acquire("inner")

    assert gpu_lock.release()
    assert gpu_lock.status()["held"] is True

    assert gpu_lock.release()
    assert gpu_lock.status()["held"] is False


def test_status_does_not_trust_stale_metadata(lock_env):
    lock_file = lock_env / "gpu.lock"
    lock_file.write_bytes(b"\0")

    stale = {
        "pid": os.getpid(),
        "desc": "stale-metadata",
        "t": time.time(),
    }
    gpu_lock.meta_path().write_text(json.dumps(stale), encoding="utf-8")

    st = gpu_lock.status()
    assert st["held"] is False
```

---

## 3. `tests/test_editor_priority.py`

```python
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for p in (str(APP), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from studio import editor_session
from studio.pipeline import _StudioQueue


@pytest.fixture
def res_env(tmp_path, monkeypatch):
    monkeypatch.setattr(editor_session, "_settings", lambda: {})
    monkeypatch.setattr(editor_session, "IDLE_LIMIT", 0.05)
    monkeypatch.setenv("GPU_RESERVATION_FILE", str(tmp_path / "reservation.json"))
    monkeypatch.setenv("GPU_LOCK_FILE", str(tmp_path / "gpu.lock"))

    p = editor_session.reservation_path()
    if p.exists():
        p.unlink()

    yield tmp_path

    p.unlink(missing_ok=True)


class FakeStudio:
    def __init__(self, prios):
        self.prios = prios

    def _prio(self, jid):
        return self.prios[jid]


def test_studio_queue_priority_order_and_fifo():
    prios = {
        "editor-first": 0,
        "newsroom-first": 1,
        "hand-first": 2,
        "newsroom-second": 1,
        "editor-second": 0,
        "hand-second": 2,
    }
    q = _StudioQueue(FakeStudio(prios))

    for jid in ["hand-first", "newsroom-first", "editor-first", "editor-second", "hand-second", "newsroom-second"]:
        q.put(jid)

    expected = [
        "editor-first",
        "editor-second",
        "newsroom-first",
        "newsroom-second",
        "hand-first",
        "hand-second",
    ]
    assert [q.get() for _ in range(6)] == expected


def test_editor_session_acquire_and_second_jid_waits(res_env):
    rv1 = editor_session.acquire("job1", pid=os.getpid(), port=42022, sid="sid-1")
    assert rv1["ok"] is True

    rv2 = editor_session.acquire("job2", pid=os.getpid(), port=42022, sid="sid-2")
    assert rv2["ok"] is False
    assert rv2["waiting"] is True
    assert rv2["holder_jid"] == "job1"


def test_idle_release_only_when_no_active_applies(res_env):
    assert editor_session.acquire("job1", pid=os.getpid(), port=42022).get("ok")
    time.sleep(0.08)
    assert editor_session.active() is None

    assert editor_session.acquire("job2", pid=os.getpid(), port=42022).get("ok")
    editor_session.apply_started("job2")
    time.sleep(0.08)
    assert editor_session.active() is not None

    editor_session.apply_finished("job2")
    time.sleep(0.08)
    assert editor_session.active() is None


def test_pid_alive_false_for_dead_pid(res_env):
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait(timeout=5)
    assert editor_session._pid_alive(p.pid) is False
```

---

## 3. How Claude should test it

Run from the repo root:

```bash
python -m pytest tests/test_gpu_lock.py tests/test_editor_priority.py -q
```

Then start the TEST Video Studio instance on a non-42021 port and manually verify in a real Short:

1. Open a beat. In DevTools network, confirm:
   - `POST /api/jobs/<jid>/edit/open/<bid>` body contains `sid`.
   - `GET /api/jobs/<jid>/editor?sid=...` fires every ~4 s.
   - `POST /api/jobs/<jid>/editor/heartbeat` fires only after recent mouse/key activity.
2. Close the editor window/tab and confirm `POST /api/jobs/<jid>/editor/close` is sent.
3. While the GPU is busy (or another editor has the reservation), confirm the correct banner appears and Apply/Skip buttons are disabled.
4. Force a 409 from an editor action and confirm the error appears in `#edmsg`, not an `alert()`.

---

## 4. Anything unsure about / missing

- The provided excerpt shows the `edWait` first two lines twice. I assumed that is a paste artifact and replaced the re-open paths inside the real single `edWait`.
- `/make/edit` was listed in the requirement but its JS call site was not in the excerpts. If it exists in `index.html`, Claude should change its body to include `sid:ED.sid`, ideally by routing it through the new `edPost()` helper.
- The Apply/Skip disable selector guesses button IDs/text based on the existing functions (`apply`/`skip` text). If the real buttons have different text or dedicated IDs, Claude should narrow `edSetApplyDisabled()` to those IDs.

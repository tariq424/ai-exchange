# Round 2b — the parts your round-2 answer did not reach (it was cut off in interview_edit.py)

Thank you: your round 2 is applied on branch `feature/gpu-interlock` (691935f), with Claude's fixes:
Windows `LK_LOCK` gives up after ~10 s so acquire() now polls `LK_NBLCK`; the lock is re-entrant with a count;
force-release never deletes the lock file; `_pid_alive` never calls `os.kill` on Windows (Python maps it to
TerminateProcess — it would have killed the live server); `GPU_STAGES` is every render stage plus frame QC; the port
comes from env `PORT`; `editor_session.apply_started/apply_finished` count in-flight applies; interview_edit is gated.
The current server editor routes and modules are below — build on them exactly; do not change their APIs.

## Please write now
1. `app/static/index.html` — ONLY new JS functions plus minimal hook edits (exact search/replace) in edOpen,
   edApply, edWait (excerpts below):
   - a per-tab editor session id `ED.sid` (crypto.randomUUID, kept in sessionStorage per job so reopening the same
     job in the `vsedit` window resumes the same sid); send `sid` in every editor POST body
     (edit/open, edit/<action>, edit_all/*, /make/edit) and `?sid=` on GET /api/jobs/<jid>/editor.
   - poll GET /api/jobs/<jid>/editor every 4 s while the editor is open; heartbeat POST every 60 s while the user
     is active (mouse/key in the last 60 s); POST editor/close on Close / "Done editing" and on `pagehide`.
   - banners in the editor panel: when `lock.held` and the holder is not this editor: "A render is on the runway —
     your edit starts at its next safe point (<lock.desc>, <age>)"; when another editor holds the reservation:
     "Waiting: editor in use (<holder_jid>)" and the apply buttons disabled; when the reservation was idle-released:
     "Edit paused after 15 min — Resume" with a Resume button that re-calls edit/open for the open beat.
   - when a 409 comes back from an editor action, show its `error` text in `#edmsg` instead of alert().
2. Unit tests (pytest, run on Linux): `tests/test_gpu_lock.py` — acquire/release; a second PROCESS cannot acquire
   while held (subprocess), gets it after the holder exits; nested acquire/release keeps it held until the outer
   release; status() never trusts stale metadata. `tests/test_editor_priority.py` — the `_StudioQueue` order
   (editor_owned 0, newsroom 1, hand 2, FIFO within a priority); `editor_session` acquire/second-jid waiting/idle
   release only when active_applies == 0 (monkeypatch IDLE_LIMIT or time); `_pid_alive` False for a dead pid.
   Use `GPU_LOCK_FILE` / `GPU_RESERVATION_FILE` env vars pointing into pytest's tmp_path.

## Answer format
Exact search/replace edits for index.html (old text copied exactly from the excerpts, unique), new JS functions in
full, then the two test files in full. Keep it compact.

## Current code
### app/studio/gpu_lock.py
```python
"""Machine-wide GPU barrier for Video Studio (design: DeepSeek round 1-2 via ai-exchange, fixes by Claude).

One GPU user at a time across every process (live 42021, test copies, QC scripts). Byte-range lock on a file
(msvcrt on Windows, fcntl elsewhere): the OS frees it when the holder process exits, so a crash never leaves a stale
lock. Metadata (holder pid/desc/since) is display-only; the OS lock is the truth.
Claude fixes over the DeepSeek draft: Windows LK_LOCK gives up after ~10 s, so acquire() polls LK_NBLCK; re-entrant
per thread with a count (nested holders no longer deadlock or release early); force-release never deletes the file.
CLI (for the WanGP watchdog):  python -m studio.gpu_lock status | force-release
"""
import argparse, contextlib, json, os, threading, time
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_rl = threading.RLock()          # in-process: one owning thread at a time, re-entrant
_fh = None; _owner = None; _depth = 0; _desc = ""; _since = 0.0


def lock_path():
    p = os.environ.get("GPU_LOCK_FILE")
    if not p:
        try:
            from . import config
            p = config.load().get("gpu_lock_file")
        except Exception:
            p = None
    return Path(p or r"F:\code\gpu.lock")


def meta_path():
    p = lock_path(); return p.with_name(p.name + ".json")


def _write_meta(d):
    p = meta_path(); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
    for _ in range(40):
        try: os.replace(tmp, p); return
        except PermissionError: time.sleep(0.05)


def _read_meta():
    try: return json.loads(meta_path().read_text(encoding="utf-8")) or {}
    except Exception: return {}


def _open():
    p = lock_path(); p.parent.mkdir(parents=True, exist_ok=True)
    fh = open(p, "a+b")
    fh.seek(0, os.SEEK_END)
    if fh.tell() == 0: fh.write(b"\0"); fh.flush()
    return fh


def _try_lock(fh):
    fh.seek(0)
    try:
        if os.name == "nt": msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else: fcntl.lockf(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0)
        return True
    except OSError:
        return False


def _unlock(fh):
    fh.seek(0)
    try:
        if os.name == "nt": msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else: fcntl.lockf(fh.fileno(), fcntl.LOCK_UN, 1, 0)
    except OSError:
        pass


def acquire(desc="gpu", timeout=None, poll=0.5, on_wait=None):
    """Take the GPU. Blocks (polling) until free, or returns False after `timeout` seconds.
    on_wait(holder_meta) is called once when we first have to wait (for 'Waiting: GPU busy' messages)."""
    global _fh, _owner, _depth, _desc, _since
    t0 = time.time()
    if not _rl.acquire(timeout=-1 if timeout is None else timeout): return False
    try:
        if _owner == threading.get_ident():
            _depth += 1; return True
        fh = _open(); told = False
        while not _try_lock(fh):
            if not told and on_wait:
                try: on_wait(_read_meta())
                except Exception: pass
                told = True
            if timeout is not None and time.time() - t0 >= timeout:
                fh.close(); _rl.release(); return False
            time.sleep(poll)
        _fh, _owner, _depth, _desc, _since = fh, threading.get_ident(), 1, desc, time.time()
        _write_meta({"pid": os.getpid(), "desc": desc, "t": _since})
        return True
    except Exception:
        _rl.release(); raise


def release():
    """Release one level; the OS lock is dropped when the outermost holder releases. Only the owner thread may."""
    global _fh, _owner, _depth, _desc, _since
    if _owner != threading.get_ident(): return False
    _depth -= 1
    if _depth <= 0:
        fh = _fh
        _fh, _owner, _depth, _desc, _since = None, None, 0, "", 0.0
        try:
            _write_meta({})
            _unlock(fh)
        finally:
            fh.close()
    _rl.release()
    return True


def held_by_me():
    return _owner == threading.get_ident()


def status():
    """{held, pid, desc, age, file}. Never trusts the metadata alone: probes the OS lock."""
    p = lock_path()
    if _fh is not None:
        return {"held": True, "pid": os.getpid(), "desc": _desc, "age": round(time.time() - _since, 1), "file": str(p), "mine": True}
    if not p.exists(): return {"held": False, "file": str(p)}
    fh = open(p, "a+b")
    try:
        if _try_lock(fh):
            _unlock(fh); return {"held": False, "file": str(p)}
    finally:
        fh.close()
    m = _read_meta()
    return {"held": True, "pid": m.get("pid", "?"), "desc": m.get("desc", "unknown"),
            "age": round(time.time() - float(m.get("t", time.time())), 1), "file": str(p)}


def force_release(reason="manual force-release"):
    """Manual escape hatch for a hung-but-alive holder. An OS byte lock belongs to its process and cannot be taken
    from outside, so this only marks the metadata; the real lock frees when that process is stopped. Never deletes
    the lock file (deleting it would let two holders lock two different files)."""
    st = status()
    if st.get("held") and not st.get("mine"):
        _write_meta(dict(_read_meta(), forced_release_requested=time.time(), reason=reason))
        st["note"] = f"held by pid {st.get('pid')}; stop that process to free the GPU"
    return st


@contextlib.contextmanager
def holder(desc="gpu", on_wait=None):
    acquire(desc=desc, on_wait=on_wait)
    try: yield
    finally: release()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Video Studio GPU barrier")
    ap.add_argument("cmd", choices=["status", "force-release"])
    a = ap.parse_args(argv)
    print(json.dumps(status() if a.cmd == "status" else force_release(), indent=1))


if __name__ == "__main__":
    main()
```
### app/studio/editor_session.py
```python
"""One machine-wide editor session (DeepSeek draft via ai-exchange; Claude fixes: Windows-safe pid check, apply counter).

The editor holds a priority reservation, not the raw GPU lock. The raw
GPU lock is taken only for each apply / preview / undo / editor re-render.
"""
import json, os, time
from pathlib import Path

IDLE_LIMIT = 15 * 60

def _settings():
    try:
        from . import config
        return config.load()
    except Exception:
        return {}

def reservation_path(namespace=None):
    p = _settings().get("editor_reservation_file") or os.environ.get("GPU_RESERVATION_FILE") or r"F:\code\gpu.reservation.json"
    p = Path(p)
    if namespace:
        return p.with_name(f"{p.stem}.{namespace}{p.suffix}")
    return p

def _write(data, namespace=None):
    p = reservation_path(namespace)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, p)
    except PermissionError:
        time.sleep(0.05)
        os.replace(tmp, p)

def _pid_alive(pid):
    """Is that process alive? NEVER os.kill(pid, 0) on Windows: Python maps it to TerminateProcess (it would kill the
    live Video Studio). Windows: OpenProcess + GetExitCodeProcess (STILL_ACTIVE = 259)."""
    try: pid = int(pid)
    except (TypeError, ValueError): return False
    if pid <= 0: return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h: return False
        try:
            code = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return True
    except OSError: return False


def _read(namespace=None):
    p = reservation_path(namespace)
    if not p.exists():
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if not _pid_alive(data.get("pid")):
        _write({}, namespace)
        return None

    if int(data.get("active_applies", 0)) == 0 and time.time() - float(data.get("last_activity", time.time())) > IDLE_LIMIT:
        _write({}, namespace)
        return None

    return data

def active(namespace=None):
    return _read(namespace)

def state(namespace=None):
    cur = _read(namespace)
    if not cur:
        return None
    cur = dict(cur)
    cur["age"] = max(0.0, time.time() - float(cur.get("last_activity", time.time())))
    return cur

def acquire(jid, pid, port, sid="", active_applies=0, namespace=None):
    now = time.time()
    cur = _read(namespace)

    if cur:
        if cur.get("jid") != jid or (cur.get("sid") and sid and cur.get("sid") != sid):
            return {
                "ok": False,
                "waiting": True,
                "holder_jid": cur.get("jid"),
                "holder_port": cur.get("port"),
                "age": max(0.0, now - float(cur.get("last_activity", now))),
            }
        cur.update({
            "pid": pid,
            "port": port,
            "last_activity": now,
            "active_applies": int(active_applies or cur.get("active_applies", 0)),
        })
        if sid:
            cur["sid"] = sid
        _write(cur, namespace)
        return {"ok": True, "owner": True, "age": 0.0}

    data = {
        "jid": jid,
        "pid": pid,
        "port": port,
        "last_activity": now,
        "active_applies": int(active_applies or 0),
    }
    if sid:
        data["sid"] = sid
    _write(data, namespace)
    return {"ok": True, "owner": True, "age": 0.0}

def is_owner(jid, pid, port, sid="", namespace=None):
    cur = _read(namespace)
    if not cur:
        return False
    return (
        cur.get("jid") == jid
        and str(cur.get("pid")) == str(pid)
        and str(cur.get("port")) == str(port)
        and (not cur.get("sid") or not sid or cur.get("sid") == sid)
    )

def heartbeat(jid, pid, port, sid="", active_applies=None, namespace=None):
    cur = _read(namespace)
    if not cur or cur.get("jid") != jid:
        return {"ok": False, "error": "not the active editor session"}
    if cur.get("sid") and sid and cur.get("sid") != sid:
        return {"ok": False, "error": "not the active editor session"}

    cur.update({"pid": pid, "port": port, "last_activity": time.time()})
    if active_applies is not None:
        cur["active_applies"] = int(active_applies)
    _write(cur, namespace)
    return {"ok": True}

def release(jid=None, pid=None, port=None, sid="", force=False, namespace=None):
    cur = _read(namespace)
    if not cur:
        return True

    jid_ok = jid is None or cur.get("jid") == jid
    pid_ok = pid is None or str(cur.get("pid")) == str(pid)
    port_ok = port is None or str(cur.get("port")) == str(port)
    sid_ok = not sid or not cur.get("sid") or cur.get("sid") == sid

    if force or (jid_ok and pid_ok and port_ok and sid_ok):
        _write({}, namespace)
        return True
    return False

def _reset(namespace=None):
    _write({}, namespace)


def apply_started(jid, namespace=None):
    """Count an in-flight apply/undo/re-render: the idle release never fires while active_applies > 0."""
    cur = _read(namespace)
    if cur and cur.get("jid") == jid:
        cur["active_applies"] = int(cur.get("active_applies", 0)) + 1; cur["last_activity"] = time.time(); _write(cur, namespace)


def apply_finished(jid, namespace=None):
    p = reservation_path(namespace)
    try: cur = json.loads(p.read_text(encoding="utf-8"))
    except Exception: return
    if isinstance(cur, dict) and cur.get("jid") == jid:
        cur["active_applies"] = max(0, int(cur.get("active_applies", 0)) - 1); cur["last_activity"] = time.time(); _write(cur, namespace)

```
### app/studio/pipeline.py: _StudioQueue and Studio._prio
```python
class _StudioQueue:
    """Priority queue: editor-owned work, then Newsroom jobs, then hand jobs.

    Existing `Studio.q.put(jid)` call sites stay unchanged.
    """
    def __init__(self, studio):
        self._q = queue.PriorityQueue()
        self._studio = studio
        self._seq = 0
        self._lk = threading.Lock()

    def put(self, jid):
        with self._lk:
            self._seq += 1
            self._q.put((self._studio._prio(jid), self._seq, jid))

    def get(self):
        return self._q.get()[2]


LENGTH_TOL = 0.10   # a finished video more than 10% off the requested length is flagged (never rejected)
    def _prio(self, jid):
        try:
            s = self.job(jid).state
        except Exception:
            return 2
        if s.get("editor_owned"):
            return 0
        if s.get("newsroom") or s.get("priority") == "newsroom":
            return 1
        return 2

```
### app/server.py editor routes (as applied)
```python
def _editor_ns():
    return None if VS_PORT == 42021 else str(VS_PORT)

def _editor_owner(jid, sid):
    from studio import editor_session
    st = editor_session.state(namespace=_editor_ns())
    if not st:
        return False, "No editor session is open; open a beat first."
    if st.get("jid") != jid or not editor_session.is_owner(jid, os.getpid(), VS_PORT, sid, namespace=_editor_ns()):
        return False, f"Waiting: editor in use ({st.get('jid')})"
    return True, st

@app.post("/api/jobs/<jid>/edit/target")
@app.post("/api/jobs/<jid>/edit/open/<bid>")
def edit_open(jid, bid):
    from studio import edit, editor_session
    j = studio.job(jid)
    b = request.get_json(silent=True) or {}
    sid = b.get("sid", "")
    ed = editor_session.acquire(jid, pid=os.getpid(), port=VS_PORT, sid=sid, namespace=_editor_ns())
    try: rv = edit.open_beat(j.dir, bid, config.load(), j.log)
    except Exception as e: return jsonify(error=str(e)[:300]), 400
    return jsonify(space="short" if edit.kind(j.dir) == "short" else "long", rv=rv,
                   editor={"ok": ed.get("ok", False), "waiting": ed.get("waiting", False),
                           "holder_jid": ed.get("holder_jid"), "holder_port": ed.get("holder_port"),
                           "age": ed.get("age", 0)})

@app.post("/api/jobs/<jid>/edit/chat")
@app.get("/api/jobs/<jid>/editor")
def editor_status(jid):
    from studio import editor_session, gpu_lock
    sid = request.args.get("sid", "")
    st = editor_session.state(namespace=_editor_ns())
    return jsonify(
        active=bool(st),
        owner=bool(st and editor_session.is_owner(jid, os.getpid(), VS_PORT, sid, namespace=_editor_ns())),
        holder_jid=st.get("jid") if st else None,
        holder_port=st.get("port") if st else None,
        age=st.get("age", 0) if st else 0,
        active_applies=st.get("active_applies", 0) if st else 0,
        lock=gpu_lock.status(),
    )

@app.post("/api/jobs/<jid>/editor/heartbeat")
def editor_heartbeat(jid):
    from studio import editor_session
    b = request.get_json(silent=True) or {}
    rv = editor_session.heartbeat(
        jid, os.getpid(), VS_PORT, b.get("sid", ""),
        b.get("active_applies"), namespace=_editor_ns(),
    )
    return jsonify(ok=rv.get("ok", False), error=rv.get("error"))

@app.post("/api/jobs/<jid>/editor/close")
def editor_close(jid):
    from studio import editor_session
    b = request.get_json(silent=True) or {}
    editor_session.release(
        jid, pid=os.getpid(), port=VS_PORT,
        sid=b.get("sid", ""), namespace=_editor_ns(),
    )
    return jsonify(ok=True)

@app.post("/make/edit")
def make_edit():
```
### app/static/index.html editor JS excerpts
```js
async function edInit(){try{const d=await j(`/api/jobs/${sel}/edit/beats`);ED.beats=d.beats||[];ED.kind=d.kind;edBar(d)}catch(e){}}
function edJump(id){const v=$('ov'),b=ED.beats.find(x=>x.id==id);if(!v||!b)return;v.pause();v.currentTime=b.start+Math.min(0.5,b.dur/2);ED.cur=b.id;edBar()}
function edAt(t){return ED.beats.find(b=>t>=b.start&&t<b.start+b.dur)}
function edTick(){scTick();const v=$('ov');if(!v||!ED.beats.length)return;const b=edAt(v.currentTime);const k=b?b.id:'';if(k!==ED.cur){ED.cur=k;edBar()}}
async function edOpen(bid){const v=$('ov');if(v)v.pause();$('edp').innerHTML='<p class="mut">Opening the beat…</p>';
 try{const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.error);
  ED.open=bid;ED.space=d.space;ED.rv=d.rv;const b=ED.rv.beats[bid];ED.sel=[...(b.current||[])];ED.fit='auto';ED.draft='';ED.chat=(await j(`/api/jobs/${sel}/edit/chat?beat=${bid}`)).chat;edDraw()}catch(e){$('edp').innerHTML=`<p style="color:var(--bad)">${esc(e.message)}</p>`}}
// ---- beat-edit panel: six labelled panes (Candidates, Fit options, Actions | Preview, Chat, Log), each with its own tint
async function edApply(){if(!ED.sel.length)return;$('edmsg').textContent='Applying…';edRelease();try{await rvPost(`/api/jobs/${sel}/edit/apply/${ED.open}`,{cands:ED.sel,fit:ED.fit});edWait()}catch(e){$('edmsg').textContent='';edReload();alert(e.message)}}
async function edSkip(){const b=ED.rv.beats[ED.open];const cid=b.cands.find(c=>ED.rv.cands[c].rung=='headline');if(!cid){alert('No headline card for this beat');return}ED.sel=[cid];ED.fit='auto';edApply()}
async function edWait(){const d=await j(`/api/jobs/${sel}/edit/beats`);edBar(d);if(d.busy){setTimeout(edWait,3000);if($('edmsg'))$('edmsg').textContent=d.busy;return}
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
async function edWait(){const d=await j(`/api/jobs/${sel}/edit/beats`);edBar(d);if(d.busy){setTimeout(edWait,3000);if($('edmsg'))$('edmsg').textContent=d.busy;return}
 if(d.error){edReload();if($('edmsg'))$('edmsg').textContent='✗ Not applied: '+d.error;const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;edDraw();$('edmsg').textContent='✗ Not applied: '+d.error}}return}
 if(POPUP&&window.opener){try{window.opener.postMessage({vsEdited:sel},'*')}catch(e){}}
 if($('edmsg'))$('edmsg').textContent='Applied. The video below is updated.';edReload();const bid=ED.open;if(bid){const r=await fetch(`/api/jobs/${sel}/edit/open/${bid}`,{method:'POST'});const x=await r.json();if(r.ok){ED.rv=x.rv;ED.sel=[...(ED.rv.beats[bid].current||[])];edDraw();$('edmsg').textContent='Applied. The video is updated.'}}}
async function edAll(a){try{await rvPost(`/api/jobs/${sel}/edit_all/${a}`);if(a=='undo'){edReload()}else{lastKey='';loadJobs()}}catch(e){alert(e.message)}}
function edReload(){const v=$('ov');if(v){const base=(v.getAttribute('src')||ED.ovSrc||'').split('?')[0];const t=v.getAttribute('src')?v.currentTime:(ED.ovT||0);if(base){v.src=base+'?t='+Date.now();v.currentTime=t}ED.ovSrc=null}edInit()}
const edQ=()=>ED.space=='long'?'?space=long':'';const edBase=()=>`/files/${sel}/${ED.space=='long'?'longedit/':''}short/`;
async function edOpen(bid){const v=$('ov');if(v)v.pause();$('edp').innerHTML='<p class="mut">Opening the beat…</p>';
async function edRv(a){const body={action:a};if(a=='refine'){body.text=$('edrf').value.trim();if(!body.text)return}
 try{ED.rv=await rvPost(`/api/jobs/${sel}/review/${ED.open}${edQ()}`,body);edDraw();setTimeout(edRefresh,1500)}catch(e){alert(e.message)}}
async function edSupply(){const t=$('edsp').value.trim();if(!t)return;$('edmsg').textContent='Adding your file…';
 try{ED.rv=await rvPost(`/api/jobs/${sel}/review/${ED.open}${edQ()}`,{action:'supply',src:t,tag:$('edst').value});ED.sel=[...ED.rv.beats[ED.open].chosen];$('edmsg').textContent='';edDraw()}catch(e){$('edmsg').textContent='';alert(e.message)}}
```

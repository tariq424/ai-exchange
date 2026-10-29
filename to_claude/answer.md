1-line summary: implement the cross-process GPU barrier (`gpu_lock.py`), the one-active-editor priority reservation (`editor_session.py`), priority/editor-wait queueing in `pipeline.py`, editor-ownership GPU gating in `server.py`/`edit.py`/`interview_edit.py`, the UI heartbeat/waiting hooks, and unit tests.

---

## New module: `app/studio/gpu_lock.py`

```python
"""Cross-process GPU barrier for Video Studio.

One renderer at a time on Tariq's single GPU. The lock is byte-range
locked (msvcrt on Windows, fcntl elsewhere) so the OS releases it when
the holder exits, even if it dies uncleanly.
"""
import argparse, contextlib, json, os, sys, threading, time
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_local = threading.Lock()
_owner_tid = None
_fh = None
_desc = ""
_held_since = 0.0

def _settings():
    try:
        from . import config
        return config.load()
    except Exception:
        return {}

def lock_path():
    p = _settings().get("gpu_lock_file") or os.environ.get("GPU_LOCK_FILE") or r"F:\code\gpu.lock"
    return Path(p)

def meta_path():
    p = lock_path()
    return p.with_name(p.name + ".json")

def _write_meta(data):
    p = meta_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for _ in range(20):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.05)
    try:
        os.replace(tmp, p)
    except Exception:
        pass

def _read_meta():
    p = meta_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _lock_region(fh, block=True):
    fh.seek(0, os.SEEK_SET)
    if os.name == "nt":
        mode = msvcrt.LK_LOCK if block else msvcrt.LK_NBLCK
        msvcrt.locking(fh.fileno(), mode, 1)
    else:
        fh.seek(0, os.SEEK_SET)
        fcntl.lockf(fh.fileno(), fcntl.LOCK_EX if block else fcntl.LOCK_EX | fcntl.LOCK_NB)

def _unlock_region(fh):
    fh.seek(0, os.SEEK_SET)
    if os.name == "nt":
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        fcntl.lockf(fh.fileno(), fcntl.LOCK_UN)

def acquire(desc="gpu", timeout=None):
    """Acquire the GPU barrier.

    `timeout` only waits for the in-process holder; the cross-process
    byte lock blocks until the other process releases it.
    """
    global _owner_tid, _fh, _desc, _held_since
    p = lock_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    got = _local.acquire(timeout=timeout) if timeout is not None else _local.acquire()
    if not got:
        return False

    try:
        if _owner_tid == threading.get_ident():
            return True

        fh = open(p, "a+b")
        try:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                fh.write(b"\0")
                fh.flush()
            fh.seek(0, os.SEEK_SET)
            _lock_region(fh, block=True)
        except Exception:
            fh.close()
            raise

        _owner_tid = threading.get_ident()
        _fh = fh
        _desc = desc
        _held_since = time.time()
        _write_meta({
            "pid": os.getpid(),
            "thread": threading.get_ident(),
            "desc": desc,
            "t": _held_since,
        })
        return True
    except Exception:
        _local.release()
        raise

def release():
    """Release the GPU barrier. Only the acquiring thread may release it."""
    global _owner_tid, _fh, _desc, _held_since
    tid = threading.get_ident()
    if _owner_tid != tid or _fh is None:
        return False

    fh = _fh
    _fh = None
    _owner_tid = None
    _desc = ""
    _held_since = 0.0
    try:
        _unlock_region(fh)
    finally:
        fh.close()
        _write_meta({})
        _local.release()
    return True

def _probe_locked():
    p = lock_path()
    if not p.exists():
        return False

    fh = open(p, "a+b")
    try:
        if os.name != "nt":
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                fh.write(b"\0")
                fh.flush()
        _lock_region(fh, block=False)
        return False
    except OSError:
        return True
    finally:
        try:
            _unlock_region(fh)
        except Exception:
            pass
        fh.close()

def status():
    """Return {held, pid, desc, age, file, ...}; usable by the UI and watchdog CLI."""
    global _owner_tid
    m = _read_meta()

    if _owner_tid is not None and _fh is not None:
        m = m or {}
        m.update({
            "held": True,
            "pid": os.getpid(),
            "desc": _desc,
            "age": max(0.0, time.time() - _held_since),
            "file": str(lock_path()),
        })
        return m

    p = lock_path()
    if not p.exists():
        if m:
            _write_meta({})
        return {"held": False, "file": str(p)}

    held = _probe_locked()
    if not held:
        if m:
            _write_meta({})
        return {"held": False, "file": str(p)}

    m = m or {"pid": "?", "desc": "unknown", "t": time.time()}
    m["held"] = True
    m["age"] = max(0.0, time.time() - float(m.get("t", time.time())))
    m["file"] = str(p)
    return m

def force_release(reason="manual force-release"):
    """Manual CLI escape hatch for a hung-but-alive holder.

    `msvcrt`/`fcntl` byte-range locks belong to the process that created
    them, so another process cannot force-unlock the region. This marks
    the metadata as forcibly released and tries to unlink the lock file;
    the real OS lock is released when the hung process exits.
    """
    global _owner_tid, _fh, _desc, _held_since
    if _owner_tid == threading.get_ident() and _fh is not None:
        release()

    _write_meta({"forced_release_at": time.time(), "reason": reason})
    try:
        lock_path().unlink()
    except OSError:
        pass
    return status()

@contextlib.contextmanager
def holder(desc="gpu"):
    acquire(desc=desc)
    try:
        yield
    finally:
        release()

def _reset():
    """Test helper: release anything held by this thread and clear stale metadata."""
    release()
    _write_meta({})

def main(argv=None):
    parser = argparse.ArgumentParser(description="GPU barrier for Video Studio")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show the current holder")
    sub.add_parser("force-release", help="manual escape hatch for a hung holder")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        print(json.dumps(status(), indent=2))
    elif args.cmd == "force-release":
        print(json.dumps(force_release(), indent=2))

if __name__ == "__main__":
    main()
```

---

## New module: `app/studio/editor_session.py`

```python
"""One machine-wide editor session.

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
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False
    except Exception:
        return True

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
```

---

## Existing file patches

### `app/studio/pipeline.py`

#### 1. Import and queue/GPU constants

```diff
-from . import config, transcript, writer, render, assemble, media, sources, short, debug
+from . import config, transcript, writer, render, assemble, media, sources, short, debug, gpu_lock
```

```diff
 SMOKE_SECS = 30.0   # "smoke test" Shorts: about 75 words of narration including the closing line
+
+GPU_STAGES = {"short_voice", "short_fallback", "voice", "presenter", "motion", "stills"}
+
+
+class _StudioQueue:
+    """Priority queue: editor-owned work, then Newsroom jobs, then hand jobs.
+
+    Existing `Studio.q.put(jid)` call sites stay unchanged.
+    """
+    def __init__(self, studio):
+        self._q = queue.PriorityQueue()
+        self._studio = studio
+        self._seq = 0
+        self._lk = threading.Lock()
+
+    def put(self, jid):
+        with self._lk:
+            self._seq += 1
+            self._q.put((self._studio._prio(jid), self._seq, jid))
+
+    def get(self):
+        return self._q.get()[2]
```

#### 2. Studio init, guard, priority helpers, editor wait watcher

Replace:

```python
    def __init__(self):
        self.q = queue.Queue(); self.current = None; self.cancel = set()
        try:   # jobs cut off by an app restart or PC reboot: show them as stopped (press Resume) instead of a stale "running"
            for d in self.jobs_dir().iterdir():
                if d.is_dir() and (d / "state.json").exists():
                    j = Job(d)
                    if j.state.get("status") in ("running", "queued"):
                        j.save(status="stopped"); j.log("Interrupted (the app or PC restarted). Press Resume to continue; finished work is kept.")
        except Exception: pass
        threading.Thread(target=self._worker, daemon=True).start()
```

with:

```python
    def __init__(self, port=None):
        self.port = port
        self.live = port in (None, "42021", 42021)
        self.q = _StudioQueue(self)
        self.current = None; self.cancel = set()
        self._editor_waits = {}
        self._editor_waits_lk = threading.Lock()
        if not self.live:
            self._refuse_live_jobs_dir()
        try:   # jobs cut off by an app restart or PC reboot: show them as stopped (press Resume) instead of a stale "running"
            for d in self.jobs_dir().iterdir():
                if d.is_dir() and (d / "state.json").exists():
                    j = Job(d)
                    if j.state.get("status") in ("running", "queued"):
                        j.save(status="stopped"); j.log("Interrupted (the app or PC restarted). Press Resume to continue; finished work is kept.")
        except Exception: pass
        threading.Thread(target=self._editor_wait_watcher, daemon=True).start()
        threading.Thread(target=self._worker, daemon=True).start()
```

After `def list(...)` add:

```python
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

    def _enqueue(self, jid):
        self.q.put(jid)

    def _refuse_live_jobs_dir(self):
        live_settings = Path(r"F:\code\video-studio-test\settings.json")
        if not live_settings.exists():
            return
        try:
            import json as _json
            live_jobs = os.path.normpath(str(_json.loads(live_settings.read_text(encoding="utf-8")).get("jobs_dir", "")))
            my_jobs = os.path.normpath(str(config.load().get("jobs_dir", "")))
            if live_jobs and my_jobs == live_jobs:
                raise RuntimeError(f"Refusing to start this copy: it points at the live jobs_dir ({live_jobs})")
        except RuntimeError:
            raise
        except Exception:
            pass

    def _wait_editor_reservation(self, j, s, log, jid):
        from . import editor_session
        res = editor_session.active()
        if not res:
            return False

        label = f"Waiting: editor in use ({res.get('jid')})"
        if s.get("status") != "paused" or (s.get("pause") or {}).get("label") != label:
            j.save(status="paused", pause={"kind": "editor_wait", "label": label,
                                          "stage": s.get("stage"), "where": s.get("stage")}, pause_req=False)
            j.log(label + f" (holder pid {res.get('pid')}, port {res.get('port')}); it will continue automatically when the editor session releases.")
            with self._editor_waits_lk:
                self._editor_waits[jid] = time.time()
        return True

    def _requeue_editor_waits(self):
        from . import editor_session
        if editor_session.active():
            return

        with self._editor_waits_lk:
            waits = list(self._editor_waits.items())
            self._editor_waits.clear()

        for jid, _ in waits:
            try:
                job = self.job(jid)
            except Exception:
                continue
            if job.state.get("status") == "paused" and (job.state.get("pause") or {}).get("kind") == "editor_wait":
                job.save(status="queued", pause=None, pause_req=False, cancel_req=False, cancelled=False)
                job.log("Editor session released; continuing automatically.")
                self._enqueue(jid)

    def _editor_wait_watcher(self):
        while True:
            time.sleep(1.0)
            try:
                self._requeue_editor_waits()
            except Exception:
                pass
```

#### 3. `create` signature and queue put

```diff
     def create(self, url, minutes, presenter=False, auto_approve=False, transcript_text="", provider="", captions=True,
                mode="both", short_secs=165, upload=None, upload_name="", src_title="", src_credit="", visual_review="auto", dbg_on=False, bps=None,
-               own_clips=None, tts_engine="", audience=""):
+               own_clips=None, tts_engine="", audience="", newsroom=False):
```

```diff
-               upload=up, src_title=src_title, src_credit=src_credit, visual_review=visual_review if visual_review in ("auto", "every", "never") else "auto", status="queued", stage="transcript", done=[], title="", created=time.time(),
-               debug={"on": bool(dbg_on), "bps": list(bps or []), "bps_off": False, "checked": [], "chat": []}, trace=bool(dbg_on))
+               upload=up, src_title=src_title, src_credit=src_credit, visual_review=visual_review if visual_review in ("auto", "every", "never") else "auto", status="queued", stage="transcript", done=[], title="", created=time.time(),
+               newsroom=bool(newsroom), priority=("newsroom" if newsroom else "normal"),
+               debug={"on": bool(dbg_on), "bps": list(bps or []), "bps_off": False, "checked": [], "chat": []}, trace=bool(dbg_on))
```

```diff
-        j.log(f"Job created for {what} (output: {'SMOKE TEST, ' if smoke else ''}{mode}; long {minutes} min, short {short_secs:.0f}s)"); self.q.put(jid); return jid
+        j.log(f"Job created for {what} (output: {'SMOKE TEST, ' if smoke else ''}{mode}; long {minutes} min, short {short_secs:.0f}s)"); self._enqueue(jid); return jid
```

#### 4. `approve`, `continue_visuals`, `rerender`, `resume`, retry queue puts

```diff
-            d = s.get("done", []); d.append("review"); j.save(done=d, status="queued"); j.log("Script approved"); self.q.put(jid)
+            d = s.get("done", []); d.append("review"); j.save(done=d, status="queued"); j.log("Script approved"); self._enqueue(jid)
```

```diff
-        j.save(done=d, status="queued"); j.log("Visual review done; rendering"); self.q.put(jid)
+        j.save(done=d, status="queued"); j.log("Visual review done; rendering"); self._enqueue(jid)
```

```diff
-    def rerender(self, jid, target="", refresh_fallbacks=False):
+    def rerender(self, jid, target="", refresh_fallbacks=False, editor_owned=False):
```

```diff
-        j.save(done=d, status="queued"); j.log("Full re-render requested"); self.q.put(jid)
+        if editor_owned:
+            j.save(editor_owned=True)
+        j.save(done=d, status="queued"); j.log("Full re-render requested"); self._enqueue(jid)
```

```diff
-        j.save(status="queued", error="", pause=None, pause_req=False, cancel_req=False, cancelled=False); j.log("Resumed"); self.q.put(jid)
+        j.save(status="queued", error="", pause=None, pause_req=False, cancel_req=False, cancelled=False); j.log("Resumed"); self._enqueue(jid)
```

```diff
-                    threading.Timer(60, lambda jid=jid: self.q.put(jid)).start()
+                    threading.Timer(60, lambda jid=jid: self._enqueue(jid)).start()
```

#### 5. `_worker` finally releases raw GPU lock

```diff
             finally:
                 self.current = None
                 try:   # a job never leaves an on-demand WanGP holding VRAM (error, cancel or success)
                     from . import wangp as _wangp; _wangp.release(print, "job ended")
                 except Exception: pass
+                try:
+                    gpu_lock.release()
+                except Exception:
+                    pass
```

#### 6. `_stages` start and GPU gating

Replace this block:

```python
    def _stages(self, j, s, cfg, wg, log, stop, dbg, jid):
        mode = s.get("mode", "long")
        for st in stages_for(mode):
            if st in j.state.get("done", []): continue
            if stop(): j.save(status="stopped"); log("Stopped"); self.cancel.discard(jid); return
            dbg.manual(st)
            j.save(prog={"out": output_of(st), "stage": st, "n": 0, "of": 0})
            j.save(stage=st); log(f"== {st} ==")
```

with:

```python
    def _stages(self, j, s, cfg, wg, log, stop, dbg, jid):
        mode = s.get("mode", "long")
        gpu_held = False

        def release_gpu():
            nonlocal gpu_held
            if gpu_held:
                gpu_lock.release()
                gpu_held = False

        for st in stages_for(mode):
            if st in j.state.get("done", []): continue

            if gpu_held and st not in GPU_STAGES:
                release_gpu()

            if stop():
                release_gpu()
                j.save(status="stopped"); log("Stopped"); self.cancel.discard(jid); return

            if st in GPU_STAGES:
                if self.live and not j.state.get("editor_owned"):
                    if self._wait_editor_reservation(j, s, log, jid):
                        release_gpu()
                        return
                if not gpu_held:
                    gpu_lock.acquire(desc=f"job:{jid}:{st}")
                    gpu_held = True

            dbg.manual(st)
            j.save(prog={"out": output_of(st), "stage": st, "n": 0, "of": 0})
            j.save(stage=st); log(f"== {st} ==")
```

#### 7. Release GPU before early returns inside `_stages`

```diff
                     j.save(status="awaiting_visuals")
                     debug.trace(j.dir, {"ev": "pause", "label": "Paused: uncertain about this beat",
                                         "beats": ", ".join(f"Beat {int(b[1:]) + 1}" for b, x in rv["beats"].items() if x.get("uncertain") and not x.get("decision"))})
                     debug.render_md(j.dir)
+                    release_gpu()
                     log("Visual review: choose a treatment for each beat on the job page (or Approve all remaining)." if vm == "every" else
                         "Visual review: some beats are uncertain; check them on the job page (or Approve all remaining)."); return
```

```diff
                 qs = [q for p in (j.plan(), j.short_plan()) if p for q in p.get("questions", [])]
                 if not s.get("auto_approve", True):
+                    release_gpu()
                     j.save(status="awaiting_review"); log("Script ready for review. Edit if you like, then press Approve."); return
                 if qs and cfg.get("pause_on_questions", False):
+                    release_gpu()
                     j.save(status="awaiting_review"); log(f"Fact-check raised {len(qs)} question(s); paused for review (setting: pause on fact-check questions)."); return
```

```diff
-            if stop(): j.save(status="stopped"); log("Stopped"); self.cancel.discard(jid); return
+            if stop():
+                release_gpu()
+                j.save(status="stopped"); log("Stopped"); self.cancel.discard(jid); return
             d = j.state.get("done", []); d.append(st); j.save(done=d)
+        release_gpu()
         if cfg.get("qc_on", False):   # (off until calibrated: the first run flagged most news frames) owner, 2026-10-24: frame QC on every video (fingers, smudges, sideways, blur, giant faces)
```

---

### `app/server.py`

#### 1. Port-plus-Studio guard

Add near the top, before `studio = Studio()`:

```python
import os
VS_PORT = int(os.environ.get("VS_PORT", "42021"))
studio = Studio(port=VS_PORT)
```

If `os` is already imported, do not add a duplicate import. If `studio = Studio()` appears differently, replace that call with `Studio(port=VS_PORT)`.

#### 2. Editor helpers

Insert before the first edit route:

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
```

#### 3. Open editor beat

Replace:

```python
@app.post("/api/jobs/<jid>/edit/open/<bid>")
def edit_open(jid, bid):
    from studio import edit
    j = studio.job(jid)
    try: rv = edit.open_beat(j.dir, bid, config.load(), j.log)
    except Exception as e: return jsonify(error=str(e)[:300]), 400
    return jsonify(space="short" if edit.kind(j.dir) == "short" else "long", rv=rv)
```

with:

```python
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
```

#### 4. Chat is browse-only, allowed for read-only popups

```diff
     if not text or not b.get("beat"): return jsonify(error="type a message (and open a beat)"), 400
-    if studio.current: return jsonify(error="A job is rendering right now; edit when it has finished."), 409
     if _interview(jid):
```

#### 5. Edit action guard and raw GPU lock

Replace:

```python
@app.post("/api/jobs/<jid>/edit/<action>/<bid>")
def edit_act(jid, action, bid):
    from studio import edit
    j = studio.job(jid); b = request.get_json(silent=True) or {}; cfg = config.load()
    if studio.current: return jsonify(error="A job is rendering right now; edit when it has finished."), 409
    try:
        if action == "preview": return jsonify(edit.preview(j.dir, bid, b.get("cands") or [], b.get("fit", "auto"), cfg, j.log))
        if action == "apply":
            err = edit.start_apply(j.dir, bid, b.get("cands") or [], b.get("fit", "auto"), cfg, j.log)
            return (jsonify(error=err), 409) if err else jsonify(ok=True)
    except Exception as e: return jsonify(error=str(e)[:300]), 400
    return jsonify(error="unknown action"), 400
```

with:

```python
@app.post("/api/jobs/<jid>/edit/<action>/<bid>")
def edit_act(jid, action, bid):
    from studio import edit, gpu_lock
    j = studio.job(jid); b = request.get_json(silent=True) or {}; cfg = config.load()
    sid = b.get("sid", "")
    ok, holder = _editor_owner(jid, sid)
    if not ok:
        return jsonify(error=holder), 409
    try:
        if action == "preview":
            with gpu_lock.holder(desc=f"editor-preview:{jid}:{bid}"):
                return jsonify(edit.preview(j.dir, bid, b.get("cands") or [], b.get("fit", "auto"), cfg, j.log))
        if action == "apply":
            err = edit.start_apply(j.dir, bid, b.get("cands") or [], b.get("fit", "auto"), cfg, j.log)
            return (jsonify(error=err), 409) if err else jsonify(ok=True)
    except Exception as e:
        return jsonify(error=str(e)[:300]), 400
    return jsonify(error="unknown action"), 400
```

#### 6. Edit-all: undo/rerender under editor ownership

Replace:

```python
@app.post("/api/jobs/<jid>/edit_all/<action>")
def edit_all(jid, action):
    from studio import edit, review
    j = studio.job(jid)
    try:
        if action == "undo": edit.undo(j.dir, j.log)
        elif action == "rerender":
            b = request.get_json(silent=True) or {}
            studio.rerender(jid, str(b.get("target") or ""), bool(b.get("refresh_fallbacks")))
        elif action == "cleanup":
            review.prune(j.dir, j.log, full=True)
            if (j.dir / "longedit").exists(): review.prune(j.dir / "longedit", j.log, full=True)
        else: return jsonify(error="unknown action"), 400
```

with:

```python
@app.post("/api/jobs/<jid>/edit_all/<action>")
def edit_all(jid, action):
    from studio import edit, review, gpu_lock
    j = studio.job(jid)
    b = request.get_json(silent=True) or {}
    sid = b.get("sid", "")
    try:
        if action == "undo":
            ok, holder = _editor_owner(jid, sid)
            if not ok:
                return jsonify(error=holder), 409
            with gpu_lock.holder(desc=f"editor-undo:{jid}"):
                edit.undo(j.dir, j.log)
        elif action == "rerender":
            ok, holder = _editor_owner(jid, sid)
            if not ok:
                return jsonify(error=holder), 409
            studio.rerender(jid, str(b.get("target") or ""), bool(b.get("refresh_fallbacks")), editor_owned=True)
        elif action == "cleanup":
            review.prune(j.dir, j.log, full=True)
            if (j.dir / "longedit").exists(): review.prune(j.dir / "longedit", j.log, full=True)
        else: return jsonify(error="unknown action"), 400
```

#### 7. `/make/edit`

Replace:

```python
    if studio.current: return jsonify(error="A job is rendering right now; edit when it has finished."), 409
    err = edit.start_apply(j.dir, b.get("beat", ""), b.get("cands") or [], b.get("fit", "auto"), config.load(), j.log)
    return (jsonify(error=err), 409) if err else jsonify(ok=True)
```

with:

```python
    sid = b.get("sid", "")
    ok, holder = _editor_owner(b.get("job", ""), sid)
    if not ok:
        return jsonify(error=holder), 409
    err = edit.start_apply(j.dir, b.get("beat", ""), b.get("cands") or [], b.get("fit", "auto"), config.load(), j.log)
    return (jsonify(error=err), 409) if err else jsonify(ok=True)
```

#### 8. New editor polling/heartbeat/close routes

Insert after `edit_all`:

```python
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
```

---

### `app/studio/edit.py`

Replace the `start_apply` background runner’s try body:

```python
    def run():
        from .pipeline import Job
        try: apply(job, bid, cids, fit, cfg, log)
        except Exception as e:
```

with:

```python
    def run():
        from .pipeline import Job
        from . import gpu_lock
        try:
            with gpu_lock.holder(desc=f"editor-apply:{Path(job).name}:{bid}"):
                apply(job, bid, cids, fit, cfg, log)
        except Exception as e:
```

The rest of the function stays unchanged.

---

### `app/studio/interview_edit.py`

Replace:

```python
    def run():
        from .pipeline import Job
        from . import review
        try:
            m, i, p = _part(job, bid, k)
            n = len(list((Path(job) / "iedit" / "parts").glob(f"{k}_{bid}_*.mp4"))) if (Path(job) / "iedit" / "parts").exists() else 0
            new = Path(job) / "iedit" / "parts" / f"{k}_{bid}_{n + 1}.mp4"; new.parent.mkdir(parents=True, exist_ok=True)
            _render_piece(job, bid, cids, new)
            hist = m.setdefault("history", []); hist.append({"bid": bid, "old": p["file"], "new": str(new), "t": time.time()})
            p["file"] = str(new); p["check"] = False; m["parts"][i] = p; _save_man(job, k, m)
            _assemble(j
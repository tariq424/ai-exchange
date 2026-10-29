# Round 1 of 2 — DESIGN REVIEW ONLY (no patch yet): GPU interlock + editor priority for Video Studio

Tariq wants the design below. Before any code: check it against the real code (excerpts at the end) and tell us
every discrepancy, contradiction, race or bug you see, and how you would fix it. Then give your implementation plan
(files, functions, data you would add). Round 2 will ask for the patch once we agree.

## The design (Tariq + Claude, agreed so far)
- Priority: (1) an editor session, (2) Newsroom jobs, (3) jobs started by hand in Video Studio.
- ONE machine-wide GPU lock (a lock file on F:, recording holder, pid, since). Every GPU user takes it before heavy
  work and releases it after: pipeline render (the queue worker), editor applies/re-renders, QC/repair runs, test
  copies of the app (other ports), and the external WanGP watchdog must never unload a model while it is held.
  A lock whose holder process is dead counts as free.
- Jobs still queue, but a job waiting for the lock shows "Waiting: <reason>" (e.g. "editor in use", "GPU busy: QC").
- Editor opened while a job renders: the popup shows "A render is on the runway — your edit starts at its next safe
  point (stage X, about N min left)" and re-checks every few seconds. The running job is asked to pause at its next
  safe point (the existing request_pause / debug.Paused mechanism, between stages) and its card says
  "Paused for the editor". While the editor holds the lock, every other job pends with that reason.
- One editor session per job, kept server-side. Clicking the job id again RESUMES the same session (same `vsedit`
  window), never a second one.
- 15 minutes with no edit activity: the editor SAVES its state (open beat, ticked candidates, chat draft, fit choice,
  pending edits), pauses, and releases the lock; paused jobs resume and the queue continues. The card shows
  "Edit paused — Resume"; Resume restores exactly that state and re-takes the lock (and may hit "on the runway" again).
- "Done editing" / Close ends the session and releases the lock. An apply is never left half done: finish or roll back.

## Facts from the code you should weigh
- The queue is a FIFO `queue.Queue` with one worker thread (`Studio._worker`); `self.current` is the running job.
- Edit routes already refuse while `studio.current` is set (409 "A job is rendering right now") — see excerpts.
  `edit_all/rerender` just re-queues the job; `edit_all/undo` has no guard.
- `debug.Paused` pauses at safe points between stages; some stages (final render, long-video assembly) run 5-15 min
  with no safe point inside.
- A job's end calls `wangp.release(...)` ("a job never leaves an on-demand WanGP holding VRAM").
- The WanGP watchdog is a separate PowerShell script on the PC (not in the repo) that unloads an idle WanGP.
- Newsroom submits jobs over HTTP to POST /api/jobs (it is a separate app; it can send an extra field if needed).
- The app may run as several processes (live 42021, test copy 42022), each with its own queue — so an in-process
  lock alone is not enough.

## Answer format
1. Numbered list of problems in the design (each: what goes wrong, concrete scenario, your fix).
2. Implementation plan: files/functions to change or add, the lock file format, how pause-for-editor and resume
   are wired, how the editor session and its saved state are stored, how the 15-minute idle is detected (client
   heartbeat?), and what the watchdog must check.
3. Questions for Tariq, if any decision is genuinely his.
No patch in this round.

## Code excerpts
### app/studio/pipeline.py (Studio: queue, resume, pause, worker, run)
```python

class Studio:
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

    def jobs_dir(self): d = Path(config.load()["jobs_dir"]); d.mkdir(parents=True, exist_ok=True); return d
    def job(self, jid): return Job(self.jobs_dir() / jid)
    def list(self):
        out = []
        for d in sorted(self.jobs_dir().iterdir(), reverse=True):
            if d.is_dir() and (d / "state.json").exists(): s = Job(d).state; s["id"] = d.name; out.append(s)
        return out

    def create(self, url, minutes, presenter=False, auto_approve=False, transcript_text="", provider="", captions=True,
               mode="both", short_secs=165, upload=None, upload_name="", src_title="", src_credit="", visual_review="auto", dbg_on=False, bps=None,
               own_clips=None, tts_engine="", audience=""):
        smoke = mode == "smoke"   # pipeline check: a ~30-second Short (about 75 words); real Shorts keep the 2:00 minimum
        if smoke: mode, short_secs = "short", SMOKE_SECS
        jid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        j = self.job(jid); j.dir.mkdir(parents=True); (j.dir / "src").mkdir()
        up = ""
        if upload is not None:
            up = re.sub(r"[^A-Za-z0-9._ -]+", "_", upload_name or "upload")[:80]; upload.save(str(j.dir / "src" / up))
        elif transcript_text.strip():
            (j.dir / "src" / ("transcript_manual.txt" if url else "pasted.txt")).write_text(transcript_text, encoding="utf-8")
        j.save(url=url, minutes=float(minutes), presenter=bool(presenter), captions=bool(captions), auto_approve=bool(auto_approve), provider=provider or "",
               mode=mode if mode in ("long", "short", "both") else "both", short_secs=SMOKE_SECS if smoke else max(120.0, min(176.0, float(short_secs))), smoke=smoke,
               upload=up, src_title=src_title, src_credit=src_credit, visual_review=visual_review if visual_review in ("auto", "every", "never") else "auto", status="queued", stage="transcript", done=[], title="", created=time.time(),
               debug={"on": bool(dbg_on), "bps": list(bps or []), "bps_off": False, "checked": [], "chat": []}, trace=bool(dbg_on))
        if dbg_on: debug.trace(j.dir, {"ev": "debug on", "at": "job start", "breakpoints": "; ".join(bps or []) or "none"})
        if own_clips:   # your footage + where it goes (clips.py places it after the script is written)
            from . import clips
            try: mc = clips.save(j.dir, own_clips.get("uploads") or [], own_clips.get("paths") or [], own_clips.get("hints", ""), j.log)
            except Exception:
                shutil.rmtree(j.dir, ignore_errors=True); raise
            j.save(my_clips=mc); j.log(f"Your clips: {len(mc)} file(s)" + (" with a placement note" if (own_clips.get("hints") or "").strip() else ""))
        if tts_engine in ("kokoro", "wanGP"): j.save(tts_engine=tts_engine)
        if audience in writer.AUDIENCE: j.save(audience=audience)
        what = url or (f"file {up}" if up else "pasted text")
        j.log(f"Job created for {what} (output: {'SMOKE TEST, ' if smoke else ''}{mode}; long {minutes} min, short {short_secs:.0f}s)"); self.q.put(jid); return jid

    def approve(self, jid):
        j = self.job(jid); s = j.state
        if s.get("status") == "awaiting_review":
            d = s.get("done", []); d.append("review"); j.save(done=d, status="queued"); j.log("Script approved"); self.q.put(jid)
    def continue_visuals(self, jid):
        """Visual review finished (every beat decided): render."""
        from . import review
        j = self.job(jid); review.close(j.dir)
        d = j.state.get("done", [])
        if "short_review" not in d: d.append("short_review")
        j.save(done=d, status="queued"); j.log("Visual review done; rendering"); self.q.put(jid)

    def rerender(self, jid, target="", refresh_fallbacks=False):
        """Full re-render on request (post-render edits are kept: Shorts from the review decisions, long videos from edit_clip).
        A job with both outputs re-renders the one being edited (edit_target), or `target` ("short" | "long").
        refresh_fallbacks (explainer): shots that fell to a headline text card (e.g. the script AI was unreachable) go down the
        visual ladder again (graphics -> simulation -> illustration -> headline), and caption emoji that weren't picked are picked
        again, before the explainer is rendered."""
        j = self.job(jid); s = j.state
        target = target or ("long" if s.get("edit_target") == "long" or refresh_fallbacks else "")
        st = "assemble" if (target == "long" and s.get("output")) or not s.get("short_output") else "short_render"
        if refresh_fallbacks and st == "assemble": j.save(refresh_fallbacks=True)
        if st == "assemble":
            for p in (j.dir / "build").glob("sec_*.mp4"): p.unlink(missing_ok=True)
        d = [x for x in j.state.get("done", []) if x != st]
        shutil.rmtree(j.dir / "edit" / "history", ignore_errors=True)   # step-by-step undo can't cross a full re-render
        j.save(done=d, status="queued"); j.log("Full re-render requested"); self.q.put(jid)

    def resume(self, jid):
        j = self.job(jid); self.cancel.discard(jid)
        was = j.state.get("pause") if j.state.get("status") == "paused" else None
        j.save(status="queued", error="", pause=None, pause_req=False, cancel_req=False, cancelled=False); j.log("Resumed"); self.q.put(jid)
        if was: debug.trace(j.dir, {"ev": "resume", "from": was.get("label", "")})

    def request_pause(self, jid):
        """'Pause now': stop at the next safe point (never inside a render or a generation)."""
        j = self.job(jid)
        if j.state.get("status") not in ("running", "queued"): return False
        j.save(pause_req=True); j.log("Pause requested: stopping at the next safe point"); return True

    def set_debug(self, jid, on=None, bps=None, bps_off=None):
        j = self.job(jid); d = j.state.get("debug") or {"on": False, "bps": [], "bps_off": False, "checked": [], "chat": []}
        s = j.state; p = s.get("pause") or {}
        where = f"Beat {p['n']}" if p.get("n") else (s.get("stage") or "")
        if on is not None and bool(on) != bool(d.get("on")):
            d["on"] = bool(on); j.save(debug=d)
            if on and not s.get("trace"): j.save(trace=True)
            debug.trace(j.dir, {"ev": "debug " + ("on" if on else "off"), "at": where, "status": s.get("status")}, force=bool(on))
            j.log(f"Debug mode {'on' if on else 'off'} for the rest of this run")
        if bps is not None:
            d["bps"] = list(bps); j.save(debug=d); debug.trace(j.dir, {"ev": "breakpoints", "list": "; ".join(bps) or "none"})
        if bps_off is not None:
            d["bps_off"] = bool(bps_off); j.save(debug=d); debug.trace(j.dir, {"ev": "breakpoints " + ("disabled" if bps_off else "enabled"), "at": where})
        debug.render_md(j.dir)
        return j.state.get("debug")

    def abort(self, jid):
        j = self.job(jid)
        if j.state.get("status") in ("running", "queued"): self.stop(jid); return
        j.save(status="stopped", pause=None, pause_req=False); j.log("Aborted"); debug.trace(j.dir, {"ev": "abort"}); debug.render_md(j.dir)
    def stop(self, jid): self.cancel.add(jid); self.job(jid).log("Stop requested")   # hard stop (Abort): interrupts WanGP / Remotion

    def cancel_job(self, jid):
        """'Stop video': cancel at the next safe point (before a stage, between AI stills, after a beat - never inside a render or
        a generation). State stays on disk; the job ends as "stopped" (cancelled) and Resume continues from where it stopped."""
        j = self.job(jid); st = j.state.get("status")
        if st == "running":
            j.save(pause_req=True, cancel_req=True); j.log("Stop video: stopping at the next safe point (never inside a render or a generation)")
            return "stopping"
        if st in ("queued", "paused", "awaiting_visuals", "awaiting_review"):
            j.save(status="stopped", pause=None, pause_req=False, cancel_req=False, cancelled=True); j.log("Cancelled (Stop video). Resume continues from here.")
            return "stopped"
        return st or "unknown"

    def _worker(self):
        while True:
            jid = self.q.get()
            try: self._run(jid)
            except Exception as e:
                j = self.job(jid); j.log("ERROR: " + str(e)); j.log(traceback.format_exc()[-1500:])
                n = int(j.state.get("auto_retries", 0))
                rendering = j.state.get("stage") in ("charts", "voice", "captions", "presenter", "motion", "stills", "assemble", "broll", "short_stock", "short_voice", "short_fallback", "short_review", "short_render")
                if jid in self.cancel and "cancelled" in str(e):   # hard stop (Abort) interrupted a step: stopped, not an error
                    self.cancel.discard(jid); j.save(status="stopped", cancelled=True); j.log("Stopped")
                elif rendering and n < 3 and jid not in self.cancel:
                    j.save(status="queued", error="", auto_retries=n + 1)
                    j.log(f"Retrying automatically in 60s (attempt {n + 1} of 3); finished work is kept")
                    threading.Timer(60, lambda jid=jid: self.q.put(jid)).start()
                else:
                    j.save(status="error", error=str(e)[:500])
            finally:
                self.current = None
                try:   # a job never leaves an on-demand WanGP holding VRAM (error, cancel or success)
                    from . import wangp as _wangp; _wangp.release(print, "job ended")
                except Exception: pass

    # ---- YouTube transcripts without hammering YouTube: reuse what we have, respect a cooldown after a block
    YT_COOLDOWN = 30 * 60

...
    def _run(self, jid):
        j = self.job(jid); s = j.state; cfg = config.load()
        if s.get("tts_engine") in ("kokoro", "wanGP"): cfg["tts_engine"] = s["tts_engine"]   # the job's own narration choice
        if s.get("audience") in writer.AUDIENCE: cfg["audience"] = s["audience"]; cfg["_audience_from"] = "job"   # the job's own audience (script prompts)
        if s.get("cancelled") and s.get("status") == "stopped": return   # cancelled while it waited in the queue
        self.current = jid
        stop = lambda: jid in self.cancel
        wg = WanGP(cfg); log = j.log
        j.save(status="running", error="")
        dbg = debug.Debugger(j, log)
        try: self._stages(j, s, cfg, wg, log, stop, dbg, jid)
        except debug.Paused as p:
            info = p.info
            if j.state.get("cancel_req"):   # Stop video reached its safe point
                where = f"Beat {info['n']}" if info.get("n") else (info.get("where") or j.state.get("stage") or "")
                j.save(status="stopped", pause=None, pause_req=False, cancel_req=False, cancelled=True)
                log(f"Cancelled at a safe point ({where}). Finished work is kept; Resume continues from here.")
                debug.trace(j.dir, {"ev": "cancel", "at": where}); return
            if info.get("stage") is None: info["stage"] = j.state.get("stage")
            sd = j.dir / "short"
            if (sd / "timings.json").exists() and (sd / "stock" / "pick.json").exists() and j.short_plan():
                beats = [info["beat"]] if info.get("beat") else list(debug.chains(j.dir))
                if beats:
                    try:
                        from . import review
                        review.collect(j.dir, j.short_plan(), cfg, log, s.get("visual_review", "auto"), debug_beats=beats)
                    except Exception as e: log(f"  couldn't gather this beat's treatments ({str(e)[:150]})")
            j.save(status="paused", pause=info, pause_req=False)
            log(info["label"] + (f" at Beat {info['n']}" if info.get("n") else f" before {info.get('where')}") + ". Press Continue to go on.")
            debug.trace(j.dir, {"ev": "pause", "label": info["label"], "beat": info.get("n"), "where": info.get("where")}, force=True)
            debug.render_md(j.dir)

```
### app/server.py (edit routes)
```python
@app.post("/api/jobs/<jid>/edit/target")
def edit_target(jid):
    """A job with a Short and an explainer: which one the timeline editor works on (short | long)."""
    from studio import edit
    j = studio.job(jid); b = request.get_json(silent=True) or {}
    try: edit.set_target(j.dir, b.get("target", ""))
    except Exception as e: return jsonify(error=str(e)[:300]), 400
    return jsonify(ok=True, target=edit.kind(j.dir))

@app.post("/api/jobs/<jid>/edit/open/<bid>")
def edit_open(jid, bid):
    from studio import edit
    j = studio.job(jid)
    try: rv = edit.open_beat(j.dir, bid, config.load(), j.log)
    except Exception as e: return jsonify(error=str(e)[:300]), 400
    return jsonify(space="short" if edit.kind(j.dir) == "short" else "long", rv=rv)

@app.post("/api/jobs/<jid>/edit/chat")
def edit_chat(jid):
    """The pause chat, inside the timeline editor of a finished job (same routing and actions + "apply")."""
    from studio import debug
    b = request.get_json(silent=True) or {}; text = (b.get("text") or "").strip()
    if not text or not b.get("beat"): return jsonify(error="type a message (and open a beat)"), 400
    if studio.current: return jsonify(error="A job is rendering right now; edit when it has finished."), 409
    if _interview(jid):
        from studio import interview_edit
        try: return jsonify(interview_edit.chat(studio.job(jid).dir, b["beat"], text, config.load()))
        except Exception as e: return jsonify(error=str(e)[:300]), 500
    try: return jsonify(debug.chat(studio, jid, b["beat"], text, config.load(), edit=True))
    except Exception as e: return jsonify(error=str(e)[:300]), 500

@app.get("/api/jobs/<jid>/edit/chat")
def edit_chat_log(jid):
    j = studio.job(jid); bid = request.args.get("beat")
    return jsonify(chat=[e for e in (j.state.get("debug") or {}).get("chat", []) if not bid or e.get("beat") == bid])

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
...
@app.post("/make/edit")
def make_edit():
    from studio import edit
    b = request.get_json(silent=True) or {}; j = studio.job(b.get("job", ""))
    if not j.dir.exists(): return jsonify(error="no such job"), 404
    if studio.current: return jsonify(error="A job is rendering right now; edit when it has finished."), 409
    err = edit.start_apply(j.dir, b.get("beat", ""), b.get("cands") or [], b.get("fit", "auto"), config.load(), j.log)
    return (jsonify(error=err), 409) if err else jsonify(ok=True)
```
### app/studio/edit.py (apply runs in a thread)
```python
    return ws

# ---------------------------------------------------------------- preview and apply
_busy, _lk = {}, threading.Lock()


def _iv(job):
    """An interview job (interview_edit.py) - its own pieces, candidates and re-assembly."""
...
    n = max([int(d.name) for d in r.glob("[0-9][0-9][0-9]")] or [0]) + 1
    d = r / f"{n:03d}"; d.mkdir(); return d

def can_undo(job): return _ie().can_undo(job) if _iv(job) else (bool(history(job)) or any(Path(job).glob("output/*.prev")))

def status(job): return _busy.get(str(Path(job)), "")

def start_apply(job, bid, cids, fit, cfg, log):
    if _iv(job): return _ie().start_apply(job, bid, cids, fit, cfg, log)
    key = str(Path(job))
    with _lk:
        if _busy.get(key): return "Already applying an edit to this video."
        _busy[key] = f"Applying the new visual to {bid}..."
    def run():
        from .pipeline import Job
        try: apply(job, bid, cids, fit, cfg, log)
        except Exception as e:
            import traceback
            msg = LOCKED_MSG if isinstance(e, FileLocked) or "WinError 5" in str(e) or "WinError 32" in str(e) else str(e)[:300]
            log(f"Edit {bid} NOT applied: {msg} The video is unchanged.")
            if not isinstance(e, FileLocked): log(traceback.format_exc()[-800:])
            _busy[key + ":err"] = msg
            try: Job(job).save(edit_last={"beat": bid, "ok": False, "msg": msg, "t": time.time()})
            except Exception: pass
            try:
                from . import review
                ws = workspace(job)
                with review._lock(ws):
                    rv = review.load(ws)
                    if rv and bid in rv.get("beats", {}): rv["beats"][bid]["msg"] = f"Not applied: {msg}"; review.save(ws, rv)
            except Exception: pass
        finally: _busy[key] = ""
    _busy.pop(key + ":err", None)
    threading.Thread(target=run, daemon=True).start(); return ""

def apply(job, bid, cids, fit, cfg, log):
    """Render the beat with its new visual and splice it into the output MP4 in place (no re-render of other beats).
    What it replaces goes on the undo stack."""
    from . import review
    from .pipeline import Job
    job = Path(job); t0 = time.time()
    k, ws, sd, rv, d, lay, mode, why = _plan_beat(job, bid, cids, fit, cfg)
    user = all(is_user(rv["cands"][c]["item"]) for c in cids)
    log(f"Edit {bid}: {', '.join(RUNG(rv, c) for c in cids)} -> {'fit-and-render (your file, no AI): ' if user else ''}{FIT_NAME.get(mode, mode)} ({why})")
    clean_leftovers(job)
    _clear_prev(job)   # older single-step undo files: the stack replaces them
```

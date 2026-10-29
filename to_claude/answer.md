1. **Design problems**

1. **The priority order is only local to each process, but the GPU lock is machine-wide.**
   What goes wrong: `Studio.q` is a per-process `queue.Queue`; the live app on 42021, the test copy on 42022, and any future process each have their own worker. The machine-wide lock only guarantees one GPU user, not which user goes next. Concrete scenario: the live process has a hand job at the head and a Newsroom job behind it; the test copy has one hand job. The lock frees; the test copy’s worker is already at its queue head and grabs the lock, while the live Newsroom job is still stuck behind the live hand job. Newsroom priority is defeated.
   Fix: either (a) all unattended pipeline jobs run through one scheduler process (live Video Studio) and test copies only take the lock for manual/test work, or (b) implement a real cross-process priority wait queue in the lock file. I recommend (a) for this round; (b) is significantly more moving parts. Tariq should confirm whether global cross-process priority is required.

2. **“The pipeline render takes the lock” is too coarse; if it means the whole job, editor preemption deadlocks.**
   What goes wrong: `_run` can run for many minutes across transcript/script/captions/render. If the worker acquires the machine lock at the start of `_run` and only releases it in `_worker`’s `finally`, then when the job reaches a safe point and pauses for the editor, the worker still holds the lock. The editor can never get it, and the “Paused for the editor” state is a lie.
   Fix: acquire the GPU lock only around actual GPU-heavy work (each render/Remotion/WanGP/still-generation stage), not the whole job. Release it at every stage boundary and at every safe point. Non-GPU stages must not hold the lock.

3. **The current edit routes hard-refuse while *any* job is `studio.current`, which prevents the new editor UX.**
   What goes wrong: `edit_chat`, `edit_act`, and `make_edit` immediately return 409 when `studio.current` is set. The design says the editor should open, show “A render is on the runway,” re-check every few seconds, and then proceed. As written, the popup could not even fetch/open its session while a job is in transcript/script stage.
   Fix: remove the blanket `if studio.current` guards. Editor session state and chat/read-only actions should be allowed. Only actual GPU-mutating actions (`preview`, `apply`, `rerender`, `undo`) should wait for the lock and return a pending/waiting response.

4. **`edit_all/undo` and `edit_all/rerender` are not guarded and are not session-aware.**
   What goes wrong: `edit_all/undo` can modify `output/*.prev` and edit history while a render is using those files. `edit_all/rerender` just calls `studio.rerender`, which queues the job but does not carry editor priority, session ownership, or a lock. Concrete scenario: an editor session holds the lock and clicks “Full re-render”; `rerender` queues the job; the single worker then waits for the same lock the editor is holding, deadlocking.
   Fix: all edit mutations go through the editor session. `undo` must wait for the lock or be rejected when no session owns the job. `rerender` must run as work owned by that editor session (or the session must temporarily hand the lock to the queued re-render), not as an independent queue item.

5. **Continuous editor lock ownership conflicts with the single queue worker.**
   The design says the editor session holds the lock for up to 15 minutes of inactivity. But full re-renders and applies run inside the same process’s queue/wrapper. If the editor holds the lock continuously, the worker cannot do the editor’s own re-render. Concrete scenario: editor active, lock held by `editor:<jid>`; `studio.rerender` enqueues the job; `_worker` tries to acquire `gpu_lock` and waits forever.
   Fix: either make the lock reentrant for the same owner (`editor:<jid>`) so the queue worker can enter on behalf of that editor, or change the semantics so the editor holds a *priority reservation* rather than the raw GPU lock between edits, acquiring the raw lock only for the duration of each apply/render. I recommend the second: it is simpler and avoids a 15-minute starvation window.

6. **There is no state for “automatically resume this job when the editor releases.”**
   Current pause is manual: `_run` catches `debug.Paused` and saves `status="paused"`; only a user pressing Resume/Continue calls `studio.resume`. If we pause a running job for the editor, nothing will automatically requeue it when the editor closes. Worse, if the job had been paused manually before the editor opened, auto-resuming it would be wrong.
   Fix: add `pause_reason` (`"user"` or `"editor"`). On editor release, scan for jobs with `status="paused"` and `pause_reason="editor"` and requeue only those. User pauses must remain manual.

7. **`studio.current`/`_worker` do not model “waiting for GPU.”**
   What goes wrong: if a worker blocks on the lock, `self.current` is still that job, but the job’s card may show `running`. There is no `wait_reason` or `wait_since` in state. The design asks for “Waiting: editor in use” / “GPU busy: QC.” With the current state shape this is impossible to display accurately.
   Fix: add `wait_reason`, `wait_since`, and optionally `wait_owner` to job state. Set them immediately before entering a lock wait and clear them after acquisition. Do not overload `studio.current` as “GPU busy.”

8. **Long stages have no safe point inside, and there is no estimated-time data for the runway message.**
   The design wants “stage X, about N min left.” The current job state has `stage`, but no `stage_start`, per-stage expected duration, or progress. Concrete scenario: editor opens during a 15-minute assemble; the UI can say only “assemble,” not “about 12 min left.”
   Fix: record `stage_start` when entering each stage and maintain a small per-stage expected-duration map. If unknown, show the stage and a conservative “up to N min” bound.

9. **One editor session per job cannot be enforced with an in-memory dict across multiple processes.**
   The app runs as 42021, 42022, etc. Scenario: the same job is opened on both ports; each process creates its own in-memory session, and both can edit/apply to the same workspace. The design says “one editor session per job, kept server-side,” but in-memory per process does not provide that.
   Fix: persist the editor session state in the job directory (`<job>/editor_session.json`) and guard it with a small cross-process lock (either the GPU lock as `editor:<jid>` or a separate `editor_session.lock`). Opening a job must load the existing session, not create a duplicate.

10. **The 15-minute idle timeout can release the GPU lock while an apply is still running.**
    `edit.start_apply` runs the actual apply in a daemon thread. If the idle timer is based only on last chat/open action, it can fire while the apply thread is still writing files. Releasing the lock at that moment lets another render start and corrupt/interleave the edit.
    Fix: track active apply/re-render count in the editor session. The idle checker must not pause/release while an apply is in flight. `start_apply` must increment in `finally` decrement, and only then can the session idle-release.

11. **A lock file with only PID/existence has a stale-cleanup race.**
    If “dead holder counts as free” is implemented by deleting the lock file when the PID is dead, two processes can both see the dead PID, both delete/recreate, and one can delete the other’s live lock. Scenario: A checks stale PID, B checks stale PID; A deletes and creates a new live lock; B deletes A’s new lock.
    Fix: use an OS-level byte-range lock (`msvcrt.locking` on Windows) as the source of truth. It is automatically released by the OS when the holder process dies, so there is no stale-file deletion race. The JSON metadata in the lock file is only for display/status; `status()` must attempt the OS lock, not simply parse and trust the JSON.

12. **The external WanGP watchdog does not yet know about the lock.**
    The watchdog is a separate PowerShell script. The design says it must never unload while the lock is held, but nothing currently tells it how to check. If it simply checks “is WanGP idle,” it can unload mid-stage or while the editor holds the lock.
    Fix: provide a tiny CLI/helper (`python -m studio.gpu_lock status` or `scripts/gpu_lock_status.py`) and have the watchdog invoke it. It must use the real OS lock check, not just file existence.

13. **Newsroom priority is not represented in `create` or job state.**
    `create` has no `priority` argument. Newsroom can send an extra field, but Video Studio has nowhere to store it. Without this, the `PriorityQueue` cannot distinguish Newsroom from hand jobs.
    Fix: add `priority` (default 3 for hand/manual, 2 from Newsroom, editor-owned work uses 1 internally) to job state and to `create`. Preserve priority across `resume`, `approve`, `continue_visuals`, `rerender`, and automatic retries.

14. **Changing `self.q` to a priority queue requires touching every enqueue/dequeue site.**
    The current queue is FIFO with bare `jid`. If we switch to `queue.PriorityQueue`, `create`, `approve`, `continue_visuals`, `rerender`, `resume`, and the 60-second retry timer all still call `self.q.put(jid)`, and `_worker` does `jid = self.q.get()`. The worker would receive a tuple and pass it as a job id.
    Fix: add `Studio._enqueue(jid)`/`_dequeue()` helpers that use `(priority, seq, jid)` with a monotonically increasing sequence, and update every call site.

15. **`rerender` deletes build files before it owns the lock.**
    `rerender` immediately deletes `build/sec_*.mp4` and edit history before the job is actually queued/taken. Scenario: the same target is still being rendered or a different process is in the middle of a stage; the deletion races the render.
    Fix: defer destructive cleanup until the job is actually about to re-run under the GPU lock, or perform cleanup inside the render stage’s lock scope. Request time should be pure state change only.

16. **A second editor session while another job is already being edited is unspecified.**
    The design says “one editor session per job,” but not whether there can be multiple active editor sessions for different jobs. Two editor sessions cannot both hold the GPU lock. Concrete scenario: edit job A, leave it open; open job B. Both are priority 1. Which one preempts the other?
    Fix/decision needed: I recommend exactly one *machine-wide active editor* (the holder of the GPU lock as `editor:<jid>`), regardless of job. Other editor popups may open for read-only/chat but their apply actions wait with “editor in use.” Tariq should confirm.

17. **Multiple processes sharing `jobs_dir` have no job-level lease.**
    If the live and test copies share the same `jobs_dir`, “Resume” from either port can enqueue the same `jid`; two workers can run the same job in parallel. The GPU lock serializes only GPU sections, not file writes.
    Fix: add a per-job run lease (`run_pid`, `run_host`, `run_start`) and only allow one process to run the job at a time, or restrict pipeline processing to one production process while test copies use a separate jobs directory. This is broader than the GPU lock but required by the multi-process design.

---

2. **Implementation plan**

**New module: `app/studio/gpu_lock.py`**
- Path: from `config.load()["gpu_lock_file"]`, default `F:/video-studio/gpu.lock`, plus `F:/video-studio/gpu.lock.json` for metadata.
- Use a one-byte OS lock file and `msvcrt.locking`:
  - `acquire(owner, kind, priority, reason, timeout=None)` opens `gpu.lock` in binary update mode, ensures one byte exists, then tries `LK_NBLCK`.
  - On success, it writes JSON metadata to `gpu.lock.json`: `holder.owner`, `holder.kind` (`render`, `editor`, `qc`, `test`), `holder.priority`, `holder.pid`, `holder.host`, `holder.since`, `holder.reason`.
  - Returns a `Lease` object. `Lease.release()` writes `{"holder": null}` while still holding the OS lock, flushes, then calls `LK_UNLCK` and closes.
  - `status()` performs a non-blocking OS lock. If it succeeds, it returns `held=False` (the lock is free, regardless of stale JSON). If it fails, returns `held=True` plus the current metadata.
  - `held(...)` is a context manager for use around GPU-heavy work.
- The OS lock is the source of truth; it is released automatically if the process dies. Metadata may be stale after a crash, but the next acquirer overwrites it.

**Pipeline changes: `app/studio/pipeline.py`**
- Change `self.q = queue.Queue()` to `queue.PriorityQueue()` and add `self._q_seq = 0`.
- Add `Studio._enqueue(jid, priority=None)` and update `_worker` to unpack `(_, _, jid)`.
- `create(..., priority=3, ...)`: store `priority` in job state. Newsroom will POST `priority=2`; hand jobs default to 3.
- Preserve priority in:
  - `approve`
  - `continue_visuals`
  - `rerender`
  - `resume`
  - the 60-second automatic retry timer
- Add state fields: `priority`, `wait_reason`, `wait_since`, `pause_reason`, `stage_start`, `stage_eta`.
- Replace hardware-heavy stage bodies with:
  ```python
  with gpu_lock.held(f"render:{jid}:{stage}", kind="render", priority=priority, reason=f"GPU busy: {stage}"):
      # existing GPU stage body
  ```
  Do not hold this lock across transcript, script, non-GPU review, or other CPU-only sections.
- Add `Studio.request_pause(jid, reason="user", editor_jid=None)`:
  - Save `pause_req=True`.
  - Save `pause_reason` only if it is not already a user pause.
- In `_run`’s `debug.Paused` handler:
  - Existing cancel logic stays first.
  - If `pause_reason == "editor"`, save:
    - `status="paused"`
    - `pause=info`
    - `pause_reason="editor"`
    - `wait_reason="Paused for the editor"`
    - `pause_req=False`
  - Do not require manual Resume for this case.
- Add an editor-release hook, e.g. `Studio._on_editor_released()`:
  - Scans jobs for `status == "paused"` and `pause_reason == "editor"`.
  - Calls `_enqueue(jid)` for each.
  - Does not touch `pause_reason == "user"`.
- Add `stage_start`/`stage_eta` updates around each stage. If no estimate exists, return a conservative `up_to_seconds` by stage.
- In `rerender`, remove the immediate `build/sec_*.mp4` deletion; move it into the re-render stage while the GPU lock is held.

**Editor session: new module `app/studio/editor_session.py`**
- State file per job: `<job_dir>/editor_session.json`.
- Suggested fields:
  ```json
  {
    "jid": "20261028_201000",
    "open_beat": "003",
    "ticked": ["cand1", "cand2"],
    "draft": "the chat draft",
    "fit": "fill",
    "pending_edits": [
      {"beat": "003", "cands": ["cand1"], "fit": "fill"}
    ],
    "last_activity": 1761696000.0,
    "active_applies": 0,
    "status": "active",
    "updated_at": 1761696000.0
  }
  ```
- `EditorSessionManager`:
  - `open(jid)`: load from disk or create. If a live session already exists, return it with `already_open=True`; never create a second session for the same job.
  - `touch(state_patch=None)`: update `last_activity`, optionally merge state changes, persist atomically.
  - `start_apply()` / `finish_apply()`: increment/decrement `active_applies`.
  - `should_idle_release()`: `now - last_activity > 15*60` and `active_applies == 0`.
- Single active editor globally:
  - The GPU lock owner is `editor:<jid>`.
  - Another editor can open in read-only/chat mode, but its apply/preview/rerender actions return `wait_reason="editor in use"`.
  - I recommend one active editor machine-wide; multiple active editors should be a waiter, not concurrent owners.

**Server routes: `app/server.py`**
- Remove blanket `if studio.current` guards from `edit_chat`, `edit_act`, and `make_edit`.
- New endpoints:
  - `GET /api/jobs/<jid>/editor`
    - Returns session state, current lock holder, `runway` info, current pipeline stage, estimated remaining time, and whether a running job has been asked to pause.
  - `POST /api/jobs/<jid>/editor/open`
    - Creates/loads the session, calls `studio.request_pause(reason="editor", editor_jid=jid)` if a job is running, and returns the runway state.
  - `POST /api/jobs/<jid>/editor/state`
    - Saves open beat, ticked candidates, chat draft, fit choice, pending edits.
  - `POST /api/jobs/<jid>/editor/heartbeat`
    - Updates `last_activity`.
  - `POST /api/jobs/<jid>/editor/close`
    - Saves state, releases the lock, immediately triggers `_on_editor_released()`.
- `edit_act`/`make_edit`:
  - If the session owns the lock, call the existing edit functions.
  - If the lock is held elsewhere, return 409/202 with `wait_reason` rather than blocking the HTTP request.
- `edit_all/rerender`:
  - Require an editor session.
  - Mark the re-render as editor-owned and proceed under the session’s lock/reservation, not as an independent low-priority queue item.
- `edit_all/undo`:
  - Must run through the same session/lock gate as apply.

**Edit apply changes: `app/studio/edit.py`**
- `start_apply` signature should accept/derive the editor session id.
- It must call `session.start_apply()` before starting the daemon thread and `session.finish_apply()` in `finally`.
- If it cannot acquire the GPU lock immediately because the editor session does not already own it, return a wait reason instead of starting the thread.
- Preserve the existing `_busy` per-job guard to keep one apply per job at a time.

**UI: `app/static/index.html`**
- The popup should poll `GET /api/jobs/<jid>/editor` every few seconds.
- Show:
  - “A render is on the runway — your edit starts at its next safe point (stage X, about N min left)” when appropriate.
  - “Waiting: editor in use” / “GPU busy: QC” / “Paused for the editor” states.
- Send state updates and a heartbeat while the popup is open.
- On 15-minute server-side pause, show “Edit paused — Resume.” Resume calls the open endpoint and reloads the saved session state.
- For full re-render/undo buttons, handle pending/waiting responses gracefully.

**Watchdog**
- Add `scripts/gpu_lock_status.py` or `python -m studio.gpu_lock status`.
- It must output JSON with `{"held": false}` when lock free and `{"held": true, "holder": {...}}` when held.
- The external PowerShell watchdog must call this helper before unloading WanGP and abort if `held` is true.
- Do not do any model unload while `held` is true.

---

3. **Questions for Tariq**

1. Should Newsroom jobs preempt a running hand job at its next safe point, or only jump the queue ahead of queued hand jobs? I recommend queue-order only, except for editor sessions.
2. Should there be only one machine-wide active editor at a time, or can two different jobs have open editor sessions simultaneously? If both are allowed, how should two priority-1 editor sessions arbitrate the GPU lock?
3. Should the editor hold the actual GPU lock for the whole active session (up to 15 idle minutes), or release it between individual apply/re-render operations and hold only a priority reservation? I recommend release-between-actions to avoid starving the queue and to simplify the worker interaction.
4. Is global cross-process priority required for test copies, or is it acceptable that test copies only take the machine lock as a barrier and do not participate in Newsroom/hand ordering?
5. If a process is alive but hung while holding the lock, should there ever be a forced takeover, or is “only dead holders count as free” the final rule?
6. When the editor opens while a job is in a non-GPU stage such as transcript/script, should that job be paused immediately anyway, or only block before its next GPU stage? I recommend the latter.
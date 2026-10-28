# Task: Publisher `POST /delete` (YouTube Publisher, Python/Flask + Playwright)

Repo: youtube-publisher-public. Files: `app.py` (Flask routes), `publisher_logic.py` (records), `studio_automation.py`
(Playwright drives YouTube Studio), `youtube_publisher.py` (helpers). Records are JSON files, not a database:
`uploads/<channel>/<job>/published.json` (or `published_<kind>.json`), one per job+kind, with keys
channel, job, kind, title, timestamp, metadata, video_id, url. `records()` already skips records with `"deleted": true`.

## Contract (the Newsroom caller is already written against this)
POST /delete  body {"channel", "job", "kind", "video_id"}  ->  200 {"deleted": true, "video_id": "<id>"}
Errors: {"error": "..."} with 4xx (the existing ValueError handler gives 400).
1. Find the published record for channel+job+kind (scan the same files `records()` reads, but INCLUDING deleted ones).
   No record -> 404. video_id in body must equal the record's video_id, else 400 (never delete a different video).
2. IDEMPOTENT: record already `"deleted": true` -> return 200 {"deleted": true} without opening Studio.
3. Otherwise delete that video in YouTube Studio on that channel (new function in studio_automation.py, below),
   then mark the record: deleted=true, deleted_at=<ISO time>, keep every other field. Never remove or rename files.
4. If Studio shows the video is already gone (its edit page says it is unavailable / redirects to the content list),
   treat as deleted (idempotent) and mark the record.
5. Reuse the same locks as `worker()` (browser_lock + profiles/.main-upload.lock) and refuse while any publish task is
   active. Run synchronously inside the request (a delete is short); timeout budget about 3 minutes.
6. Never delete anything not named by the call. No other behaviour changes.

## New Studio function — please write it
`delete_video(cfg, channel_name, video_id, folder, emit, dry_run=False)` in studio_automation.py, same style as
`publish()`: persistent Chrome context from cfg['chrome_profile'], the same off-screen window args, checkpoint
screenshots into `folder`, the SAME channel switch + `#entity-name` verification as publish(). Then open
`https://studio.youtube.com/video/<id>/edit`, and delete through Studio's UI (three-dot / options menu on the edit
page -> "Delete forever" -> tick the "I understand that deleting is permanent" checkbox -> final Delete button).
I cannot give you exact Studio selectors: write them with `get_by_role`/`get_by_text` like the existing code, keep
every selector in one small block at the top of the function so I can correct them against the real screens.
`dry_run=True` must do everything EXCEPT the final Delete click (stop with the confirm dialog open, screenshot it,
close the dialog, return {"dry_run": true}). After a real delete, verify: reload the edit page and confirm it no longer
shows the video. Return {"deleted": true, "already_gone": bool}.
Add `?dry_run=1` support to the route (dry run never marks the record).

## Also
- Unit tests (unittest, same style as tests/) for the route with `studio_automation.delete_video` mocked:
  happy path marks the record; already-deleted returns 200 without calling Studio; video_id mismatch 400;
  no record 404; dry_run does not mark; active publish task refused.

## Existing code you must fit (excerpts)

### app.py lines 1-34
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

```

### app.py lines 128-195
```python
def worker(task, data, mode):
    folder = task['folder']
    try:
        if not browser_lock.acquire(blocking=False):
            raise ValueError('Another publish is using the shared Chrome profile. Try again after it finishes.')
        try:
            profile_lock = ROOT / 'profiles' / '.main-upload.lock'
            fd = os.open(profile_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            try:
                cfg = logic.config()
                backend.load_global(require_profile=True)
                _, channel = backend.load_channel(data['channel'])
                task['status'] = 'running'
                result = backend.upload_from_form(data, logic.assets(data['job'], data['kind'])[0], logic.thumbnail_path(data),
                                 cfg, channel['youtube_channel_name'], folder,
                                 lambda message, shot=None: update(task, message, shot),
                                 lambda: task.get('cancel_requested', False), mode)
                record = dict(channel=data['channel'], job=data['job'], kind=data['kind'],
                              title=data['title'], timestamp=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                              metadata=data, **result)
                destination = logic.destination(data['channel'], data['job'])
                name = 'published.json'
                if (destination / name).exists() and backend.read_json(destination / name).get('kind') != data['kind']:
                    name = f"published_{data['kind']}.json"
                backend.write_json(destination / name, record)
                (destination / f"youtube_{data['kind']}_url.txt").write_text(result['url'] + '\n', encoding='utf-8')
                task.update(status='complete', result=record)
                update(task, 'Upload complete.' + (' Linking needs manual completion.' if result.get('link_error') else ''))
            finally:
                profile_lock.unlink(missing_ok=True)
        finally:
            browser_lock.release()
    except Exception as error:
        summary = str(error).splitlines()[0]
        task.update(status='cancelled' if task.get('cancel_requested') else 'error', error=summary)
        update(task, summary)
        logging.exception('Publish failed')

@app.post('/publish')
def submit():
    body = request.get_json()
    data = logic.finalize(body)
    mode = body.get('mode', 'new')
    if mode not in ('new', 'resume', 'restart'):
        raise ValueError('Unknown retry mode')
    destination = logic.destination(data['channel'], data['job'])
    destination.mkdir(parents=True, exist_ok=True)
    if any(r.get('channel') == data['channel'] and r.get('job') == data['job'] and r.get('kind') == data['kind'] for r in logic.records()) and mode != 'resume':
        raise ValueError('This video already has a published record. Use Retry to finish linking or edit it in Studio.')
    active = [t for t in tasks.values() if t['status'] in ('queued', 'running', 'waiting')]
    if active:
        raise ValueError('Another publish is in progress.')
    state = destination / f"automation_{data['kind']}.json"
    if state.exists() and mode == 'new':
        raise ValueError('Previous upload state exists. Use Retry from this step or explicitly Restart upload.')
    if mode == 'restart' and not body.get('confirm_restart'):
        raise ValueError('Confirm possible duplicate upload before restarting.')
    backend.write_json(destination / 'draft.json', data)
    task_id = uuid.uuid4().hex
    folder = destination / 'tasks' / task_id
    folder.mkdir(parents=True)
    task = dict(id=task_id, status='queued', events=[], folder=folder)
    tasks[task_id] = task
    update(task, 'Metadata validated. Starting publisher...')
    threading.Thread(target=worker, args=(task, data, mode), daemon=True).start()
    return jsonify(task_id=task_id), 202

```

### publisher_logic.py lines 41-52
```python
def records():
    result, seen = [], set()
    for path in (ROOT / 'uploads').glob('*/*/published*.json'):
        try:
            record = backend.read_json(path)
            if record.get('deleted') or record.get('video_id') in seen or not record.get('video_id'):
                continue
            seen.add(record['video_id'])
            result.append(record)
        except (ValueError, OSError):
            continue
    return result
```

### publisher_logic.py lines 115-117
```python
def destination(channel, job):
    return ROOT / 'uploads' / identifier(channel).lower() / identifier(job)

```

### studio_automation.py lines 1-8
```python
"""Playwright-only Studio upload and linking, with bounded recovery and screenshots."""
import re
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeoutError
import youtube_publisher as backend

```

### studio_automation.py lines 21-41
```python
def publish(data, video, thumbnail, cfg, channel_name, folder, emit, cancelled, mode='new'):
    state_path = folder.parents[1] / f"automation_{data['kind']}.json"
    state = backend.read_json(state_path) if state_path.exists() and mode != 'restart' else {}
    if mode == 'restart' and state_path.exists():
        backend.write_json(state_path.with_name(f'automation_{data["kind"]}_{int(time.time())}.json'), backend.read_json(state_path))
    state.update(channel=data['channel'], job=data['job'], kind=data['kind'])
    state.pop('error', None)
    sequence = 0
    with sync_playwright() as pw:
        args = ['--lang=en-US']
        if not cfg.get('playwright_headless', False) and cfg.get('offscreen_window', True):
            # a real Chrome window (YouTube Studio is reliable that way) parked off the screen, so nothing pops up
            args += ['--window-position=-32000,-32000', '--window-size=1440,1000']
        context = pw.chromium.launch_persistent_context(cfg['chrome_profile'], channel='chrome',
                    headless=cfg.get('playwright_headless', False), locale='en-US', args=args)
        page = context.new_page()
        page.set_default_timeout(20000)
        def checkpoint(message):
            nonlocal sequence
            if cancelled():
                raise RuntimeError('Publish cancelled. Any existing draft is preserved for recovery.')
```

### studio_automation.py lines 204-212
```python
        try:
            action('Navigating to YouTube Studio...', lambda: page.goto('https://studio.youtube.com/', wait_until='domcontentloaded'))
            click(page.locator('ytcp-app #avatar-btn'), 'Opening channel switcher...')
            click(page.get_by_text('Switch account', exact=True), 'Switching to ' + channel_name + ' channel...')
            entries = page.locator('ytd-account-item-renderer').filter(has=page.get_by_text(channel_name, exact=True))
            expect(entries).to_have_count(1)
            click(entries, 'Selecting ' + channel_name + '...')
            expect(page.locator('ytcp-navigation-drawer #entity-name')).to_have_text(channel_name, timeout=60000)
            checkpoint('Channel verified: ' + channel_name)
```

### studio_automation.py lines 372-376
```python
            remember()
            checkpoint('Upload failed: ' + str(error).splitlines()[0])
            raise
        finally:
            context.close()
```

### youtube_publisher.py lines 93-100
```python
def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

```

One-line summary: add an idempotent `POST /delete` route that finds the published record (including already-deleted records), refuses during active publishes, calls a new `studio_automation.delete_video()`, and marks the record `deleted=true` unless `?dry_run=1`.

```diff
--- a/publisher_logic.py
+++ b/publisher_logic.py
@@ -52,6 +52,18 @@ def records():
             continue
     return result
 
+def find_record(channel, job, kind):
+    """Return (path, record) for channel+job+kind, including deleted records."""
+    for path in (ROOT / 'uploads').glob('*/*/published*.json'):
+        try:
+            record = backend.read_json(path)
+        except (ValueError, OSError):
+            continue
+        if record.get('channel') == channel and record.get('job') == job and record.get('kind') == kind:
+            return path, record
+    return None, None
+
 
 def destination(channel, job):
     return ROOT / 'uploads' / identifier(channel).lower() / identifier(job)
```

```diff
--- a/app.py
+++ b/app.py
@@ -195,6 +195,59 @@ def submit():
     threading.Thread(target=worker, args=(task, data, mode), daemon=True).start()
     return jsonify(task_id=task_id), 202
 
+@app.post('/delete')
+def delete_video_route():
+    body = request.get_json(silent=True) or {}
+    for key in ('channel', 'job', 'kind', 'video_id'):
+        if not body.get(key):
+            raise ValueError(f'Missing {key}')
+
+    record_path, record = logic.find_record(body['channel'], body['job'], body['kind'])
+    if record_path is None:
+        return jsonify(error='No published record for this channel, job, and kind.'), 404
+    if record.get('video_id') != body['video_id']:
+        raise ValueError('video_id does not match the published record.')
+    if record.get('deleted'):
+        return jsonify(deleted=True, video_id=record['video_id'])
+
+    active = [t for t in tasks.values() if t['status'] in ('queued', 'running', 'waiting')]
+    if active:
+        raise ValueError('A publish task is active. Try again after it finishes.')
+
+    dry_run = request.args.get('dry_run') == '1'
+
+    if not browser_lock.acquire(blocking=False):
+        raise ValueError('Another publish is using the shared Chrome profile. Try again after it finishes.')
+    try:
+        profile_lock = ROOT / 'profiles' / '.main-upload.lock'
+        try:
+            fd = os.open(profile_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
+            os.close(fd)
+        except FileExistsError:
+            raise ValueError('Another publish is using the shared Chrome profile. Try again after it finishes.')
+
+        try:
+            cfg = logic.config()
+            backend.load_global(require_profile=True)
+            _, channel = backend.load_channel(body['channel'])
+            folder = logic.destination(body['channel'], body['job']) / 'tasks' / f"delete_{uuid.uuid4().hex}"
+            folder.mkdir(parents=True, exist_ok=True)
+
+            import studio_automation as studio
+            result = studio.delete_video(
+                cfg, channel['youtube_channel_name'], body['video_id'], folder,
+                lambda message, shot=None: None, dry_run=dry_run)
+
+            if dry_run:
+                return jsonify(deleted=False, dry_run=True, video_id=body['video_id'])
+
+            updated = dict(record)
+            updated['deleted'] = True
+            updated['deleted_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
+            backend.write_json(record_path, updated)
+            return jsonify(deleted=True, video_id=body['video_id'])
+        finally:
+            profile_lock.unlink(missing_ok=True)
+    finally:
+        browser_lock.release()
+
```

```diff
--- a/studio_automation.py
+++ b/studio_automation.py
@@ -376,6 +376,135 @@ def publish(data, video, thumbnail, cfg, channel_name, folder, emit, cancelled,
             raise
         finally:
             context.close()
+
+def delete_video(cfg, channel_name, video_id, folder, emit, dry_run=False):
+    """Delete a video from YouTube Studio, then verify that it is gone."""
+    open_studio_url = 'https://studio.youtube.com/'
+    edit_url_template = 'https://studio.youtube.com/video/{video_id}/edit'
+    avatar_selector = 'ytcp-app #avatar-btn'
+    switch_account_text = 'Switch account'
+    entity_name_selector = 'ytcp-navigation-drawer #entity-name'
+    options_button_role_name = 'Options'
+    options_button_selector = 'button[aria-label="Options"]'
+    delete_forever_text = 'Delete forever'
+    understand_checkbox_text = 'I understand that deleting is permanent'
+    final_delete_button_text = 'Delete'
+    unavailable_texts = ('Video unavailable', 'This video has been removed')
+
+    folder.mkdir(parents=True, exist_ok=True)
+    sequence = 0
+
+    def already_gone(page):
+        if not page.url.startswith('https://studio.youtube.com/video/'):
+            return True
+        for text in unavailable_texts:
+            if page.get_by_text(text, exact=False).count() > 0:
+                return True
+        return False
+
+    with sync_playwright() as pw:
+        args = ['--lang=en-US']
+        if not cfg.get('playwright_headless', False) and cfg.get('offscreen_window', True):
+            args += ['--window-position=-32000,-32000', '--window-size=1440,1000']
+        context = pw.chromium.launch_persistent_context(
+            cfg['chrome_profile'], channel='chrome',
+            headless=cfg.get('playwright_headless', False), locale='en-US', args=args)
+        page = context.new_page()
+        page.set_default_timeout(20000)
+
+        def checkpoint(message):
+            nonlocal sequence
+            sequence += 1
+            safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', message).strip('_')[:60] or 'step'
+            shot = folder / f'{sequence:03d}_{safe}.png'
+            page.screenshot(path=str(shot))
+            emit(message, str(shot))
+
+        def click(locator, message):
+            locator.first.wait_for(state='visible', timeout=20000)
+            locator.first.click()
+            checkpoint(message)
+
+        try:
+            checkpoint('Navigating to YouTube Studio...')
+            page.goto(open_studio_url, wait_until='domcontentloaded')
+            click(page.locator(avatar_selector), 'Opening channel switcher...')
+            click(page.get_by_text(switch_account_text, exact=True), 'Switching to ' + channel_name + ' channel...')
+            entries = page.locator('ytd-account-item-renderer').filter(has=page.get_by_text(channel_name, exact=True))
+            expect(entries).to_have_count(1)
+            click(entries, 'Selecting ' + channel_name + '...')
+            expect(page.locator(entity_name_selector)).to_have_text(channel_name, timeout=60000)
+            checkpoint('Channel verified: ' + channel_name)
+
+            edit_url = edit_url_template.format(video_id=video_id)
+            checkpoint('Opening video edit page...')
+            page.goto(edit_url, wait_until='domcontentloaded')
+            page.wait_for_timeout(1500)
+
+            if already_gone(page):
+                checkpoint('Video already unavailable in Studio')
+                return {'deleted': True, 'already_gone': True}
+
+            options_button = page.get_by_role('button', name=options_button_role_name, exact=True)
+            if options_button.count() == 0:
+                options_button = page.locator(options_button_selector)
+            click(options_button, 'Opening video options menu...')
+
+            delete_item = page.get_by_text(delete_forever_text, exact=True)
+            if delete_item.count() == 0:
+                delete_item = page.get_by_role('menuitem', name=delete_forever_text, exact=True)
+            click(delete_item, 'Choosing Delete forever...')
+
+            checkbox = page.get_by_role('checkbox', name=understand_checkbox_text, exact=True)
+            if checkbox.count() == 1:
+                checkbox.check()
+            else:
+                checkbox_label = page.get_by_text(understand_checkbox_text, exact=True)
+                if checkbox_label.count() == 0:
+                    raise RuntimeError('Could not find the permanent deletion confirmation checkbox.')
+                checkbox_label.first.click()
+            checkpoint('Confirmed permanent deletion checkbox')
+
+            if dry_run:
+                checkpoint('Dry run: delete confirmation dialog shown')
+                close_button = page.get_by_role('button', name='Close', exact=True)
+                if close_button.count():
+                    close_button.first.click()
+                else:
+                    page.keyboard.press('Escape')
+                checkpoint('Dry run: closed delete confirmation dialog')
+                return {'deleted': False, 'already_gone': False, 'dry_run': True}
+
+            dialog = page.get_by_role('dialog')
+            if dialog.count():
+                confirm_button = dialog.last.get_by_role('button', name=final_delete_button_text, exact=True)
+            else:
+                confirm_button = page.get_by_role('button', name=final_delete_button_text, exact=True)
+            if confirm_button.count() == 0:
+                confirm_button = page.locator('ytcp-button').filter(has_text=final_delete_button_text).last
+            checkpoint('Clicking final Delete button...')
+            confirm_button.click()
+
+            page.wait_for_timeout(3000)
+            checkpoint('Delete submitted; verifying the edit page no longer shows it...')
+            page.goto(edit_url, wait_until='domcontentloaded')
+            if already_gone(page):
+                checkpoint('Verified video is gone')
+                return {'deleted': True, 'already_gone': False}
+            raise RuntimeError('Delete verification failed: Studio still shows the video.')
+        except Exception as error:
+            checkpoint('Delete failed: ' + str(error).splitlines()[0])
+            raise
+        finally:
+            context.close()
```

```diff
--- /dev/null
+++ b/tests/test_delete.py
@@ -0,0 +1,131 @@
+import tempfile
+import unittest
+from contextlib import ExitStack
+from pathlib import Path
+from unittest.mock import patch
+
+import app as app_module
+
+
+class DeleteRouteTest(unittest.TestCase):
+    def setUp(self):
+        app_module.tasks.clear()
+        self.tmp = tempfile.TemporaryDirectory()
+        self.addCleanup(self.tmp.cleanup)
+        self.client = app_module.app.test_client()
+        self.path = Path(self.tmp.name) / 'published.json'
+        self.record = {
+            'channel': 'news',
+            'job': 'job-1',
+            'kind': 'short',
+            'video_id': 'vid-123',
+            'title': 'Test video',
+            'timestamp': '2026-01-01T00:00:00+0000',
+        }
+        self.body = {
+            'channel': 'news',
+            'job': 'job-1',
+            'kind': 'short',
+            'video_id': 'vid-123',
+        }
+
+    def _base(self, find_result, delete_result=None, active=False):
+        stack = ExitStack()
+        mocks = {}
+        mocks['find_record'] = stack.enter_context(patch('publisher_logic.find_record', return_value=find_result))
+        mocks['config'] = stack.enter_context(patch('publisher_logic.config', return_value={}))
+        mocks['destination'] = stack.enter_context(patch('publisher_logic.destination', return_value=Path(self.tmp.name) / 'dest'))
+        mocks['load_global'] = stack.enter_context(patch('youtube_publisher.load_global'))
+        mocks['load_channel'] = stack.enter_context(patch('youtube_publisher.load_channel', return_value=(None, {'youtube_channel_name': 'Test Channel'})))
+        mocks['write_json'] = stack.enter_context(patch('youtube_publisher.write_json'))
+        mocks['delete_video'] = stack.enter_context(patch('studio_automation.delete_video', return_value=delete_result or {'deleted': True, 'already_gone': False}))
+        mocks['lock_acquire'] = stack.enter_context(patch.object(app_module.browser_lock, 'acquire', return_value=True))
+        mocks['lock_release'] = stack.enter_context(patch.object(app_module.browser_lock, 'release'))
+        mocks['os_open'] = stack.enter_context(patch('app.os.open', return_value=7))
+        mocks['os_close'] = stack.enter_context(patch('app.os.close'))
+        mocks['unlink'] = stack.enter_context(patch('pathlib.Path.unlink'))
+        app_module.tasks.clear()
+        if active:
+            app_module.tasks['active-test'] = {'status': 'running'}
+        return stack, mocks
+
+    def test_happy_path_marks_record(self):
+        stack, mocks = self._base((self.path, self.record), {'deleted': True, 'already_gone': False})
+        with stack:
+            response = self.client.post('/delete', json=self.body)
+
+        self.assertEqual(response.status_code, 200)
+        self.assertEqual(response.json, {'deleted': True, 'video_id': 'vid-123'})
+        mocks['delete_video'].assert_called_once()
+        written_path, written_record = mocks['write_json'].call_args.args
+        self.assertEqual(written_path, self.path)
+        self.assertTrue(written_record['deleted'])
+        self.assertEqual(written_record['video_id'], 'vid-123')
+        self.assertIn('deleted_at', written_record)
+
+    def test_already_deleted_is_idempotent(self):
+        record = dict(self.record, deleted=True)
+        stack, mocks = self._base((self.path, record))
+        with stack:
+            response = self.client.post('/delete', json=self.body)
+
+        self.assertEqual(response.status_code, 200)
+        self.assertEqual(response.json, {'deleted': True, 'video_id': 'vid-123'})
+        mocks['delete_video'].assert_not_called()
+        mocks['write_json'].assert_not_called()
+
+    def test_video_id_mismatch_is_400(self):
+        record = dict(self.record, video_id='other-video')
+        stack, mocks = self._base((self.path, record))
+        with stack:
+            response = self.client.post('/delete', json=self.body)
+
+        self.assertEqual(response.status_code, 400)
+        self.assertIn('video_id', response.json['error'])
+        mocks['delete_video'].assert_not_called()
+        mocks['write_json'].assert_not_called()
+
+    def test_no_record_returns_404(self):
+        stack, mocks = self._base((None, None))
+        with stack:
+            response = self.client.post('/delete', json=self.body)
+
+        self.assertEqual(response.status_code, 404)
+        mocks['delete_video'].assert_not_called()
+
+    def test_dry_run_does_not_mark_record(self):
+        stack, mocks = self._base((self.path, self.record), {'deleted': False, 'already_gone': False, 'dry_run': True})
+        with stack:
+            response = self.client.post('/delete?dry_run=1', json=self.body)
+
+        self.assertEqual(response.status_code, 200)
+        self.assertEqual(response.json, {'deleted': False, 'dry_run': True, 'video_id': 'vid-123'})
+        mocks['write_json'].assert_not_called()
+        self.assertTrue(mocks['delete_video'].call_args.kwargs['dry_run'])
+
+    def test_active_publish_task_is_refused(self):
+        stack, mocks = self._base((self.path, self.record), {'deleted': True}, active=True)
+        with stack:
+            response = self.client.post('/delete', json=self.body)
+
+        self.assertEqual(response.status_code, 400)
+        self.assertIn('active', response.json['error'].lower())
+        mocks['delete_video'].assert_not_called()
+        mocks['write_json'].assert_not_called()
+
+
+if __name__ == '__main__':
+    unittest.main()
```

How Claude should test it:
- Run the unit tests from the repo root:
  `python -m unittest tests.test_delete -v`
- Then, if there is a safe scratch record on the PC, test the dry-run path:
  `curl -X POST "http://127.0.0.1:<port>/delete?dry_run=1" -H "Content-Type: application/json" -d "{\"channel\":\"...\",\"job\":\"...\",\"kind\":\"short\",\"video_id\":\"...\"}"`
  and confirm the task folder under `uploads/<channel>/<job>/tasks/delete_*` has screenshots ending at the opened confirmation dialog, and the record is not marked deleted.

Anything unsure about:
- YouTube Studio DOM/selectors are best-effort because I cannot inspect the live Studio UI. I kept that block at the top of `delete_video()`: `options_button_selector`, menu text, checkbox text, final button text, and unavailable-text probes. Those are the values you or Claude should correct against the real Studio screens.
- `find_record()` returns the first matching `channel/job/kind` record. The existing worker normally prevents duplicate same-kind records, so that should be fine.

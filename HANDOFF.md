# HANDOFF — state at 2026-10-28 18:35 EDT (Claude standing down; Codex picks up)

Public repo: no keys, emails, phone numbers or document IDs here. PC paths are on Tariq's machine (F:).

## 1. The two-AI loop (live)
- `ai-exchange` repo: Claude writes `from_claude/question.md`; DeepSeek's reply lands in `to_claude/answer.md`.
- **Mailman** (PC, `F:\code\ai-exchange\mailman.py`, running): every 60 s pulls this repo; a NEW question (by sha256,
  see `archive\processed.txt`) goes to the DeepSeek API (`deepseek-v4-pro`) with `CONTEXT.md` + current date as the
  system briefing; reply pushed as `to_claude/answer.md`. Key from env `DEEPSEEK_API_KEY`, else the Windows vault
  entry the pipeline uses; never in a file. Git calls run in a hidden console with prompts disabled (an earlier
  CREATE_NO_WINDOW version hung silently). Start/stop: write `mailman-start` / `mailman-stop` to
  `F:\code\.restart-only`, touch `F:\code\.restart-request`. Log: `mailman.log`. Not started on reboot.
- **Watcher** (Claude's cloud workspace only): polls this repo every 5 min, wakes Claude when `to_claude/` changes.
  Codex does not need it; Codex can just read `to_claude/answer.md` after pushing a question.
- The DeepSeek API has NO internet: every question must contain the code it needs (see the two questions in history).
- After applying an answer, clear `from_claude/question.md` (commit) as README says.

## 2. Branches (nothing below is merged to live)
| Repo | Branch | What | Tests |
|---|---|---|---|
| youtube-publisher | `claude/publisher-delete` (531b509) | `POST /delete` per Koda's MSG 030 contract, `find_record`, Studio `delete_video(..., dry_run)`, `tests/test_delete.py` | 32/32 pass |
| youtube-publisher | `feature/unified-ui` (f06f0f0, on top of the delete branch) | Newsroom light theme, list panels (Ready / Published), shared popup `/player` (`templates/player.html`, `static/js/player.js`), port-based TEST mode | 32/32 pass |
| video-studio-test | `koda/light-theme-source-note` (5f644d8) | light theme + per-beat "Picture source" note | files ALREADY copied into live; see 4 |
| newsroom | `koda/light-theme-source-note` (c5a9e9b) | panels + popup (11266dd) + resubmit/move (c5a9e9b) | 11266dd is LIVE; c5a9e9b not |
Public mirrors (scrubbed): `*-public` repos, updated with `F:\code\public\mirror_public.sh <repo> <ref>` after every
push to origin. Never push origin history straight to public.

## 3. Running test copies on the PC
- **Publisher TEST** `http://127.0.0.1:42031` from `F:\code\pub-test` (branch `feature/unified-ui`, own logs, copied
  records only). Any non-GET request is refused 403 because the port is not the live 42030; TEST pill shown.
  Hooks: `pub-test-start` / `pub-test-stop`.
- **Video Studio TEST** `http://127.0.0.1:42022` from `F:\code\vs-branch` (own jobs folder). Hook `vs-branch-stop`.
- Live ports, never touch: Video Studio 42021, Publisher 42030, Newsroom 42040.

## 4. Open items, in order
1. **BUG (Publisher popup, published items):** "No published link was recorded" for e.g.
   `/player?job=source_LRdb8UmPnh0&kind=long&channel=moonshots_source&published=1`. NOT a JSON key mismatch: the
   record has channel/job/kind/video_id/url. Cause: `app.py` `/player` replaces a channel that has no
   `channel_configs/<name>.json` (moonshots_source has none) with the first channel (cuttv); `player.js`
   `renderPublishedLinks()` then filters records by that wrong channel. Fix: keep the requested channel when
   `published=1` (add it to the select as a read-only option), or match published records by job+kind+video_id.
2. **Publisher delete, Studio selectors unverified:** run a DRY RUN only (`POST /delete?dry_run=1`) on the LIVE port
   after Tariq approves; it stops before the final Delete click. Fix selectors in the block at the top of
   `delete_video()` from the screenshots in `uploads/<channel>/<job>/tasks/delete_*`. A real delete needs Tariq's
   explicit approval, a throwaway video, and a test channel.
3. **Video Studio unified UI:** same look + every beat-edit control in a popup with the scrubber (bigger rework than
   the Publisher). TEST badge by port; test copy on 42022. Not started.
4. **Video Studio restart:** the light-theme files are live since 2026-10-27 20:38 but the server was not restarted,
   so the per-beat source note is not served yet. Restart only when idle (`vs-restart-idle`); never kill a render.
5. Merges to live (Publisher branches, Newsroom c5a9e9b) wait for Tariq's word.

## 5. Standing rules (also in CONTEXT.md)
Never interrupt a render; never auto-publish; YouTube deletes need explicit approval; no permanent deletes (move to
`_to_delete`); never type passwords or bypass human-verification checks; no Google/Gemini image generation;
DeepSeek for scripts, no Anthropic API key; `qc.py` belongs to Koda; save outputs on F:.

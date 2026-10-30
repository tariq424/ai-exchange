# STATUS — updated by Claude after every round (sent to the reviewer with every question)

Last update: 2026-10-28 23:25 EDT

## BOARD.md — common page (Koda sync, 2026-10-30)
- BOARD.md in this repo is the single common page for Claude, Codex, DeepSeek and Koda: agreed design, current live state, the fixed-on-test vs pending ledger, merge-order status, open items, and standing rules. Read it before working. A claim not on the board is not agreed.
- Whoever finishes work updates BOARD.md's ledger and open items in the same commit round as their RESULT.
- PC-side task completed 2026-10-30: mailman reads CONTEXT.md + STATUS.md + BOARD.md fresh before each question. Missing/empty files prevent sending. Three offline tests verified the actual request payload and failure paths; no real question sent. No mailman process was running at verification; next normal launch loads the change. See BOARD open item 4 (closed), patches/mailman-board-briefing.patch and tests/test_mailman_briefing.py.

## Koda sync - 2026-10-29 (merge approved by Tariq)
- Tariq approved GO LIVE for the tested test-copy work on 2026-10-29. Full order: MERGE-ORDER.md in this repo (also posted to Claude as MSG 032 in the Claude-Koda exchange doc).
- Stages, in order: (1) Video Studio idle restart, source note verified live; (2) Publisher feature/unified-ui incl. /delete to live, delete DRY RUN only; (3) Video Studio popup beat editor to live; (4) GPU interlock + Newsroom newsroom=true + WanGP watchdog check, then the real apply-during-render test; (5) Newsroom resubmit/move to live, last, after stage 2 verifies.
- NOT approved: any real YouTube delete, any real move of a published video, any publishing. Those still need Tariq's separate explicit go and a throwaway video.
- Claude is at about 98% usage per Tariq. If the cap hits mid-merge: post STATUS here (stages done/undone, exact live state), then stop - Codex picks up the same order.
- Reviewer note: until this merge lands, the "Next" section below is the pre-approval state.

## Done (this evening)
- Publisher `POST /delete` + `delete_video(dry_run)` + tests — written by DeepSeek, applied by Claude
  (branch `claude/publisher-delete`, 531b509; all later fixes are on `feature/unified-ui`).
- Publisher unified UI (Newsroom theme, Ready/Published list panels, shared popup `/player`, port-based TEST mode)
  — DeepSeek patch, applied on `feature/unified-ui`. 32/32 tests pass. TEST copy live on 42031 (actions refused 403).
- Popup bug fixed (9960658): a published item on a channel with no `channel_configs` file (moonshots_source) kept
  being swapped for the first channel, so no record matched. Not a JSON key mismatch.
- Studio delete DRY RUN on a real private YouSocial video, nothing deleted (5458f1e). Verified selectors:
  three-dot menu item "Delete"; dialog "Permanently delete this video?"; checkbox "I understand that deleting this
  video is permanent…"; buttons "Cancel" / "Delete forever". Dry run stops before "Delete forever", presses Cancel.

- Video Studio beat editor in a popup (`/?job=<id>&popup=edit`) + TEST pill when port != 42021 — DeepSeek patch
  (bfaf25c) applied on `feature/unified-ui` (0c52566) with Claude fixes: edit 5 re-anchored (closing braces differed),
  title/Close shown in popup (inline display:none beat the CSS), popup video capped at 62vh, card text for interview
  jobs. Tested on 42022 with a real Short: card, popup, video, scrubber, beat strip, six panes, source note.

## In progress
- GPU interlock + editor priority: round 2 core applied on video-studio-test `feature/gpu-interlock` (691935f) with Claude
  fixes (Windows LK_LOCK 10 s limit, re-entrant lock, no file delete on force-release, no os.kill on Windows, all
  render stages + QC locked, PORT env, apply counter, interview_edit gated). 117/117 existing tests pass.
  Round 2b applied as written (cf88d5a): popup JS + 8 tests; full suite 125/125. On the 42022 test copy: beat open
  claims the reservation, lock status readable, reload resumes the same session, another session's apply gets 409
  'Waiting: editor in use'. Not yet tested: a real apply under the lock while a render runs (live server does not
  respect the lock until merged). To do outside Video Studio: Newsroom must send newsroom=true; WanGP watchdog
  must check `python -m studio.gpu_lock status` before unloading.
- Mailman hang fixed (git output to temp files, timeout kills the process tree, heartbeat file). It had hung 18:54-22:26.
- Video Studio idle restart armed (10 h window) so the per-beat "Picture source" note goes live; the Newsroom is on
  hold (no new jobs) until that restart is done, then the hold lifts itself. No render is interrupted.

## Next
- Merge the Publisher `feature/unified-ui` and Video Studio popup to live together, once both are tested.
- Real deletes still need a throwaway video and an explicit go from Tariq.

## Ports
Live: Video Studio 42021, Publisher 42030, Newsroom 42040. TEST: Video Studio 42022, Publisher 42031.

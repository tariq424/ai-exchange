# MERGE ORDER — GO LIVE (Tariq approved Oct 29, 2026, 12:22 PM EDT)

TL;DR: Merge the tested test-copy work to LIVE, in the stages below, in order.
Backups before every stage. Idle only — never interrupt a render; if a stage
cannot get an idle window, stop and post STATUS instead of forcing it.
If any stage fails its check: restore that stage's backup, restart the same
safe way, post what happened, and do not start the next stage.

## Stage 1 — Video Studio restart (finish the half-done merge)
- The light-theme / source-note files are already in the live folder.
- Restart 42021 via vs-restart-idle when /api/status shows idle.
- Verify on live 42021: light theme, solid stage chips, Nea job beats load,
  "Picture source:" line shows, play/scrub works on real media.
- Stop the 42022 test server once live checks pass.

## Stage 2 — Publisher unified UI + /delete to live (42030)
- Merge branch feature/unified-ui (includes POST /delete + delete_video
  with dry_run) to live.
- Verify: Ready/Published panels and the shared popup work on 42030, the
  published-channel popup fix (moonshots_source) holds, normal publish
  flow is unchanged.
- /delete may be exercised DRY RUN ONLY. No real delete in this order.

## Stage 3 — Video Studio popup beat editor to live (42021)
- Merge the popup editor (/?job=<id>&popup=edit) from feature/unified-ui.
- Verify on a real job: popup opens, video + scrubber work, beat strip and
  six panes show, source note present, Close returns to the main page.

## Stage 4 — GPU interlock + editor priority to live
- Merge feature/gpu-interlock. Include the two outside pieces in the same
  round: Newsroom sends newsroom=true; the WanGP watchdog checks
  `python -m studio.gpu_lock status` before unloading.
- Then the real-fight test: open a beat in the editor and apply while a
  real render runs. Expected: the apply waits / gets 409 "editor in use"
  behaviour per the test-copy results, and the render is NOT interrupted.

## Stage 5 — Newsroom resubmit/move to live (LAST)
- Only after Stage 2 is live and verified: merge newsroom
  koda/light-theme-source-note @ c5a9e9b (resubmit/move) to live 42040.
- Test end-to-end with dry-run / no real delete. A real move of a real
  video is NOT in this order — it still needs Tariq's separate go and a
  throwaway video.

## NOT approved in this order
- No real YouTube delete of any video.
- No real move of any published video between channels.
- No publishing of anything.

## Reporting
- Post a RESULT for each stage as it completes (ai-exchange STATUS.md
  update + the usual report to Tariq/Koda).
- If your credit cap hits mid-merge: post a short STATUS first — stages
  done, stages undone, exact live state (what is merged, what is running,
  any helpers armed) — then stop. Codex picks up this same order.
- After all stages: update the private repos and the sanitized public
  mirrors, and refresh HANDOFF.md.

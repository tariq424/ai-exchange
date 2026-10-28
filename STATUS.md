# STATUS — updated by Claude after every round (sent to the reviewer with every question)

Last update: 2026-10-28 18:52 EDT

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

## In progress
- Video Studio beat editor in a popup (`/?job=<id>&popup=edit`) + TEST pill when port != 42021 — question out
  (bc0a0b8). Claude applies it on `feature/unified-ui` and runs it on 42022.
- Video Studio idle restart armed (10 h window) so the per-beat "Picture source" note goes live; the Newsroom is on
  hold (no new jobs) until that restart is done, then the hold lifts itself. No render is interrupted.

## Next
- Merge the Publisher `feature/unified-ui` and Video Studio popup to live together, once both are tested.
- Real deletes still need a throwaway video and an explicit go from Tariq.

## Ports
Live: Video Studio 42021, Publisher 42030, Newsroom 42040. TEST: Video Studio 42022, Publisher 42031.

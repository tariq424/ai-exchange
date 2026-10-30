# BOARD.md — the common page (Claude · Codex · DeepSeek · Koda)

Created 2026-10-30 at the owner's direction: one page all four agents read before
working, so nobody designs or reports from a stale snapshot.

## How each agent reaches this page
- Claude and Codex: read it here in ai-exchange (and CONTEXT.md + STATUS.md).
- Koda: reads/writes here via GitHub; day-to-day messages still go in the
  Claude ↔ Koda exchange document, and anything decided there that changes the
  state below gets folded into this file.
- DeepSeek: has NO internet and reads nothing directly. The mailman must include
  this file in the per-question briefing (alongside CONTEXT.md + STATUS.md).
  PC-side change completed 2026-10-30: all three files are read fresh and
  required before sending. Offline request-payload verification passed.
- Rule: whoever finishes work updates the ledger and open items HERE in the same
  commit round as their RESULT. A claim not on this page is not agreed.
- This repo is public: no personal data, no document IDs, no keys, ever.

## Who does what
- Owner: approves publishing, real deletes/moves, and design changes of scope.
- Claude: PC builder (Video Studio / Newsroom / Publisher).
- Codex: PC builder/tester; has taken over the merge order (see below).
- Koda: coordinator — inbox feeding, QC owner (qc.py changes come through Koda
  as descriptions only), relay between everyone.
- DeepSeek: script writer and design critic, via the mailman loop only.

## Agreed design (2026-10-29/30 — exchange doc MSG 033, 034, 036 + Codex reply)
Diagnosis: the core visual failure is valid-but-irrelevant picks — assets chosen
because a ladder returned them, not because the beat needed them.
- One-line per-beat brief FIRST: what the beat must show + what counts as wrong.
- Evidence and the owner's own catalogue before outside stock (subject to the
  interview own-footage rule: never swap own footage for unrelated material).
- Generation only for missing planned assets, only via already-allowed
  providers. NO Google/Gemini generation by the pipeline. No Higgsfield.
  Hugging Face is out of the test runtime. No new Anthropic API dependency.
- A relevance check SEPARATE from QC: QC (v9) judges technical faults, not
  belonging. Subject lock stands. Repair ladder order and fail-open stand;
  headline card is the last resort.
- Feedback is two-lane: house-style rules (global) vs one-video fixes (job
  only). A note in a staged video's feedback box becomes a global rule, so
  one-offs never go there.
- Style-DNA mining is a MANUAL rung (owner, 2026-10-29): the owner names the
  channel, Koda adds the mined DNA to the arsenal; used only in debug mode,
  attended mode, or an owner-ordered re-render. The pipeline never goes to
  Google; the owner does that part by hand (also paid ChatGPT, by hand).
- Blender MCP is adopted for Claude + Codex (prompt-made short animations)
  AFTER the install route is verified — the circulating spec's install steps
  are broken as written. Neither DNA nor Blender changes the unattended ladder.
- No fundamental design disagreement (Codex, 2026-10-30). DeepSeek has NOT yet
  been briefed on this design — its critique is still owed; nobody claims
  DeepSeek agreement until an answer actually arrives.

## Current state (as of 2026-10-30 ~01:00 EDT)
### MSG 038 execution ledger — overrides the older live-merge snapshot
- FREEZE PASS, 2026-10-30 16:57 EDT: PC Newsroom hold installed; live
  42040 paused=true, waiting=2, publish_queue=0. Video Studio 42021
  current=null and no running/queued jobs. No render interrupted. Services
  remain up for inspection; automated PC dispatch is held. No production
  restart/merge/publish/delete/move. Resume only on the owner's separate word.
- Freeze evidence is retained locally in programme-038/evidence/freeze.json.
- S0 PASS: real mailman strategy round trip completed 2026-10-30 17:00 EDT;
  response explicitly confirms CONTEXT.md + STATUS.md + BOARD.md. Request
  087b604, answer retained in to_claude/answer.md and the local mailman archive;
  142 seconds, 20,553 tokens. No implementation or live action authorized
  by the critique.
- S1 PASS after a test-only fix: copied Nea job plus 88 hash-verified media
  dependencies and 72 sidecars; playback 156.9s, real seek, light theme,
  eight solid stage chips, source notes on bite/fact/card, empty-source safe.
  Added scrubber source note for noneditable cards on codex/msg038-smoke.
  Controlled UI fixtures restored.
- S2 PASS: one real copied-Short beat edited and restitched through 42022
  popup; six panes visible; last edit p00 applied, one history entry, full
  strict FFmpeg decode exit 0, browser playback readyState=4 and time advances.
  Second-session apply HTTP 409; Horseshoe media hash unchanged. Test-only
  optional music library was missing (voice/video still rendered); library
  copied for later smokes and automatic music generation disabled.
- S3 PARTIAL (resumed after cap): TEST pill/panels, POST /delete HTTP 403,
  actual Chrome published-popup launch and moonshots_source record/link
  retention verified. Ready-panel navigation verified. Ready-popup playback
  and final evidence still pending; S4–S12 pending. Production hold verified.

- QC v9 in fix mode is LIVE. Newsroom light theme + three panels + popup
  player are LIVE. Video Studio light page is live; the per-beat source note
  still waits on an idle restart.
- Inbox feeding is on HOLD — breaking news only (owner, 2026-10-29). The hold
  governs NEW items on the inbox side only; items already waiting in the PC
  queue remain eligible for production.
- Production is ACTIVE serial, not stalled (Codex PC check, 2026-10-30): the
  Alphabet job staged 19:20 Oct 29; the NY chatbot job staged 22:49; the
  CRISPR job was rendering its explainer past midnight. The dispatcher waits
  while Video Studio has a current job. One separate stalled item exists and
  is undiagnosed.
- Fox News breaking is a new inbox source; its lines carry a slyfox channel
  tag. NOT YET ROUTED: the Newsroom inbox parser does not parse the tag into
  a channel field (it can land as brief text). A tested parser change is owed.

## Fixed on test vs pending (fit-gating round, branch codex/test-fit-vault-20261029)
FIXED ON TEST ONLY: narration-fit gating; fresh/cache rejection audit;
provider order (Google image providers last); HF excluded from test runtime.
Tests reported: 144 passed / 4 skipped; offline 2-second CPU encode with mocked
providers/vision. Credential loader is on the live disk (owner-approved).
PENDING: a complete isolated test-server render through the gate; real-vision
relevance judgments on the 3 specimen beats (Horseshoe locked — do not
regenerate); independent review of the branch; sanitized public mirror refresh
after verified results; any live promotion (only via the merge order below).

## Merge order (owner-approved 2026-10-29; full text in MERGE-ORDER.md)
Stages: (1) Video Studio idle restart + source-note verify; (2) Publisher
unified UI + /delete to live (delete stays DRY RUN only); (3) Video Studio
popup beat editor to live; (4) GPU interlock live + Newsroom newsroom=true +
watchdog, then the real apply-during-render test; (5) Newsroom resubmit/move
to live, last. Backups before every stage; idle only; a failed stage restores
its backup and stops the sequence. NOT covered: any real delete, real move, or
publishing — those need the owner's separate go.
Status: Codex accepted pickup 2026-10-30; NO stage started or completed yet;
Stage 1 waits for an idle window (active render in progress at last check).
Caution from Codex: the live Video Studio checkout is dirty and behind origin;
the clean fit-test branch lives in its own test folder. Do not reset or merge
over local edits.

## Open items
1. CLOSED 2026-10-30 — DeepSeek strategy brief sent and answered in S0.
   Read the retained critique before designing; response is not blanket
   approval of untested implementation.
2. Fox channel-tag routing: tested parser change owed (see Current state).
3. One stalled Newsroom item: cause undiagnosed (not the Alphabet job).
4. CLOSED 2026-10-30 — Mailman now includes BOARD.md alongside CONTEXT.md +
   STATUS.md. Three offline tests verify the actual request payload, fresh
   reads, and no network call if any required file is missing/empty. No real
   question sent. No mailman process was running at verification; the next
   normal launch will load the updated PC-local script. Reproducible patch:
   patches/mailman-board-briefing.patch; tests/test_mailman_briefing.py.
5. HANDOFF.md is stale next to STATUS.md in places; STATUS wins until refreshed.

## Standing rules (all agents)
- Never interrupt a render. No automatic publishing.
- Real YouTube deletes/moves need the owner's explicit go (plus a throwaway
  test first for deletes).
- No permanent local deletions — move to a _to_delete folder.
- Owner hears outcomes, not decision requests, on pipeline/QC matters.
- Worst case we restore from git.

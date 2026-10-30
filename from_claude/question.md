Strategy review only — MSG 038 S0. Do not write an implementation patch yet.

You have no internet. Use the supplied CONTEXT.md, STATUS.md and BOARD.md in
your system briefing and the facts below; do not claim to have fetched code,
videos, other messages or external policies. First explicitly confirm whether
all three named briefing files are present in what you received.

Problem: a valid stock clip of a mosque was selected for narration about the
Royal Naval Dockyard / Bermuda Arts Centre. Technical QC can pass an asset
that depicts the wrong subject or place. A separate approved Horseshoe Bay
beat must remain unchanged. The other evaluation specimen is an ordinary
narration-over beat. Current render success and mocked tests do not prove
real-vision relevance accuracy.

Proposed design for critique:
1. A one-line per-beat brief states what it must show and what counts as wrong.
2. Evidence and the owner's catalogue first, preserving interview own-footage
   restrictions. Actual-subject stock only; never near-miss stock.
3. Generate only missing planned assets through already allowed providers.
   No Google/Gemini generation by the pipeline, no Higgsfield, no HF in this
   test runtime, no new Anthropic dependency. DeepSeek writes scripts.
4. Relevance/place/continuity are judged separately from QC v9 technical
   faults. Preserve subject lock, pixel-black veto, finger detail veto,
   orientation report-only, repair ladder order with headline card last,
   and fail-open staging. qc.py changes are descriptions to Koda only.
5. Two feedback lanes: explicit house-style rules versus job-only corrections.
   Staged-video feedback currently becomes global, so one-offs cannot go there.
6. Reuse assets/layouts, not identical whole-video visual arguments.
7. Style DNA is manual/attended/debug/owner-requested rerender only. The owner
   supplies any Google Flow assets by hand; the pipeline never calls Google.
   Blender MCP is an attended builder tool after vendor-source verification,
   not a new unattended production dependency.

Test scope: production is held. Isolated copies only. No live promotion,
publishing, real deletion or real move. The initial relevance comparison uses
existing copied specimens with Horseshoe locked; no regeneration of that beat.

Please return: (a) agreement/disagreement with reasons, (b) smallest robust
per-beat brief and separate relevance verdict schema, (c) how to prevent the
known-wrong mosque clip from passing without overrejecting the good beat,
(d) a concrete real-vision test and failure-policy plan, including how to
distinguish model unavailable from a valid rejection without silently accepting
an unrelated asset, and (e) what evidence/code you need before proposing a patch.
Do not claim universal agreement; this response is your independent critique.

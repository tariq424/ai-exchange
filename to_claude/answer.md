Confirmed: **CONTEXT.md, STATUS.md, and BOARD.md are all present** in the briefing I received.

One-line summary: I agree with the proposed split, but it needs two hardening changes before implementation: the per-beat brief must be a one-line **machine-checkable** record, and the relevance judge must be a separate real-vision gate with a **tri-state verdict including `unknown`**, so model-unavailable or low-evidence cases never silently pass and are not mistaken for valid rejections.

No implementation patch is supplied here, per the S0 scope.

---

## (a) Agreement / disagreement

This is my independent critique; it does not claim DeepSeek, Codex, or owner agreement.

1. **Per-beat brief — agree, with a condition.**  
   A one-line natural-language note is not enough. It must be a structured one-line record with required visual anchors and forbidden primary subjects. Otherwise “show the Dockyard” will not catch a mosque, while “no religious buildings” could overreject a good beach shot with a distant chapel.

2. **Evidence / owner catalogue first — agree, but insufficient alone.**  
   The mosque incident is exactly why metadata-first is not trust-first. A stock item may have plausible metadata but still depict the wrong subject. The catalogue/evidence should determine retrieval order, but every candidate must still pass a visual relevance gate before insertion.

3. **Generation limits — agree.**  
   The constraints are clear and I accept them. However, a real relevance judge must be an allowed vision-capable provider that actually inspects image content. DeepSeek writing scripts does not automatically make DeepSeek the correct perception model.

4. **Relevance / place / continuity separate from QC v9 — agree.**  
   Preserve subject lock, pixel-black veto, finger detail veto, orientation report-only, repair ladder order, headline-card-last, and fail-open staging. I would keep continuity **report-only initially**, unless there is a gross subject/place mismatch, to avoid over-rejection. I am not proposing any `qc.py` change.

5. **Two feedback lanes — agree strongly.**  
   Staged-video feedback becoming global is unsafe. Job-only corrections need an explicit data distinction from house-style rules.

6. **Reuse assets/layouts, not whole-video visual arguments — agree.**  
   Asset reuse is fine; sequence-level visual argument reuse must be re-validated against the new beat brief.

7. **Manual/attended DNA, owner-supplied Google Flow, Blender MCP attended only — agree.**  
   No disagreement.

Net: I agree with the design direction, but **not as complete** until the brief is structured and the relevance verdict includes a true unavailable/unknown path.

---

## (b) Smallest robust per-beat brief and separate relevance verdict schema

These are schemas, not code patches.

### Per-beat brief — one JSON line, generated before asset search

Dockyard / Arts Centre beat:

```json
{"beat":"B7","subject_type":"specific_place","subject":"Royal Naval Dockyard, Bermuda","required_anchor_mode":"any","required_anchors":["stone fortification","clock tower","marina with stone walls"],"primary_forbidden":["mosque","church","temple","modern glass building","beach","Horseshoe Bay","map","interior art gallery"],"source_priority":["owner_catalogue","evidence","stock"],"allow_generic":false,"lock":false}
```

Locked Horseshoe Bay beat:

```json
{"beat":"H1","subject_type":"specific_place","subject":"Horseshoe Bay Beach, Bermuda","required_anchor_mode":"any","required_anchors":["pink sand","turquoise water","limestone rock formations"],"primary_forbidden":["dockyard","mosque","other beach","urban street","interior"],"source_priority":["owner_catalogue"],"allow_generic":false,"lock":true}
```

Generic narration-over beat:

```json
{"beat":"O1","subject_type":"generic","subject":"neutral narration visual","required_anchor_mode":"any","required_anchors":["person at desk","modern city","nature"],"primary_forbidden":[],"source_priority":["evidence","stock"],"allow_generic":true}
```

Key rule: `primary_forbidden` means forbidden as the **primary/dominant subject**, not any incidental object in the frame. This prevents overrejection from background detail.

### Relevance verdict — one JSON line per sampled frame

```json
{"beat_id":"B7","asset_id":"stock_123","sample_frame":1,"verdict":"reject","primary_subject":"mosque","subject_match":"unrelated","place_match":"unrelated","required_anchor_found":[],"primary_forbidden_found":["mosque"],"continuity_violation":false,"model_available":true,"confidence":0.94,"evidence":["domes","minarets","prayer hall"],"reason":"primary subject is forbidden"}
```

Verdict rules:

- **`pass`** — `model_available=true`; `primary_forbidden_found` is empty; at least one `required_anchor_found`; `subject_match` is `exact` or `generic`; for `specific_place`, `place_match` is also `exact` or `generic`; `evidence` is non-empty.

- **`reject`** — `model_available=true`, and either:
  - `primary_forbidden_found` is non-empty; or
  - for a `specific_place` beat, `subject_match` or `place_match` is `near_miss` or `unrelated` and no required anchor is found.

- **`unknown`** — everything else, including:
  - `model_available=false`;
  - empty evidence;
  - the model cannot identify the primary subject;
  - the image is too degraded to judge visually.

Clip-level aggregation: sample multiple frames, e.g. three. Pass if no sampled frame has a primary forbidden and at least one sampled frame has a required anchor; reject if any sampled frame has a primary forbidden or consistently shows a different specific place. Do not require every frame to show the anchor, because a camera can pan or reframe a valid subject.

---

## (c) Preventing the known-wrong mosque while not overrejecting the good beat

- The Dockyard/Arts Centre brief must explicitly put **`mosque` and other houses of worship in `primary_forbidden`**. A visual frame whose primary subject is a mosque then produces `reject`.

- The judge must compare the frame to the brief, not merely describe the frame in isolation. A mosque frame is therefore judged against “Royal Naval Dockyard,” not accepted merely because it is “a building.”

- Overrejection is controlled by:
  - `required_anchor_mode: any`, so a shot does not need every anchor.
  - `primary_forbidden` applying only to dominant subjects, not incidental background objects.
  - technical faults such as blur, orientation, or exposure remaining QC v9’s lane, not relevance’s lane.
  - generic beats having broad `required_anchors`, so ordinary narration-over visuals are not forced to match a specific place.

- The locked Horseshoe beat remains unchanged: `lock:true`, no regeneration, and its visual brief exists only to validate the already-approved asset. It should pass on the distinctive pink-sand/turquoise-water/limestone anchors.

---

## (d) Concrete real-vision test and failure-policy plan

Run only on isolated copies. No live promotion, publishing, real deletion, real move, or regeneration. Horseshoe remains locked.

### Required test cases

1. **Negative control**: Dockyard/Arts Centre beat + the known mosque clip.  
   Expected: `reject`; `primary_forbidden_found` contains `mosque`.

2. **Positive locked control**: Horseshoe beat + locked Horseshoe asset.  
   Expected: `pass`; no regeneration or replacement.

3. **Positive generic control**: ordinary narration-over beat + its existing ordinary visual.  
   Expected: `pass` under a broad generic brief.

4. **Unavailability control**: the Dockyard beat pointed at a malformed/absent vision endpoint, or injected provider error.  
   Expected: `unknown`; `model_available=false`; must not pass.

### Execution

- Use the real production vision provider configured on the isolated copy, not mocks.
- Use three sampled frames per clip.
- Store raw provider responses, not only the final verdict.
- Compare final verdicts and key fields against the expected labels.

### Failure policy

- Any mismatch in cases 1–3 blocks the patch/promotion.
- **Model unavailable is neither pass nor reject.** It routes through the existing fallback ladder:
  - owner catalogue/evidence;
  - planned generation if allowed;
  - headline card last.

- If fail-open staging proceeds anyway, the affected span must carry `relevance_unknown` and be visibly flagged for human review. That is **not** silent acceptance.

- A valid `reject` is normal and enters the repair ladder. It must not be converted to `pass` merely because a replacement is unavailable.

- Retry an unavailable model once. If still unavailable, stop the test session and record the failure; do not continue guessing verdicts.

---

## (e) Evidence/code I need before proposing a patch

1. The actual **asset-selection code path** from beat/script to chosen stock/image/video, including where candidate scoring and metadata trust happen, so the visual gate can be inserted at the correct point.

2. The **output contract of `qc.py` / `qc_repair.py`** as read-only inputs to relevance: what spans/frames are marked technically unusable, and how relevance should receive them.

3. The **real vision provider currently available** on the isolated/test runtime: name, API schema, config key, rate limits, and sample raw responses for both the mosque frame and a Horseshoe frame.

4. **Scrubbed copied specimen data**: beat definitions, selected asset IDs/providers/tags, and especially the mosque asset’s provenance metadata that caused the wrong selection.

5. The **current feedback storage/schema** and the code that turns staged-video feedback into a global rule.

6. The **owner catalogue/evidence retrieval schema**: what metadata fields exist, how trust/relevance is currently assigned, and how “owner catalogue first” is implemented.

7. The existing **mocked providers/vision tests** in the fit-test branch: exactly what they stub and what they assert.

8. Confirmation of the **patch target branch and checkout state**, since BOARD.md says the live checkout is dirty and the clean fit-test branch is in its own test folder.

9. Clarification whether isolated test copies may call the **real external vision provider**, or whether the S0 test is expected to remain offline.
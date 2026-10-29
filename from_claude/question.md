# Codex test-only request — 2026-10-29

Tariq has explicitly resumed execution. This request overrides old CONTEXT restrictions only as follows: keep Gemini and Google Photos available as controlled LAST fallbacks; prefer local/catalogued/stock assets first. Higgsfield is CANCELLED: no integration, no MCP investigation, no paid service adoption. No live deployment, restart, publishing, deletion, or qc.py changes. All code is on private video-studio-test branch codex/test-fit-vault-20261029 based on cf88d5a.

Please return a narrowly scoped executable unified diff (no prose inside the diff) and tests for:
1. Narration/image FIT check: keep vet_provider=local, but enforce the NEW narration-fit rejection only when actual process PORT=42022. Unset PORT, malformed PORT, and all other ports must preserve existing behavior. Do not globally turn off stock vetting, corruption checks, image physical checks or frame QC. Force this new check to the local vision model, never a paid model. Test both fresh generated images and resumed cached images; no rejected image should be selected. Rejection advances to the next provider. Match narration, not incidental text/logos. Exceptions/malformed verdicts should be clearly counted as unavailable, fail closed on 42022 and continue to next provider (do not count unavailable as a narration mismatch). Keep rejected files as evidence, not permanent deletions. Store per-workspace audit JSON with counts checked, rejected_for_narration, unavailable, accepted and reasons; log a cumulative summary and image/provider/reason. Avoid counting the same unchanged cached asset again, but invalidate a prior verdict when narration/image/model changes. Cancellation must propagate.
2. Controlled fallback order: preserve Gemini config and Google Photos code; stable-partition Google providers behind non-Google providers even if imagegen rotation/settings prefer Google. Stock/own clips already precede generation. Inspect the excerpt and propose a minimal default-off test flag if needed for local catalogue reuse; never scan private Google Photos or alter its manual workflow. Do not add a Google API credential or spend Flow credits. Existing Google Photos is browser automation, not an API: don't invent an API integration.
3. HF token support: add hf_token to DEFAULTS and SECRETS so Windows Credential Manager service ExplainerStudio/hf_token is used, public settings are masked, save accepts it. Preserve Linux VS_HF_TOKEN fallback. Migration must verify vault storage before rewriting settings, be atomic, retain no plaintext backup, and fail closed for hf_token if Windows vault migration is unavailable (never expose token via public(), errors, logs, tests or patches). Do not rotate/revoke a real credential in code/tests. Provide a separate safe local migration entry point if useful; no network calls during unit tests.

Use the existing Python style. No Anthropic dependency. Do not change qc.py or qc_repair.py. Include meaningful offline tests for port isolation, cached/fresh mismatch rejection, fallback ordering including rotation, provider unavailable and cancellation, vault persistence failure, redaction and environment lookup. Explicitly note missing code needed rather than guessing.

Reference research: likely Christian Peverelli video HzXD4GVqXwM, creator's own LinkedIn says timestamped Parakeet transcription, separately rendered HyperFrames graphics, Chrome research, Tella MCP, sound assets, FFmpeg final black-screen/audio-sync QA, reusable editorial rules. No exact FFmpeg commands verified; YouTube subtitle request got HTTP 429, no retries. Do not invent or apply performance flags based on this.

Current source excerpts follow. NO SETTINGS FILE OR CREDENTIAL IS INCLUDED.


## app/studio/config.py lines 1-40
```python
"""Settings stored in <studio>/settings.json (local only)."""
import json
from pathlib import Path
APP = Path(__file__).resolve().parent.parent
ROOT = APP.parent
CFG = ROOT / "settings.json"
DEFAULTS = {
    "source_visuals": True,           # opt-in per beat via a timestamp + original commentary purpose
    "source_visual_max_uses": 2,      # editorial cap per output, not a legal safe harbor
    "editorial_attempts": 5,          # editorial review (our analysis + a joke per beat): regenerate with feedback up to this many times
    "source_clips_auto": True,        # Source Clip rung: when the script asked for none, match the beat to a caption cue (2.5 s clip)
    "flow_on": True,                  # Google Flow rung (flow.py): skipped by itself until scripts\flow-login.ps1 has been run once
    "flow_profile": "",               # Chrome profile for Flow ("" = <jobs_dir parent>\flow_profile)
    "flow_url": "https://labs.google/fx/tools/flow",
    "flow_timeout": 480,              # seconds to wait for one generated clip (Flow queues at busy times)
    "flow_max_per_video": 1,          # Flow clips per output: Google account + credits, only when everything else failed
    "flow_headless": False,
    "flow_auto_approve": True,        # click Flow's "Approve" (spend the quoted credits) for each clip; never "Always approve"
    # image generator (imagegen.py, rung 3): Gemini describes the source screenshot, writes a prompt, generates the image;
    # then rembg parallax (rung 4). Uses the Google-signed-in Flow profile unless gemini_profile is set.
    "imagegen_on": True,
    "gemini_profile": "",
    "gemini_url": "https://gemini.google.com/app",
    "imagegen_timeout": 240,
    "imagegen_max_per_video": 8,      # beats per output that get Gemini images
    "imagegen_per_beat": 1,           # 1 AI image per beat (2026-10-21: protect the accounts); parallax/zoom add the variety
    "imagegen_cooldown_hours": 6,     # after a usage-limit message
    "imagegen_headless": True,        # no visible Chrome window for Gemini (2026-10-21)
    "imagegen_delay_secs": [15, 30],  # human pacing: a random 15-30 s between requests to the same service
    # fixed priority, every beat (2026-10-22): Hugging Face (free) -> ChatGPT -> Bing -> Gemini only when all three fail,
    # to keep automation away from Tariq's main Google account. imagegen_rotate: true brings back the per-video rotation.
    "imagegen_providers": ["hf", "chatgpt", "bing", "gemini"],
    "imagegen_rotate": False,
    "imagegen_first": "hf",   # one service per video, rotating; the others are the fallback
    "source_snapshot_max_uses": 2,    # source screenshots taken just for describing (rung-2 clips/screenshots are reused free)
    # WanGP memory policy (wangp.py): never started with the job; launched for a generation, stopped right after
    "wangp_on_demand": True,   # owner: last resort only; stopped after each use, idle copies stopped by wangp-watchdog.ps1
    "wangp_start_timeout": 300,
    "script_provider": "deepseek",
    "qa_provider": "off",
```


## app/studio/config.py lines 135-220
```python
    "capcut_max_actions": 30,         # computer-use budget per video (screenshots + clicks)
    "capcut_timeout": 600,            # seconds for the whole CapCut session (draft + export)
    "aisstream_api_key": "",          # optional (aisstream.io, free): live AIS position for ship_route when the narration gives an MMSI
}

SECRETS = ("anthropic_api_key", "zai_api_key", "deepseek_api_key", "aisstream_api_key")

VAULT = "ExplainerStudio"   # shared with Explainer Studio so saved keys carry over

def _kr():
    try:
        import keyring; return keyring
    except Exception: return None

def _vault_get(name):
    kr = _kr()
    try: return (kr.get_password(VAULT, name) or "") if kr else ""
    except Exception: return ""

def _vault_set(name, value):
    kr = _kr()
    if not kr: raise RuntimeError("Windows Credential Manager not available (keyring missing)")
    if value: kr.set_password(VAULT, name, value)
    else:
        try: kr.delete_password(VAULT, name)
        except Exception: pass

def _raw():
    if CFG.exists():
        try: return json.loads(CFG.read_text(encoding="utf-8"))
        except Exception: pass
    return {}

def _migrate():
    """Move any plain-text keys from settings.json into the Windows vault."""
    raw = _raw(); changed = False
    for k in SECRETS:
        v = raw.get(k, "")
        if v and v != "vault":
            _vault_set(k, v); raw[k] = "vault"; changed = True
    if changed: CFG.write_text(json.dumps(raw, indent=1), encoding="utf-8")

def load():
    d = dict(DEFAULTS)
    try: _migrate()
    except Exception: pass
    raw = _raw(); d.update(raw)
    import os
    for k in SECRETS:   # Windows vault; on the Linux worker the service's environment (VS_<NAME>) or a plain value
        plain = raw.get(k) if raw.get(k) not in (None, "", "vault") else ""
        d[k] = _vault_get(k) or os.environ.get("VS_" + k.upper(), "") or plain
    if os.environ.get("VS_HF_TOKEN") and not d.get("hf_token"): d["hf_token"] = os.environ["VS_HF_TOKEN"]
    return d

def save(upd):
    raw = _raw()
    for k, v in upd.items():
        if k in DEFAULTS and v is not None:
            if k in SECRETS:
                v = v.strip()
                if v == "" or v.startswith("••"): continue
                if v == "delete": v = ""
                _vault_set(k, v); raw[k] = "vault" if v else ""
            else: raw[k] = v
    CFG.write_text(json.dumps(raw, indent=1), encoding="utf-8")
    return load()

def public(d=None):
    d = dict(d or load())
    for s in SECRETS:
        k = d.get(s, ""); d[s] = ("••••" + k[-4:]) if k else ""
    return d
```


## app/studio/imagegen.py lines 30-120
```python
"""
import json
import re
import time
from pathlib import Path

URL = "https://gemini.google.com/app"
LABEL = "GEMINI"
DESCRIBE = "Describe this image in detail, then write a prompt to recreate it without brands or text."
FORMAT = "Put the final prompt on its own line, starting with PROMPT:"
# Never a real person's likeness (a "US president at a podium" came back looking like a former president, in a story
# about another one): people only as anonymous figures.
NO_PEOPLE = ("The prompt must not show any real or recognizable person, politician or celebrity: show people only as "
             "anonymous figures seen from behind, in silhouette, as hands, or out of focus.")
NARRATION = "Write a prompt for a photorealistic image that illustrates this narration, without brands or text: "
GENERATE = "Generate an image: "
VARIANTS = ["Generate a second image of the same scene from a different camera angle, same style and lighting.",
            "Generate another image of the same scene as a close-up of the main subject, same style and lighting."]

RATE = re.compile(r"(reached your (daily )?limit|usage limit|limit for (today|now)|try again (later|tomorrow|in \d+)|"
                  r"too many requests|out of (quota|credits)|(hit|reached) (the|your) [a-z ]{0,30}limit|limit resets)", re.I)
CAPTCHA = re.compile(r"(captcha|unusual traffic|verify (that )?you('| a)re (a )?human|are you a robot|not a robot)", re.I)
REFUSED = re.compile(r"(can.t (create|generate|make) (images|that|this)|couldn.t (create|generate)|i can.t help with (that|this)|"
                     r"against (my|our) (policies|guidelines)|unable to (create|generate))", re.I)

PROVIDERS = ("gemini", "chatgpt", "bing", "hf")
HF_SPACE = "black-forest-labs/FLUX.1-schnell"   # Hugging Face's free hosted FLUX (ZeroGPU): runs on their GPUs, not this PC
_job_skip = {}       # site -> why it's skipped for the rest of this job
_last = {}           # site -> when it last answered: each service is paced like a person, not a script
_site = {"cur": "gemini"}   # the service that made the images generate_many returned last (for tag())
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
UA_EDGE = UA + " Edg/141.0.0.0"
CHATGPT_URL = "https://chatgpt.com/"
BING_URL = "https://www.bing.com/images/create"


def _pause(cfg, log, why, site="gemini"):
    """Wait a human-looking 15-30 s (imagegen_delay_secs) since this service's last answer before the next request."""
    import random
    lo, hi = (cfg.get("imagegen_delay_secs") or [15, 30])[:2]
    wait = random.uniform(float(lo), float(hi)) - (time.time() - _last.get(site, 0.0))
    if wait > 0:
        log(f"  {site}: pausing {wait:.0f}s before {why} (human pacing)")
        time.sleep(wait)


def _answered(site="gemini"):
    _last[site] = time.time()


def reset():
    _job_skip.clear()


def last_site():
    return _site["cur"]


class Skip(Exception):
    def __init__(self, why, cool_secs=0):
        super().__init__(why)
        self.why, self.cool = why, cool_secs


def _state_path(cfg, sd):
    if cfg.get("imagegen_state"):
        return Path(cfg["imagegen_state"])
    return Path(cfg.get("jobs_dir") or Path(sd).parent.parent).parent / "imagegen_state.json"


def _cooling(cfg, sd, site="gemini"):
    try: e = (json.loads(_state_path(cfg, sd).read_text(encoding="utf-8")) or {}).get(site) or {}
    except (OSError, ValueError): return None
    return e if float(e.get("until") or 0) > time.time() else None


def _cool(cfg, sd, secs, why, site="gemini"):
    p = _state_path(cfg, sd)
    try: st = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError): st = {}
    st[site] = {"until": time.time() + secs, "why": why, "set": time.strftime("%Y-%m-%d %H:%M")}
    try: p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(st, indent=1), encoding="utf-8")
    except OSError: pass


def profile_dir(cfg, site="gemini"):
    if site != "gemini":
        if cfg.get(f"{site}_profile"): return Path(cfg[f"{site}_profile"])
        return Path(cfg.get("jobs_dir") or ".").parent / f"{site}_profile"
    if cfg.get("gemini_profile"): return Path(cfg["gemini_profile"])
    from .flow import profile_dir as flow_profile
```


## app/studio/imagegen.py lines 570-760
```python
        finally:
            context.close()


def _session_hf(cfg, sec, aspect, out, timeout, log, evidence, extras=()):
    """Hugging Face Space (FLUX.1-schnell) through the official gradio client: no browser, no Google/OpenAI/Microsoft
    account. Free quota per day (more with a free HF token: settings hf_token)."""
    try:
        from gradio_client import Client
    except ImportError:
        raise Skip("gradio_client is not installed (pip install gradio_client)")
    from .flow import visual_prompt
    import shutil
    prompt = re.sub(r"(?i)slow (cinematic )?camera move[^.]*\.?", "", sec.get("described_prompt") or visual_prompt(cfg, sec, log))
    prompt = re.sub(r"\s+", " ", prompt).strip()[:700] + " Photorealistic. No text, no logos. No real or recognizable people."
    w, h = (768, 1344) if aspect == "9:16" else (1344, 768)
    _pause(cfg, log, "this beat's image", "hf")
    log(f"  hf: prompt ({len(prompt.split())} words): \"{prompt[:140]}...\"")
    try:
        client = Client(cfg.get("hf_space") or HF_SPACE, token=cfg.get("hf_token") or None, verbose=False)
        files = []
        for k in range(1 + len(extras)):
            if k: _pause(cfg, log, f"image {k + 1}", "hf")
            res = client.predict(prompt, 0, True, w, h, 4, api_name="/infer")
            files.append(res[0] if isinstance(res, (list, tuple)) else res)
    except Exception as e:
        msg = str(e)
        if re.search(r"quota|rate limit|too many|exceeded", msg, re.I): raise Skip(f"Hugging Face quota ({msg[:120]})", -1)
        raise RuntimeError(f"Hugging Face: {msg[:200]}")
    _answered("hf")
    from PIL import Image
    for k, (f, dest) in enumerate(zip(files, [out] + list(extras))):
        src = f.get("path") if isinstance(f, dict) else f
        with Image.open(src) as im: im.convert("RGB").save(dest, "JPEG", quality=93)
        why = _has_text(cfg, dest, log)
        if why and k == 0:   # an obvious physical mistake: one more try with a new seed, then the next service
            log(f"  hf: image looks wrong ({why}); one more try")
            try:
                _pause(cfg, log, "a retry", "hf")
                res = client.predict(prompt, 0, True, w, h, 4, api_name="/infer"); _answered("hf")
                f2 = res[0] if isinstance(res, (list, tuple)) else res
                with Image.open(f2.get("path") if isinstance(f2, dict) else f2) as im: im.convert("RGB").save(dest, "JPEG", quality=93)
                why = _has_text(cfg, dest, log)
            except Exception as e:
                why = why or str(e)[:80]
            if why:
                Path(dest).unlink(missing_ok=True)
                raise RuntimeError(f"Hugging Face images kept coming out wrong ({why})")
        elif why:
            log(f"  hf: image {k + 1} looks wrong ({why}); dropped"); Path(dest).unlink(missing_ok=True)
    return prompt


TEXT_CHECK = ('Check this AI-generated image for obvious physical mistakes only: an object with the wrong number of parts (a plane '
              'with extra wings or engines, a car with extra wheels, a bike with three pedals), malformed hands or limbs, or impossible, '
              'melted or fused structures. Ignore any text, lettering, signs or license plates. Reply with JSON only: '
              '{"broken": "yes" or "no", "what": "<the mistake, a few words>"}')


def _has_text(cfg, image, log):
    """Local vision check (Ollama on this PC, no account usage): -> short reason if the image has an obvious physical mistake
    (a four-winged plane, extra wheels, mangled hands), else "". Text and fake plates are fine."""
    if cfg.get("vet_provider", "local") != "local" or not cfg.get("imagegen_text_check", True): return ""
    try:
        from .footage import _vision
        from .llm import parse_json
        j = parse_json(_vision(cfg, image, TEXT_CHECK))
        return str(j.get("what") or "a physical mistake")[:60] if str(j.get("broken", "no")).strip().lower() in ("yes", "true", "1") else ""
    except Exception as e:
        log(f"  text check unavailable ({str(e)[:80]}); keeping the image"); return ""


# ---------------------------------------------------------------- ladder entry
def generate(cfg, sd, sec, key, log, aspect="9:16", image=None, count=1):
    """Rung 3. -> (image_path, site, prompt) or (None, None, None). Never raises (cancel aside)."""
    res = generate_many(cfg, sd, sec, key, log, aspect, image, count)
    return (res[0][0], _site["cur"], res[0][1]) if res else (None, None, None)


def generate_many(cfg, sd, sec, key, log, aspect="9:16", image=None, count=1):
    """-> [(image_path, prompt), ...] (first = the scene, then variants), or []. Never raises (cancel aside).
    The video's service first (rotation), then the others if it fails; last_site() says which one made them."""
    count = max(1, min(int(count), 1 + len(VARIANTS), int(cfg.get("imagegen_per_beat", 1))))
    if not cfg.get("imagegen_on", True):
        return []
    order = [x for x in (cfg.get("imagegen_providers") or PROVIDERS) if x in PROVIDERS] or ["gemini"]
    d = Path(sd) / "imagegen"; d.mkdir(parents=True, exist_ok=True)
    led = d / "gemini_usage.json"   # (name kept from when Gemini was the only service: one ledger per video)
    try: used = json.loads(led.read_text(encoding="utf-8")) if led.exists() else {}
    except (OSError, ValueError): used = {}
    if key in used:   # already made (a resumed job)
        site = used[key].get("site", "gemini")
        files = [d / f for f in used[key].get("files", [])] or [d / f"{key}_gemini.jpg"] + [d / f"{key}_gemini_{k + 2}.jpg" for k in range(count - 1)]
        files = [x for x in files if x.is_file()]
        if files:
            _site["cur"] = site
            return [(x, used[key].get("prompt", "")) for x in files]
    cap = int(cfg.get("imagegen_max_per_video", 8))
    if len(used) >= cap:
        log(f"  image generators: {cap} images already made for this video; next rung"); return []
    if not cfg.get("imagegen_rotate", False):   # fixed priority (default): the list order, every beat
        pref, first, tries = None, order[0], list(order)
    else:   # rotation: one service per video, taking turns (imagegen_first tried before it)
        pref = cfg.get("imagegen_first") if cfg.get("imagegen_first") in order else None
        first = _job_provider(cfg, sd, [x for x in order if x != pref] or order)
        tries = ([pref] if pref else []) + [first] + [x for x in order if x not in (first, pref)]
    image = str(image) if image and Path(image).is_file() else None
    timeout = int(cfg.get("imagegen_timeout", 240))
    vo = str(sec.get("vo") or sec.get("still_prompt") or "")
    described = None   # the screenshot described once by the local vision model, for the services that take a text prompt
    for site in tries:
        if _job_skip.get(site):
            log(f"  {site} skipped ({_job_skip[site][:140]})"); continue
        cool = _cooling(cfg, sd, site)
        if cool:
            _job_skip[site] = f"cooling down until {time.strftime('%H:%M', time.localtime(cool['until']))}: {cool['why'][:100]}"
            log(f"  {site} skipped ({_job_skip[site]})"); continue
        out = d / f"{key}_{site}.jpg"
        extras = [d / f"{key}_{site}_{k + 2}.jpg" for k in range(count - 1)]
        def evidence(page, step, site=site):
            try:
                (d / f"{key}_{site}_{step}_fail.png").write_bytes(page.screenshot(full_page=False))
                (d / f"{key}_{site}_{step}_fail.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
        t0 = time.time()
        try:
            if site == "gemini":
                prompt = _session(cfg, image, aspect, vo, out, timeout, log, evidence, extras)
            elif site == "chatgpt":
                prompt = _session_chatgpt(cfg, image, aspect, vo, out, timeout, log, evidence, extras)
            elif site in ("hf", "bing"):
                if image and described is None: described = describe_local(cfg, image, vo, log)
                s2 = dict(sec, described_prompt=described) if described else sec
                prompt = (_session_hf if site == "hf" else _session_bing)(cfg, s2, aspect, out, timeout, log, evidence, extras)
        except Skip as s_:
            cool = int(float(cfg.get("imagegen_cooldown_hours", 6)) * 3600) if s_.cool == -1 else s_.cool
            _job_skip[site] = s_.why
            if cool: _cool(cfg, sd, cool, s_.why, site)
            log(f"  {site} skipped: {s_.why}" + (f" (retried after {cool // 3600} h)" if cool else " (rest of this job)") + "; next service")
            continue
        except Exception as e:
            if str(e) == "cancelled": raise
            out.unlink(missing_ok=True)
            fails = sorted(d.glob(f"{key}_{site}_*_fail.png"))
            log(f"  {site} failed ({str(e).splitlines()[0][:200]})" + (f"; screenshot {fails[-1]}" if fails else "") + "; next service")
            continue
        got = [out] + [x for x in extras if x.is_file()]
        if cfg.get("imagegen_rotate", False) and site not in (first, pref):   # the video's service is out: the rest of this video uses the one that worked (one look per video)
            try: (d / "provider.txt").write_text(site, encoding="utf-8")
            except OSError: pass
        used[key] = {"prompt": prompt, "site": site, "files": [x.name for x in got], "from_screenshot": bool(image),
                     "made": time.strftime("%Y-%m-%d %H:%M")}
        led.write_text(json.dumps(used, indent=1), encoding="utf-8")
        out.with_suffix(".prompt.txt").write_text(prompt, encoding="utf-8")
        _site["cur"] = site
        log(f"  {site}: {len(got)} image(s) ready ({time.time() - t0:.0f}s)")
        return [(x, prompt) for x in got]
    return []


def tag(site=None):
    return f"GENERATED · {(site or _site['cur']).upper()}"
```


## app/studio/footage.py lines 236-252
```python

def _vision(cfg, image, prompt):
    prov = cfg.get("vet_provider", "local")
    if prov == "local":
        url = cfg.get("ollama_url", "http://127.0.0.1:11434").rstrip("/")
        b64 = base64.b64encode(Path(image).read_bytes()).decode()
        r = requests.post(url + "/api/chat", timeout=300, json={"model": cfg.get("vet_model", "qwen2.5vl:7b"), "stream": False, "keep_alive": "5m",
            "messages": [{"role": "user", "content": prompt, "images": [b64]}], "options": {"temperature": 0.1, "num_predict": 200}})
        if r.status_code != 200: raise RuntimeError(f"Ollama vision error {r.status_code}: {r.text[:200]}")
        return r.json()["message"]["content"]
    from .llm import vision
    c = dict(cfg); c["qa_provider"] = prov
    return vision(c, image, prompt)

def ensure_vet_model(cfg, log):
    if cfg.get("vet_provider", "local") != "local": return
    url = cfg.get("ollama_url", "http://127.0.0.1:11434").rstrip("/"); model = cfg.get("vet_model", "qwen2.5vl:7b")
```


## app/studio/short.py lines 369-480
```python
def do_fallback(job, plan, cfg, wg, log, stop, full=False, dbg=None):
    """The visual ladder for beats that step 1 didn't cover (stock footage for generic beats, real photos for subject beats):
    2a cloud still (Gemini -> ChatGPT, GENERATED · CLOUD) -> 2b WanGP still -> 3 WanGP image-to-video (on click only) -> 4 parallax of the
    still (PARALLAX) -> 5 3D reconstruction / headline card.
    Every step is checked against the beat's narration (ladder.py); a failed check escalates. A beat's map backdrop (geography)
    is kept as its first visual. Writes short/fallback.json = {beat: [bg items]} and logs one ladder line per beat.
    Also writes short/fallback/chains.json (every beat's decision chain: stock found, what was tried and why it failed, what is used)
    for the debugger and the trace. dbg (debug.Debugger): safe points for 'Pause now'; with breakpoints on, beats run one at a time
    and each is checked after its visuals are decided (normal runs keep the batched GPU order)."""
    from . import flow as _flow, imagegen as _imagegen; _flow.reset(); _imagegen.reset()   # job-wide skips start clear for every run
    from . import depth, coherence, photos, ladder, cloudgen, illustrate, physics
    v2 = bool(cfg.get("ladder_v2"))   # visual ladder v2 (graphics / physics / CapCut); off = the ladder below, unchanged
    sd = job / "short"; fd = sd / "fallback"; fd.mkdir(parents=True, exist_ok=True)
    tm = json.loads((sd / "timings.json").read_text(encoding="utf-8"))
    pick = json.loads((sd / "stock" / "pick.json").read_text(encoding="utf-8"))
    for bid, cs in list(pick.items()):   # a clip whose file is missing or broken (failed download) is not footage
        ok = [c for c in cs if media.ok(sd / "stock" / "clips" / f"{c['id']}.mp4", 0.3)]
        if len(ok) != len(cs):
            log(f"  {bid}: {len(cs) - len(ok)} stock clip(s) missing or unreadable; not used")
            for c in cs:
                if c not in ok: (sd / "stock" / "clips" / f"{c['id']}.mp4").unlink(missing_ok=True)
            pick[bid] = ok
    (sd / "stock" / "pick.json").write_text(json.dumps(pick, indent=1), encoding="utf-8")
    fsf = sd / "stock" / "footage.json"; fst = json.loads(fsf.read_text(encoding="utf-8")) if fsf.exists() else {}
    ff = sd / "fallback.json"; out = json.loads(ff.read_text(encoding="utf-8")) if ff.exists() else {}
    cf = fd / "chains.json"; chs = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {}
    def save_out(): ff.write_text(json.dumps(out, indent=1), encoding="utf-8"); cf.write_text(json.dumps(chs, indent=1), encoding="utf-8")
    demoted = {}   # beat -> the stock set aside for its source clip (given back if the clip fails)
    if v2 and cfg.get("source_clips_auto", True) and cfg.get("source_visuals", True) and cfg.get("source_over_stock", True):
        # A beat about a specific story moment the source itself shows: its own footage beats a generic stock clip
        # (a laptop for a model launch, test tubes for an enzyme). The strongest caption matches (within the source-clip
        # budget) set their generic stock aside, so the Source Clip rung (2) runs for them.
        from . import source_visuals
        cand = []
        for x in plan["sections"]:
            if x.get("cta") or x["id"] not in tm or any(c.get("own") for c in pick.get(x["id"], [])): continue
            r = source_visuals.auto_request(job, x, min_overlap=int(cfg.get("source_over_stock_min", 4)))
            if r: cand.append((r["match"], x["id"], r["start"]))
        cap = max(0, min(2, int(cfg.get("source_visual_max_uses", 2))))
        for score, bid, start in sorted(cand, reverse=True)[:cap]:
            if pick.get(bid):
                log(f"  {bid}: generic stock set aside: the source itself covers this beat (caption cue at {start:.1f}s, {score} shared words)")
                demoted[bid] = pick[bid]; pick[bid] = []
        if demoted: (sd / "stock" / "pick.json").write_text(json.dumps(pick, indent=1), encoding="utf-8")
    allneeds = base_needs = _needs(plan, tm, pick, sd, cfg)
    if full:   # Review every beat: every beat gets the whole menu, also the ones stock footage already covers (one slot)
        allneeds = {s["id"]: allneeds.get(s["id"], 1) for s in plan["sections"] if not s.get("cta") and s["id"] in tm}
    needs = {k: v for k, v in allneeds.items() if k not in out}
    beats = [s for s in plan["sections"] if not s.get("cta") and s["id"] in tm]
    def srej(bid): return [{"id": r.get("id"), "why": r.get("why", "")} for r in fst.get("rejected", {}).get(bid, [])][:12]
    def stock_beat(sec):
        bid = sec["id"]
        if bid in chs: return
        k = len(pick.get(bid, []))
        mine = any(c.get("own") for c in pick.get(bid, []))
        chs[bid] = {"n": int(bid[1:]) + 1, "vo": sec["vo"], "stock_found": k, "chain": ["your footage" if mine else f"stock ({k} clip(s), coherent)"], "uses": ["yours" if mine else "stock"],
                    "failed": [], "stock_rejected": srej(bid), "photos_rejected": []}
    def info(sec):
        c = chs.get(sec["id"], {})
        return {"bid": sec["id"], "n": int(sec["id"][1:]) + 1, "vo": sec["vo"], "stock_found": c.get("stock_found", len(pick.get(sec["id"], []))),
                "uses": c.get("uses", []), "failed": c.get("failed", [])}
    if v2: log("Visual ladder v2 per beat (1 stock -> 2 source clip -> 3 image generator (Gemini: describe the source screenshot, "
               "write a prompt, generate a new image) -> 4 source parallax (rembg + Remotion) -> 5 Google Flow (paid, last) -> "
               "6 WanGP (on demand) -> 7 physics -> 8 Remotion graphics -> 9 headline card):")
    else: log("Visual ladder per beat (1 stock/photo -> 2 cloud still -> 3 WanGP still -> 4 parallax -> 5 illustration / silhouette -> 6 reconstruction / headline; animate on click):")
    for s in beats:   # beats step 1 covered on its own
        if s["id"] in base_needs: continue
        log(f"  {s['id']}: " + ("your footage" if any(c.get("own") for c in pick.get(s["id"], [])) else f"stock ({len(pick.get(s['id'], []))} clip(s), coherent)")); _safe(log, f"{s['id']} stock", lambda: stock_beat(s))
    if not needs and not dbg:
        log("  no other beats need visuals"); save_out(); return
    ents = json.loads((job / "entities.json").read_text(encoding="utf-8")) if (job / "entities.json").exists() else []
    phases = coherence.beat_phases([x for x in plan["sections"] if not x.get("cta")])
    pre, step1, slots, prej = {}, {}, [], {}

    def prepare(s):
        n = needs[s["id"]]; items = []; rej = []
        from . import source_visuals
        raw_source = _safe(log, f"{s['id']} source clip", lambda: source_visuals.make(cfg, job, sd, s, log))
        source = None
        if raw_source:
            source = dict(raw_source); source["src"] = _rel_sd(source.pop("path"), sd)
            items.append(source)
        elif s["id"] in demoted:   # the source clip failed: the beat gets back the stock set aside for it
            pick[s["id"]] = demoted.pop(s["id"])
            (sd / "stock" / "pick.json").write_text(json.dumps(pick, indent=1), encoding="utf-8")
            log(f"  {s['id']}: source clip failed; the stock set aside for it is back ({len(pick[s['id']])} clip(s))")
            needs.pop(s["id"], None)
            _safe(log, f"{s['id']} stock", lambda: stock_beat(s))
            return
        snap = None
        if v2 and len(items) < n and cfg.get("imagegen_on", True):   # rung 3: free image generators (describe the source screenshot -> new image)
            from . import imagegen
            snap = _safe(log, f"{s['id']} source screenshot", lambda: source_visuals.snapshot(cfg, job, sd, s, log, source_item=raw_source))
            want = n - len(items)   # a beat that needs several visuals gets a second Gemini image (another angle / close-up), not Flow
            imgs = _safe(log, "image generators", lambda: imagegen.generate_many(cfg, sd, s, s["id"], log, aspect="9:16",
                                                                                image=(snap or {}).get("path"), count=want), []) or []
            for k, (img, _p) in enumerate(imgs):   # rung 4: source parallax (rembg cut-out + Remotion 2.5D)
                lay = _safe(log, f"{s['id']} parallax", lambda: depth.cutout_layers(img, sd / "imagegen" / f"{s['id']}_px{k or ''}", log))
                if lay:
                    items.append({"type": "layers", "layers": [_rel_sd(p_, sd) for p_ in lay], "tag": imagegen.tag(),
                                  "rung": "imagegen", "site": imagegen.last_site(), "described": bool(snap), "variant": k})
                else:
                    items.append({"type": "image", "src": _rel_sd(img, sd), "tag": imagegen.tag(), "rung": "imagegen", "site": imagegen.last_site(), "variant": k})
        if v2 and cfg.get("flow_on", True) and not items:   # rung 5: Google Flow (paid, Google account): only a beat nothing else could fill
            from . import flow
            clip = _safe(log, "flow", lambda: flow.generate(cfg, sd, s, f"{s['id']}_flow", log, aspect="9:16"))
            if clip:
                items.append({"type": "video", "src": _rel_sd(clip, sd), "secs": round(media.dur(clip), 2), "rate": 1.0, "freeze": True,
                              "tag": "GENERATED · FLOW", "rung": "flow"})
        bd = s.get("backdrop") or {"kind": "headline", "kicker": "", "text": s["vo"][:60], "sub": ""}
        if bd.get("kind") == "map" and len(items) < n: items.append({"type": "graphic", "g": bd, "rung": "map"})
        have = len(pick.get(s["id"], []))
```


## app/studio/render.py lines 314-373
```python
            else: log(f"Motion {v['id']} done")

def do_stills(job, plan, cfg, wg, log, stop):
    d = job / "stills"; d.mkdir(exist_ok=True); seed = 1000; n = 0
    todo = [(v, vo_slice(plan, s, v) if cfg.get("ladder_v2") else s.get("vo", "")) for s in plan["sections"] for v in s["visuals"] if v["type"] == "still" and not v.get("stock")]
    sec_of = {v["id"]: s for s in plan["sections"] for v in s["visuals"]}
    snap_cache = {}
    def section_snapshot(sec):
        """A frame of this section's source clip, for the image generators to describe (rung 3)."""
        if sec["id"] in snap_cache: return snap_cache[sec["id"]]
        res = None
        sv = next((x for x in sec["visuals"] if x.get("stock_src") == "source" and x.get("stock")), None)
        if sv:
            from . import source_visuals
            clip = job / sv["stock"]
            item = {"type": "video" if clip.suffix == ".mp4" else "image", "path": str(clip), "secs": media.dur(clip) if clip.suffix == ".mp4" else 0}
            try: res = source_visuals.snapshot(cfg, job, _ws(job), {"id": sec["id"]}, log, source_item=item)
            except Exception as e: log(f"  {sec['id']}: source screenshot failed ({str(e)[:100]})")
        snap_cache[sec["id"]] = res
        return res
    from .pipeline import progress
    for i, (v, vo) in enumerate(todo):
        progress(job, i + 1, len(todo))
        seed += 1; out = d / f"{v['id']}.jpg"
        if out.exists(): continue
        if stop(): raise RuntimeError("cancelled")
        if cfg.get("ladder_v2") and cfg.get("imagegen_on", True):   # rung 3: free image generators, rung 4: rembg parallax
            from . import imagegen, depth
            snap = section_snapshot(sec_of[v["id"]]) if v["id"] in sec_of else None
            beat = {"id": v["id"], "vo": vo, "still_prompt": v.get("prompt", ""), "queries": v.get("queries") or []}
            try: img, site, _p = imagegen.generate(cfg, _ws(job), beat, "L_" + v["id"], log, aspect="16:9", image=(snap or {}).get("path"))
            except Exception as e:
                if str(e) == "cancelled": raise
                log(f"  {v['id']}: image generators failed ({str(e)[:100]}); next rung"); img = None
            if img:
                shutil.copy(img, out); v["tag"] = imagegen.tag(site); v.pop("g", None)
                try:
                    lay = depth.cutout_layers(out, d / f"{v['id']}_px", log, size=(1920, 1080))
                    v["layers"] = [str(Path(x).relative_to(job)).replace("\\", "/") for x in lay]
                except Exception as e: log(f"  {v['id']}: parallax failed ({str(e)[:100]}); the image is shown as a still")
                log(f"  {v['id']}: new image from {site}" + (" (described from the source)" if snap else "")); n += 1; continue
        if cfg.get("ladder_v2") and cfg.get("flow_on", True):   # rung 5: Google Flow (paid credits), last resort for AI video
            from . import flow
            try: clip = flow.generate(cfg, _ws(job), {"id": v["id"], "vo": vo, "still_prompt": v.get("prompt", ""), "queries": v.get("queries") or []},
                                      "L_" + v["id"], log, aspect="16:9")
            except Exception as e:
                if str(e) == "cancelled": raise
                log(f"  {v['id']}: flow failed ({str(e)[:100]}); next rung"); clip = None
            if clip:
                md = job / "motion"; md.mkdir(exist_ok=True)
                shutil.copy(clip, md / f"{v['id']}.mp4"); v["type"] = "motion"; v["tag"] = "GENERATED · FLOW"; v.pop("g", None)
                log(f"  {v['id']}: Google Flow clip"); n += 1; continue
        if cloud_still(cfg, job, v, vo, log): continue   # cloud first
        if cfg.get("ladder_v2"):   # v2: WanGP still for atmospheric beats, then graphics -> physics -> illustration -> headline
            from . import illustrate
            lock = illustrate.wangp_lock({"id": v["id"], "vo": vo, "still_prompt": v.get("prompt", "")}, _ents(job))
            from . import physics
            if not lock and physics.action({"vo": vo, "subject": v.get("subject")})[0]: lock = "action"   # animate an action, no still
            try: alive = (not lock) and wg.alive()
            except Exception: alive = False
```


## app/server.py lines 1-13
```python
"""Video Studio: YouTube link, audio file (e.g. NotebookLM) or text in -> long explainer and/or a 2-3 min vertical Short out. Runs locally."""
import os, sys, json, socket
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, abort
sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio import config
from studio.pipeline import Studio, STAGES, stages_for
from studio.wangp import WanGP

VS_PORT = int(os.environ.get("PORT") or 42021)   # the launcher sets PORT; unset = live (42021) as before
app = Flask(__name__, static_folder="static"); studio = Studio(port=VS_PORT)

@app.get("/")
```

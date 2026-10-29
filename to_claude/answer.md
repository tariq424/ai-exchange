One-line fix: add a 42022-only local narration-fit gate for generated/cached images with audit + rejected-evidence handling, force Google image providers behind non-Google providers, and add `hf_token` vault/redaction/atomic-migration support.

## Patch

### app/studio/config.py

```diff
@@
     "script_provider": "deepseek",
     "qa_provider": "off",
+    "hf_token": "",
+    "catalogue_reuse_test": False,   # default-off local-catalogue-only test flag (never Google Photos)
@@
-SECRETS = ("anthropic_api_key", "zai_api_key", "deepseek_api_key", "aisstream_api_key")
+SECRETS = ("anthropic_api_key", "zai_api_key", "deepseek_api_key", "aisstream_api_key", "hf_token")
@@
 def _raw():
     if CFG.exists():
         try: return json.loads(CFG.read_text(encoding="utf-8"))
         except Exception: pass
     return {}
 
+def _atomic_write(path, text):
+    import os, tempfile
+    path = Path(path)
+    path.parent.mkdir(parents=True, exist_ok=True)
+    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
+    try:
+        with os.fdopen(fd, "w", encoding="utf-8") as f:
+            f.write(text)
+            f.flush()
+            os.fsync(f.fileno())
+        os.replace(tmp, path)
+    except Exception:
+        try: os.unlink(tmp)
+        except OSError: pass
+        raise
+
 def _migrate():
-    """Move any plain-text keys from settings.json into the Windows vault."""
-    raw = _raw(); changed = False
+    """Move plaintext secrets into the OS vault.
+
+    Vault writes are verified before settings.json is rewritten. The rewrite is
+    atomic and keeps no plaintext backup. Returns the number of settings keys moved.
+    """
+    raw = _raw()
+    new_raw = dict(raw)
+    migrated = 0
     for k in SECRETS:
         v = raw.get(k, "")
         if v and v != "vault":
-            _vault_set(k, v); raw[k] = "vault"; changed = True
-    if changed: CFG.write_text(json.dumps(raw, indent=1), encoding="utf-8")
+            if k == "hf_token":
+                kr = _kr()
+                if kr is None:
+                    raise RuntimeError("Windows Credential Manager unavailable; refusing to migrate hf_token")
+            _vault_set(k, v)
+            if _vault_get(k) != v:
+                raise RuntimeError("vault verification failed for " + k)
+            new_raw[k] = "vault"
+            migrated += 1
+    if migrated:
+        _atomic_write(CFG, json.dumps(new_raw, indent=1))
+    return migrated
+
+def migrate_secrets():
+    """Safe local entry point for moving plaintext secrets into the OS vault."""
+    return _migrate()
 
 def load():
     d = dict(DEFAULTS)
     try: _migrate()
     except Exception: pass
     raw = _raw(); d.update(raw)
     import os
     for k in SECRETS:   # Windows vault; on the Linux worker the service's environment (VS_<NAME>) or a plain value
         plain = raw.get(k) if raw.get(k) not in (None, "", "vault") else ""
-        d[k] = _vault_get(k) or os.environ.get("VS_" + k.upper(), "") or plain
-    if os.environ.get("VS_HF_TOKEN") and not d.get("hf_token"): d["hf_token"] = os.environ["VS_HF_TOKEN"]
+        if k == "hf_token":
+            d[k] = _vault_get(k) or os.environ.get("VS_HF_TOKEN", "")
+        else:
+            d[k] = _vault_get(k) or os.environ.get("VS_" + k.upper(), "") or plain
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
-    CFG.write_text(json.dumps(raw, indent=1), encoding="utf-8")
+    _atomic_write(CFG, json.dumps(raw, indent=1))
     return load()
```

### app/studio/imagegen.py

```diff
@@
 import json
+import hashlib
+import os
 import re
 import time
@@
 PROVIDERS = ("gemini", "chatgpt", "bing", "hf")
+GOOGLE_IMAGE_PROVIDERS = ("gemini",)
+FIT_AUDIT = "fit_audit.json"
@@
 def last_site():
     return _site["cur"]
+
+def _port_from_env(env=None):
+    raw = (os.environ if env is None else env).get("PORT", "")
+    if raw is None:
+        return None
+    raw = str(raw).strip()
+    if not raw:
+        return None
+    try:
+        return int(raw)
+    except ValueError:
+        return None
+
+def narration_fit_on(env=None):
+    """The new narration/image fit check is enforced only on test port 42022.
+
+    Unset PORT, malformed PORT, and every other port keep the old behavior.
+    """
+    return _port_from_env(env) == 42022
+
+def _stable_non_google_first(order):
+    non_google = [x for x in order if x not in GOOGLE_IMAGE_PROVIDERS]
+    google = [x for x in order if x in GOOGLE_IMAGE_PROVIDERS]
+    return non_google + google
```

Insert these helpers after `_has_text` and before the ladder entry:

```python
FIT_PROMPT = ('Does this image directly illustrate the narration below? Ignore on-screen text, logos, watermarks, captions '
              'and incidental labels. Reply with JSON only: {"match": "yes" or "no", "reason": "<a few words>"}\n\nNarration: ')

def _empty_fit_audit():
    return {"counts": {"checked": 0, "accepted": 0, "rejected_for_narration": 0, "unavailable": 0}, "entries": {}}

def _fit_audit_file(d):
    return d / FIT_AUDIT

def _load_fit_audit(d):
    p = _fit_audit_file(d)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else _empty_fit_audit()
    except (OSError, ValueError):
        return _empty_fit_audit()

def _save_fit_audit(d, audit):
    try:
        p = _fit_audit_file(d)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(audit, indent=1), encoding="utf-8")
    except OSError:
        pass

def _fit_fingerprint(sec, source_image, model, prompt, image_path=None):
    h = hashlib.sha256()
    h.update(((sec.get("vo") or sec.get("still_prompt") or "")).encode("utf-8", "replace"))

    def stat_fp(p):
        try:
            st = Path(p).stat()
            return f"{st.st_mtime_ns}:{st.st_size}".encode("utf-8")
        except OSError:
            return b"missing"

    h.update(b"\0source")
    h.update(stat_fp(source_image) if source_image else b"none")
    h.update(b"\0model")
    h.update((model or "").encode("utf-8", "replace"))
    h.update(b"\0prompt")
    h.update((prompt or "").encode("utf-8", "replace"))
    if image_path:
        h.update(b"\0candidate")
        h.update(stat_fp(image_path))
    return h.hexdigest()

def _local_fit_vision(cfg, image, prompt):
    local_cfg = dict(cfg)
    local_cfg["vet_provider"] = "local"
    from .footage import _vision
    return _vision(local_cfg, image, prompt)

def _fit_check_now(cfg, image_path, sec, log):
    vo = (sec.get("vo") or sec.get("still_prompt") or "").strip()
    if not vo:
        return "unavailable", "no narration"
    try:
        from .llm import parse_json
        raw = _local_fit_vision(cfg, image_path, FIT_PROMPT + vo[:2000])
        j = parse_json(raw)
        match = str(j.get("match", "")).strip().lower()
        reason = str(j.get("reason") or "").strip()[:80]
        if match in ("yes", "true", "1"):
            return "accepted", reason or "image matches narration"
        if match in ("no", "false", "0"):
            return "rejected", reason or "narration mismatch"
        log(f"  fit: malformed local vision verdict ({raw[:120]!r}); counted as unavailable")
        return "unavailable", "malformed verdict"
    except Exception as e:
        if str(e) == "cancelled":
            raise
        log(f"  fit: local vision unavailable ({str(e)[:120]})")
        return "unavailable", str(e)[:80]

def _keep_fit_rejected(img, d, log):
    try:
        rdir = d / "_rejected"
        rdir.mkdir(parents=True, exist_ok=True)
        dest = rdir / (img.stem + "_fit_" + time.strftime("%Y%m%d_%H%M%S") + img.suffix)
        if dest.exists():
            dest = rdir / (img.stem + "_fit_" + str(time.time_ns()) + img.suffix)
        img.replace(dest)
        return dest
    except OSError as e:
        log(f"    fit: could not keep rejected image {img.name} for evidence ({str(e)[:80]})")
        return None

def _fit_verdict_for(cfg, d, sec, image_path, prompt, log, provider="imagegen", source_image=None):
    audit = _load_fit_audit(d)
    if not isinstance(audit, dict):
        audit = _empty_fit_audit()
    audit.setdefault("counts", {})
    audit.setdefault("entries", {})
    for c in ("checked", "accepted", "rejected_for_narration", "unavailable"):
        audit["counts"].setdefault(c, 0)

    model = cfg.get("vet_model", "qwen2.5vl:7b")
    fp = _fit_fingerprint(sec, source_image, model, prompt, image_path)
    key = Path(image_path).name

    ent = audit["entries"].get(key)
    if ent and ent.get("fp") == fp and ent.get("verdict") in ("accepted", "rejected") and Path(image_path).is_file():
        log(f"  fit[{provider}] {key}: cached {ent['verdict']}: {ent.get('reason', '')}")
        return ent["verdict"], ent.get("reason", "")

    verdict, reason = _fit_check_now(cfg, image_path, sec, log)
    audit["entries"][key] = {
        "fp": fp,
        "verdict": verdict,
        "reason": reason,
        "provider": provider,
        "image": key,
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    counts = audit["counts"]
    counts["checked"] += 1
    if verdict == "accepted":
        counts["accepted"] += 1
    elif verdict == "rejected":
        counts["rejected_for_narration"] += 1
    else:
        counts["unavailable"] += 1
    _save_fit_audit(d, audit)
    log(f"  fit[{provider}] {key}: {verdict}: {reason}")
    log(f"  fit audit: checked={counts['checked']} accepted={counts['accepted']} "
        f"rejected_for_narration={counts['rejected_for_narration']} unavailable={counts['unavailable']}")
    return verdict, reason
```

Replace `generate_many` with the following function:

```python
def generate_many(cfg, sd, sec, key, log, aspect="9:16", image=None, count=1):
    """-> [(image_path, prompt), ...] (first = the scene, then variants), or []. Never raises (cancel aside).
    The video's service first (rotation), then the others if it fails; last_site() says which one made them.
    On PORT=42022 only, every generated/resumed image also has to pass a local narration-fit check before
    it can be selected; rejected and unavailable evidence is kept under imagegen/_rejected."""
    count = max(1, min(int(count), 1 + len(VARIANTS), int(cfg.get("imagegen_per_beat", 1))))
    if not cfg.get("imagegen_on", True):
        return []
    order = [x for x in (cfg.get("imagegen_providers") or PROVIDERS) if x in PROVIDERS] or ["gemini"]
    order = _stable_non_google_first(order)
    fit_on = narration_fit_on()
    source_image = str(image) if image and Path(image).is_file() else None
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
            if not fit_on:
                return [(x, used[key].get("prompt", "")) for x in files]
            kept = []
            for img in files:
                verdict, reason = _fit_verdict_for(cfg, d, sec, img, used[key].get("prompt", ""), log, site, source_image=source_image)
                if verdict == "accepted":
                    kept.append(img)
                else:
                    _keep_fit_rejected(img, d, log)
                    log(f"  fit: cached {site}: {img.name}: {verdict} ({reason}); evidence kept")
            if kept:
                used[key]["files"] = [x.name for x in kept]
                led.write_text(json.dumps(used, indent=1), encoding="utf-8")
                return [(x, used[key].get("prompt", "")) for x in kept]
            used.pop(key, None)
            led.write_text(json.dumps(used, indent=1), encoding="utf-8")
            log(f"  fit: cached {site} image(s) failed narration fit; trying next provider")

    cap = int(cfg.get("imagegen_max_per_video", 8))
    if len(used) >= cap:
        log(f"  image generators: {cap} images already made for this video; next rung"); return []
    if not cfg.get("imagegen_rotate", False):   # fixed priority (default): the list order, every beat
        pref, first, tries = None, order[0], list(order)
    else:   # rotation: one service per video, taking turns (imagegen_first tried before it)
        pref = cfg.get("imagegen_first") if cfg.get("imagegen_first") in order else None
        first = _job_provider(cfg, sd, [x for x in order if x != pref] or order)
        tries = ([pref] if pref else []) + [first] + [x for x in order if x not in (first, pref)]
        tries = _stable_non_google_first(tries)
    image = source_image
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
        if fit_on:
            kept = []
            for img in got:
                verdict, reason = _fit_verdict_for(cfg, d, sec, img, prompt, log, site, source_image=source_image)
                if verdict == "accepted":
                    kept.append(img)
                else:
                    _keep_fit_rejected(img, d, log)
                    log(f"  fit: {site}: {img.name}: {verdict} ({reason}); evidence kept")
            if kept:
                got = kept
            else:
                log(f"  fit: {site}: all image(s) failed narration fit; next provider")
                continue

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
```

### tests/test_codex_fit_vault.py

```diff
--- /dev/null
+++ b/tests/test_codex_fit_vault.py
@@
+import json
+from pathlib import Path
+
+import pytest
+from PIL import Image
+
+from studio import config, imagegen
+
+
+def _img(path, size=(16, 16)):
+    Image.new("RGB", size, (120, 130, 140)).save(path, "JPEG", quality=90)
+
+
+class FakeVault:
+    def __init__(self):
+        self.data = {}
+
+    def get_password(self, service, name):
+        return self.data.get(name, "")
+
+    def set_password(self, service, name, value):
+        self.data[name] = value
+
+    def delete_password(self, service, name):
+        self.data.pop(name, None)
+
+
+def test_narration_fit_port_isolation(monkeypatch):
+    monkeypatch.delenv("PORT", raising=False)
+    assert imagegen.narration_fit_on() is False
+
+    monkeypatch.setenv("PORT", "42021")
+    assert imagegen.narration_fit_on() is False
+
+    monkeypatch.setenv("PORT", "42022")
+    assert imagegen.narration_fit_on() is True
+
+    monkeypatch.setenv("PORT", "not-a-port")
+    assert imagegen.narration_fit_on() is False
+
+
+def test_stable_non_google_first():
+    assert imagegen._stable_non_google_first(["gemini", "hf", "chatgpt"]) == ["hf", "chatgpt", "gemini"]
+    assert imagegen._stable_non_google_first(["bing", "chatgpt", "gemini"]) == ["bing", "chatgpt", "gemini"]
+
+
+def test_generate_many_rejects_fresh_mismatch_and_advances(monkeypatch, tmp_path):
+    monkeypatch.setenv("PORT", "42022")
+    sd = tmp_path / "ws"
+    d = sd / "imagegen"
+    d.mkdir(parents=True)
+    cfg = {
+        "imagegen_on": True,
+        "imagegen_providers": ["hf", "chatgpt"],
+        "imagegen_rotate": False,
+        "imagegen_max_per_video": 8,
+        "imagegen_per_beat": 1,
+        "imagegen_timeout": 60,
+        "imagegen_text_check": False,
+        "imagegen_delay_secs": [0, 0],
+        "imagegen_state": str(sd / "state.json"),
+        "jobs_dir": str(tmp_path),
+    }
+    monkeypatch.setattr(imagegen, "_pause", lambda *a, **k: None)
+    monkeypatch.setattr(imagegen, "_answered", lambda *a, **k: None)
+
+    def fake_hf(cfg, sec, aspect, out, timeout, log, evidence, extras=()):
+        _img(out)
+        return "hf prompt"
+
+    def fake_chatgpt(cfg, image, aspect, vo, out, timeout, log, evidence, extras):
+        _img(out)
+        return "chatgpt prompt"
+
+    monkeypatch.setattr(imagegen, "_session_hf", fake_hf)
+    monkeypatch.setattr(imagegen, "_session_chatgpt", fake_chatgpt)
+
+    def fake_fit(cfg, image_path, sec, log):
+        if "hf" in str(image_path):
+            return "rejected", "does not match narration"
+        return "accepted", "matches narration"
+
+    monkeypatch.setattr(imagegen, "_fit_check_now", fake_fit)
+
+    res = imagegen.generate_many(cfg, sd, {"id": "b1", "vo": "the moon"}, "b1", lambda *a, **k: None, count=1)
+
+    assert len(res) == 1
+    assert "chatgpt" in res[0][0].name
+    assert len(list((d / "_rejected").glob("b1_hf*"))) == 1
+    audit = json.loads((d / "fit_audit.json").read_text(encoding="utf-8"))
+    assert audit["counts"] == {"checked": 2, "accepted": 1, "rejected_for_narration": 1, "unavailable": 0}
+
+
+def test_generate_many_resumed_cached_rejection_advances(monkeypatch, tmp_path):
+    monkeypatch.setenv("PORT", "42022")
+    sd = tmp_path / "ws"
+    d = sd / "imagegen"
+    d.mkdir(parents=True)
+    cached = d / "b1_hf.jpg"
+    _img(cached)
+    (d / "gemini_usage.json").write_text(
+        json.dumps({"b1": {"site": "hf", "files": ["b1_hf.jpg"], "prompt": "old prompt"}}),
+        encoding="utf-8",
+    )
+    cfg = {
+        "imagegen_on": True,
+        "imagegen_providers": ["hf", "chatgpt"],
+        "imagegen_rotate": False,
+        "imagegen_max_per_video": 8,
+        "imagegen_per_beat": 1,
+        "imagegen_timeout": 60,
+        "imagegen_text_check": False,
+        "imagegen_delay_secs": [0, 0],
+        "imagegen_state": str(sd / "state.json"),
+        "jobs_dir": str(tmp_path),
+    }
+    monkeypatch.setattr(imagegen, "_pause", lambda *a, **k: None)
+    monkeypatch.setattr(imagegen, "_answered", lambda *a, **k: None)
+    monkeypatch.setattr(imagegen, "_session_hf", lambda *a, **k: pytest.fail("cached hf should not regenerate"))
+
+    def fake_chatgpt(cfg, image, aspect, vo, out, timeout, log, evidence, extras):
+        _img(out)
+        return "chatgpt prompt"
+
+    monkeypatch.setattr(imagegen, "_session_chatgpt", fake_chatgpt)
+    monkeypatch.setattr(
+        imagegen,
+        "_fit_check_now",
+        lambda cfg, img, sec, log: ("rejected", "narration mismatch") if "hf" in str(img) else ("accepted", "ok"),
+    )
+
+    res = imagegen.generate_many(cfg, sd, {"id": "b1", "vo": "the moon"}, "b1", lambda *a, **k: None, count=1)
+
+    assert len(res) == 1
+    assert "chatgpt" in res[0][0].name
+    assert len(list((d / "_rejected").glob("b1_hf*"))) == 1
+    audit = json.loads((d / "fit_audit.json").read_text(encoding="utf-8"))
+    assert audit["counts"]["checked"] == 2
+    assert audit["counts"]["rejected_for_narration"] == 1
+    assert audit["counts"]["accepted"] == 1
+
+
+def test_fit_verdict_unavailable_counts_fail_closed(monkeypatch, tmp_path):
+    monkeypatch.setenv("PORT", "42022")
+    d = tmp_path / "imagegen"
+    d.mkdir()
+    img = d / "b1.jpg"
+    _img(img)
+    cfg = {}
+
+    def boom(cfg, image_path, sec, log):
+        raise RuntimeError("ollama down")
+
+    monkeypatch.setattr(imagegen, "_fit_check_now", boom)
+
+    verdict, reason = imagegen._fit_verdict_for(cfg, d, {"vo": "narration"}, img, "prompt", lambda *a, **k: None, "hf")
+
+    assert verdict == "unavailable"
+    assert "ollama down" in reason
+    audit = json.loads((d / "fit_audit.json").read_text(encoding="utf-8"))
+    assert audit["counts"]["unavailable"] == 1
+    assert audit["counts"]["rejected_for_narration"] == 0
+
+
+def test_fit_verdict_cancelled_propagates(monkeypatch, tmp_path):
+    monkeypatch.setenv("PORT", "42022")
+    d = tmp_path / "imagegen"
+    d.mkdir()
+    img = d / "b1.jpg"
+    _img(img)
+
+    def cancel(cfg, image_path, sec, log):
+        raise RuntimeError("cancelled")
+
+    monkeypatch.setattr(imagegen, "_fit_check_now", cancel)
+
+    with pytest.raises(RuntimeError, match="cancelled"):
+        imagegen._fit_verdict_for({}, d, {"vo": "narration"}, img, "prompt", lambda *a, **k: None, "hf")
+
+
+def test_hf_token_migration_verifies_before_rewrite(monkeypatch, tmp_path):
+    cfgfile = tmp_path / "settings.json"
+    cfgfile.write_text(json.dumps({"hf_token": "hf_plain_1234"}), encoding="utf-8")
+    monkeypatch.setattr(config, "CFG", cfgfile)
+    vault = FakeVault()
+    monkeypatch.setattr(config, "_kr", lambda: vault)
+    monkeypatch.delenv("VS_HF_TOKEN", raising=False)
+
+    d = config.load()
+
+    assert vault.data["hf_token"] == "hf_plain_1234"
+    raw = json.loads(cfgfile.read_text(encoding="utf-8"))
+    assert raw["hf_token"] == "vault"
+    assert "hf_plain_1234" not in cfgfile.read_text(encoding="utf-8")
+    assert d["hf_token"] == "hf_plain_1234"
+
+
+def test_hf_token_fail_closed_when_vault_unavailable(monkeypatch, tmp_path):
+    cfgfile = tmp_path / "settings.json"
+    cfgfile.write_text(json.dumps({"hf_token": "hf_plain_9999"}), encoding="utf-8")
+    monkeypatch.setattr(config, "CFG", cfgfile)
+    monkeypatch.setattr(config, "_kr", lambda: None)
+    monkeypatch.delenv("VS_HF_TOKEN", raising=False)
+
+    d = config.load()
+
+    assert d["hf_token"] == ""
+    raw = json.loads(cfgfile.read_text(encoding="utf-8"))
+    assert raw["hf_token"] == "hf_plain_9999"  # migration refused: no rewritten plaintext backup
+
+
+def test_hf_token_env_fallback(monkeypatch, tmp_path):
+    cfgfile = tmp_path / "settings.json"
+    cfgfile.write_text("{}", encoding="utf-8")
+    monkeypatch.setattr(config, "CFG", cfgfile)
+    monkeypatch.setattr(config, "_kr", lambda: None)
+    monkeypatch.setenv("VS_HF_TOKEN", "hf_env_1234")
+
+    d = config.load()
+
+    assert d["hf_token"] == "hf_env_1234"
+
+
+def test_save_hf_token_to_vault_and_public_redacts(monkeypatch, tmp_path):
+    cfgfile = tmp_path / "settings.json"
+    cfgfile.write_text("{}", encoding="utf-8")
+    monkeypatch.setattr(config, "CFG", cfgfile)
+    vault = FakeVault()
+    monkeypatch.setattr(config, "_kr", lambda: vault)
+
+    d = config.save({"hf_token": "hf_save_1234"})
+
+    assert vault.data["hf_token"] == "hf_save_1234"
+    assert json.loads(cfgfile.read_text(encoding="utf-8"))["hf_token"] == "vault"
+    assert d["hf_token"] == "hf_save_1234"
+    pub = config.public()
+    assert pub["hf_token"] == "••••1234"
+    assert "hf_save_1234" not in json.dumps(pub)
+
+
+def test_migrate_secrets_entrypoint_counts(monkeypatch, tmp_path):
+    cfgfile = tmp_path / "settings.json"
+    cfgfile.write_text(
+        json.dumps({"hf_token": "hf_plain_1234", "deepseek_api_key": "deep_plain"}),
+        encoding="utf-8",
+    )
+    monkeypatch.setattr(config, "CFG", cfgfile)
+    vault = FakeVault()
+    monkeypatch.setattr(config, "_kr", lambda: vault)
+
+    assert config.migrate_secrets() == 2
+    raw = json.loads(cfgfile.read_text(encoding="utf-8"))
+    assert raw["hf_token"] == "vault"
+    assert raw["deepseek_api_key"] == "vault"
```

## How Claude should test it

```powershell
cd F:\path\to\video-studio-test
python -m pytest tests/test_codex_fit_vault.py -q
python -m pytest tests/ -q
```

Expected: the new test file passes offline; existing suite remains green.

## Notes / missing pieces

- I did **not** change `qc.py` or `qc_repair.py`.
- The excerpts do not include the local catalogue / Google Photos module, so `catalogue_reuse_test` is only a default-off config flag here. If the catalogue code lives elsewhere, it should explicitly check `cfg.get("catalogue_reuse_test")` before enabling any local-catalogue-only reuse path.
- I did not add any Google API integration or Flow credit calls.
- No real credentials or keys are exposed by these patches/tests; all test tokens are fake.

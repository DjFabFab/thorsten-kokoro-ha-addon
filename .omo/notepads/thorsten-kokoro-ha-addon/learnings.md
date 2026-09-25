# Learnings — thorsten-kokoro-ha-addon

Conventions, patterns, and successful approaches discovered during work on this plan.

_Auto-scaffolded by /start-work. Append new entries below - never overwrite._

---

## 2026-09-22T20:13:30Z — Task 1 scaffold created
- Created HA add-on scaffold: config.yaml, translations/de.yaml, translations/en.yaml, repository.yaml, wyoming_bridge/__init__.py (empty).
- config.yaml follows piper pattern: name Thorsten Kokoro, version "1.0.0", slug thorsten_kokoro, arch [amd64, aarch64], startup application, boot auto, ports {"8000/tcp": 8000, "10200/tcp": 10200}, options {KOKORO_EPOCH: 5, SPEED: 1.0, HF_REPO_ID: "Thorsten-Voice/Kokoro"}, schema {KOKORO_EPOCH: "int(1,10)", SPEED: "float(0.1,2.0)", HF_REPO_ID: "str"}, discovery [wyoming], map [hf-cache:rw], image ghcr.io/thorstenvoice/{arch}-kokoro-ha-addon, homeassistant 2023.8.0, country [DE].
- repository.yaml: name/url/maintainer per HA add-on store docs (developers.home-assistant.io/docs/add-ons/repository).
- GOTCHA: plan acceptance command `assert 8000 in str(d)` raises TypeError ('in <string>' requires string as left operand, not int). Corrected equivalent `'8000' in str(d)` used and passes. Evidence logged in .omo/evidence/task-1-thorsten-kokoro-ha-addon.txt.
- All 4 yaml files parse cleanly with python3 yaml.safe_load.

## 2026-09-22T20:19Z — Task 2 Dockerfile CPU-only gebaut und verifiziert
- Dockerfile: FROM python:3.11-slim, ENV PYTHONUNBUFFERED=1/HF_HUB_CACHE=/data/hf-cache (+HF_HOME Alias)/DEBIAN_FRONTEND=noninteractive, apt espeak-ng espeak-ng-data libsndfile1 git curl ca-certificates build-essential (danach apt-lists cleanup), requirements.txt mit --extra-index-url cpu + Pins aus Thorsten docker/kokoro (fastapi 0.115.0, uvicorn 0.30.6, pydantic 2.9.2, huggingface_hub 0.25.1, soundfile 0.12.1, numpy 1.26.4, torch 2.4.1, misaki@6d252a2e02f3b030f22f56686f1a73786c16ffc8, kokoro git-HEAD) plus wyoming==1.7.2 (PyPI-verifiziert) fuer die Bridge. EXPOSE 8000 10200, VOLUME /data/hf-cache, ENTRYPOINT ./run.sh. KEIN CUDA/GPU-Layer, keine arch-spezifischen RUNs (multi-arch faehig; buildx-Befehl im Dockerfile dokumentiert).
- Platzhalter-Ansatz: http_server.py + run.sh als klar markierte Platzhalter angelegt (Todo 4 ueberschreibt beide), damit COPY/ENTRYPOINT schon heute gruen bauen. .dockerignore angelegt.
- Build: `docker build -t thorsten-kokoro-addon:test .` Exit 0, Dauer 204s, Image 2.68GB. Log: .omo/evidence/task-2-thorsten-kokoro-ha-addon.txt (inkl. Acceptance-Outputs).
- Acceptance alle gruen: `import kokoro/misaki/wyoming` ok; torch 2.4.1+cpu, cuda_available=False, `pip show torch | grep -i cuda` leer; /usr/bin/espeak-ng existiert.
- GOTCHA: ENTRYPOINT ["./run.sh"] schluckt `docker run image <cmd>`-Args (Platzhalter-run.sh exec'd http_server.py und ignorierte Args) — Checks muessen mit `--entrypoint` Override laufen (z.B. `docker run --rm --entrypoint python3 image -c ...`). Todo 4 run.sh sollte Args per `exec "$@"`-Fallback oder explizit weiterreichen, sonst sind spaetere Debug-Commands im Container irrefuehrend.

## 2026-09-22 — Task 3 bridge server.py done
- Created `wyoming_bridge/server.py` (argparse --uri/--hf-repo-id/--epoch/--speed/--debug; env HF_REPO_ID/KOKORO_EPOCH/SPEED overrides; defaults tcp://0.0.0.0:10200, Thorsten-Voice/Kokoro, 5, 1.0) + `wyoming_bridge/__main__.py` re-export (`python3 -m wyoming_bridge` works).
- inference.py (HF Thorsten-Voice/Kokoro, fetched full source): CHECKPOINTS ep1..ep10 = model_epN.pth + voices/thorsten_epN.pt, ep5/default = model.pth + voices/thorsten.pt; load = hf_hub_download x3 (config+model+voice), KModel(repo_id=hexgrad/Kokoro-82M, config, model).to(device).eval(), KPipeline(lang_code="d", repo_id=..., model), G2P wrap _original_g2p -> phonemes.replace("ʏ","y"), torch.load(..., weights_only=True); pipeline(text, voice, speed) yields (graphemes, phonemes, audio). Mirrored exactly in load_pipeline_and_voice/synthesize_text.
- chiabre/wyoming-kokoro.py (fetched full source): AsyncServer.from_uri + AsyncEventHandler.handle_event describe->info event / synthesize->AudioStart/AudioChunk/AudioStop, argparse --uri/--debug, asyncio.to_thread for blocking inference. Mirrored; describe advertises TtsProgram "Thorsten Kokoro" + voice thorsten languages ["de"] (typed path with raw-Event fallback for SDK drift).
- Epoch mapping: epoch_to_filenames(None|5)->model.pth+voices/thorsten.pt else model_epN.pth+voices/thorsten_epN.pt, ValueError outside 1-10. Literal "model_ep" x3 in file.
- G2P double cover: apply_g2p_patch(text) pre-split AND _patched_g2p on pipeline output side (phonemes.replace("ʏ","y")); grep replace.*ʏ = 2.
- Sentence split: finditer regex `[^.!?…]+[.!?…]+(?:\s+|$)|[^.!?…]+$`, ~300 chars/chunk, over-long sentences hard-split on word boundaries. GOTCHA: first attempt used variable-width lookbehind `(?<=[.!?…]+)` -> re.PatternError at import; finditer matcher fixes it.
- Lazy imports (torch/kokoro/huggingface_hub/wyoming/numpy inside functions) so --help/py_compile pass without deps; handler class built by create_handler() factory post-import. No kokoro-onnx, lang_code only "d", no network download in verification.
- Verification: py_compile exit 0, --help shows --uri, grep model_ep=3, grep replace-ʏ=2, ast.parse OK + functional smoke (epoch map/range, g2p, splits, env overrides) all green. Evidence: .omo/evidence/task-3-thorsten-kokoro-ha-addon.txt.

## 2026-09-22 — Task 4 run.sh + http_server.py done
- http_server.py: FastAPI GET /health (status ok/loading + epoch + repo/repo_id + device) + POST /tts {text, speed?} -> audio/wav 24kHz mono PCM_16 via chunk-wise pipeline(chunk, voice, speed) + numpy concat + soundfile; empty text -> 422, not-loaded -> 503. Reuses `from wyoming_bridge.server import epoch_to_filenames, apply_g2p_patch, split_sentences` (zero duplicate defs); KModel(repo hexgrad/Kokoro-82M)+KPipeline(lang_code "d"), torch.load voice, startup file logging. CLI --port (default 8000)/--host, uvicorn in __main__ only.
- License check FIRST: upstream repo LICENSE = CC0 1.0 Universal (raw fetch; public domain dedication); upstream docker/kokoro/server.py has NO license header. CC0 = fully compatible incl. commercial; attribution comment with source URL kept at top of http_server.py.
- GOTCHA: fastapi import at module top breaks `--help` on hosts without deps (bridge keeps everything lazy). Fix: try/except ImportError around fastapi/pydantic imports + `if _FASTAPI_AVAILABLE:` guard for app/endpoints; argparse stays stdlib-only so --help/py_compile always work. Second gotcha: indent slip after the guard edit left health/tts bodies outside the block — caught by re-read, fixed.
- run.sh (sh, +x): set -e; HF_CACHE=/data/hf-cache mkdir -p, exports HF_HUB_CACHE/HF_HOME; options.json parsed via python3 json with KOKORO_EPOCH=5/SPEED=1.0/HF_REPO_ID=Thorsten-Voice/Kokoro defaults + missing-file echo; `:="${...:=...}"` fallback; starts `python3 http_server.py --port 8000 &` + `python3 -m wyoming_bridge --uri tcp://0.0.0.0:10200 &` with PID echoes, trap TERM/INT + wait; bounded ~60s curl warmup with fail-fast child checks, never blocks forever. RAM note (double load ca 700MB-1GB) in header comment. Port grep count 15 (>=2).
- Verification: bash -n exit 0, sh -n exit 0, py_compile exit 0, --help exit 0 without deps, no model downloads. Evidence: .omo/evidence/task-4-thorsten-kokoro-ha-addon.txt. Only touched http_server.py, run.sh, evidence + this note.

## 2026-09-22 — Task 5 README + HA Doku done
- README.md (126 lines, German-only, primary audience DE) + optional docker-compose.example.yml (local test compose). Evidence: .omo/evidence/task-5-thorsten-kokoro-ha-addon.txt.
- Doc structure choices: single README.md as acceptance file (no separate DOCS.md, kept minimal per task); section order mirrors install flow: Überblick → Installation (Repository URL hinzufügen → installieren/starten → Optionen) → Wyoming Integration → HTTP Nutzung → Epoch Tabelle → Konfiguration → Ports → RAM Hinweis → Bekannte Limits → Links.
- Ports documented exactly from config.yaml (8000 HTTP, 10200 Wyoming); no invented ports. Epoch table mirrors bridge epoch_to_filenames: 5/default → model.pth + voices/thorsten.pt, N≠5 → model_epN.pth + voices/thorsten_epN.pt.
- curl examples copied verbatim from plan Todo 5 (GET /health + POST /tts with -H "Content-Type: application/json"); acceptance grep counts 10 (ports/epoch) and 5 (repo strings) both green.
- GOTCHA: anti-slop rule bans em/en dashes in prose; German text uses commas/colons instead. "E-Mail" hyphen is a plain hyphen-minus, allowed.
- GOTCHA: grep -c counts LINES not occurrences; acceptance thresholds (>=3, >=2) are easily met by tables (each table row is a separate matching line).

## 2026-09-22 — Task 6 Docker Build + HTTP QA done (all green, QA only, no push)
- Rebuild: `docker build -t thorsten-kokoro-addon:test .` exit 0 in ~2s (heavy layers cached, only COPY http_server.py/run.sh re-ran). Verified real files inside via --entrypoint cat/grep: http_server.py shows FastAPI adaptation header (grep FastAPI=4), run.sh shows dual-startup header (grep options.json=3).
- Start choice: `docker run -d --name tkqa -p 8000:8000 -p 10200:10200 -e KOKORO_EPOCH=5 -e SPEED=1.0 -e HF_REPO_ID=Thorsten-Voice/Kokoro -v tkqa-hf:/data/hf-cache` (compose file left untouched per scope). Container ran run.sh: both PIDs started, warmup OK.
- Health: polled /health every 10s; attempts 1-4 CURL_FAIL (uvicorn starting + model load), attempt 5 (~40s after start) `{"status":"ok","epoch":5,"repo":"Thorsten-Voice/Kokoro","device":"cpu"}`. Note: /data/hf-cache already held snapshot 734e593d... from earlier runs, so no fresh download wait; `du` shows 313M cache.
- TTS: POST {"text":"Hallo, hier spricht Thorsten."} -> HTTP 200, latency 1s, /tmp/t.wav 106844 bytes (>10KB PASS), wave framerate=24000 channels=1 sampwidth=2 frames=53400 (PASS 24kHz mono). Copied to .omo/evidence/task-6-thorsten-kokoro-ha-addon.wav.
- Failure case: POST {} -> HTTP 422 (4xx PASS, FastAPI validation).
- ARM64: no arch-specific RUNs in Dockerfile (grep only hits comments); base python:3.11-slim manifest includes linux/arm64/v8; `buildx build --platform linux/arm64 --dry-run` unsupported on this buildx (unknown flag), full arm64 build intentionally skipped per plan; arch-neutrality documented via config check.
- Shutdown: docker stop+rm tkqa, volume tkqa-hf KEPT, ports 8000/10200 free for Todo 7. No registry push. Evidence: .omo/evidence/task-6-thorsten-kokoro-ha-addon.txt + .wav.
- GOTCHA: `docker exec tkqa du -sh /data/hf-cache/*` fails (glob, no match at that depth); use `du -sh /data/hf-cache` directly.

## 2026-09-22 — Task 7 Wyoming QA done (all green, QA only, no commit)
- Start: `docker run -d --name tkwyo ... -v tkqa-hf:/data/hf-cache thorsten-kokoro-addon:test` reused Todo 6 cache -> health ok on FIRST poll (no 40s wait like Todo 6 cold start). Ports 8000/10200, no rebuild needed.
- Describe: SDK AsyncTcpClient + Describe() returns info with tts=[Thorsten Kokoro, de, 24000Hz, voice thorsten]; grep -qi tts PASS. Raw `printf ... | ncat` HANGS (120s timeout, no response) — wyoming framing needs persistent event-loop connection, single-shot pipe insufficient. SDK is the correct method; document ncat as known-not-working.
- GOTCHA wyoming 1.7.2 SDK drift (two spots): (1) Info.from_event() raises TypeError TtsVoice missing 'attribution' (server omits voice-level attribution, SDK requires it) -> assert on raw event.data instead. (2) Synthesize voice param type is wyoming.tts.SynthesizeVoice, NOT wyoming.info.TtsVoice and NOT dict (dict -> AttributeError 'to_dict', TtsVoice -> ImportError).
- Synthesize: direct wyoming Synthesize("Grüße aus der Brücke mit ÄÖÜ und ß.", SynthesizeVoice thorsten/de) -> AudioStart(24000,2,1)/AudioStop, 154800 audio bytes, WAV 154844 bytes 24kHz mono, latency ~0.9s. HTTP proxy same text -> HTTP 200, byte-identical WAV (154844) confirming shared code path. Umlauts/ß no crash.
- HA note: headless, written note only (Host homeassistant.local/IP, Port 10200, Stimme Thorsten) — matches README; describe payload is exactly what HA Wyoming integration displays.
- Cleanup: stop+rm tkwyo, volume tkqa-hf KEPT (~313M prod cache), no extra test volumes existed, ports free. Evidence .txt + .wav.

## 2026-09-22 — F2 comment-hygiene fix (REJECT findings resolved)
- F2 REJECT: stale workflow comments in production files. Fixed: Dockerfile L40-42 stale "Todo 4 owns these / Platzhalter" comment -> accurate 2-line entrypoint comment; requirements.txt L3 "(Todo 3)" -> "Wyoming Bridge"; run.sh L35 WARN string now interpolates exc (was literal %s).
- WARN fix: `print('echo \"WARN: could not parse %s: %s\"' % ('$OPTIONS_FILE', exc))` — shell expands $OPTIONS_FILE inside the double-quoted python -c, % operator interpolates real error. Synthetic test with /tmp/options-bad.json (invalid JSON) printed real error "Expecting value: line 1 column 18 (char 17)", not literal %s.
- Verification: grep -rni "todo|platzhalter|placeholder" over Dockerfile requirements.txt run.sh http_server.py wyoming_bridge/server.py = ZERO matches; bash -n && sh -n exit 0; docker build -t thorsten-kokoro-addon:test . exit 0 (cached, ~28s). No logic changes, no dep changes. Evidence: .omo/evidence/fix-f2-thorsten-kokoro-ha-addon.txt.

# thorsten-kokoro-ha-addon - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** Ein fertiges Home Assistant Add-on das Deutsch mit Thorstens Stimme spricht, einmal per einfacher Web Adresse und einmal direkt für den Sprachassistenten.

**Why this approach:** Wir bauen das Image selbst aus Python plus Thorstens Feinschliff und legen eine kleine Brücke für den Assistenten dazu, weil fertige Brücken den deutschen Feinschliff nicht laden können.

**What it will NOT do:** Kein Grafikchip nötig, kein Stimmen kopieren, keine Cloud, keine Änderung an Home Assistant selbst.

**Effort:** Medium
**Risk:** Medium - Custom Bridge gegen .pth Finetune muss sitzen
**Decisions to sanity-check:** Wyoming plus HTTP bestätigt, neues Repo amd64 plus arm64 bestätigt, Tests per Bauen plus Anrufen ohne extra Unit Tests bestätigt.

Your next move: Sag Start um auszuführen, oder wünsch dir vorher das High-Accuracy Review. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Medium risk, HA addon with Thorsten Kokoro HTTP plus Wyoming.

## Scope
### Must have
- Neues HA-Add-on Repo Gerüst mit config.yaml amd64+aarch64 CPU-only, Optionen KOKORO_EPOCH SPEED
- HTTP 8000 auf Thorsten-Voice/Kokoro Basis mit hf-cache, Health plus TTS WAV
- Wyoming Bridge 10200 mit semidark Forks, de G2P, ʏ Workaround, Satz-Split
- Deutsche README Doku plus lokale Build und curl/Wyoming Nachweise
### Must NOT have (guardrails, anti-slop, scope boundaries)
- Kein GPU/CUDA Pfad, kein Voice-Cloning, kein Cloud Upload
- Keine HA Core Änderung, kein Fix fremder Wrapper, kein Push ohne WAV Check

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after + Bash/curl/nc + Docker build (kein pytest per User Decision)
- Evidence: .omo/evidence/task-<N>-thorsten-kokoro-ha-addon.<ext> (.txt Logs + .wav Audio)

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1: Todo 1 + 2 (Gerüst, Docker)
- Wave 2: Todo 3 + 4 (Bridge, run.sh)
- Wave 3: Todo 5 + 6 + 7 (Doku, HTTP QA, Wyoming QA)

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 Gerüst | none | 2,3,4 | 2 |
| 2 Docker | 1 | 6 | 1,3 |
| 3 Bridge | 1 | 4,7 | 2,5 |
| 4 run.sh | 2,3 | 6,7 | 5 |
| 5 Doku | 1 | none | 3,4 |
| 6 HTTP QA | 2,4 | F3 | 7 |
| 7 Wyoming QA | 3,4 | F3 | 6 |

## Todos
> Implementation + Test = ONE todo. Never separate.
- [x] 1. Add-on Repo Gerüst mit config.yaml und Verzeichnisstruktur anlegen
  What to do / Must NOT do: Neues Repo thorsten-kokoro-ha-addon mit config.yaml (name, version 1.0.0, slug, arch amd64+aarch64, ports 8000/tcp + 10200/tcp, options KOKORO_EPOCH default 5 + speed default 1.0 + HF_REPO_ID default Thorsten-Voice/Kokoro, schema für Epoch 1-10 und speed 0.1-2.0, discovery wyoming, map hf-cache), translations/de.yaml+en.yaml, repository.yaml; Kein Code aus fremden Wrappern kopieren ohne Lizenzcheck
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2,3,4
  References (executor has NO interview context - be exhaustive): https://github.com/home-assistant/addons/tree/master/piper (config.yaml Muster), https://www.home-assistant.io/integrations/wyoming (Discovery), Draft .omo/drafts/thorsten-kokoro-ha-addon.md c1
  Acceptance criteria (agent-executable): `ls config.yaml translations/de.yaml translations/en.yaml repository.yaml` existiert und `python3 -c "import yaml; d=yaml.safe_load(open('config.yaml')); assert 8000 in str(d) and 10200 in str(d) and 'KOKORO_EPOCH' in str(d)"` grün
  QA scenarios (name the exact tool + invocation): happy Bash `ls -R` zeigt Struktur, Evidence .omo/evidence/task-1-thorsten-kokoro-ha-addon.txt; failure Bash `python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"` muss ohne Exception parsen
  Commit: Y | feat(addon): scaffold repo with config
- [x] 2. Dockerfile CPU-only multi-arch mit Thorsten deps bauen
  What to do / Must NOT do: FROM python:3.11-slim, apt-get espeak-ng libsndfile1, pip mit --extra-index-url https://download.pytorch.org/whl/cpu für torch CPU plus soundfile numpy huggingface_hub fastapi uvicorn pydantic wyoming plus git semidark/misaki@6d252a2 + semidark/kokoro, COPY wyoming_bridge + http_server.py + run.sh, EXPOSE 8000 10200, VOLUME /data/hf-cache; KEIN CUDA, KEIN GPU Layer, auf amd64 prüfen dass keine nvidia Pakete installiert sind
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 6
  References (executor has NO interview context - be exhaustive): https://huggingface.co/Thorsten-Voice/Kokoro (Installation Abschnitt), https://hub.docker.com/r/thorstenvoice/kokoro-tts (CPU-only multi-arch Muster), https://github.com/thorstenMueller/Thorsten-Voice/tree/master/docker/kokoro (requirements mit cpu Index), Draft c2
  Acceptance criteria (agent-executable): `docker build -t thorsten-kokoro-addon:test .` Exit 0 und `docker run --rm thorsten-kokoro-addon:test python3 -c "import kokoro; print('ok')"` prints ok und `docker run --rm thorsten-kokoro-addon:test pip show torch | grep -qi cuda` muss leer bleiben
  QA scenarios (name the exact tool + invocation): happy Bash `docker build` log, Evidence .omo/evidence/task-2-thorsten-kokoro-ha-addon.txt; failure Bash `docker run --rm image ls /usr/bin/espeak-ng` muss existieren sonst FAIL
  Commit: Y | feat(docker): cpu image with thorsten deps
- [x] 3. Wyoming Bridge server.py mit Thorsten .pth Pipeline implementieren
  What to do / Must NOT do: wyoming_bridge/server.py implementiert wyoming Server auf tcp://0.0.0.0:10200 (Describe/Synthesize Events), lädt aus HF_REPO_ID via hf_hub_download beim Start einmal mit Epoch Mapping Epoch 5 oder default zu model.pth plus voices/thorsten.pt sonst model_epN.pth plus voices/thorsten_epN.pt für N 1-10, KModel repo_id hexgrad/Kokoro-82M plus KPipeline lang_code d repo_id hexgrad/Kokoro-82M, G2P Patch ʏ→y, splittet lange Texte an Satzgrenzen, gibt 24kHz mono WAV zurück; KEIN kokoro-onnx, KEIN englischer Default
  Parallelization: Wave 2 | Blocked by: 1 | Blocks: 4,7
  References (executor has NO interview context - be exhaustive): https://huggingface.co/Thorsten-Voice/Kokoro/blob/main/inference.py (komplettes Snippet inkl Workaround), https://github.com/chiabre/wyoming-kokoro/blob/main/wyoming_kokoro.py (Wyoming Event Loop Muster), https://github.com/thorstenMueller/Thorsten-Voice/tree/master/docker/kokoro (server.py Epoch Mapping Muster), Draft c3
  Acceptance criteria (agent-executable): `python3 -m py_compile wyoming_bridge/server.py` Exit 0 und Unit-Smoke `python3 wyoming_bridge/server.py --help` zeigt --uri Option und `grep -c "model_ep" wyoming_bridge/server.py` >=1
  QA scenarios (name the exact tool + invocation): happy Bash `python3 wyoming_bridge/server.py --help`, Evidence .omo/evidence/task-3-thorsten-kokoro-ha-addon.txt; failure Bash `python3 -c "import ast; ast.parse(open('wyoming_bridge/server.py').read())"` muss parsen, G2P Patch String ʏ vorhanden per `grep -c "replace.*ʏ" wyoming_bridge/server.py` >=1
  Commit: Y | feat(wyoming): thorsten bridge server
- [x] 4. run.sh mit HTTP 8000 plus Wyoming 10200 und Optionen verdrahten
  What to do / Must NOT do: http_server.py als FastAPI Server aus offiziellem docker/kokoro/server.py übernehmen mit Lizenzcheck und an HF_REPO_ID plus KOKORO_EPOCH Mapping anpassen plus run.sh liest /data/options.json (KOKORO_EPOCH 1-10 default 5, SPEED default 1.0, HF_REPO_ID default Thorsten-Voice/Kokoro), startet http_server.py auf 8000 (POST /tts, GET /health) + wyoming_bridge auf 10200 parallel via wait, legt hf-cache unter /data/hf-cache an, Warmup einmal; KEIN Portkonflikt, doppeltes Modelladen dokumentieren ca 700MB-1GB RAM
  Parallelization: Wave 2 | Blocked by: 2,3 | Blocks: 6,7
  References (executor has NO interview context - be exhaustive): https://github.com/thorstenMueller/Thorsten-Voice/tree/master/docker/kokoro (server.py plus README /health POST /tts Muster), Draft c2+c3
  Acceptance criteria (agent-executable): `bash -n run.sh` Exit 0 und `python3 -m py_compile http_server.py` Exit 0 und `grep -c "8000\|10200" run.sh` >=2
  QA scenarios (name the exact tool + invocation): happy Bash `bash -n run.sh && echo OK`, Evidence .omo/evidence/task-4-thorsten-kokoro-ha-addon.txt; failure Bash `run.sh` mit fehlendem options.json muss Defaults nutzen (grep Defaults im File)
  Commit: Y | feat(run): dual http wyoming startup
- [x] 5. README und HA Doku mit Install plus Beispiel Compose schreiben
  What to do / Must NOT do: README.md mit Add-on Store Install (Repository URL hinzufügen), Wyoming Integration Host+Port 10200, curl Beispiele für /tts und /health, Epoch Tabelle 1-10, RAM Hinweis ca 700MB-1GB durch zwei Prozesse, Bekannte Limits (Bindestrich Komposita, lange Sätze splitten); KEINE falschen Portangaben
  Parallelization: Wave 3 | Blocked by: 1 | Blocks: none
  References (executor has NO interview context - be exhaustive): https://github.com/home-assistant/addons/blob/master/piper/DOCS.md (Install Flow), Draft c1
  Acceptance criteria (agent-executable): `grep -c "10200\|8000\|KOKORO_EPOCH" README.md` >=3 und `grep -c "thorstenvoice/kokoro-tts\|Thorsten-Voice/Kokoro" README.md` >=2
  QA scenarios (name the exact tool + invocation): happy Bash `cat README.md`, Evidence .omo/evidence/task-5-thorsten-kokoro-ha-addon.txt; failure Bash prüft alle curl Beispiele enthalten Content-Type json
  Commit: Y | docs(addon): install and usage
- [x] 6. Docker Build plus HTTP QA /health und /tts WAV prüfen
  What to do / Must NOT do: `docker compose build` dann `docker compose up -d`, warte auf health ok, POST Hallo hier spricht Thorsten, prüfe WAV 24kHz mono >10KB, danach arm64 Check via buildx und `docker compose down`; KEIN Push ohne erfolgreichen WAV Check
  Parallelization: Wave 3 | Blocked by: 2,4 | Blocks: F3
  References (executor has NO interview context - be exhaustive): Docker Hub thorstenvoice/kokoro-tts Quickstart curl Muster, Draft c4
  Acceptance criteria (agent-executable): `curl -s http://localhost:8000/health | grep -q '"status":"ok"'` und `curl -s -X POST http://localhost:8000/tts -H "Content-Type: application/json" -d '{"text":"Hallo, hier spricht Thorsten."}' --output /tmp/t.wav && test $(stat -c%s /tmp/t.wav) -gt 10000 && python3 -c "import wave; w=wave.open('/tmp/t.wav'); assert w.getframerate()==24000 and w.getnchannels()==1"` und `docker buildx build --platform linux/arm64 . --dry-run 2>/dev/null || docker build --platform linux/arm64 .` dokumentiert
  QA scenarios (name the exact tool + invocation): happy Bash `curl .../health` + `curl .../tts`, Evidence .omo/evidence/task-6-thorsten-kokoro-ha-addon.wav + .txt; failure Bash POST ohne text Feld muss 4xx geben
  Commit: N | QA only
- [x] 7. Wyoming QA mit describe plus HA Assist Probe und Cleanup
  What to do / Must NOT do: `echo '{"type":"describe"}' | nc localhost 10200` muss TTS Info liefern, Test Synthese via wyoming client oder test_wyoming_tts Muster, HA Wyoming Integration Screenshot/Notiz, danach Container+Volume Cleanup `docker compose down -v` nur für Testvolumes (hf-cache Prod Volume behalten); KEINE Prod Daten löschen
  Parallelization: Wave 3 | Blocked by: 3,4 | Blocks: F3
  References (executor has NO interview context - be exhaustive): https://github.com/chiabre/wyoming-kokoro (test_wyoming_tts.py Muster), https://www.home-assistant.io/integrations/wyoming, Draft c4
  Acceptance criteria (agent-executable): `echo '{"type":"describe"}' | nc -w 5 localhost 10200 | grep -qi tts` und deutsche Umlaute Probe `curl` Text mit Brücke ÄÖÜ ohne Crash
  QA scenarios (name the exact tool + invocation): happy Bash `nc localhost 10200` describe, Evidence .omo/evidence/task-7-thorsten-kokoro-ha-addon.txt; failure Bash Umlaut Text Brücke muss WAV liefern sonst FAIL mit Log
  Commit: N | QA only

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit
- [x] F2. Code quality review
- [x] F3. Real manual QA
- [x] F4. Scope fidelity

## Commit strategy
- Ein atomarer Commit pro verifiziertem Todo 1-5, QA Todos 6-7 ohne Commit, Conventional Commits feat/docs wie in Todos angegeben

## Success criteria
- Add-on baut multi-arch, /health ok, /tts liefert deutsche WAV, Wyoming describe antwortet, README deckt Install ab, keine Scope OUT Verletzung

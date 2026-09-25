---
slug: thorsten-kokoro-ha-addon
status: approved
intent: clear
review_required: true
pending-action: review .omo/plans/thorsten-kokoro-ha-addon.md
approach: Neues HA-Add-on Repo (amd64+arm64, CPU-only) mit thorstenvoice/kokoro-tts als Basis (HTTP 8000) plus Custom Wyoming Bridge (10200) auf semidark kokoro/misaki Forks für Thorsten-Voice/Kokoro .pth
---

# Draft: thorsten-kokoro-ha-addon

## Components (topology ledger)
- c1 | Add-on Hülle (config.yaml/Docker/run.sh/Doku) läuft als HA Add-on | status: active | evidence: HA addon docs + wyoming-piper addon pattern
- c2 | HTTP Backend (thorstenvoice/kokoro-tts, 8000, KOKORO_EPOCH, hf-cache) | status: active | evidence: Docker Hub thorstenvoice/kokoro-tts + Thorsten-Voice/docker/kokoro/README
- c3 | Wyoming Bridge (10200, semidark forks, .pth + thorsten.pt, de G2P) | status: active | evidence: HF Thorsten-Voice/Kokoro model card + inference.py
- c4 | Verifikation (build, curl health/tts, wyoming describe) | status: active | evidence: user decision Agent-QA

## Open assumptions (announced defaults)
- Basis-Image thorstenvoice/kokoro-tts:latest | adopted | offizielles Thorsten Image, multi-arch amd64+arm64 | reversible: yes (pin möglich)
- Default Epoch 5, speed 1.0, CPU | adopted | Model Card Default + CPU-first | reversible: yes via Add-on Optionen
- Tests-after + Agent-QA, kein pytest | adopted | user decision | reversible: yes

## Findings (cited - path:lines)
- thorstenvoice/kokoro-tts spricht nur HTTP 8000, kein Wyoming (Docker Hub Overview + README Ver Verwendung/POST /tts)
- Gängige Wyoming Wrapper (kokoro-onnx) laden kein .pth Finetune; Thorsten braucht semidark misaki/kokoro Forks + espeak-ng + ʏ→y Workaround (HF model card Installation/Usage/Known limitations)
- HA Piper Add-on Muster: Wyoming Auto-Discovery via Wyoming Integration (home-assistant/addons piper/DOCS)

## Decisions (with rationale)
- Wyoming + HTTP gewählt (user) | Rationale: HA Assist braucht Wyoming, HTTP bleibt für Direktnutzer
- Neues Repo Standard amd64+arm64 CPU-only (user) | Rationale: Greenfield, keine bestehende Repo-Bindung
- Agent-QA ohne Unit (user) | Rationale: Shell/curl/Wyoming checks reichen für Add-on Hülle

## Scope IN
- Neues Add-on Repo Gerüst, Docker Build, HTTP + Wyoming, deutsche Doku, lokale Verifikation

## Scope OUT (Must NOT have)
- Kein Voice-Cloning, kein GPU-Pfad, kein Cloud Upload, kein Fix fremder Wrapper, keine HA Core Änderung

## Open questions
- none (alle Forks beantwortet)

## Approval gate
status: approved (user said review first, 2026-09-22)
approach: wie oben
next: dual high-accuracy review, then handoff
- metis gap analysis bg_348a5bce: CANCELLED stale timeout, no replacement per policy; gaps via self-check abgedeckt
- review round 1: momus APPROVED, oracle CHANGES_REQUESTED B1-B4 plus M1-M6; alle gefixt, Runde 2 gestartet
- review round 2 rev-f7f9af3dca7f: momus APPROVED (bg_d399f367), oracle APPROVED (bg_a701af81); live sha 20a9abbed41601aa6df643c8a76f8ea7fb4adb3de2c2db671f0444dae815b272 matches approved digest, no drift

<!-- ulw-plan-review-round-state-contract -->
```json
{
  "transition": "replace",
  "phase": "review_round_initialized",
  "atomic": true,
  "review_required": true,
  "plan_path": ".omo/plans/thorsten-kokoro-ha-addon.md",
  "plan_sha256": "20a9abbed41601aa6df643c8a76f8ea7fb4adb3de2c2db671f0444dae815b272",
  "review_round_id": "rev-f7f9af3dca7f",
  "round_status": "active",
  "pending-action": "review .omo/plans/thorsten-kokoro-ha-addon.md",
  "review": {
    "momus": { "status": "pending", "workspace_root": "/home/waescherf/.config/openchamber/chats/2026-09-22/session-7eb70d9e-fdbd-423d-ae20-fa26e6f81e3f", "runtime_home": null, "target": ".omo/plans/thorsten-kokoro-ha-addon.md", "round_id": "rev-f7f9af3dca7f", "plan_sha256": "20a9abbed41601aa6df643c8a76f8ea7fb4adb3de2c2db671f0444dae815b272", "launch_id": null, "session": null, "result": null },
    "independent": { "status": "pending", "workspace_root": "/home/waescherf/.config/openchamber/chats/2026-09-22/session-7eb70d9e-fdbd-423d-ae20-fa26e6f81e3f", "runtime_home": null, "target": ".omo/plans/thorsten-kokoro-ha-addon.md", "round_id": "rev-f7f9af3dca7f", "plan_sha256": "20a9abbed41601aa6df643c8a76f8ea7fb4adb3de2c2db671f0444dae815b272", "launch_id": null, "session": null, "result": null }
  }
}
```

<!-- ulw-plan-review-round-state-contract -->
```json
{
  "transition": "replace",
  "phase": "review_round_initialized",
  "atomic": true,
  "review_required": true,
  "plan_path": ".omo/plans/thorsten-kokoro-ha-addon.md",
  "plan_sha256": "9cf35f9103031fe0dd9f1c5f7e28ab84292f652db332f9811f92011be49f218f",
  "review_round_id": "rev-45f35d1b9d0d",
  "round_status": "active",
  "pending-action": "review .omo/plans/thorsten-kokoro-ha-addon.md",
  "review": {
    "momus": { "status": "pending", "workspace_root": "/home/waescherf/.config/openchamber/chats/2026-09-22/session-7eb70d9e-fdbd-423d-ae20-fa26e6f81e3f", "runtime_home": null, "target": ".omo/plans/thorsten-kokoro-ha-addon.md", "round_id": "rev-45f35d1b9d0d", "plan_sha256": "9cf35f9103031fe0dd9f1c5f7e28ab84292f652db332f9811f92011be49f218f", "launch_id": null, "session": null, "result": null },
    "independent": { "status": "pending", "workspace_root": "/home/waescherf/.config/openchamber/chats/2026-09-22/session-7eb70d9e-fdbd-423d-ae20-fa26e6f81e3f", "runtime_home": null, "target": ".omo/plans/thorsten-kokoro-ha-addon.md", "round_id": "rev-45f35d1b9d0d", "plan_sha256": "9cf35f9103031fe0dd9f1c5f7e28ab84292f652db332f9811f92011be49f218f", "launch_id": null, "session": null, "result": null }
  }
}
```

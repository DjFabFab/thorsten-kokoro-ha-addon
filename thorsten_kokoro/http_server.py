# Adapted from https://github.com/thorstenMueller/Thorsten-Voice/blob/master/docker/kokoro/server.py
# Upstream repo license: CC0 1.0 Universal (public domain dedication, see LICENSE in
# thorstenMueller/Thorsten-Voice) — no license header in upstream server.py itself.
# This adaptation is compatible (CC0: free reuse incl. commercial, attribution kept here).
# Changes vs upstream: HF_REPO_ID/KOKORO_EPOCH/SPEED env mapping kept, epoch->filename
# mapping + G2P patch + sentence split REUSED from wyoming_bridge.server
# (epoch_to_filenames, apply_g2p_patch, split_sentences — NOT duplicated here),
# chunk-wise synthesis, --port CLI flag (default 8000), /health shape with epoch+repo.
"""Thorsten Kokoro HTTP TTS server (FastAPI, 24 kHz mono WAV).

Endpoints:
  GET  /health -> {"status": "ok"|"loading", "epoch": N, "repo": ..., ...}
  POST /tts {text, speed?} -> audio/wav (24000 Hz, mono, 16-bit)

Model/voice files are downloaded ONCE at startup via hf_hub_download and
synthesized through KModel + KPipeline (lang_code "d", repo hexgrad/Kokoro-82M).

Heavy dependencies (torch/kokoro/huggingface_hub/numpy/soundfile) are imported
lazily inside startup/synthesis functions so `py_compile` and `--help` work
without them installed.
"""

from __future__ import annotations

import argparse
import io
import logging
import os

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field

    _FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - deps installed in Docker image
    FastAPI = HTTPException = StreamingResponse = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment]
    Field = lambda *a, **k: None  # type: ignore[assignment]  # noqa: E731
    _FASTAPI_AVAILABLE = False

try:
    from wyoming_bridge.server import (
        apply_g2p_patch,
        epoch_to_filenames,
        split_sentences,
    )
except ImportError:  # pragma: no cover - local package layout
    from server import (  # type: ignore[no-redef]
        apply_g2p_patch,
        epoch_to_filenames,
        split_sentences,
    )

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("thorsten-kokoro-http")

HF_REPO_ID = os.environ.get("HF_REPO_ID", "Thorsten-Voice/Kokoro")
KOKORO_EPOCH = int(os.environ.get("KOKORO_EPOCH", "5") or 5)
DEFAULT_SPEED = float(os.environ.get("SPEED", "1.0") or 1.0)
BASE_REPO_ID = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24000
DEFAULT_PORT = int(os.environ.get("PORT", "8000") or 8000)

_state: dict = {}


def load_model() -> None:
    """Download checkpoint files once and build KModel + KPipeline."""
    import torch
    from huggingface_hub import hf_hub_download
    from kokoro import KModel, KPipeline

    model_file, voice_file = epoch_to_filenames(KOKORO_EPOCH)
    log.info(
        "Loading %s epoch=%s files=(%s, %s) ...",
        HF_REPO_ID,
        KOKORO_EPOCH,
        model_file,
        voice_file,
    )
    config_path = hf_hub_download(repo_id=HF_REPO_ID, filename="config.json")
    model_path = hf_hub_download(repo_id=HF_REPO_ID, filename=model_file)
    voice_path = hf_hub_download(repo_id=HF_REPO_ID, filename=voice_file)
    log.info("Startup files: config=%s model=%s voice=%s", config_path, model_path, voice_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    kmodel = KModel(repo_id=BASE_REPO_ID, config=config_path, model=model_path)
    kmodel = kmodel.to(device).eval()
    pipeline = KPipeline(lang_code="d", repo_id=BASE_REPO_ID, model=kmodel)

    # G2P patch (same as upstream server.py + bridge): map misaki 'ʏ' to 'y'.
    _original_g2p = pipeline.g2p

    def _patched_g2p(text):
        phonemes, tokens = _original_g2p(apply_g2p_patch(text))
        return phonemes.replace("ʏ", "y"), tokens

    pipeline.g2p = _patched_g2p

    voice = torch.load(voice_path, map_location="cpu", weights_only=True)

    _state["pipeline"] = pipeline
    _state["voice"] = voice
    _state["epoch"] = KOKORO_EPOCH
    _state["repo"] = HF_REPO_ID
    _state["device"] = device
    log.info("Model ready (epoch=%s device=%s).", KOKORO_EPOCH, device)


app = (
    FastAPI(
        title="Thorsten Kokoro TTS API",
        description="German Kokoro-82M fine-tune TTS (Thorsten voice) over HTTP.",
        version="1.0.0",
    )
    if _FASTAPI_AVAILABLE
    else None
)


if _FASTAPI_AVAILABLE:

    @app.on_event("startup")
    def _startup() -> None:
        load_model()


    class TTSRequest(BaseModel):
        text: str = Field(..., min_length=1, description="Text to synthesize.")
        speed: float = Field(DEFAULT_SPEED, gt=0.0, le=2.0, description="Speaking speed.")


    @app.get("/health")
    def health():
        ready = "pipeline" in _state
        return {
            "status": "ok" if ready else "loading",
            "epoch": _state.get("epoch", KOKORO_EPOCH),
            "repo": _state.get("repo", HF_REPO_ID),
            "repo_id": _state.get("repo", HF_REPO_ID),
            "device": _state.get("device", "cpu"),
        }


    @app.post("/tts")
    def tts(req: TTSRequest):
        if "pipeline" not in _state:
            raise HTTPException(503, "Model still loading, please retry shortly.")
        text = (req.text or "").strip()
        if not text:
            raise HTTPException(422, "Field 'text' must be non-empty.")

        import numpy as np
        import soundfile as sf

        pipeline = _state["pipeline"]
        voice = _state["voice"]
        try:
            chunks = []
            for chunk in split_sentences(apply_g2p_patch(text)):
                for _, _, audio in pipeline(chunk, voice=voice, speed=req.speed):
                    chunks.append(audio)
        except Exception as exc:  # noqa: BLE001
            log.exception("Inference failed")
            raise HTTPException(500, f"Inference error: {exc}") from exc
        if not chunks:
            raise HTTPException(500, "No audio generated.")

        audio = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="output.wav"'},
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Thorsten Kokoro HTTP TTS server.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port (default 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)

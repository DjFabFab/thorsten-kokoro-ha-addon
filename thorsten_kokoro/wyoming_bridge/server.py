#!/usr/bin/env python3
"""Thorsten Kokoro Wyoming bridge (German TTS, 24 kHz mono).

Listens on ``tcp://0.0.0.0:10200`` and serves the Wyoming ``Describe`` /
``Synthesize`` events. The Thorsten-Voice/Kokoro ``.pth`` checkpoint and the
``thorsten.pt`` voice tensor are downloaded ONCE at startup via
``hf_hub_download`` and synthesized through the semidark ``kokoro`` fork
(``KModel`` + ``KPipeline`` with ``lang_code="d"``).

Epoch mapping (matches ``inference.py`` from Thorsten-Voice/Kokoro):
epoch 5 (or default/None) -> ``model.pth`` + ``voices/thorsten.pt``,
otherwise epoch N (1-10) -> ``model_epN.pth`` + ``voices/thorsten_epN.pt``.

Heavy dependencies (torch/kokoro/misaki/wyoming) are imported lazily inside
functions so ``--help`` and ``py_compile`` work without them installed.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re

_LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 24000
BASE_REPO_ID = "hexgrad/Kokoro-82M"
DEFAULT_HF_REPO_ID = "Thorsten-Voice/Kokoro"
DEFAULT_URI = "tcp://0.0.0.0:10200"
DEFAULT_EPOCH = 5
DEFAULT_SPEED = 1.0
MAX_CHUNK_CHARS = 300

# Sentence matcher: run of non-terminators + terminator(s), or trailing rest.
_SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…]+(?:\s+|$)|[^.!?…]+$")


def epoch_to_filenames(epoch: int | None) -> tuple[str, str]:
    """Map an epoch number to (model_file, voice_file) on the Hub.

    Epoch 5 (the default) reuses the plain ``model.pth`` /
    ``voices/thorsten.pt`` files; every other epoch N (1-10) maps to
    ``model_epN.pth`` / ``voices/thorsten_epN.pt``.
    """
    if epoch is None or epoch == DEFAULT_EPOCH:
        return "model.pth", "voices/thorsten.pt"
    if not isinstance(epoch, int) or not 1 <= epoch <= 10:
        raise ValueError(f"Epoch must be an int in 1-10 (got {epoch!r})")
    return f"model_ep{epoch}.pth", f"voices/thorsten_ep{epoch}.pt"


def apply_g2p_patch(text: str) -> str:
    """Pre-G2P workaround: misaki's German frontend can emit 'ʏ' (short ü).

    Kokoro's 178-symbol vocabulary only knows the long-ü symbol 'y', so an
    unpatched 'ʏ' silently breaks short-ü words (e.g. "Brücke"). This is the
    same substitution used when preparing the Thorsten training data.
    """
    return text.replace("ʏ", "y")


def split_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split long texts at sentence boundaries into <= ``max_chars`` chunks."""
    text = text.strip()
    if not text:
        return []
    sentences = [m.group(0).strip() for m in _SENTENCE_RE.finditer(text)]
    sentences = [s for s in sentences if s]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            # Single over-long sentence: hard-split on word boundaries.
            if current:
                chunks.append(current)
                current = ""
            words = sentence.split()
            part = ""
            for word in words:
                candidate = f"{part} {word}".strip()
                if len(candidate) > max_chars and part:
                    chunks.append(part)
                    part = word
                else:
                    part = candidate
            if part:
                chunks.append(part)
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def load_pipeline_and_voice(hf_repo_id: str, epoch: int | None):
    """Download checkpoint files once and build KModel + KPipeline.

    Returns ``(pipeline, voice_tensor, device)``. Heavy imports (torch,
    kokoro, huggingface_hub) happen here so module import stays light.
    """
    try:
        import torch
        from huggingface_hub import hf_hub_download
        from kokoro import KModel, KPipeline
    except ImportError as exc:
        raise RuntimeError(
            "Missing TTS dependencies (torch/kokoro/huggingface_hub). "
            "Install them per the add-on Dockerfile "
            "(torch CPU + semidark kokoro/misaki forks + huggingface_hub)."
        ) from exc

    model_file, voice_file = epoch_to_filenames(epoch)
    config_path = hf_hub_download(repo_id=hf_repo_id, filename="config.json")
    model_path = hf_hub_download(repo_id=hf_repo_id, filename=model_file)
    voice_path = hf_hub_download(repo_id=hf_repo_id, filename=voice_file)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    kmodel = KModel(repo_id=BASE_REPO_ID, config=config_path, model=model_path)
    kmodel = kmodel.to(device).eval()
    pipeline = KPipeline(lang_code="d", repo_id=BASE_REPO_ID, model=kmodel)

    # G2P patch from inference.py: wrap the pipeline G2P call so a 'ʏ'
    # emitted by misaki/espeak-ng is mapped to 'y' before phonemization.
    _original_g2p = pipeline.g2p

    def _patched_g2p(text):
        phonemes, tokens = _original_g2p(apply_g2p_patch(text))
        return phonemes.replace("ʏ", "y"), tokens

    pipeline.g2p = _patched_g2p

    voice = torch.load(voice_path, map_location="cpu", weights_only=True)
    return pipeline, voice, device


def synthesize_text(pipeline, voice, text: str, speed: float = 1.0):
    """Synthesize ``text`` chunk-wise; return float32 mono audio at 24 kHz."""
    import numpy as np

    chunks = split_sentences(apply_g2p_patch(text))
    audio_parts = []
    for chunk in chunks:
        for _, _phonemes, audio in pipeline(chunk, voice=voice, speed=speed):
            audio_parts.append(audio)
    if not audio_parts:
        return np.zeros(0, dtype=np.float32)
    combined = np.concatenate(audio_parts)
    return combined.astype(np.float32, copy=False)


def build_info_event():
    """Build the Wyoming ``info`` event advertising the Thorsten TTS program."""
    from wyoming.event import Event

    try:
        from wyoming.info import Info
        from wyoming.tts import TtsProgram, TtsVoice

        program = TtsProgram(
            name="Thorsten Kokoro",
            description="Thorsten-Voice Kokoro German TTS",
            attribution={"name": "Thorsten-Voice", "url": "https://huggingface.co/Thorsten-Voice/Kokoro"},
            installed=True,
            version="1.0.0",
            voices=[
                TtsVoice(
                    name="thorsten",
                    description="Thorsten (German)",
                    attribution={"name": "Thorsten-Voice", "url": "https://huggingface.co/Thorsten-Voice/Kokoro"},
                    installed=True,
                    version="1.0.0",
                    languages=["de"],
                )
            ],
        )
        program.languages = ["de"]  # type: ignore[attr-defined]
        return Info(tts=[program]).event()
    except Exception:  # pragma: no cover - SDK version fallback
        return Event(
            type="info",
            data={
                "tts": [
                    {
                        "name": "Thorsten Kokoro",
                        "description": "Thorsten-Voice Kokoro German TTS",
                        "language": "de",
                        "languages": ["de"],
                        "rate": SAMPLE_RATE,
                        "channels": 1,
                        "width": 2,
                        "installed": True,
                        "attribution": {
                            "name": "Thorsten-Voice",
                            "url": "https://huggingface.co/Thorsten-Voice/Kokoro",
                        },
                        "voices": [
                            {
                                "name": "thorsten",
                                "description": "Thorsten (German)",
                                "languages": ["de"],
                                "installed": True,
                            }
                        ],
                    }
                ]
            },
        )


def create_handler(pipeline, voice, speed: float):  # type: ignore[no-untyped-def]
    """Create a ``(reader, writer) -> AsyncEventHandler`` factory for the server."""
    from wyoming.server import AsyncEventHandler

    class _ThorstenKokoroHandler(AsyncEventHandler):
        def __init__(self, reader, writer) -> None:
            super().__init__(reader, writer)
            self.pipeline = pipeline
            self.voice = voice
            self.speed = speed

        async def handle_event(self, event) -> bool:  # type: ignore[no-untyped-def]
            from wyoming.audio import AudioChunk, AudioStart, AudioStop
            from wyoming.tts import Synthesize

            _LOGGER.debug("Received event: %s", event.type)
            if event.type == "describe":
                await self.write_event(build_info_event())
                return True

            if event.type == "synthesize":
                synth = Synthesize.from_event(event)
                _LOGGER.debug("Synthesizing: %r (speed=%s)", synth.text, self.speed)
                try:
                    await self.write_event(
                        AudioStart(rate=SAMPLE_RATE, width=2, channels=1).event()
                    )
                    audio = await asyncio.to_thread(
                        synthesize_text, self.pipeline, self.voice, synth.text, self.speed
                    )
                    pcm16 = (audio * 32767).astype("int16")
                    raw = pcm16.tobytes()
                    # Stream in ~0.25s slices (24000 Hz * 2 bytes * 0.25s).
                    step = SAMPLE_RATE // 4 * 2
                    for offset in range(0, len(raw) or 1, step):
                        piece = raw[offset : offset + step]
                        if not piece:
                            break
                        await self.write_event(
                            AudioChunk(
                                audio=piece, rate=SAMPLE_RATE, width=2, channels=1
                            ).event()
                        )
                    await self.write_event(AudioStop().event())
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.error("Synthesis error: %s", exc)
                    return False
                return True

            return True

    _ThorstenKokoroHandler.__name__ = "ThorstenKokoroHandler"
    return _ThorstenKokoroHandler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Thorsten Kokoro Wyoming bridge (German TTS, 24 kHz mono)."
    )
    parser.add_argument("--uri", default=DEFAULT_URI, help="Wyoming server URI")
    parser.add_argument(
        "--hf-repo-id",
        default=os.environ.get("HF_REPO_ID", DEFAULT_HF_REPO_ID),
        help="Hugging Face repo with the Thorsten .pth checkpoints",
    )
    parser.add_argument(
        "--epoch",
        type=int,
        default=int(os.environ.get("KOKORO_EPOCH", str(DEFAULT_EPOCH))),
        help="Stage-2 checkpoint epoch 1-10 (5 = default model.pth)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=float(os.environ.get("SPEED", str(DEFAULT_SPEED))),
        help="Speaking speed multiplier (0.1-2.0)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    model_file, voice_file = epoch_to_filenames(args.epoch)
    print(
        f"Loading Thorsten Kokoro repo={args.hf_repo_id} epoch={args.epoch} "
        f"files=({model_file}, {voice_file}) speed={args.speed}",
        flush=True,
    )
    pipeline, voice, device = await asyncio.to_thread(
        load_pipeline_and_voice, args.hf_repo_id, args.epoch
    )
    print(f"Model ready on {device}; listening on {args.uri}", flush=True)

    from wyoming.server import AsyncServer

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Ready. Listening on %s", args.uri)
    handler_cls = create_handler(pipeline, voice, args.speed)
    await server.run(lambda reader, writer: handler_cls(reader, writer))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

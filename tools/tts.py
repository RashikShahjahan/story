from __future__ import annotations

import re
import time
from pathlib import Path

from .common import WORKSPACE, json_result


DEFAULT_TTS_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"
SAMPLE_RATE = 24_000


def _safe_file_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")[:80]
    return name or "speech"


def _resolve_output_path(output_path: str | None, text: str) -> Path:
    if output_path and output_path.strip():
        path = Path(output_path.strip())
        resolved = path if path.is_absolute() else WORKSPACE / path
        return resolved if resolved.suffix == ".wav" else resolved.with_suffix(".wav")
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    preview = _safe_file_name(text[:48])
    return WORKSPACE / ".opencode" / "generated" / "tts" / f"{stamp}-{preview}.wav"


def _resolve_device(device: str | None) -> str:
    if device and device != "auto":
        return device

    import torch

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _as_audio_array(chunk):
    import numpy as np

    if hasattr(chunk, "detach"):
        chunk = chunk.detach().cpu().numpy()
    return np.asarray(chunk, dtype=np.float32).reshape(-1)


def kokoro_tts(
    text: str,
    outputPath: str | None = None,
    voice: str | None = None,
    langCode: str | None = None,
    speed: float | None = None,
    splitPattern: str | None = None,
    device: str | None = None,
) -> str:
    """Convert text to speech with Kokoro and save the generated audio as a WAV file."""
    text = text.strip()
    if not text:
        raise ValueError("text is required")

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    output_path = _resolve_output_path(outputPath, text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voice_name = (voice or DEFAULT_TTS_VOICE).strip()
    lang_code = (langCode or DEFAULT_LANG_CODE).strip()
    tts_speed = speed if isinstance(speed, (int, float)) and speed > 0 else 1.0
    split_pattern = (splitPattern or r"\n+").strip()
    device_name = _resolve_device((device or "auto").strip())

    pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M", device=device_name)
    chunks = []
    for _, _, chunk in pipeline(text, voice=voice_name, speed=tts_speed, split_pattern=split_pattern):
        audio = _as_audio_array(chunk)
        if audio.size:
            chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro did not generate any audio")

    audio = np.concatenate(chunks)
    sf.write(output_path, audio, SAMPLE_RATE)
    duration_seconds = round(float(len(audio)) / SAMPLE_RATE, 3)
    return json_result(
        f"Generated speech with hexgrad/Kokoro-82M ({voice_name}).\nFile: {output_path}\nDuration: {duration_seconds} seconds at {SAMPLE_RATE} Hz",
        {
            "output_path": str(output_path),
            "model": "hexgrad/Kokoro-82M",
            "text": text,
            "voice": voice_name,
            "lang_code": lang_code,
            "speed": tts_speed,
            "split_pattern": split_pattern,
            "device": device_name,
            "duration_seconds": duration_seconds,
            "sample_rate": SAMPLE_RATE,
        },
    )

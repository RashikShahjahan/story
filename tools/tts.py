from __future__ import annotations

import re
import time
from pathlib import Path

from .common import WORKSPACE, json_result


DEFAULT_TTS_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"
SAMPLE_RATE = 24_000


def _safe_file_name(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")[:80]


def _resolve_output_path(output_path: str | None, text: str) -> Path:
    if output_path is not None:
        path = Path(output_path.strip())
        resolved = path if path.is_absolute() else WORKSPACE / path
        return resolved.with_suffix(".wav")
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    preview = _safe_file_name(text[:48])
    return WORKSPACE / ".opencode" / "generated" / "tts" / f"{stamp}-{preview}.wav"


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device

    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
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
    voice: str = DEFAULT_TTS_VOICE,
    langCode: str = DEFAULT_LANG_CODE,
    speed: float = 1.0,
    splitPattern: str = r"\n+",
    device: str = "auto",
) -> str:
    """Convert text to speech with Kokoro and save the generated audio as a WAV file."""
    text = text.strip()

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    output_path = _resolve_output_path(outputPath, text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voice_name = voice.strip()
    lang_code = langCode.strip()
    split_pattern = splitPattern.strip()
    device_name = _resolve_device(device.strip())

    pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M", device=device_name)
    chunks = []
    for _, _, chunk in pipeline(text, voice=voice_name, speed=speed, split_pattern=split_pattern):
        chunks.append(_as_audio_array(chunk))

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
            "speed": speed,
            "split_pattern": split_pattern,
            "device": device_name,
            "duration_seconds": duration_seconds,
            "sample_rate": SAMPLE_RATE,
        },
    )

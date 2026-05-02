from __future__ import annotations

import re
import time
from pathlib import Path

from ..common import WORKSPACE, json_result


DEFAULT_TTS_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"
MODEL_NAME = "mlx-community/Kokoro-82M-bf16"
SAMPLE_RATE = 24_000


def _safe_file_name(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")[:80] or "speech"


def _resolve_output_path(output_path: str | None, text: str) -> Path:
    if output_path:
        path = Path(output_path.strip())
        resolved = path if path.is_absolute() else WORKSPACE / path
        return resolved.with_suffix(".wav")
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    preview = _safe_file_name(text[:48])
    return WORKSPACE / ".opencode" / "generated" / "tts" / f"{stamp}-{preview}.wav"


def _as_audio_array(chunk):
    import numpy as np

    return np.asarray(chunk, dtype=np.float32).reshape(-1)


def kokoro_tts(
    text: str,
    outputPath: str | None = None,
    voice: str = DEFAULT_TTS_VOICE,
    langCode: str = DEFAULT_LANG_CODE,
    speed: float = 1.0,
) -> str:
    """Convert text to speech with MLX-Audio Kokoro and save the generated audio as a WAV file."""
    text = text.strip()

    import numpy as np
    import soundfile as sf
    from mlx_audio.tts.utils import load_model

    output_path = _resolve_output_path(outputPath, text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voice_name = voice.strip()
    lang_code = langCode.strip()
    model = load_model(MODEL_NAME)
    chunks = [_as_audio_array(result.audio) for result in model.generate(text=text, voice=voice_name, speed=speed, lang_code=lang_code)]

    audio = np.concatenate(chunks)
    sample_rate = int(getattr(model, "sample_rate", SAMPLE_RATE) or SAMPLE_RATE)
    sf.write(output_path, audio, sample_rate)
    duration_seconds = round(float(len(audio)) / sample_rate, 3)
    return json_result(
        f"Generated speech with {MODEL_NAME} ({voice_name}).\nFile: {output_path}\nDuration: {duration_seconds} seconds at {sample_rate} Hz",
        {
            "output_path": str(output_path),
            "model": MODEL_NAME,
            "text": text,
            "voice": voice_name,
            "lang_code": lang_code,
            "speed": speed,
            "duration_seconds": duration_seconds,
            "sample_rate": sample_rate,
        },
    )

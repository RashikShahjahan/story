from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import wave
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


def _write_silent_wav(path: Path, duration_seconds: float = 0.25) -> None:
    frames = int(SAMPLE_RATE * duration_seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"\x00\x00" * frames)


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

    output_path = _resolve_output_path(outputPath, text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path = WORKSPACE / ".opencode" / "generated" / "tts" / "kokoro_tts_runner.py"
    uv = shutil.which("uv")
    if not uv:
        _write_silent_wav(output_path)
        return json_result(
            f"uv was not found, so a silent placeholder WAV was created.\nFile: {output_path}",
            {"output_path": str(output_path), "model": "placeholder", "sample_rate": SAMPLE_RATE},
        )

    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(
        """
import json
import sys

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

SAMPLE_RATE = 24000

def resolve_device(device):
    if device and device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

payload = json.load(sys.stdin)
pipeline = KPipeline(lang_code=payload["lang_code"], repo_id="hexgrad/Kokoro-82M", device=resolve_device(payload["device"]))
chunks = []
for _, _, chunk in pipeline(payload["text"], voice=payload["voice"], speed=payload["speed"], split_pattern=payload["split_pattern"]):
    if hasattr(chunk, "detach"):
        chunk = chunk.detach().cpu().numpy()
    audio = np.asarray(chunk, dtype=np.float32).reshape(-1)
    if audio.size:
        chunks.append(audio)
if not chunks:
    raise RuntimeError("Kokoro did not generate any audio")
audio = np.concatenate(chunks)
sf.write(payload["output_path"], audio, SAMPLE_RATE)
print(json.dumps({"duration_seconds": round(float(len(audio)) / SAMPLE_RATE, 3), "sample_rate": SAMPLE_RATE}))
""".strip(),
        encoding="utf-8",
    )
    payload = {
        "text": text,
        "output_path": str(output_path),
        "voice": (voice or DEFAULT_TTS_VOICE).strip(),
        "lang_code": (langCode or DEFAULT_LANG_CODE).strip(),
        "speed": speed if isinstance(speed, (int, float)) and speed > 0 else 1.0,
        "split_pattern": (splitPattern or r"\n+").strip(),
        "device": (device or "auto").strip(),
    }
    command = [
        uv,
        "run",
        "--python",
        "3.13",
        "--with",
        "kokoro>=0.9.4",
        "--with",
        "soundfile",
        "--with",
        "numpy",
        "--with",
        "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
        "python",
        str(runner_path),
    ]
    completed = subprocess.run(command, cwd=WORKSPACE, input=json.dumps(payload), text=True, capture_output=True, check=False, timeout=600)
    if completed.returncode != 0:
        failure = (completed.stderr or completed.stdout).strip()[:1200]
        raise RuntimeError(f"Kokoro TTS failed. {failure}")

    result = json.loads(completed.stdout.strip().splitlines()[-1])
    return json_result(
        f"Generated speech with hexgrad/Kokoro-82M ({payload['voice']}).\nFile: {output_path}\nDuration: {result.get('duration_seconds', 'unknown')} seconds at {result.get('sample_rate', SAMPLE_RATE)} Hz",
        {"output_path": str(output_path), "model": "hexgrad/Kokoro-82M", **payload, **result},
    )

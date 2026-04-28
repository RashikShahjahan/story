import { tool } from "@opencode-ai/plugin"
import path from "path"

const MODEL_ID = "hexgrad/Kokoro-82M"
const DEFAULT_VOICE = "af_heart"
const DEFAULT_LANG_CODE = "a"
const SAMPLE_RATE = 24000
const PYTHON_VERSION = "3.13"
const EN_SPACY_MODEL = "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

function safeFileName(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "speech"
}

function resolveOutputPath(directory: string, outputPath: string | undefined, text: string) {
  const trimmed = outputPath?.trim()
  if (trimmed) {
    const resolved = path.isAbsolute(trimmed) ? trimmed : path.resolve(directory, trimmed)
    return resolved.endsWith(".wav") ? resolved : `${resolved}.wav`
  }

  const preview = safeFileName(text.slice(0, 48))
  const stamp = new Date().toISOString().replace(/[:.]/g, "-")
  return path.resolve(directory, ".opencode/generated/tts", `${stamp}-${preview}.wav`)
}

async function commandExists(command: string) {
  const proc = Bun.spawn(["/bin/zsh", "-lc", `command -v ${command}`], {
    stdout: "ignore",
    stderr: "ignore",
  })
  return (await proc.exited) === 0
}

export default tool({
  description: "Convert text to speech with hexgrad/Kokoro-82M and save the generated audio as a WAV file.",
  args: {
    text: tool.schema.string().describe("Text to synthesize into speech"),
    outputPath: tool.schema.string().optional().describe("Optional output WAV path. Relative paths are resolved from the workspace root."),
    voice: tool.schema.string().optional().describe("Kokoro voice name. Defaults to af_heart."),
    langCode: tool.schema.string().optional().describe("Kokoro language code matching the voice. Defaults to a for American English."),
    speed: tool.schema.number().optional().describe("Speech speed multiplier. Defaults to 1.0."),
    splitPattern: tool.schema.string().optional().describe("Regex used by Kokoro to split long text. Defaults to one or more newlines."),
    device: tool.schema.string().optional().describe("Device for Kokoro. Defaults to auto: cuda, then mps, then cpu."),
  },
  async execute(args, context) {
    const text = args.text.trim()
    if (!text) throw new Error("text is required")

    if (!(await commandExists("uv"))) {
      throw new Error("uv is required to run Kokoro TTS. Install it from https://docs.astral.sh/uv/ or add it to PATH.")
    }

    const outputPath = resolveOutputPath(context.directory, args.outputPath, text)
    const outputDir = path.dirname(outputPath)
    const voice = args.voice?.trim() || DEFAULT_VOICE
    const langCode = args.langCode?.trim() || DEFAULT_LANG_CODE
    const speed = typeof args.speed === "number" && Number.isFinite(args.speed) && args.speed > 0 ? args.speed : 1
    const splitPattern = args.splitPattern?.trim() || String.raw`\n+`
    const device = args.device?.trim() || "auto"

    await Bun.$`mkdir -p ${outputDir}`.quiet()

    const scriptPath = path.resolve(context.directory, ".opencode/generated/tts/kokoro_tts_runner.py")
    await Bun.write(scriptPath, String.raw`import json
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


def main():
    payload = json.load(sys.stdin)
    text = payload["text"]
    output_path = payload["output_path"]
    voice = payload.get("voice") or "af_heart"
    lang_code = payload.get("lang_code") or "a"
    speed = float(payload.get("speed") or 1.0)
    split_pattern = payload.get("split_pattern") or r"\n+"
    device = resolve_device(payload.get("device") or "auto")

    pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M", device=device)
    generated = pipeline(text, voice=voice, speed=speed, split_pattern=split_pattern)

    chunks = []
    chunk_metadata = []
    for index, (graphemes, phonemes, chunk) in enumerate(generated):
        if hasattr(chunk, "detach"):
            chunk = chunk.detach().cpu().numpy()
        audio = np.asarray(chunk, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            continue
        chunks.append(audio)
        chunk_metadata.append({
            "index": index,
            "samples": int(audio.size),
            "text": graphemes,
            "phonemes": phonemes,
        })

    if not chunks:
        raise RuntimeError("Kokoro did not generate any audio")

    audio = np.concatenate(chunks)
    sf.write(output_path, audio, SAMPLE_RATE)

    print(json.dumps({
        "output_path": output_path,
        "model": "hexgrad/Kokoro-82M",
        "voice": voice,
        "lang_code": lang_code,
        "sample_rate": SAMPLE_RATE,
        "duration_seconds": round(float(len(audio)) / SAMPLE_RATE, 3),
        "chunks": chunk_metadata,
        "device": device,
    }))


if __name__ == "__main__":
    main()
`)

    context.metadata({ title: `Kokoro TTS: ${voice}` })

    const proc = Bun.spawn([
      "uv",
      "run",
      "--python",
      PYTHON_VERSION,
      "--with",
      "kokoro>=0.9.4",
      "--with",
      "soundfile",
      "--with",
      "numpy",
      "--with",
      EN_SPACY_MODEL,
      "python",
      scriptPath,
    ], {
      cwd: context.directory,
      stdin: "pipe",
      stdout: "pipe",
      stderr: "pipe",
      env: { ...process.env, PYTHONUNBUFFERED: "1", PYTORCH_ENABLE_MPS_FALLBACK: "1" },
      signal: context.abort,
    })

    proc.stdin.write(JSON.stringify({
      text,
      output_path: outputPath,
      voice,
      lang_code: langCode,
      speed,
      split_pattern: splitPattern,
      device,
    }))
    proc.stdin.end()

    const [stdout, stderr, exitCode] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
      proc.exited,
    ])

    if (exitCode !== 0) {
      const details = stderr.trim() || stdout.trim() || `exit code ${exitCode}`
      throw new Error([
        "Kokoro TTS failed.",
        details.slice(0, 2000),
        "The first run downloads hexgrad/Kokoro-82M and may require espeak-ng for some languages.",
      ].join("\n"))
    }

    const result = JSON.parse(stdout.trim().split("\n").at(-1) ?? "{}") as {
      output_path?: string
      model?: string
      voice?: string
      lang_code?: string
      sample_rate?: number
      duration_seconds?: number
      chunks?: Array<{ index: number; samples: number; text?: string; phonemes?: string }>
      device?: string
    }

    return {
      output: [
        `Generated speech with ${result.model ?? MODEL_ID} (${result.voice ?? voice}).`,
        `File: ${result.output_path ?? outputPath}`,
        `Duration: ${result.duration_seconds ?? "unknown"} seconds at ${result.sample_rate ?? SAMPLE_RATE} Hz`,
      ].join("\n"),
      metadata: {
        output_path: result.output_path ?? outputPath,
        model: result.model ?? MODEL_ID,
        voice: result.voice ?? voice,
        lang_code: result.lang_code ?? langCode,
        speed,
        split_pattern: splitPattern,
        device: result.device ?? device,
        sample_rate: result.sample_rate ?? SAMPLE_RATE,
        duration_seconds: result.duration_seconds,
        chunks: result.chunks ?? [],
      },
    }
  },
})

import { tool } from "@opencode-ai/plugin"
import path from "path"

const MODEL_ID = "k2-fsa/OmniVoice"
const DEFAULT_NUM_STEP = 32
const SAMPLE_RATE = 24000
const PYTHON_VERSION = "3.13"

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

function resolveOptionalInputPath(directory: string, inputPath: string | undefined) {
  const trimmed = inputPath?.trim()
  if (!trimmed) return undefined
  return path.isAbsolute(trimmed) ? trimmed : path.resolve(directory, trimmed)
}

async function commandExists(command: string) {
  const proc = Bun.spawn(["/bin/zsh", "-lc", `command -v ${command}`], {
    stdout: "ignore",
    stderr: "ignore",
  })
  return (await proc.exited) === 0
}

export default tool({
  description: "Convert text to speech with k2-fsa/OmniVoice and save the generated audio as a WAV file.",
  args: {
    text: tool.schema.string().describe("Text to synthesize into speech"),
    outputPath: tool.schema.string().optional().describe("Optional output WAV path. Relative paths are resolved from the workspace root."),
    instruct: tool.schema.string().optional().describe("Optional OmniVoice voice-design prompt, such as 'female, low pitch, British accent'. If omitted with no refAudio, OmniVoice chooses a voice."),
    refAudio: tool.schema.string().optional().describe("Optional reference audio path for OmniVoice voice cloning. Relative paths are resolved from the workspace root."),
    refText: tool.schema.string().optional().describe("Optional transcription of refAudio. If omitted with refAudio, OmniVoice may auto-transcribe it."),
    languageId: tool.schema.string().optional().describe("Optional OmniVoice language_id hint, such as en, when the model needs one."),
    speed: tool.schema.number().optional().describe("Speech speed multiplier. Defaults to 1.0."),
    duration: tool.schema.number().optional().describe("Optional fixed output duration in seconds. Overrides speed when provided."),
    numStep: tool.schema.number().optional().describe("OmniVoice diffusion step count. Defaults to 32; use 16 for faster inference."),
    device: tool.schema.string().optional().describe("Device map for OmniVoice. Defaults to auto: cuda:0, then mps, then cpu."),
    dtype: tool.schema.string().optional().describe("Torch dtype for model loading: auto, float16, float32, or bfloat16. Defaults to auto."),
  },
  async execute(args, context) {
    const text = args.text.trim()
    if (!text) throw new Error("text is required")

    if (!(await commandExists("uv"))) {
      throw new Error("uv is required to run OmniVoice TTS. Install it from https://docs.astral.sh/uv/ or add it to PATH.")
    }

    const outputPath = resolveOutputPath(context.directory, args.outputPath, text)
    const outputDir = path.dirname(outputPath)
    const instruct = args.instruct?.trim() || undefined
    const refAudio = resolveOptionalInputPath(context.directory, args.refAudio)
    const refText = args.refText?.trim() || undefined
    if (instruct && refAudio) throw new Error("Use either instruct for voice design or refAudio for voice cloning, not both.")
    if (refText && !refAudio) throw new Error("refText requires refAudio.")

    const languageId = args.languageId?.trim() || undefined
    const speed = typeof args.speed === "number" && Number.isFinite(args.speed) && args.speed > 0 ? args.speed : 1
    const duration = typeof args.duration === "number" && Number.isFinite(args.duration) && args.duration > 0 ? args.duration : undefined
    const numStep = typeof args.numStep === "number" && Number.isFinite(args.numStep) && args.numStep > 0 ? Math.round(args.numStep) : DEFAULT_NUM_STEP
    const device = args.device?.trim() || "auto"
    const dtype = args.dtype?.trim() || "auto"

    await Bun.$`mkdir -p ${outputDir}`.quiet()

    const scriptPath = path.resolve(context.directory, ".opencode/generated/tts/omnivoice_tts_runner.py")
    await Bun.write(scriptPath, String.raw`import json
import sys

import numpy as np
import soundfile as sf
import torch
from omnivoice import OmniVoice

SAMPLE_RATE = 24000


def optional(value):
    if isinstance(value, str):
        value = value.strip()
    return value or None


def resolve_device(device):
    if device and device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda:0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_dtype(dtype, device):
    choices = {
        "float16": torch.float16,
        "float32": torch.float32,
        "bfloat16": torch.bfloat16,
    }
    if dtype and dtype != "auto":
        if dtype not in choices:
            raise ValueError(f"Unsupported dtype {dtype!r}; use auto, float16, float32, or bfloat16")
        return choices[dtype], dtype
    if device.startswith("cuda") or device == "mps":
        return torch.float16, "float16"
    return torch.float32, "float32"


def main():
    payload = json.load(sys.stdin)
    text = payload["text"]
    output_path = payload["output_path"]
    model_id = payload.get("model_id") or "k2-fsa/OmniVoice"
    device = resolve_device(payload.get("device") or "auto")
    dtype, dtype_name = resolve_dtype(payload.get("dtype") or "auto", device)

    model = OmniVoice.from_pretrained(model_id, device_map=device, dtype=dtype)

    generate_kwargs = {
        "text": text,
        "speed": payload.get("speed") or 1.0,
        "num_step": int(payload.get("num_step") or 32),
    }
    duration = payload.get("duration")
    if duration is not None:
        generate_kwargs["duration"] = float(duration)

    ref_audio = optional(payload.get("ref_audio"))
    ref_text = optional(payload.get("ref_text"))
    instruct = optional(payload.get("instruct"))
    language_id = optional(payload.get("language_id"))

    if ref_audio:
        generate_kwargs["ref_audio"] = ref_audio
    if ref_text:
        generate_kwargs["ref_text"] = ref_text
    if instruct:
        generate_kwargs["instruct"] = instruct
    if language_id:
        generate_kwargs["language_id"] = language_id

    generated = model.generate(**generate_kwargs)
    if generated is None:
        raise RuntimeError("OmniVoice did not generate any audio")
    if isinstance(generated, np.ndarray) or hasattr(generated, "detach"):
        generated = [generated]
    if len(generated) == 0:
        raise RuntimeError("OmniVoice did not generate any audio")

    chunks = []
    chunk_metadata = []
    for index, chunk in enumerate(generated):
        if hasattr(chunk, "detach"):
            chunk = chunk.detach().cpu().numpy()
        audio = np.asarray(chunk, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            continue
        chunks.append(audio)
        chunk_metadata.append({"index": index, "samples": int(audio.size)})

    if not chunks:
        raise RuntimeError("OmniVoice generated only empty audio chunks")

    audio = np.concatenate(chunks)
    sf.write(output_path, audio, SAMPLE_RATE)

    print(json.dumps({
        "output_path": output_path,
        "model": model_id,
        "sample_rate": SAMPLE_RATE,
        "duration_seconds": round(float(len(audio)) / SAMPLE_RATE, 3),
        "chunks": chunk_metadata,
        "device": device,
        "dtype": dtype_name,
    }))


if __name__ == "__main__":
    main()
`)

    const title = instruct ? `OmniVoice TTS: ${instruct}` : refAudio ? "OmniVoice TTS: voice clone" : "OmniVoice TTS"
    context.metadata({ title })

    const proc = Bun.spawn([
      "uv",
      "run",
      "--python",
      PYTHON_VERSION,
      "--with",
      "omnivoice>=0.1.4",
      "--with",
      "torch==2.8.0",
      "--with",
      "torchaudio==2.8.0",
      "--with",
      "soundfile",
      "--with",
      "numpy",
      "python",
      scriptPath,
    ], {
      cwd: context.directory,
      stdin: "pipe",
      stdout: "pipe",
      stderr: "pipe",
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      signal: context.abort,
    })

    proc.stdin.write(JSON.stringify({
      text,
      output_path: outputPath,
      model_id: MODEL_ID,
      instruct,
      ref_audio: refAudio,
      ref_text: refText,
      language_id: languageId,
      speed,
      duration,
      num_step: numStep,
      device,
      dtype,
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
        "OmniVoice TTS failed.",
        details.slice(0, 2000),
        "The first run downloads k2-fsa/OmniVoice and may require substantial disk space and memory.",
      ].join("\n"))
    }

    const result = JSON.parse(stdout.trim().split("\n").at(-1) ?? "{}") as {
      output_path?: string
      model?: string
      sample_rate?: number
      duration_seconds?: number
      chunks?: Array<{ index: number; samples: number }>
      device?: string
      dtype?: string
    }

    const mode = refAudio ? " using reference audio" : instruct ? ` using voice design "${instruct}"` : ""
    return {
      output: [
        `Generated speech with ${result.model ?? MODEL_ID}${mode}.`,
        `File: ${result.output_path ?? outputPath}`,
        `Duration: ${result.duration_seconds ?? "unknown"} seconds at ${result.sample_rate ?? SAMPLE_RATE} Hz`,
      ].join("\n"),
      metadata: {
        output_path: result.output_path ?? outputPath,
        model: result.model ?? MODEL_ID,
        instruct,
        ref_audio: refAudio,
        ref_text: refText,
        language_id: languageId,
        speed,
        duration,
        num_step: numStep,
        device: result.device ?? device,
        dtype: result.dtype ?? dtype,
        sample_rate: result.sample_rate ?? SAMPLE_RATE,
        duration_seconds: result.duration_seconds,
        chunks: result.chunks ?? [],
      },
    }
  },
})

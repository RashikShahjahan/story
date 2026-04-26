import { tool } from "@opencode-ai/plugin"
import path from "path"

const DEFAULT_VOICE = "af_heart"
const DEFAULT_LANG_CODE = "a"
const SAMPLE_RATE = 24000

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
    langCode: tool.schema.string().optional().describe("Kokoro language code. Defaults to a for American English."),
    speed: tool.schema.number().optional().describe("Speech speed multiplier. Defaults to 1.0."),
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

    await Bun.$`mkdir -p ${outputDir}`.quiet()

    const scriptPath = path.resolve(context.directory, ".opencode/generated/tts/kokoro_tts_runner.py")
    await Bun.write(scriptPath, String.raw`import json
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def main():
    payload = json.load(sys.stdin)
    text = payload["text"]
    output_path = payload["output_path"]
    voice = payload["voice"]
    lang_code = payload["lang_code"]
    speed = payload["speed"]

    pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
    chunks = []
    segments = []

    for index, (graphemes, phonemes, audio) in enumerate(pipeline(text, voice=voice, speed=speed)):
        chunks.append(audio)
        segments.append({
            "index": index,
            "text": graphemes,
            "phonemes": phonemes,
            "samples": int(len(audio)),
        })

    if not chunks:
        raise RuntimeError("Kokoro did not generate any audio")

    audio = np.concatenate(chunks)
    sf.write(output_path, audio, 24000)

    print(json.dumps({
        "output_path": output_path,
        "sample_rate": 24000,
        "duration_seconds": round(float(len(audio)) / 24000, 3),
        "segments": segments,
    }))


if __name__ == "__main__":
    main()
`)

    context.metadata({ title: `Kokoro TTS: ${voice}` })

    const proc = Bun.spawn([
      "uv",
      "run",
      "--with",
      "kokoro>=0.9.2",
      "--with",
      "soundfile",
      "--with",
      "numpy",
      "--with",
      "torch",
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
      voice,
      lang_code: langCode,
      speed,
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
        "If the error mentions espeak-ng, install it with: brew install espeak-ng",
      ].join("\n"))
    }

    const result = JSON.parse(stdout.trim().split("\n").at(-1) ?? "{}") as {
      output_path?: string
      sample_rate?: number
      duration_seconds?: number
      segments?: Array<{ index: number; text: string; phonemes: string; samples: number }>
    }

    return {
      output: [
        `Generated speech with Kokoro voice ${voice}.`,
        `File: ${result.output_path ?? outputPath}`,
        `Duration: ${result.duration_seconds ?? "unknown"} seconds at ${result.sample_rate ?? SAMPLE_RATE} Hz`,
      ].join("\n"),
      metadata: {
        output_path: result.output_path ?? outputPath,
        voice,
        lang_code: langCode,
        speed,
        sample_rate: result.sample_rate ?? SAMPLE_RATE,
        duration_seconds: result.duration_seconds,
        segments: result.segments ?? [],
      },
    }
  },
})

import { tool } from "@opencode-ai/plugin"
import path from "path"

type MemoryEntry = {
  id?: string
  memory?: string
  source?: string
  metadata?: Record<string, unknown>
  createdAt?: string
}

function memoriesPath(context: { directory: string }) {
  return path.resolve(context.directory, ".opencode/memories.json")
}

export default tool({
  description: "Read all durable user memories from the local JSON memory file.",
  args: {},
  async execute(_args, context) {
    const filePath = memoriesPath(context)
    const file = Bun.file(filePath)

    if (!(await file.exists())) {
      return {
        output: "No memories saved yet.",
      }
    }

    const text = (await file.text()).trim()
    if (!text) {
      return {
        output: "No memories saved yet.",
      }
    }

    const parsed = JSON.parse(text)
    if (!Array.isArray(parsed)) {
      throw new Error(`Expected ${filePath} to contain a JSON array`)
    }

    const memories = parsed as MemoryEntry[]
    if (memories.length === 0) {
      return {
        output: "No memories saved yet.",
      }
    }

    const output = memories
      .map((entry, index) => `${index + 1}. ${entry.memory ?? JSON.stringify(entry)}`)
      .join("\n")

    return {
      output,
    }
  },
})

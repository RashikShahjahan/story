import { tool } from "@opencode-ai/plugin"
import path from "path"

type MemoryEntry = {
  id: string
  memory: string
  source?: string
  metadata?: Record<string, unknown>
  createdAt: string
}

function memoriesPath(context: { directory: string }) {
  return path.resolve(context.directory, ".opencode/memories.json")
}

async function readMemories(filePath: string): Promise<MemoryEntry[]> {
  const file = Bun.file(filePath)

  if (!(await file.exists())) {
    return []
  }

  const text = (await file.text()).trim()
  if (!text) {
    return []
  }

  const parsed = JSON.parse(text)
  if (!Array.isArray(parsed)) {
    throw new Error(`Expected ${filePath} to contain a JSON array`)
  }

  return parsed as MemoryEntry[]
}

export default tool({
  description: "Record a durable user memory to the local JSON memory file.",
  args: {
    memory: tool.schema.string().min(1).describe("Concise memory text to save"),
    source: tool.schema.string().optional().describe("Optional source or reason for the memory"),
    metadata: tool.schema.record(tool.schema.string(), tool.schema.unknown()).optional().describe("Optional structured metadata"),
  },
  async execute(args, context) {
    const memory = args.memory.trim()

    if (!memory) {
      throw new Error("memory must not be empty")
    }

    const filePath = memoriesPath(context)
    const memories = await readMemories(filePath)
    const entry: MemoryEntry = {
      id: crypto.randomUUID(),
      memory,
      createdAt: new Date().toISOString(),
    }

    if (args.source?.trim()) {
      entry.source = args.source.trim()
    }

    if (args.metadata && Object.keys(args.metadata).length > 0) {
      entry.metadata = args.metadata
    }

    memories.push(entry)

    await Bun.write(filePath, `${JSON.stringify(memories, null, 2)}\n`)

    return {
      output: `Recorded memory: ${memory}`,
      metadata: {
        id: entry.id,
        path: filePath,
      },
    }
  },
})

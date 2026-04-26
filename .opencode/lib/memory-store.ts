import { mkdir } from "fs/promises"
import path from "path"

export const ENTRY_SEPARATOR = "§"
const FILE_SEPARATOR = `\n${ENTRY_SEPARATOR}\n`

export const MEMORY_TARGETS = {
  memory: {
    fileName: "MEMORY.md",
    label: "MEMORY (agent notes)",
    limit: 2200,
  },
  user: {
    fileName: "USER.md",
    label: "USER PROFILE",
    limit: 1375,
  },
} as const

export type MemoryTarget = keyof typeof MEMORY_TARGETS

export type MemoryStore = {
  target: MemoryTarget
  entries: string[]
}

export function isMemoryTarget(value: string): value is MemoryTarget {
  return value === "memory" || value === "user"
}

export function parseTarget(value: string | undefined): MemoryTarget {
  const target = value?.trim().toLowerCase() || "memory"

  if (!isMemoryTarget(target)) {
    throw new Error(`target must be either "memory" or "user", got: ${value}`)
  }

  return target
}

function memoriesDirectory(context: { directory: string }) {
  return path.resolve(context.directory, ".opencode/memories")
}

export function memoryPath(context: { directory: string }, target: MemoryTarget) {
  return path.join(memoriesDirectory(context), MEMORY_TARGETS[target].fileName)
}

function normalizeEntry(value: string) {
  return value.trim().replace(/\r\n/g, "\n")
}

export function parseEntries(text: string) {
  return text
    .split(new RegExp(`\\s*${ENTRY_SEPARATOR}\\s*`, "u"))
    .map(normalizeEntry)
    .filter(Boolean)
}

export async function readEntries(context: { directory: string }, target: MemoryTarget) {
  const file = Bun.file(memoryPath(context, target))

  if (!(await file.exists())) {
    return []
  }

  return parseEntries(await file.text())
}

export async function writeEntries(context: { directory: string }, target: MemoryTarget, entries: string[]) {
  await mkdir(memoriesDirectory(context), { recursive: true })
  const normalized = entries.map(normalizeEntry).filter(Boolean)
  const content = normalized.length > 0 ? `${normalized.join(FILE_SEPARATOR)}\n` : ""

  await Bun.write(memoryPath(context, target), content)
}

export async function readStores(context: { directory: string }): Promise<MemoryStore[]> {
  return [
    { target: "memory", entries: await readEntries(context, "memory") },
    { target: "user", entries: await readEntries(context, "user") },
  ]
}

export function usedChars(entries: string[]) {
  return entries.join(ENTRY_SEPARATOR).length
}

export function usage(target: MemoryTarget, entries: string[]) {
  const limit = MEMORY_TARGETS[target].limit
  const used = usedChars(entries)

  return {
    used,
    limit,
    percent: Math.round((used / limit) * 100),
  }
}

export function formatStore(target: MemoryTarget, entries: string[]) {
  const config = MEMORY_TARGETS[target]
  const currentUsage = usage(target, entries)
  const body = entries.length > 0 ? entries.join(ENTRY_SEPARATOR) : "(empty)"

  return `${config.label} [${currentUsage.percent}% - ${currentUsage.used}/${currentUsage.limit} chars]\n${body}`
}

export function formatStores(stores: MemoryStore[]) {
  return stores.map((store) => formatStore(store.target, store.entries)).join("\n\n")
}

export function assertSafeEntry(content: string) {
  if (content.includes(ENTRY_SEPARATOR)) {
    throw new Error(`memory content cannot contain the ${ENTRY_SEPARATOR} delimiter`)
  }

  if (/\p{Cf}/u.test(content)) {
    throw new Error("memory content cannot contain invisible Unicode control characters")
  }

  const blockedPatterns = [
    /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|system|developer)/i,
    /(reveal|print|dump|exfiltrate).{0,40}(system prompt|developer message|secrets?|credentials?)/i,
    /(?:password|token|secret|api[_ -]?key)\s*[:=]\s*["']?[A-Za-z0-9_./+=-]{12,}/i,
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
  ]

  for (const pattern of blockedPatterns) {
    if (pattern.test(content)) {
      throw new Error("memory content matched a blocked injection or secret pattern")
    }
  }
}

export function findSubstringMatches(entries: string[], oldText: string) {
  const needle = oldText.trim()

  if (!needle) {
    throw new Error("old_text must not be empty")
  }

  return entries
    .map((entry, index) => ({ entry, index }))
    .filter(({ entry }) => entry.includes(needle))
}

export function wouldExceedLimit(target: MemoryTarget, entries: string[]) {
  return usedChars(entries) > MEMORY_TARGETS[target].limit
}

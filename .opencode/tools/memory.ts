import { tool } from "@opencode-ai/plugin"
import {
  assertSafeEntry,
  findSubstringMatches,
  formatStore,
  MEMORY_TARGETS,
  parseTarget,
  readEntries,
  usage,
  wouldExceedLimit,
  writeEntries,
} from "../lib/memory-store"

type Action = "add" | "replace" | "remove"

const ACTIONS = new Set(["add", "replace", "remove"])

function parseAction(value: string): Action {
  const action = value.trim().toLowerCase()

  if (!ACTIONS.has(action)) {
    throw new Error(`action must be "add", "replace", or "remove", got: ${value}`)
  }

  return action as Action
}

function requireContent(value: string | undefined) {
  const content = value?.trim() ?? ""

  if (!content) {
    throw new Error("content is required for add and replace actions")
  }

  assertSafeEntry(content)
  return content
}

function currentEntriesText(entries: string[]) {
  return entries.length > 0
    ? entries.map((entry, index) => `${index + 1}. ${entry}`).join("\n")
    : "(empty)"
}

function capacityError(action: Action, target: keyof typeof MEMORY_TARGETS, entries: string[], nextEntries: string[]) {
  const currentUsage = usage(target, entries)
  const nextUsage = usage(target, nextEntries)

  return {
    output: `${MEMORY_TARGETS[target].label} is at ${currentUsage.used}/${currentUsage.limit} chars. ${action} would use ${nextUsage.used}/${nextUsage.limit} chars and exceed the limit. Replace, remove, or consolidate existing entries first.\nCurrent entries:\n${currentEntriesText(entries)}`,
    metadata: {
      success: false,
      error: "capacity_exceeded",
      target,
      usage: currentUsage,
      nextUsage,
      current_entries: entries,
    },
  }
}

function substringError(target: keyof typeof MEMORY_TARGETS, oldText: string, matches: number, entries: string[]) {
  const problem = matches === 0
    ? `No ${target} memory entry matched old_text: ${oldText}`
    : `${matches} ${target} memory entries matched old_text: ${oldText}. Use a more specific substring.`

  return {
    output: `${problem}\nCurrent entries:\n${currentEntriesText(entries)}`,
    metadata: {
      success: false,
      error: matches === 0 ? "not_found" : "ambiguous_match",
      target,
      old_text: oldText,
      current_entries: entries,
    },
  }
}

function success(action: Action, target: keyof typeof MEMORY_TARGETS, entries: string[], message: string) {
  return {
    output: `${message}\n${formatStore(target, entries)}`,
    metadata: {
      success: true,
      action,
      target,
      usage: usage(target, entries),
    },
  }
}

export default tool({
  description: "Manage bounded persistent memory stores with Hermes-style add, replace, and remove actions.",
  args: {
    action: tool.schema.string().describe("One of: add, replace, remove"),
    target: tool.schema.string().optional().describe("memory for agent notes, or user for user profile. Defaults to memory."),
    content: tool.schema.string().optional().describe("Memory entry content for add or replace actions"),
    old_text: tool.schema.string().optional().describe("Unique substring identifying the entry to replace or remove"),
  },
  async execute(args, context) {
    const action = parseAction(args.action)
    const target = parseTarget(args.target)
    const entries = await readEntries(context, target)

    if (action === "add") {
      const content = requireContent(args.content)

      if (entries.includes(content)) {
        return success(action, target, entries, `Duplicate ${target} memory not added.`)
      }

      const nextEntries = [...entries, content]
      if (wouldExceedLimit(target, nextEntries)) {
        return capacityError(action, target, entries, nextEntries)
      }

      await writeEntries(context, target, nextEntries)
      return success(action, target, nextEntries, `Added ${target} memory.`)
    }

    const oldText = args.old_text?.trim() ?? ""
    const matches = findSubstringMatches(entries, oldText)
    if (matches.length !== 1) {
      return substringError(target, oldText, matches.length, entries)
    }

    const [{ index, entry }] = matches

    if (action === "remove") {
      const nextEntries = entries.filter((_, entryIndex) => entryIndex !== index)

      await writeEntries(context, target, nextEntries)
      return success(action, target, nextEntries, `Removed ${target} memory: ${entry}`)
    }

    const content = requireContent(args.content)
    const duplicateIndex = entries.findIndex((current, entryIndex) => entryIndex !== index && current === content)
    if (duplicateIndex !== -1) {
      return success(action, target, entries, `Replacement already exists in ${target} memory; no duplicate added.`)
    }

    const nextEntries = entries.map((current, entryIndex) => (entryIndex === index ? content : current))
    if (wouldExceedLimit(target, nextEntries)) {
      return capacityError(action, target, entries, nextEntries)
    }

    await writeEntries(context, target, nextEntries)
    return success(action, target, nextEntries, `Replaced ${target} memory.`)
  },
})

---
name: save-memory
description: Create a concise memory from provided context and persist it with the memory tool.
license: MIT
compatibility: opencode
metadata:
  tool: memory
  output: json
---

## Purpose

Use this skill when the user shares a durable preference, personal detail, story continuity fact, project convention, or instruction that should be remembered for future sessions.

## Memory Criteria

Save a memory only when the context is likely to remain useful beyond the current conversation, such as:

- User preferences for story tone, genre, characters, pacing, or visual style.
- Recurring facts about a world, character, location, or ongoing story arc.
- User-specific instructions for how stories or animations should be created.
- Environment facts, project conventions, workflow lessons, or completed work that will help future sessions.
- Corrections to previously stored preferences or continuity.

Do not save temporary requests, one-off commands, sensitive secrets, credentials, or information the user has not implied should persist.

## Targets

- Use `target: "user"` for user profile facts: preferences, communication style, personal details, expectations, and pet peeves.
- Use `target: "memory"` for agent notes: project structure, environment facts, story-world continuity, workflow conventions, tool quirks, and completed work.

## Workflow

1. Read the provided context carefully.
2. Extract one clear, durable memory.
3. Write the memory as a concise factual sentence in third person where possible.
4. If the context contains multiple unrelated durable facts, create separate memories.
5. Use `memory(action: "add", target: "user" | "memory", content: "...")` to save each new memory.
6. For corrections, use `memory(action: "replace", target: "user" | "memory", old_text: "unique substring", content: "...")` instead of adding a conflicting duplicate.
7. If the target store is near capacity, consolidate related entries with `replace` before adding more.
8. Briefly confirm what was saved.

## Tool Usage

Call `memory` with an action, target, and content.

Add a user preference:

```json
{
  "action": "add",
  "target": "user",
  "content": "The user prefers whimsical stories with gentle humor."
}
```

Replace a corrected project or continuity fact:

```json
{
  "action": "replace",
  "target": "memory",
  "old_text": "Mira's lantern",
  "content": "The user's story world includes Mira's lantern, which reveals hidden doors only under moonlight."
}
```

## Memory Style

- Keep each memory specific and short.
- Preserve the user's stated meaning without adding assumptions.
- Use neutral wording.
- Prefer "The user prefers..." or "The user's story world includes..." for clarity.
- When updating an existing preference, replace the old entry so the newest correction is the current preference.



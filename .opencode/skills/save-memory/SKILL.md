---
name: save-memory
description: Create a concise memory from provided context and persist it with the record-memory tool.
license: MIT
compatibility: opencode
metadata:
  tool: record-memory
  output: json
---

## Purpose

Use this skill when the user shares a durable preference, personal detail, story continuity fact, or instruction that should be remembered for future sessions.

## Memory Criteria

Save a memory only when the context is likely to remain useful beyond the current conversation, such as:

- User preferences for story tone, genre, characters, pacing, or visual style.
- Recurring facts about a world, character, location, or ongoing story arc.
- User-specific instructions for how stories or animations should be created.
- Corrections to previously stored preferences or continuity.

Do not save temporary requests, one-off commands, sensitive secrets, credentials, or information the user has not implied should persist.

## Workflow

1. Read the provided context carefully.
2. Extract one clear, durable memory.
3. Write the memory as a concise factual sentence in third person where possible.
4. If the context contains multiple unrelated durable facts, create separate memories.
5. Use the `record-memory` tool to write each memory to the JSON memory file.
6. Briefly confirm what was saved.

## Tool Usage

Call `record-memory` with the memory text and any useful metadata supported by the tool.

Prefer this shape when the tool accepts structured input:

```json
{
  "memory": "The user prefers whimsical stories with gentle humor.",
  "source": "user-provided context"
}
```

If the tool only accepts plain text, pass only the memory sentence.

## Memory Style

- Keep each memory specific and short.
- Preserve the user's stated meaning without adding assumptions.
- Use neutral wording.
- Prefer "The user prefers..." or "The user's story world includes..." for clarity.
- When updating an existing preference, save the newest correction as the current preference.

## Examples

User context: "I like dragons, but make them friendly and a little clumsy."

Memory: "The user prefers friendly, slightly clumsy dragons in stories."

User context: "In our story, Mira's lantern can reveal hidden doors."

Memory: "The user's story world includes Mira's lantern, which can reveal hidden doors."

User context: "Just make this scene shorter."

Do not save: this is a temporary editing request.

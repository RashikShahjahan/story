import { tool } from "@opencode-ai/plugin"
import { formatStores, readStores } from "../lib/memory-store"

export default tool({
  description: "Read the session-start snapshot of bounded persistent memory stores.",
  args: {},
  async execute(_args, context) {
    return {
      output: formatStores(await readStores(context)),
    }
  },
})

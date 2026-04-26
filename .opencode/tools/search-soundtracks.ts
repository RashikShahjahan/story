import { tool } from "@opencode-ai/plugin"

const OPENVERSE_AUDIO_URL = "https://api.openverse.org/v1/audio/"

type OpenverseAudio = {
  id?: string
  title?: string | null
  url?: string | null
  creator?: string | null
  creator_url?: string | null
  foreign_landing_url?: string | null
  license?: string | null
  license_version?: string | null
  license_url?: string | null
  provider?: string | null
  source?: string | null
  category?: string | null
  genres?: string[] | null
  filetype?: string | null
  duration?: number | null
  attribution?: string | null
  tags?: Array<{ name?: string | null }> | null
  mature?: boolean | null
  detail_url?: string | null
  thumbnail?: string | null
}

type OpenverseAudioResponse = {
  result_count?: number
  page_count?: number
  page_size?: number
  page?: number
  results?: OpenverseAudio[]
}

function clampInteger(value: number | undefined, fallback: number, min: number, max: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, Math.floor(value)))
}

function addOptionalParam(params: URLSearchParams, key: string, value: string | undefined) {
  const trimmed = value?.trim()
  if (trimmed) params.set(key, trimmed)
}

function durationSeconds(durationMs: number | null | undefined) {
  if (typeof durationMs !== "number" || !Number.isFinite(durationMs)) return null
  return Math.max(0, Math.round(durationMs / 1000))
}

function formatDuration(durationMs: number | null | undefined) {
  const totalSeconds = durationSeconds(durationMs)
  if (totalSeconds === null) return "unknown"

  const minutes = Math.floor(totalSeconds / 60)
  const seconds = String(totalSeconds % 60).padStart(2, "0")
  return `${minutes}:${seconds}`
}

function compactText(value: string | null | undefined, fallback = "Unknown") {
  return value?.trim() || fallback
}

function normalizeResult(result: OpenverseAudio) {
  return {
    id: result.id ?? "",
    title: compactText(result.title, "Untitled audio"),
    creator: compactText(result.creator),
    creator_url: result.creator_url ?? "",
    audio_url: result.url?.trim() ?? "",
    landing_url: result.foreign_landing_url ?? "",
    license: compactText(result.license, "unknown"),
    license_version: result.license_version ?? "",
    license_url: result.license_url ?? "",
    source: compactText(result.source ?? result.provider, "openverse"),
    category: result.category ?? "",
    genres: result.genres ?? [],
    filetype: result.filetype ?? "",
    duration_seconds: durationSeconds(result.duration),
    duration: formatDuration(result.duration),
    attribution: result.attribution ?? "",
    tags: result.tags?.map((tag) => tag.name).filter(Boolean).slice(0, 8) ?? [],
    detail_url: result.detail_url ?? "",
    thumbnail: result.thumbnail ?? "",
  }
}

export default tool({
  description: "Search Openverse audio for soundtrack and ambience tracks suitable for animations, returning playable URLs and attribution.",
  args: {
    query: tool.schema.string().describe("Search terms describing the scene mood, setting, instrument, or ambience"),
    count: tool.schema.number().optional().describe("Number of usable tracks to return. Defaults to 5, maximum 10."),
    page: tool.schema.number().optional().describe("Openverse results page to search. Defaults to 1."),
    category: tool.schema.string().optional().describe("Optional Openverse audio category, for example: music"),
    source: tool.schema.string().optional().describe("Optional Openverse source/provider, for example: freesound or jamendo"),
    license: tool.schema.string().optional().describe("Optional Creative Commons license code, for example: by, by-sa, by-nc"),
    extension: tool.schema.string().optional().describe("Optional audio file extension, for example: mp3, wav, or ogg"),
    minDurationSeconds: tool.schema.number().optional().describe("Optional minimum track duration in seconds"),
    maxDurationSeconds: tool.schema.number().optional().describe("Optional maximum track duration in seconds"),
    includeMature: tool.schema.boolean().optional().describe("Include results Openverse marks as mature. Defaults to false."),
  },
  async execute(args, context) {
    const query = args.query.trim()
    if (!query) throw new Error("query is required")

    const count = clampInteger(args.count, 5, 1, 10)
    const page = clampInteger(args.page, 1, 1, 100)
    const hasDurationFilter = typeof args.minDurationSeconds === "number" || typeof args.maxDurationSeconds === "number"
    const pageSize = hasDurationFilter ? Math.min(20, count * 4) : count
    const minDurationMs = typeof args.minDurationSeconds === "number" ? Math.max(0, args.minDurationSeconds * 1000) : null
    const maxDurationMs = typeof args.maxDurationSeconds === "number" ? Math.max(0, args.maxDurationSeconds * 1000) : null

    const url = new URL(OPENVERSE_AUDIO_URL)
    url.searchParams.set("q", query)
    url.searchParams.set("page_size", String(pageSize))
    url.searchParams.set("page", String(page))
    addOptionalParam(url.searchParams, "category", args.category)
    addOptionalParam(url.searchParams, "source", args.source)
    addOptionalParam(url.searchParams, "license", args.license)
    addOptionalParam(url.searchParams, "extension", args.extension)

    context.metadata({ title: `Openverse audio: ${query}` })

    const response = await fetch(url, {
      signal: context.abort,
      headers: {
        Accept: "application/json",
        "User-Agent": "opencode-story-animation/1.0",
      },
    })

    if (!response.ok) {
      const body = await response.text().catch(() => "")
      throw new Error(`Openverse audio search failed (${response.status}): ${body.slice(0, 500)}`)
    }

    const data = await response.json() as OpenverseAudioResponse
    const results = (data.results ?? [])
      .filter((result) => args.includeMature || result.mature !== true)
      .filter((result) => Boolean(result.url?.trim()))
      .filter((result) => minDurationMs === null || (typeof result.duration === "number" && result.duration >= minDurationMs))
      .filter((result) => maxDurationMs === null || (typeof result.duration === "number" && result.duration <= maxDurationMs))
      .slice(0, count)
      .map(normalizeResult)

    const header = `Openverse audio results for "${query}" (${results.length} usable of ${data.result_count ?? 0} total)`
    const body = results.length > 0
      ? results.map((result, index) => [
        `${index + 1}. ${result.title} by ${result.creator}`,
        `Duration: ${result.duration} | License: ${result.license}${result.license_version ? ` ${result.license_version}` : ""} | Source: ${result.source}${result.filetype ? ` | File: ${result.filetype}` : ""}`,
        `Audio URL: ${result.audio_url}`,
        result.landing_url ? `Landing URL: ${result.landing_url}` : "Landing URL: unavailable",
        result.attribution ? `Attribution: ${result.attribution}` : "Attribution: unavailable",
      ].join("\n")).join("\n\n")
      : "No usable audio URLs matched the query and filters. Try a broader mood or ambience query."

    return {
      output: `${header}\nSearch URL: ${url.href}\n\n${body}`,
      metadata: {
        query,
        search_url: url.href,
        result_count: data.result_count ?? 0,
        returned_count: results.length,
        results,
      },
    }
  },
})

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .common import json_result


def search_soundtracks(
    query: str,
    count: int = 5,
    page: int = 1,
    category: str | None = None,
    source: str | None = None,
    license: str | None = None,
    extension: str | None = None,
    minDurationSeconds: int | None = None,
    maxDurationSeconds: int | None = None,
    includeMature: bool = False,
) -> str:
    """Search Openverse audio for soundtrack and ambience tracks."""
    query = query.strip()
    if not query:
        raise ValueError("query is required")
    count = min(10, max(1, int(count or 5)))
    page = min(100, max(1, int(page or 1)))
    params = {"q": query, "page_size": str(count * 4 if minDurationSeconds or maxDurationSeconds else count), "page": str(page)}
    for key, value in {"category": category, "source": source, "license": license, "extension": extension}.items():
        if value:
            params[key] = value.strip()
    url = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "story-animation/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = []
    for item in data.get("results", []):
        if item.get("mature") and not includeMature:
            continue
        if not (item.get("url") or "").strip():
            continue
        duration_ms = item.get("duration")
        if minDurationSeconds is not None and (not isinstance(duration_ms, (int, float)) or duration_ms < minDurationSeconds * 1000):
            continue
        if maxDurationSeconds is not None and (not isinstance(duration_ms, (int, float)) or duration_ms > maxDurationSeconds * 1000):
            continue
        duration_seconds = round(duration_ms / 1000) if isinstance(duration_ms, (int, float)) else None
        results.append(
            {
                "id": item.get("id", ""),
                "title": item.get("title") or "Untitled audio",
                "creator": item.get("creator") or "Unknown",
                "audio_url": item.get("url") or "",
                "landing_url": item.get("foreign_landing_url") or "",
                "license": item.get("license") or "unknown",
                "license_version": item.get("license_version") or "",
                "license_url": item.get("license_url") or "",
                "source": item.get("source") or item.get("provider") or "openverse",
                "filetype": item.get("filetype") or "",
                "duration_seconds": duration_seconds,
                "attribution": item.get("attribution") or "",
            }
        )
        if len(results) >= count:
            break

    lines = [f'Openverse audio results for "{query}" ({len(results)} usable of {data.get("result_count", 0)} total)', f"Search URL: {url}"]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. {result['title']} by {result['creator']}\n"
            f"License: {result['license']} {result['license_version']} | Source: {result['source']} | File: {result['filetype']}\n"
            f"Audio URL: {result['audio_url']}\nLanding URL: {result['landing_url'] or 'unavailable'}\n"
            f"Attribution: {result['attribution'] or 'unavailable'}"
        )
    if not results:
        lines.append("No usable audio URLs matched the query and filters. Try a broader query.")
    return json_result("\n\n".join(lines), {"query": query, "search_url": url, "results": results})

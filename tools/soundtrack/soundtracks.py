from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..common import json_result


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
    params = {"q": query, "page_size": str(count), "page": str(page)}
    for key, value in {"category": category, "source": source, "license": license, "extension": extension}.items():
        if value:
            params[key] = value.strip()
    url = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "story-animation/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = []
    for item in data["results"]:
        if item.get("mature") and not includeMature:
            continue
        audio_url = item.get("url", "").strip()
        duration_ms = item.get("duration")
        if minDurationSeconds is not None and duration_ms < minDurationSeconds * 1000:
            continue
        if maxDurationSeconds is not None and duration_ms > maxDurationSeconds * 1000:
            continue
        results.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "creator": item.get("creator"),
                "audio_url": audio_url,
                "landing_url": item.get("foreign_landing_url"),
                "license": item.get("license"),
                "license_version": item.get("license_version"),
                "license_url": item.get("license_url"),
                "source": item.get("source"),
                "filetype": item.get("filetype"),
                "duration_seconds": round(duration_ms / 1000) if duration_ms else None,
                "attribution": item.get("attribution"),
            }
        )
        if len(results) >= count:
            break

    lines = [f'Openverse audio results for "{query}" ({len(results)} usable of {data["result_count"]} total)', f"Search URL: {url}"]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. {result['title']} by {result['creator']}\n"
            f"License: {result['license']} {result['license_version']} | Source: {result['source']} | File: {result['filetype']}\n"
            f"Audio URL: {result['audio_url']}\nLanding URL: {result['landing_url']}\n"
            f"Attribution: {result['attribution']}"
        )
    return json_result("\n\n".join(lines), {"query": query, "search_url": url, "results": results})

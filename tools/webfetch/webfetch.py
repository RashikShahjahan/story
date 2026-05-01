from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from ..common import json_result


MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 200_000


class _ReadableHTMLParser(HTMLParser):
    def __init__(self, markdown: bool):
        super().__init__(convert_charrefs=True)
        self.markdown = markdown
        self.parts: list[str] = []
        self.href: str | None = None
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in {"p", "div", "section", "article", "header", "footer", "tr"}:
            self.parts.append("\n\n")
        elif tag in {"br", "li"}:
            self.parts.append("\n")
            if tag == "li" and self.markdown:
                self.parts.append("- ")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "a" and self.markdown:
            self.href = dict(attrs).get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "a" and self.markdown and self.href:
            self.parts.append(f" ({self.href})")
            self.href = None
        elif tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme.lower() == "http":
        parsed = parsed._replace(scheme="https")
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("url must be a fully formed HTTP or HTTPS URL")
    return urllib.parse.urlunparse(parsed)


def _format_content(content: str, content_type: str, output_format: str) -> str:
    if output_format == "html":
        return content
    if "html" not in content_type.lower():
        return content.strip()
    parser = _ReadableHTMLParser(markdown=output_format == "markdown")
    parser.feed(content)
    parser.close()
    return parser.text()


def webfetch(url: str, format: str = "markdown", timeout: int = 30) -> str:
    """Fetch a URL and return its content as markdown, text, or HTML."""
    output_format = format.strip().lower()
    if output_format not in {"markdown", "text", "html"}:
        raise ValueError("format must be one of: markdown, text, html")

    fetch_url = _normalize_url(url)
    timeout_seconds = max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))
    request = urllib.request.Request(
        fetch_url,
        headers={"Accept": "text/html, text/plain, */*", "User-Agent": "story-webfetch/1.0"},
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset()
        final_url = response.geturl()

    content = raw.decode(charset or "utf-8", errors="replace")
    output = _format_content(content, content_type, output_format)
    truncated = len(output) > MAX_OUTPUT_CHARS
    if truncated:
        output = output[:MAX_OUTPUT_CHARS].rstrip() + "\n\n[Output truncated]"

    return json_result(
        output,
        {
            "success": True,
            "url": fetch_url,
            "final_url": final_url,
            "format": output_format,
            "content_type": content_type,
            "bytes": len(raw),
            "truncated": truncated,
        },
    )

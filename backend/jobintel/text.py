"""Clean scraped job descriptions into readable, semantic text."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe"}
_HEADING_TAGS = {
    "h1": "##",
    "h2": "##",
    "h3": "###",
    "h4": "###",
    "h5": "###",
    "h6": "###",
}
_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "blockquote"}

_SECTION_HEADINGS = sorted(
    [
        "about the company",
        "about the team",
        "about the role",
        "about the job",
        "about us",
        "about you",
        "key responsibilities",
        "responsibilities",
        "essential functions",
        "what you'll do",
        "what you will do",
        "what you do",
        "the role",
        "overview",
        "description",
        "requirements",
        "minimum qualifications",
        "preferred qualifications",
        "qualifications",
        "must have",
        "must-have",
        "nice to have",
        "nice-to-have",
        "you will",
        "you have",
        "you are",
        "who you are",
        "what we offer",
        "benefits",
        "perks",
        "compensation",
        "how to apply",
        "equal opportunity",
        "tech stack",
        "technical stack",
        "our values",
        "duties",
    ],
    key=len,
    reverse=True,
)

_HEADING_LINE = re.compile(
    r"^(?:"
    + "|".join(re.escape(item) for item in _SECTION_HEADINGS)
    + r")\s*:?\s*$",
    re.I,
)

_START_HEADING = re.compile(
    r"^("
    + "|".join(re.escape(item) for item in _SECTION_HEADINGS)
    + r")\b\s*:?\s*",
    re.I,
)

_INLINE_SECTION = re.compile(
    r"(?i)(?<=[^\s#])[ \t]+("
    + "|".join(re.escape(item) for item in _SECTION_HEADINGS)
    + r")\b"
)

_BULLET_HEADING = re.compile(
    r"responsibilit|requirement|qualification|duties|you will|what you.?ll|"
    r"must[\s-]have|nice[\s-]to[\s-]have|essential function|you have|you are|"
    r"who you are|what we offer|benefits|perks",
    re.I,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])")

_CHROME_LINE = re.compile(
    r"(?im)^(?:Headquarters|HQ)\s*:\s*.{0,80}$"
    r"|^(?:URL|APPLY HERE|Apply here|Apply now)\s*:\s*https?://\S+$"
    r"|^(?:Tags)\s*:\s*.{0,200}$"
)
_CHROME_INLINE = [
    re.compile(
        r"(?i)\bHeadquarters:\s*.*?"
        r"(?=(?:\sURL:|\sAPPLY HERE:|\sFully Remote|\sAbout |\sOverview |\sDescription\b|$))"
    ),
    re.compile(r"(?i)\bURL:\s*https?://\S+"),
    re.compile(r"(?i)\bAPPLY HERE:\s*\S+"),
    re.compile(r"(?i)\bclick here to apply\b[^\n]*"),
    re.compile(r"(?i)\bshare this job\b[^\n]*"),
]


class _HTMLToMarkdown(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in {"br", "hr"}:
            self.parts.append("\n")
        elif tag in _HEADING_TAGS:
            self.parts.append(f"\n\n{_HEADING_TAGS[tag]} ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag in {"ul", "ol"}:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "tr":
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag in _HEADING_TAGS or tag in _BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("\n")
        elif tag in {"ul", "ol"}:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        text = data.replace("\xa0", " ")
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        if text:
            self.parts.append(text)

    def output(self) -> str:
        return "".join(self.parts)


def html_to_markdown(value: str) -> str:
    parser = _HTMLToMarkdown()
    try:
        parser.feed(value)
        parser.close()
        rendered = parser.output()
        if rendered.strip():
            return rendered
    except Exception:
        pass
    rough = re.sub(r"(?i)</(?:p|div|h[1-6]|li|tr|section|article)>", "\n", value)
    rough = re.sub(r"(?i)<br\s*/?>", "\n", rough)
    rough = re.sub(r"(?i)<li[^>]*>", "\n- ", rough)
    rough = re.sub(r"(?i)<h[1-6][^>]*>", "\n\n## ", rough)
    rough = re.sub(r"<[^>]+>", " ", rough)
    return unescape(rough)


def clean_description(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(value).replace("\xa0", " ").replace("\r\n", "\n")
    if re.search(r"<\s*[a-zA-Z][^>]*>", text):
        text = html_to_markdown(text)
    text = _strip_listing_chrome(text)
    text = re.sub(r"(?m)^\s*[•●▪◦]\s+", "- ", text)
    text = _break_inline_sections(text)
    text = _promote_headings(text)
    text = _structure_sections(text)
    return _normalize_whitespace(text)


def _break_inline_sections(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        heading = match.group(1)
        if not heading[:1].isupper():
            return match.group(0)
        return f"\n\n{heading}"

    return _INLINE_SECTION.sub(repl, text)


def _strip_listing_chrome(text: str) -> str:
    text = _CHROME_LINE.sub("", text)
    for pattern in _CHROME_INLINE:
        text = pattern.sub(" ", text)
    return text


def _promote_headings(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("#"):
            if not line.lstrip("#").strip():
                continue
            lines.append(line)
            continue
        unlabeled = line.rstrip(":").strip()
        start = _START_HEADING.match(line)
        if start and start.group(1)[:1].isupper():
            heading = start.group(1).strip()
            rest = line[start.end() :].strip()
            lines.append(f"## {heading}")
            if rest:
                lines.append(rest)
            continue
        if _HEADING_LINE.match(unlabeled) or (
            line.endswith(":") and 3 <= len(unlabeled) <= 48 and not line.startswith("- ")
        ):
            lines.append(f"## {unlabeled}")
        else:
            lines.append(line)
    return "\n".join(lines)


def _structure_sections(text: str) -> str:
    chunks = re.split(r"(?m)^## ", text)
    if len(chunks) == 1:
        return _paragraphize(chunks[0])
    rebuilt: list[str] = []
    lead = chunks[0].strip()
    if lead:
        rebuilt.append(_paragraphize(lead))
    for chunk in chunks[1:]:
        heading, _, body = chunk.partition("\n")
        heading = heading.strip()
        body = body.strip()
        rebuilt.append(f"## {heading}")
        if _BULLET_HEADING.search(heading):
            rebuilt.append(_as_bullets(body))
        else:
            rebuilt.append(_paragraphize(body))
    return "\n\n".join(part for part in rebuilt if part.strip())


def _as_bullets(body: str) -> str:
    if not body:
        return ""
    if re.search(r"(?m)^(?:- |\* |\d+[.)]\s+)", body):
        return body
    sentences = [item.strip() for item in _SENTENCE_SPLIT.split(body) if item.strip()]
    if len(sentences) >= 3:
        return "\n".join(f"- {item.rstrip('.')}" for item in sentences)
    return _paragraphize(body)


def _paragraphize(body: str) -> str:
    if not body:
        return ""
    if "\n" in body.strip():
        return body.strip()
    if len(body) < 420:
        return body.strip()
    sentences = [item.strip() for item in _SENTENCE_SPLIT.split(body) if item.strip()]
    if len(sentences) < 3:
        return body.strip()
    grouped: list[str] = []
    for index in range(0, len(sentences), 2):
        grouped.append(" ".join(sentences[index : index + 2]))
    return "\n\n".join(grouped)


def _normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in text.splitlines()]
    compact = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return compact.strip()

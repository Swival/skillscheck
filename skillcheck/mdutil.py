"""Markdown text utilities."""

from __future__ import annotations

import re
import unicodedata

FENCED_BLOCK_RE = re.compile(r"^(`{3,}|~{3,})", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#*)?$", re.MULTILINE)
SETEXT_H1_RE = re.compile(r"^(.+)\n=+\s*$", re.MULTILINE)
SETEXT_H2_RE = re.compile(r"^(.+)\n-+\s*$", re.MULTILINE)


def strip_code(text: str) -> str:
    text = _strip_fenced_blocks(text)
    text = _strip_indented_blocks(text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def _strip_fenced_blocks(text: str) -> str:
    lines = text.split("\n")
    result = []
    in_fence = False
    fence_marker = ""

    for line in lines:
        if in_fence:
            stripped = line.strip()
            if stripped == fence_marker:
                in_fence = False
            continue

        m = FENCED_BLOCK_RE.match(line)
        if m:
            in_fence = True
            fence_marker = m.group(1)
            continue

        result.append(line)

    return "\n".join(result)


def _strip_indented_blocks(text: str) -> str:
    lines = text.split("\n")
    result = []
    prev_blank = True

    for line in lines:
        is_indented = line.startswith("    ") or line.startswith("\t")
        is_blank = line.strip() == ""

        if is_indented and prev_blank and not is_blank:
            prev_blank = False
            continue
        if is_indented and not prev_blank and len(result) > 0:
            last_kept = result[-1] if result else ""
            if last_kept.strip() == "" or (
                last_kept.startswith("    ") or last_kept.startswith("\t")
            ):
                continue

        result.append(line)
        prev_blank = is_blank

    return "\n".join(result)


def slugify_heading(text: str) -> str:
    """Convert a markdown heading to a GitHub-style anchor slug."""
    text = INLINE_CODE_RE.sub("", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    return text


def extract_headings(text: str) -> set[str]:
    """Extract all heading slugs from markdown text (outside code blocks).

    Generates GitHub-style suffixed slugs for duplicate headings
    (e.g. ``intro``, ``intro-1``, ``intro-2``).
    """
    clean = strip_code(text)
    slugs: set[str] = set()
    counts: dict[str, int] = {}

    positioned: list[tuple[int, str]] = []
    for match in ATX_HEADING_RE.finditer(clean):
        positioned.append((match.start(), match.group(2)))
    for regex in (SETEXT_H1_RE, SETEXT_H2_RE):
        for match in regex.finditer(clean):
            text_line = match.group(1).strip()
            if not text_line.startswith("#"):
                positioned.append((match.start(), text_line))
    positioned.sort(key=lambda x: x[0])
    raw_headings = [h for _, h in positioned]

    for heading in raw_headings:
        base = slugify_heading(heading)
        count = counts.get(base, 0)
        if count == 0:
            slugs.add(base)
        else:
            slugs.add(f"{base}-{count}")
        counts[base] = count + 1

    return slugs


def extract_fragment_links(text: str) -> list[tuple[str, str]]:
    """Extract links with fragments. Returns (file_path_or_empty, fragment) tuples."""
    clean = strip_code(text)
    results: list[tuple[str, str]] = []
    for match in MD_LINK_RE.finditer(clean):
        if match.group(0).startswith("!"):
            continue
        target = match.group(2).strip()
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if "#" not in target:
            continue
        path_part, fragment = target.split("#", 1)
        if "?" in path_part:
            path_part = path_part.split("?")[0]
        if fragment:
            results.append((path_part, fragment))
    return results


def extract_local_link_targets(text: str) -> list[str]:
    clean = strip_code(text)
    targets = []
    for match in MD_LINK_RE.finditer(clean):
        target = match.group(2).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if "?" in target:
            target = target.split("?")[0]
        if "#" in target:
            target = target.split("#")[0]
        if target:
            targets.append(target)
    return targets

"""Markdown text utilities."""

from __future__ import annotations

import re
from typing import NamedTuple

FENCED_BLOCK_RE = re.compile(r"^(`{3,}|~{3,})", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#*)?$", re.MULTILINE)
SETEXT_H1_RE = re.compile(r"^(.+)\n=+\s*$", re.MULTILINE)
SETEXT_H2_RE = re.compile(r"^(.+)\n-+\s*$", re.MULTILINE)

BLOCKQUOTE_PREFIX_RE = re.compile(r"^(?: {0,3}> ?)+")
HEADING_LINE_RE = re.compile(r"^ {0,3}#{1,6}\s")
THEMATIC_BREAK_RE = re.compile(r"^ {0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$")
LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
STRONG_RE = re.compile(r"(?<!\\)(\*\*|__)(?=\S)(.+?)(?<=\S)(?<!\\)\1")
WORD_CHAR_RE = re.compile(r"\w")

MAX_LABEL_WORDS = 4


def strip_code(text: str) -> str:
    text = strip_code_blocks(text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def strip_code_blocks(text: str) -> str:
    """Remove fenced and indented code blocks but leave inline code intact.

    Heading slugs keep the visible text of inline code (an inline span like
    xqd_cache.go contributes "xqd_cachego"), so heading extraction strips only
    block-level code, never inline spans.
    """
    text = _strip_fenced_blocks(text)
    text = _strip_indented_blocks(text)
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
        is_indented = line.startswith(("    ", "\t"))
        is_blank = line.strip() == ""

        if is_indented and prev_blank and not is_blank:
            prev_blank = False
            continue
        if is_indented and not prev_blank and len(result) > 0:
            last_kept = result[-1] if result else ""
            if last_kept.strip() == "" or last_kept.startswith(("    ", "\t")):
                continue

        result.append(line)
        prev_blank = is_blank

    return "\n".join(result)


def slugify_heading(text: str) -> str:
    """Convert a markdown heading to a GitHub-style anchor slug.

    Mirrors markdownlint's MD051 (and GitHub's) algorithm: inline code and link
    syntax are reduced to their visible text, the result is lowercased, every
    character outside word characters, spaces, and hyphens is dropped, and each
    remaining space becomes a single hyphen. Whitespace runs are NOT collapsed,
    so two spaces left behind by a removed em dash produce two hyphens.
    """
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = text.lower()
    text = re.sub(r"[^\w\- ]", "", text)
    text = text.replace(" ", "-")
    return text


def extract_headings(text: str) -> set[str]:
    """Extract all heading slugs from markdown text (outside code blocks).

    Generates GitHub-style suffixed slugs for duplicate headings
    (e.g. ``intro``, ``intro-1``, ``intro-2``).
    """
    clean = strip_code_blocks(text)
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


def find_unclosed_fence(text: str) -> int | None:
    """Find an unclosed code fence. Returns the 1-based line number or None."""
    lines = text.split("\n")
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_line = 0

    for i, line in enumerate(lines):
        stripped = _strip_fence_indent(line)

        if not in_fence:
            char, n = _fence_prefix(stripped)
            if n >= 3:
                in_fence = True
                fence_char = char
                fence_len = n
                fence_line = i + 1
        else:
            char, n = _fence_prefix(stripped)
            # Closing fence: rest must be only whitespace
            if n >= fence_len and char == fence_char and stripped[n:].strip() == "":
                in_fence = False

    return fence_line if in_fence else None


def _strip_fence_indent(line: str) -> str:
    """Drop the up to three leading spaces a fence may carry (CommonMark)."""
    for _ in range(3):
        if line.startswith(" "):
            line = line[1:]
        else:
            break
    return line


def _fence_prefix(line: str) -> tuple[str, int]:
    """Return (fence_char, count) if line starts with 3+ backticks or tildes."""
    if not line:
        return "", 0
    ch = line[0]
    if ch not in ("`", "~"):
        return "", 0
    n = 0
    while n < len(line) and line[n] == ch:
        n += 1
    if n < 3:
        return "", 0
    return ch, n


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


class StrongLabel(NamedTuple):
    count: int
    first_line: int


def collect_strong_labels(text: str) -> dict[str, StrongLabel]:
    """Count the bold field labels of a markdown document.

    A field label is a short `**Name:**` or `__Name:__` span that opens a
    paragraph or a list item. Labels that come back again and again are the
    signature of a record schema.

    Code, headings, and thematic breaks never give a label. Table cells do
    not either, because a row starts with a pipe and not with the span.
    Blockquote markers go away before the classification, so a quoted list
    behaves like a plain one. The reported line numbers stay physical.
    """
    labels: dict[str, StrongLabel] = {}
    lines = text.split("\n")
    in_fence = False
    fence_char = ""
    fence_len = 0
    prev_blank = True

    for number, source_line in enumerate(lines, 1):
        line = BLOCKQUOTE_PREFIX_RE.sub("", source_line)
        unindented = _strip_fence_indent(line)
        char, run = _fence_prefix(unindented)

        if in_fence:
            if (
                char == fence_char
                and run >= fence_len
                and unindented[run:].strip() == ""
            ):
                in_fence = False
            continue
        if run >= 3:
            in_fence = True
            fence_char = char
            fence_len = run
            prev_blank = False
            continue
        if not line.strip():
            prev_blank = True
            continue
        if prev_blank and line.startswith(("    ", "\t")):
            continue
        if HEADING_LINE_RE.match(line) or THEMATIC_BREAK_RE.match(line):
            prev_blank = False
            continue
        # Under a list item the same dashes are a break, not an underline.
        if not LIST_MARKER_RE.match(line) and _is_setext_underline(
            lines[number] if number < len(lines) else ""
        ):
            prev_blank = False
            continue

        label = _leading_strong_label(line, prev_blank)
        if label is not None:
            known = labels.get(label)
            labels[label] = StrongLabel(
                known.count + 1 if known else 1,
                known.first_line if known else number,
            )
        prev_blank = False

    return labels


def _is_setext_underline(source_line: str) -> bool:
    """Tell if a line turns the paragraph above it into a heading."""
    return bool(SETEXT_UNDERLINE_RE.match(BLOCKQUOTE_PREFIX_RE.sub("", source_line)))


def _leading_strong_label(line: str, paragraph_start: bool) -> str | None:
    """Return the normalized field label that opens a line, if there is one."""
    marker = LIST_MARKER_RE.match(line)
    if marker is None and not paragraph_start:
        return None

    body = (line[marker.end() :] if marker else line).lstrip()
    match = STRONG_RE.match(body)
    if match is None:
        return None
    # Underscore emphasis, unlike `**`, does not survive inside a word.
    if match.group(1) == "__" and WORD_CHAR_RE.match(body[match.end() :]):
        return None

    content = match.group(2)
    if not content.endswith(":") or len(content.split()) > MAX_LABEL_WORDS:
        return None
    return re.sub(r"\s+", " ", content.rstrip(":").strip()).casefold() or None

"""Quality checks (2a-2e)."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from ..models import Diagnostic, Level, SPEC_URL, SkillInfo
from ..mdutil import (
    collect_strong_labels,
    extract_fragment_links,
    extract_headings,
    extract_local_link_targets,
    find_unclosed_fence,
)

SECRET_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    ".pem",
    ".key",
    "credentials.json",
    ".pfx",
    ".p12",
}
SECRET_FILENAME_PATTERNS = [re.compile(r"_secret", re.IGNORECASE)]
SECRET_CONTENT_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"gho_[A-Za-z0-9]{36}"),
    re.compile(r"ghs_[A-Za-z0-9]{36}"),
    re.compile(r"-----BEGIN.*PRIVATE KEY-----"),
    re.compile(r"glpat-[A-Za-z0-9\-_]{20,}"),
    re.compile(r"xoxb-[0-9]+-[0-9A-Za-z]+"),
    re.compile(r"xoxp-[0-9]+-[0-9A-Za-z]+"),
    re.compile(r"xapp-[0-9]+-[0-9A-Za-z]+"),
    re.compile(r"LS0tLS1CRUdJTi[A-Za-z0-9+/=]+"),
]

BINARY_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".o",
    ".a",
    ".pyc",
    ".class",
    ".wasm",
}

USE_WHEN_HINTS = re.compile(
    r"\b(use when|use for|use if|use this|when you need|invoke when|trigger when|designed for|required for|needed for)\b",
    re.IGNORECASE,
)

QUOTED_STRING_RE = re.compile(r'"[^"]*"')

# Files commonly found in repos but not intended for agent consumption.
# Agents may load these into their context window, wasting space.
EXTRANEOUS_FILES = {
    "readme.md",
    "readme",
    "readme.txt",
    "readme.rst",
    "changelog.md",
    "changelog",
    "changelog.txt",
    "license",
    "license.md",
    "license.txt",
    "contributing.md",
    "code_of_conduct.md",
    "makefile",
    "agents.md",
}

USER_CENTRIC_TRIGGER = re.compile(
    r"\b(whenever the user|when the user|if the user|user asks|user mentions|user requests|user wants)\b",
    re.IGNORECASE,
)

MAX_FILE_SIZE = 100 * 1024  # 100KB


def check_skill(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if skill.parse_error:
        return diags

    diags.extend(_check_description_quality(skill))
    diags.extend(_check_file_hygiene(skill))
    diags.extend(_check_links(skill))
    diags.extend(_check_unclosed_fences(skill))
    diags.extend(_check_reference_links(skill))
    diags.extend(_check_reference_fragment_links(skill))
    diags.extend(_check_excessive_strong(skill))
    diags.extend(_check_orphan_files(skill))
    return diags


def _check_description_quality(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    fm = skill.frontmatter or {}
    desc = fm.get("description")
    if desc is None:
        return diags

    desc = str(desc)
    if len(desc) < 20:
        diags.append(
            Diagnostic(
                Level.WARNING,
                "2a.description.short",
                f"description is only {len(desc)} chars — probably insufficient for agent matching",
                path=skill.skill_md_path,
                source_url=SPEC_URL,
            )
        )

    if not USE_WHEN_HINTS.search(desc):
        diags.append(
            Diagnostic(
                Level.WARNING,
                "2a.description.no-when",
                "description doesn't indicate when to use the skill (spec recommends describing both what and when)",
                path=skill.skill_md_path,
                source_url=SPEC_URL,
            )
        )

    if USER_CENTRIC_TRIGGER.search(desc):
        diags.append(
            Diagnostic(
                Level.WARNING,
                "2a.description.user-centric",
                "description uses user-centric trigger (e.g. 'whenever the user mentions') — "
                "prefer agent-directed phrasing (e.g. 'Use when working with…')",
                path=skill.skill_md_path,
            )
        )

    diags.extend(_check_keyword_stuffing(desc, skill.skill_md_path))

    return diags


def _check_file_hygiene(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)

    diags.extend(_check_extraneous_files(skill_dir))

    for dirpath, _dirnames, filenames in os.walk(skill_dir):
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel = fpath.relative_to(skill_dir)

            suffix = fpath.suffix.lower()
            stem = fpath.name.lower()

            if stem in SECRET_FILENAMES or suffix in SECRET_FILENAMES:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2b.secrets.filename",
                        f"file '{rel}' matches a known secret filename pattern",
                        path=str(fpath),
                    )
                )

            for pat in SECRET_FILENAME_PATTERNS:
                if pat.search(stem):
                    diags.append(
                        Diagnostic(
                            Level.WARNING,
                            "2b.secrets.filename",
                            f"file '{rel}' matches secret filename pattern",
                            path=str(fpath),
                        )
                    )
                    break

            if suffix in BINARY_EXTENSIONS:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2b.binary",
                        f"binary file '{rel}' found in skill directory",
                        path=str(fpath),
                    )
                )

            try:
                size = fpath.stat().st_size
                if size > MAX_FILE_SIZE:
                    diags.append(
                        Diagnostic(
                            Level.WARNING,
                            "2b.large-file",
                            f"file '{rel}' is {size // 1024}KB (> 100KB)",
                            path=str(fpath),
                        )
                    )
            except OSError:
                pass

            if suffix in (".md", ".txt", ".yaml", ".yml", ".json"):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    for pat in SECRET_CONTENT_PATTERNS:
                        if pat.search(content):
                            diags.append(
                                Diagnostic(
                                    Level.WARNING,
                                    "2b.secrets.content",
                                    f"file '{rel}' may contain a secret token",
                                    path=str(fpath),
                                )
                            )
                            break
                except OSError:
                    pass

    return diags


def _check_extraneous_files(skill_dir: Path) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        entries = list(os.scandir(skill_dir))
    except OSError:
        return diags

    for entry in sorted(entries, key=lambda e: e.name):
        name = entry.name
        if name == "SKILL.md" or name.startswith("."):
            continue
        if entry.is_dir():
            continue
        lower = name.lower()
        if lower in EXTRANEOUS_FILES:
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "2b.extraneous-file",
                    f"'{name}' is not needed in a skill — agents may load it "
                    "into their context window, wasting space that could be "
                    "used for actual instructions",
                    path=str(skill_dir / name),
                )
            )
    return diags


def _check_keyword_stuffing(desc: str, path: str) -> list[Diagnostic]:
    # Heuristic 1: many quoted strings with little surrounding prose.
    # Descriptions with substantial prose alongside quoted trigger lists are
    # fine — the spec encourages keywords. This catches descriptions that are
    # *only* keyword lists.
    quotes = QUOTED_STRING_RE.findall(desc)
    if len(quotes) >= 5:
        prose = QUOTED_STRING_RE.sub("", desc)
        prose_words = [w for w in prose.split() if any(c.isalnum() for c in w)]
        if len(prose_words) < len(quotes):
            return [
                Diagnostic(
                    Level.INFO,
                    "2a.description.keyword-stuffing",
                    f"description contains {len(quotes)} quoted strings with "
                    "little surrounding prose — consider also explaining what "
                    "the skill does and when to activate it",
                    path=path,
                    source_url=SPEC_URL,
                )
            ]

    # Heuristic 2: long comma-separated list of short segments in a single
    # sentence, suggesting a bare keyword dump.
    desc_no_quotes = QUOTED_STRING_RE.sub("", desc)
    for sentence in _split_sentences(desc_no_quotes):
        segments = [s.strip() for s in sentence.split(",") if s.strip()]
        if len(segments) >= 8:
            short = sum(1 for s in segments if len(s.split()) <= 3)
            if short * 100 // len(segments) >= 60:
                return [
                    Diagnostic(
                        Level.INFO,
                        "2a.description.keyword-stuffing",
                        f"description has {len(segments)} comma-separated "
                        "segments, most very short — consider also explaining "
                        "what the skill does and when to activate it",
                        path=path,
                        source_url=SPEC_URL,
                    )
                ]

    return []


_PERIOD_PLACEHOLDER = "\u222f"  # ∯ — extremely unlikely in skill descriptions
_ABBREV_RE = re.compile(r"(?i)\b(e\.g|i\.e|vs|al|approx|etc)\.\s")
_DIGIT_PERIOD_RE = re.compile(r"(\d)\.(\d)")
_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?]\s+([A-Z])")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using a lightweight heuristic."""
    if not text:
        return []
    # Protect abbreviations and decimal numbers from being treated as boundaries
    protected = _ABBREV_RE.sub(
        lambda m: m.group().replace(".", _PERIOD_PLACEHOLDER),
        text,
    )
    protected = _DIGIT_PERIOD_RE.sub(
        lambda m: m.group(1) + _PERIOD_PLACEHOLDER + m.group(2),
        protected,
    )

    parts: list[str] = []
    # Split on sentence-ending punctuation followed by whitespace + uppercase
    indices = list(_SENTENCE_BOUNDARY_RE.finditer(protected))
    start = 0
    for m in indices:
        cap_start = m.start(1)
        s = protected[start:cap_start].strip().replace(_PERIOD_PLACEHOLDER, ".")
        if s:
            parts.append(s)
        start = cap_start
    remainder = protected[start:].strip().replace(_PERIOD_PLACEHOLDER, ".")
    if remainder:
        parts.append(remainder)
    return parts


def _check_links(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not skill.body:
        return diags

    skill_dir = Path(skill.dir_path)
    targets = extract_local_link_targets(skill.body)

    for target in targets:
        resolved = skill_dir / target
        if not resolved.exists():
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "2c.broken-link",
                    f"link target '{target}' does not exist",
                    path=skill.skill_md_path,
                )
            )

    diags.extend(_check_fragment_links(skill, skill_dir))
    return diags


def _check_fragment_links(skill: SkillInfo, skill_dir: Path) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    fragment_links = extract_fragment_links(skill.body)
    self_headings = extract_headings(skill.body)
    file_headings_cache: dict[Path, set[str]] = {}

    for path_part, fragment in fragment_links:
        if not path_part:
            # Fragment-only link (e.g. #heading) — resolve against SKILL.md itself
            if fragment not in self_headings:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2c.broken-link.fragment",
                        f"fragment '#{fragment}' does not match any heading in SKILL.md",
                        path=skill.skill_md_path,
                    )
                )
        else:
            # File + fragment link (e.g. references/guide.md#section)
            target_path = skill_dir / path_part
            if not target_path.exists():
                continue  # Already reported by the file-level broken link check
            if target_path not in file_headings_cache:
                try:
                    content = target_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                file_headings_cache[target_path] = extract_headings(content)
            headings = file_headings_cache[target_path]
            if fragment not in headings:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2c.broken-link.fragment",
                        f"fragment '#{fragment}' does not match any heading in '{path_part}'",
                        path=skill.skill_md_path,
                    )
                )

    return diags


_DISCLOSURE_SUBDIRS = ("references", "scripts", "assets")

_NON_LOCAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "ftp://")


def _iter_disclosure_md_files(skill_dir: Path) -> Iterator[Path]:
    """Yield every .md file under references/, scripts/, assets/ recursively.

    Uses a case-insensitive suffix match so `.MD` is picked up on
    case-sensitive filesystems.
    """
    for name in _DISCLOSURE_SUBDIRS:
        d = skill_dir / name
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() == ".md":
                yield p


def _resolve_skill_local_link(
    base_dir: Path,
    target: str,
    skill_root: Path,
) -> tuple[Path | None, bool]:
    """Resolve a markdown link target to a normalized filesystem path.

    Returns (resolved_path, escapes).

    - resolved_path is None when the target is not a local file link:
      http/https/mailto/tel/ftp schemes, scheme-relative `//host/...`,
      or an empty string.
    - escapes is True when the target points outside skill_root. Absolute
      filesystem paths (`/etc/...`) always count as escaping. After
      resolution, paths that lie outside skill_root — including through
      symlinks — also count as escaping. base_dir and skill_root must
      both be already-resolved Paths.
    """
    if not target:
        return None, False
    lowered = target.lower()
    if lowered.startswith(_NON_LOCAL_SCHEMES):
        return None, False
    if target.startswith("//"):
        return None, False
    if target.startswith("/"):
        return None, True

    resolved = (base_dir / target).resolve(strict=False)
    try:
        resolved.relative_to(skill_root)
    except ValueError:
        return resolved, True
    return resolved, False


def _check_unclosed_fences(skill: SkillInfo) -> list[Diagnostic]:
    """Check for unclosed code fences in SKILL.md and disclosure markdown files."""
    diags: list[Diagnostic] = []
    path = skill.skill_md_path

    fence_line = find_unclosed_fence(skill.body)
    if fence_line is not None:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "2d.unclosed-fence",
                f"SKILL.md has an unclosed code fence starting at line "
                f"{skill.body_line_offset + fence_line} — agents may "
                f"misinterpret everything after it as code",
                path=path,
                line=skill.body_line_offset + fence_line,
            )
        )

    skill_dir = Path(skill.dir_path)
    for entry in _iter_disclosure_md_files(skill_dir):
        try:
            content = entry.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        fence_line = find_unclosed_fence(content)
        if fence_line is not None:
            rel = entry.relative_to(skill_dir)
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "2d.unclosed-fence",
                    f"'{rel}' has an unclosed code fence starting at "
                    f"line {fence_line} — agents may misinterpret "
                    f"everything after it as code",
                    path=str(entry),
                    line=fence_line,
                )
            )

    return diags


def _check_reference_links(skill: SkillInfo) -> list[Diagnostic]:
    """Validate local markdown links inside disclosure files.

    Mirrors `_check_links` but operates per-file: link targets in
    `references/foo.md` resolve relative to that file's directory, not
    the skill root.
    """
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)
    skill_root = skill_dir.resolve()

    for ref_file in _iter_disclosure_md_files(skill_dir):
        try:
            content = ref_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        base_dir = ref_file.parent.resolve()
        rel_ref = ref_file.relative_to(skill_dir)

        for target in extract_local_link_targets(content):
            resolved, escapes = _resolve_skill_local_link(base_dir, target, skill_root)
            if escapes:
                diags.append(
                    Diagnostic(
                        Level.INFO,
                        "2c.escapes-skill",
                        f"'{rel_ref}': link target '{target}' resolves "
                        "outside the skill directory",
                        path=str(ref_file),
                    )
                )
                continue
            if resolved is None:
                continue
            if not resolved.exists():
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2c.broken-link",
                        f"'{rel_ref}': link target '{target}' does not exist",
                        path=str(ref_file),
                    )
                )

    return diags


def _check_reference_fragment_links(skill: SkillInfo) -> list[Diagnostic]:
    """Validate fragment links inside disclosure files.

    Self-fragments resolve against the reference file's own headings.
    File+fragment links resolve relative to the reference file's
    directory. Targets that escape the skill or do not exist are
    silently skipped — `_check_reference_links` already reported them.
    """
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)
    skill_root = skill_dir.resolve()
    headings_cache: dict[Path, set[str]] = {}

    for ref_file in _iter_disclosure_md_files(skill_dir):
        try:
            content = ref_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        base_dir = ref_file.parent.resolve()
        rel_ref = ref_file.relative_to(skill_dir)
        self_headings: set[str] | None = None

        for path_part, fragment in extract_fragment_links(content):
            if not path_part:
                if self_headings is None:
                    self_headings = extract_headings(content)
                if fragment not in self_headings:
                    diags.append(
                        Diagnostic(
                            Level.WARNING,
                            "2c.broken-link.fragment",
                            f"'{rel_ref}': fragment '#{fragment}' does not "
                            "match any heading in this file",
                            path=str(ref_file),
                        )
                    )
                continue

            resolved, escapes = _resolve_skill_local_link(
                base_dir, path_part, skill_root
            )
            if escapes or resolved is None:
                continue
            if not resolved.is_file():
                continue
            if resolved not in headings_cache:
                try:
                    target_content = resolved.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                except OSError:
                    continue
                headings_cache[resolved] = extract_headings(target_content)
            if fragment not in headings_cache[resolved]:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "2c.broken-link.fragment",
                        f"'{rel_ref}': fragment '#{fragment}' does not "
                        f"match any heading in '{path_part}'",
                        path=str(ref_file),
                    )
                )

    return diags


_MIN_LABEL_REPEATS = 2
_MIN_DISTINCT_LABELS = 3
_MIN_LABEL_TOTAL = 8
_SAMPLE_LABELS = 3


class _StrongSchema(NamedTuple):
    distinct: int
    total: int
    line: int
    sample: str


def _repeated_strong_schema(text: str) -> _StrongSchema | None:
    """Describe the repeated bold field schema of a file, if it has one."""
    repeated = {
        name: label
        for name, label in collect_strong_labels(text).items()
        if label.count >= _MIN_LABEL_REPEATS
    }
    total = sum(label.count for label in repeated.values())
    if len(repeated) < _MIN_DISTINCT_LABELS or total < _MIN_LABEL_TOTAL:
        return None

    # Most repeated first, then in the order the schema introduces its fields.
    ordered = sorted(repeated.items(), key=lambda kv: (-kv[1].count, kv[1].first_line))
    sample = ", ".join(
        f"{name} ({label.count})" for name, label in ordered[:_SAMPLE_LABELS]
    )
    line = min(label.first_line for label in repeated.values())
    return _StrongSchema(len(repeated), total, line, sample)


def _strong_schema_message(subject: str, schema: _StrongSchema) -> str:
    return (
        f"{subject} repeats {schema.distinct} bold field labels "
        f"{schema.total} times ({schema.sample}) — pervasive emphasis "
        "dilutes which instructions stand out"
    )


def _check_excessive_strong(skill: SkillInfo) -> list[Diagnostic]:
    """Check for markdown files that bold the same field labels over and over."""
    diags: list[Diagnostic] = []

    schema = _repeated_strong_schema(skill.body)
    if schema is not None:
        diags.append(
            Diagnostic(
                Level.INFO,
                "2e.excessive-strong",
                _strong_schema_message("SKILL.md", schema),
                path=skill.skill_md_path,
                line=skill.body_line_offset + schema.line,
            )
        )

    skill_dir = Path(skill.dir_path)
    for entry in _iter_disclosure_md_files(skill_dir):
        try:
            content = entry.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        schema = _repeated_strong_schema(content)
        if schema is None:
            continue
        rel = entry.relative_to(skill_dir)
        diags.append(
            Diagnostic(
                Level.INFO,
                "2e.excessive-strong",
                _strong_schema_message(f"'{rel}'", schema),
                path=str(entry),
                line=schema.line,
            )
        )

    return diags


_RECOGNIZED_DIRS = {"scripts", "references", "assets"}


def _check_orphan_files(skill: SkillInfo) -> list[Diagnostic]:
    """Check for files in scripts/references/assets not referenced from SKILL.md."""
    diags: list[Diagnostic] = []
    if not skill.body:
        return diags

    skill_dir = Path(skill.dir_path)
    body = skill.body

    for subdir_name in sorted(_RECOGNIZED_DIRS):
        subdir = skill_dir / subdir_name
        if not subdir.is_dir():
            continue
        for fpath in sorted(subdir.rglob("*")):
            if not fpath.is_file():
                continue
            # Skip __init__.py — these are package markers, not standalone files
            if fpath.name == "__init__.py":
                continue
            rel = str(fpath.relative_to(skill_dir))
            # Check if the file is referenced by its relative path or just
            # its filename anywhere in the body (simple string containment).
            if rel not in body and fpath.name not in body:
                diags.append(
                    Diagnostic(
                        Level.INFO,
                        "2b.orphan",
                        f"'{rel}' is not referenced from SKILL.md — agents "
                        "may not discover this file",
                        path=str(fpath),
                    )
                )

    return diags

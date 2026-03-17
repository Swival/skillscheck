"""Quality checks (2a-2c)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..models import Diagnostic, Level, SPEC_URL, SkillInfo
from ..mdutil import (
    extract_fragment_links,
    extract_headings,
    extract_local_link_targets,
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
    r"\b(use when|use for|use if|use this|when you need|invoke when|trigger when|designed for)\b",
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

    return diags


def _check_file_hygiene(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)

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

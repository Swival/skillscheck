from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import SkillInfo


def parse_skill(skill_dir: Path) -> SkillInfo:
    dir_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    info = SkillInfo(
        dir_name=dir_name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
    )

    if not skill_md.exists():
        info.parse_error = "SKILL.md not found"
        return info

    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body, body_line_offset, error = _split_frontmatter(text)

    if error:
        info.parse_error = error
        return info

    info.frontmatter = frontmatter
    info.body = body
    info.body_line_offset = body_line_offset
    return info


def _split_frontmatter(
    text: str,
) -> tuple[dict | None, str, int, str | None]:
    """Split SKILL.md into frontmatter dict and body string.

    Returns (frontmatter, body, body_line_offset, error).
    """
    lines = text.split("\n")

    if not lines or lines[0].strip() != "---":
        return None, text, 0, "missing opening frontmatter delimiter (---)"

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, text, 0, "missing closing frontmatter delimiter (---)"

    fm_text = "\n".join(lines[1:end_idx])
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        return None, text, 0, f"invalid YAML in frontmatter: {e}"

    if fm is None:
        fm = {}
    if not isinstance(fm, dict):
        return None, text, 0, "frontmatter must be a YAML mapping"

    body_start = end_idx + 1
    body = "\n".join(lines[body_start:])
    return fm, body, body_start, None


def discover_skills(root: Path) -> list[Path]:
    """Walk root looking for SKILL.md files. Also picks up children of
    any skills/ directory even if SKILL.md is missing, so we can report
    the absence."""
    skill_dirs: list[Path] = []
    seen: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root):
        p = Path(dirpath)
        if "SKILL.md" in filenames:
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                skill_dirs.append(p)

        if p.name == "skills":
            for d in dirnames:
                child = p / d
                key = str(child.resolve())
                if key not in seen and child.is_dir():
                    seen.add(key)
                    skill_dirs.append(child)

    skill_dirs.sort(key=lambda p: p.name)
    return skill_dirs

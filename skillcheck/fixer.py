"""Auto-fix for issues that have safe, mechanical fixes."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .checks.spec import CONSECUTIVE_HYPHEN_RE, NAME_RE
from .models import Diagnostic, SkillDiagnostics, SkillInfo

NAME_LINE_RE = re.compile(r"^name\s*:")
CONSECUTIVE_HYPHENS_SUB = re.compile(r"-{2,}")


def apply_fixes(
    skills: list[SkillInfo],
    result_skills: dict[str, SkillDiagnostics],
) -> list[str]:
    """Apply auto-fixes based on diagnostics. Returns list of fix descriptions.

    Fixes are applied in order: name format first, then dir-match
    (since fixing the name may create or resolve dir-match issues).
    """
    applied: list[str] = []
    for skill, d in _fixable_diagnostics(skills, result_skills):
        fix = _try_fix(skill, d)
        if fix:
            applied.append(fix)
    return applied


def has_fixable(
    skills: list[SkillInfo],
    result_skills: dict[str, SkillDiagnostics],
) -> bool:
    """Check whether any fixable diagnostics remain, without applying them."""
    return any(True for _ in _fixable_diagnostics(skills, result_skills))


def _fixable_diagnostics(
    skills: list[SkillInfo],
    result_skills: dict[str, SkillDiagnostics],
) -> Iterator[tuple[SkillInfo, Diagnostic]]:
    for skill in skills:
        if skill.frontmatter is None:
            continue
        sd = result_skills.get(skill.dir_name)
        if sd is None:
            continue
        for d in sd.spec:
            if d.fixable:
                yield skill, d


def _try_fix(skill: SkillInfo, diag: Diagnostic) -> str | None:
    if diag.check == "1b.name.format":
        return _fix_name_lowercase(skill)
    if diag.check == "1b.name.consecutive-hyphens":
        return _fix_name_consecutive_hyphens(skill)
    if diag.check == "1b.name.dir-match":
        return _fix_dir_match(skill)
    return None


def _fix_name_lowercase(skill: SkillInfo) -> str | None:
    fm = skill.frontmatter or {}
    name = fm.get("name")
    if name is None or name == name.lower():
        return None

    new_name = name.lower()
    if not _update_frontmatter_name(Path(skill.skill_md_path), new_name):
        return None

    old_name = name
    skill.frontmatter["name"] = new_name
    return f"lowercased name '{old_name}' to '{new_name}' in {skill.skill_md_path}"


def _fix_name_consecutive_hyphens(skill: SkillInfo) -> str | None:
    fm = skill.frontmatter or {}
    name = fm.get("name")
    if name is None or not CONSECUTIVE_HYPHEN_RE.search(str(name)):
        return None

    new_name = CONSECUTIVE_HYPHENS_SUB.sub("-", str(name))
    if not _update_frontmatter_name(Path(skill.skill_md_path), new_name):
        return None

    old_name = name
    skill.frontmatter["name"] = new_name
    return f"fixed consecutive hyphens in name '{old_name}' to '{new_name}' in {skill.skill_md_path}"


def _fix_dir_match(skill: SkillInfo) -> str | None:
    fm = skill.frontmatter or {}
    name = fm.get("name")
    if name is None:
        return None

    name = str(name)
    if name == skill.dir_name:
        return None

    if not NAME_RE.match(name) or CONSECUTIVE_HYPHEN_RE.search(name):
        return None

    old_dir = Path(skill.dir_path)
    new_dir = old_dir.parent / name
    if new_dir.exists():
        return None
    try:
        old_dir.rename(new_dir)
    except OSError:
        return None

    old_dir_name = skill.dir_name
    skill.dir_name = name
    skill.dir_path = str(new_dir)
    skill.skill_md_path = str(new_dir / "SKILL.md")
    return f"renamed directory '{old_dir_name}' to '{name}'"


def _update_frontmatter_name(skill_md: Path, new_name: str) -> bool:
    """Replace the name field value in SKILL.md frontmatter.

    Does a line-level replacement to preserve all other formatting.
    Returns True if the file was updated.
    """
    text = skill_md.read_text(encoding="utf-8")
    lines = text.split("\n")

    if not lines or lines[0].strip() != "---":
        return False

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        if NAME_LINE_RE.match(lines[i]):
            lines[i] = f"name: {new_name}"
            skill_md.write_text("\n".join(lines), encoding="utf-8")
            return True

    return False

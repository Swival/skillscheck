"""Swival agent adapter (3i).

Swival discovers skills from skills/ (project-level) and additional directories
specified via --skills-dir or swival.toml. Swival enforces its own limits on
description length and body size for all discovered skills. Detection is based
on swival.toml or .swival/.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo

SWIVAL_SOURCE_URL = "https://github.com/swival/swival"


class SwivalAdapter:
    name = "swival"
    source_url = SWIVAL_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / "swival.toml").is_file() or (repo_root / ".swival").is_dir()

    def known_frontmatter_fields(self) -> set[str]:
        return set()

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        for skill in skills:
            diags.extend(self._check_skill(skill))
        return diags

    def _check_skill(self, skill: SkillInfo) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        fm = skill.frontmatter or {}

        desc = fm.get("description", "")
        if isinstance(desc, str) and len(desc) > 1024:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3i.description-length",
                    f"Swival truncates descriptions over 1024 chars (got {len(desc)})",
                    path=skill.skill_md_path,
                    source_url=self.source_url,
                )
            )

        body = skill.body or ""
        char_limit = 20000
        if len(body) > char_limit:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3i.body-length",
                    f"Swival truncates skill body over {char_limit} chars (got {len(body)})",
                    path=skill.skill_md_path,
                    source_url=self.source_url,
                )
            )

        return diags

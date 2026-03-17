"""Windsurf agent adapter (3g).

Windsurf discovers skills from .windsurf/skills/ (project-level) and .agents/skills/.
No Windsurf-specific frontmatter extensions beyond the base spec.
No sidecar config files.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo

WINDSURF_SOURCE_URL = "https://docs.windsurf.com/windsurf/cascade/skills"


class WindsurfAdapter:
    name = "windsurf"
    source_url = WINDSURF_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (
            (repo_root / ".windsurf").is_dir()
            or (repo_root / ".agents" / "skills").is_dir()
            or (repo_root / ".windsurfrules").is_file()
        )

    def known_frontmatter_fields(self) -> set[str]:
        return set()

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []

        if (repo_root / ".windsurfrules").is_file():
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3g.windsurfrules-deprecated",
                    ".windsurfrules is deprecated; migrate to .windsurf/rules/",
                    path=str(repo_root / ".windsurfrules"),
                    source_url=self.source_url,
                )
            )

        return diags

"""Cursor agent adapter (3f).

Cursor discovers skills from .cursor/skills/ (project-level) and .agents/skills/.
It extends the base spec frontmatter with disable-model-invocation (boolean).
No sidecar config files — all metadata lives in SKILL.md frontmatter.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo
from ._util import check_field_types

CURSOR_SOURCE_URL = "https://docs.cursor.com/context/rules"

BOOL_FIELDS = {"disable-model-invocation"}
EXTENSION_FIELDS = BOOL_FIELDS


class CursorAdapter:
    name = "cursor"
    source_url = CURSOR_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / ".cursor").is_dir() or (
            repo_root / ".agents" / "skills"
        ).is_dir()

    def known_frontmatter_fields(self) -> set[str]:
        return EXTENSION_FIELDS

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []

        cursor_skills_prefix = str(repo_root / ".cursor" / "skills") + "/"
        agents_skills_prefix = str(repo_root / ".agents" / "skills") + "/"

        for skill in skills:
            if skill.dir_path.startswith(
                cursor_skills_prefix
            ) or skill.dir_path.startswith(agents_skills_prefix):
                diags.extend(
                    check_field_types(
                        skill, BOOL_FIELDS, bool, "a boolean", "3f", self.source_url
                    )
                )

        if (repo_root / ".cursorrules").is_file():
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3f.cursorrules-deprecated",
                    ".cursorrules is deprecated; migrate to .cursor/rules/",
                    path=str(repo_root / ".cursorrules"),
                    source_url=self.source_url,
                )
            )

        return diags

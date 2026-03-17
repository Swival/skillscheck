"""Roo Code agent adapter (3h).

Roo Code discovers skills from .roo/skills/ and .roo/skills-{mode}/ (project-level),
as well as .agents/skills/ and .agents/skills-{mode}/ (cross-agent shared).
It extends the base spec frontmatter with modeSlugs (list of strings) and the
deprecated mode (string) field. No sidecar config files.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo
from ._util import check_field_types

ROO_SOURCE_URL = "https://docs.roocode.com/features/skills"

LIST_STRING_FIELDS = {"modeSlugs"}
STRING_FIELDS = {"mode"}
EXTENSION_FIELDS = LIST_STRING_FIELDS | STRING_FIELDS


def _is_list_of_strings(val: object) -> bool:
    return isinstance(val, list) and all(isinstance(v, str) for v in val)


class RooAdapter:
    name = "roo"
    source_url = ROO_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (
            (repo_root / ".roo").is_dir()
            or (repo_root / ".roomodes").is_file()
            or (repo_root / ".roorules").is_file()
        )

    def known_frontmatter_fields(self) -> set[str]:
        return EXTENSION_FIELDS

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []

        roo_base = str(repo_root / ".roo" / "skills")
        agents_base = str(repo_root / ".agents" / "skills")
        prefixes = (
            roo_base + "/",
            roo_base + "-",
            agents_base + "/",
            agents_base + "-",
        )

        for skill in skills:
            if skill.dir_path.startswith(prefixes):
                diags.extend(self._check_frontmatter(skill))

        if (repo_root / ".roorules").is_file():
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3h.roorules-deprecated",
                    ".roorules is deprecated; migrate to .roo/rules/",
                    path=str(repo_root / ".roorules"),
                    source_url=self.source_url,
                )
            )

        if (repo_root / ".clinerules").is_file():
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3h.clinerules-deprecated",
                    ".clinerules is deprecated; migrate to .roo/rules/",
                    path=str(repo_root / ".clinerules"),
                    source_url=self.source_url,
                )
            )

        return diags

    def _check_frontmatter(self, skill: SkillInfo) -> list[Diagnostic]:
        diags: list[Diagnostic] = []

        diags.extend(
            check_field_types(
                skill,
                LIST_STRING_FIELDS,
                list,
                "a list of strings",
                "3h",
                self.source_url,
                validator=_is_list_of_strings,
            )
        )
        diags.extend(
            check_field_types(
                skill,
                STRING_FIELDS,
                str,
                "a string",
                "3h",
                self.source_url,
            )
        )

        fm = skill.frontmatter or {}
        mode_val = fm.get("mode")
        if mode_val is not None and isinstance(mode_val, str):
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "3h.frontmatter.mode-deprecated",
                    "'mode' is deprecated; use 'modeSlugs' instead",
                    path=skill.skill_md_path,
                    source_url=self.source_url,
                )
            )

        return diags

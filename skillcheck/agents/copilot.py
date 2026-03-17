"""VS Code Copilot agent adapter (3e).

Copilot discovers skills from .github/skills/ (and other configurable paths).
It extends the base spec frontmatter with argument-hint, user-invocable, and
disable-model-invocation fields. No sidecar config files.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, SkillInfo
from ._util import check_field_types

COPILOT_SOURCE_URL = "https://code.visualstudio.com/docs/copilot/chat/chat-agent-skills"

BOOL_FIELDS = {"user-invocable", "disable-model-invocation"}
STRING_FIELDS = {"argument-hint"}
EXTENSION_FIELDS = BOOL_FIELDS | STRING_FIELDS


class CopilotAdapter:
    name = "copilot"
    source_url = COPILOT_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / ".github" / "skills").is_dir()

    def known_frontmatter_fields(self) -> set[str]:
        return EXTENSION_FIELDS

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        copilot_skills_prefix = str(repo_root / ".github" / "skills") + "/"
        diags: list[Diagnostic] = []
        for skill in skills:
            if skill.dir_path.startswith(copilot_skills_prefix):
                diags.extend(
                    check_field_types(
                        skill, BOOL_FIELDS, bool, "a boolean", "3e", self.source_url
                    )
                )
                diags.extend(
                    check_field_types(
                        skill, STRING_FIELDS, str, "a string", "3e", self.source_url
                    )
                )
        return diags

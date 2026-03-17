"""Gemini CLI agent adapter (3b)."""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo
from ._util import load_json_object


class GeminiAdapter:
    name = "gemini"
    source_url = "https://geminicli.com/docs/cli/skills/"

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / "gemini-extension.json").exists()

    def known_frontmatter_fields(self) -> set[str]:
        return set()

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        path = repo_root / "gemini-extension.json"
        data, diags = load_json_object(
            path, "3b.gemini-ext", "gemini-extension.json", self.source_url
        )
        if data is None:
            return diags

        if "name" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3b.gemini-ext.name",
                    "gemini-extension.json missing 'name' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        if "version" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3b.gemini-ext.version",
                    "gemini-extension.json missing 'version' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        if "description" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3b.gemini-ext.description",
                    "gemini-extension.json missing 'description' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        ctx_file = data.get("contextFileName")
        if ctx_file:
            if not (repo_root / ctx_file).exists():
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "3b.gemini-ext.context-missing",
                        f"contextFileName '{ctx_file}' does not exist",
                        path=str(path),
                        source_url=self.source_url,
                    )
                )
        else:
            if not (repo_root / "GEMINI.md").exists():
                diags.append(
                    Diagnostic(
                        Level.INFO,
                        "3b.gemini-ext.no-context",
                        "no contextFileName and no GEMINI.md — Gemini will get no root context",
                        path=str(path),
                        source_url=self.source_url,
                    )
                )

        return diags

"""Agent adapters and cross-agent checks."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import Diagnostic, Level, SkillInfo

from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .copilot import CopilotAdapter
from .cursor import CursorAdapter
from .gemini import GeminiAdapter
from .roo import RooAdapter
from .swival import SwivalAdapter
from .windsurf import WindsurfAdapter


class AgentAdapter(Protocol):
    name: str
    source_url: str

    def detect(self, repo_root: Path) -> bool: ...
    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]: ...
    def known_frontmatter_fields(self) -> set[str]: ...
    def allows_tools_list_syntax(self) -> bool: ...


ALL_ADAPTERS: list[AgentAdapter] = [
    ClaudeAdapter(),
    CodexAdapter(),
    CopilotAdapter(),
    CursorAdapter(),
    GeminiAdapter(),
    RooAdapter(),
    SwivalAdapter(),
    WindsurfAdapter(),
]  # type: ignore[list-item]


def get_adapters(names: list[str] | None, repo_root: Path) -> list[AgentAdapter]:
    if names is None or names == ["all"]:
        return [a for a in ALL_ADAPTERS if a.detect(repo_root)]
    result = []
    name_map = {a.name: a for a in ALL_ADAPTERS}
    for n in names:
        if n in name_map:
            result.append(name_map[n])
    return result


def _read_json_metadata(path: Path) -> dict | None:
    import json

    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def cross_agent_check(
    repo_root: Path, adapters: list[AgentAdapter]
) -> list[Diagnostic]:
    if len(adapters) < 2:
        return []

    diags: list[Diagnostic] = []
    names: dict[str, str] = {}
    versions: dict[str, str] = {}
    descriptions: dict[str, str] = {}

    config_files = {
        "plugin.json": repo_root / ".claude-plugin" / "plugin.json",
        "gemini-extension.json": repo_root / "gemini-extension.json",
    }

    for label, path in config_files.items():
        data = _read_json_metadata(path)
        if data is None:
            continue
        if "name" in data:
            names[label] = data["name"]
        if "version" in data:
            versions[label] = data["version"]
        if "description" in data:
            descriptions[label] = data["description"]

    for field, collected, check_id in [
        ("name", names, "3c.name-mismatch"),
        ("version", versions, "3c.version-mismatch"),
        ("description", descriptions, "3c.description-mismatch"),
    ]:
        if len(set(collected.values())) > 1:
            detail = ", ".join(f"{k}={v!r}" for k, v in collected.items())
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    check_id,
                    f"{field} mismatch across agent configs: {detail}",
                    path=str(repo_root),
                )
            )

    return diags

"""Core spec compliance checks (1a-1g) per agentskills.io/specification."""

from __future__ import annotations

import re

from ..models import Diagnostic, Level, SPEC_URL, SkillInfo
from ..tokenutil import count_tokens

BASE_SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
CONSECUTIVE_HYPHEN_RE = re.compile(r"--")

PLACEHOLDER_PATTERNS = [
    re.compile(r"^\s*TODO\b", re.IGNORECASE),
    re.compile(r"^\s*FIXME\b", re.IGNORECASE),
    re.compile(r"^\s*TBD\b", re.IGNORECASE),
    re.compile(r"^\s*PLACEHOLDER\b", re.IGNORECASE),
    re.compile(r"^\s*A skill that\b", re.IGNORECASE),
    re.compile(r"^\s*This skill\b", re.IGNORECASE),
    re.compile(r"^\s*Description goes here", re.IGNORECASE),
    re.compile(r"^\s*Enter description", re.IGNORECASE),
    re.compile(r"^\s*Replace this", re.IGNORECASE),
    re.compile(r"^\s*\.\.\.\s*$"),
]

KNOWN_TOOL_NAMES = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Agent",
    "WebFetch",
    "WebSearch",
    "Skill",
    "NotebookEdit",
    "LSP",
    "AskUserQuestion",
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskOutput",
    "TaskStop",
    "TaskUpdate",
    "CronCreate",
    "CronDelete",
    "CronList",
    "EnterPlanMode",
    "ExitPlanMode",
    "EnterWorktree",
    "ExitWorktree",
    "TodoRead",
    "TodoWrite",
    "ToolSearch",
    "computer",
    "text_editor",
    "bash",
    "mcp__*",
}


def _is_known_tool(name: str) -> bool:
    base = name.split("(")[0] if "(" in name else name
    if base in KNOWN_TOOL_NAMES:
        return True
    if base.startswith("mcp__"):
        return True
    return False


def check_skill(
    skill: SkillInfo,
    known_extension_fields: set[str] | None = None,
    adapters_authorize_list_tools: bool = False,
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    path = skill.skill_md_path

    if skill.parse_error:
        if skill.parse_error == "SKILL.md not found":
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1a.presence",
                    "SKILL.md not found",
                    path=skill.dir_path,
                    source_url=SPEC_URL,
                )
            )
        else:
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1a.frontmatter",
                    skill.parse_error,
                    path=path,
                    source_url=SPEC_URL,
                )
            )
        return diags

    fm = skill.frontmatter or {}
    diags.extend(_check_name(fm, skill.dir_name, path))
    diags.extend(_check_description(fm, path))
    diags.extend(_check_optional_fields(fm, path, adapters_authorize_list_tools))
    diags.extend(_check_unknown_fields(fm, path, known_extension_fields or set()))
    diags.extend(_check_body(skill))
    return diags


def _check_name(fm: dict, dir_name: str, path: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    name = fm.get("name")

    if name is None:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.name.missing",
                "required field 'name' is missing",
                path=path,
                source_url=SPEC_URL,
            )
        )
        return diags

    name = str(name)

    if len(name) == 0:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.name.empty",
                "field 'name' must not be empty",
                path=path,
                source_url=SPEC_URL,
            )
        )
        return diags

    if len(name) > 64:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.name.length",
                f"field 'name' is {len(name)} chars (max 64)",
                path=path,
                source_url=SPEC_URL,
            )
        )

    if not NAME_RE.match(name):
        if name[0] == "-":
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    "name must not start with a hyphen",
                    path=path,
                    source_url=SPEC_URL,
                )
            )
        elif name[-1] == "-":
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    "name must not end with a hyphen",
                    path=path,
                    source_url=SPEC_URL,
                )
            )
        elif name != name.lower():
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    "name must be lowercase",
                    path=path,
                    source_url=SPEC_URL,
                    fixable=True,
                )
            )
        else:
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    f"name '{name}' contains invalid characters (only lowercase a-z, 0-9, hyphens)",
                    path=path,
                    source_url=SPEC_URL,
                )
            )

    if CONSECUTIVE_HYPHEN_RE.search(name):
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.name.consecutive-hyphens",
                "name must not contain consecutive hyphens (--)",
                path=path,
                source_url=SPEC_URL,
                fixable=True,
            )
        )

    if name != dir_name:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.name.dir-match",
                f"name '{name}' does not match directory name '{dir_name}'",
                path=path,
                source_url=SPEC_URL,
                fixable=True,
            )
        )

    return diags


def _check_description(fm: dict, path: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    desc = fm.get("description")

    if desc is None:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.description.missing",
                "required field 'description' is missing",
                path=path,
                source_url=SPEC_URL,
            )
        )
        return diags

    desc = str(desc)

    if len(desc) == 0:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.description.empty",
                "field 'description' must not be empty",
                path=path,
                source_url=SPEC_URL,
            )
        )
        return diags

    if len(desc) > 1024:
        diags.append(
            Diagnostic(
                Level.ERROR,
                "1b.description.length",
                f"field 'description' is {len(desc)} chars (max 1024)",
                path=path,
                source_url=SPEC_URL,
            )
        )

    for pat in PLACEHOLDER_PATTERNS:
        if pat.search(desc):
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "1b.description.placeholder",
                    "description looks like a placeholder or template text",
                    path=path,
                    source_url=SPEC_URL,
                )
            )
            break

    return diags


def _check_optional_fields(
    fm: dict, path: str, adapters_authorize_list_tools: bool
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    if "compatibility" in fm:
        val = fm["compatibility"]
        if val is not None:
            s = str(val)
            if len(s) == 0:
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "1c.compatibility.empty",
                        "field 'compatibility' must not be empty if present",
                        path=path,
                        source_url=SPEC_URL,
                    )
                )
            elif len(s) > 500:
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "1c.compatibility.length",
                        f"field 'compatibility' is {len(s)} chars (max 500)",
                        path=path,
                        source_url=SPEC_URL,
                    )
                )

    if "metadata" in fm:
        val = fm["metadata"]
        if val is not None:
            if not isinstance(val, dict):
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "1c.metadata.type",
                        "field 'metadata' must be a mapping",
                        path=path,
                        source_url=SPEC_URL,
                    )
                )
            else:
                for k, v in val.items():
                    if not isinstance(k, str):
                        diags.append(
                            Diagnostic(
                                Level.ERROR,
                                "1c.metadata.key-type",
                                f"metadata key {k!r} must be a string",
                                path=path,
                                source_url=SPEC_URL,
                            )
                        )
                    if not isinstance(v, str):
                        diags.append(
                            Diagnostic(
                                Level.ERROR,
                                "1c.metadata.value-type",
                                f"metadata value for '{k}' must be a string, got {type(v).__name__}",
                                path=path,
                                source_url=SPEC_URL,
                            )
                        )

    if "allowed-tools" in fm:
        val = fm["allowed-tools"]
        if isinstance(val, list):
            if not adapters_authorize_list_tools:
                diags.append(
                    Diagnostic(
                        Level.INFO,
                        "1c.allowed-tools.list-form",
                        "allowed-tools uses list form; accepted for compatibility but not portable base-spec syntax (spec defines space-delimited string)",
                        path=path,
                        source_url=SPEC_URL,
                    )
                )
            for item in val:
                if not isinstance(item, str):
                    diags.append(
                        Diagnostic(
                            Level.ERROR,
                            "1c.allowed-tools.item-type",
                            f"allowed-tools list items must be strings, got {type(item).__name__}",
                            path=path,
                            source_url=SPEC_URL,
                        )
                    )
        elif not isinstance(val, str):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "1c.allowed-tools.type",
                    f"field 'allowed-tools' must be a string or list, got {type(val).__name__}",
                    path=path,
                    source_url=SPEC_URL,
                )
            )

    diags.extend(_check_allowed_tools_stale(fm, path))
    return diags


def _check_allowed_tools_stale(fm: dict, path: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    val = fm.get("allowed-tools")
    if val is None:
        return diags

    tool_names: list[str] = []
    if isinstance(val, list):
        tool_names = [str(t) for t in val if isinstance(t, str)]
    elif isinstance(val, str):
        tool_names = val.split()

    for name in tool_names:
        if not _is_known_tool(name):
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "1c.allowed-tools.unknown-tool",
                    f"tool '{name}' in allowed-tools is not recognized by any known agent",
                    path=path,
                    source_url=SPEC_URL,
                )
            )

    return diags


def _check_unknown_fields(
    fm: dict, path: str, extension_fields: set[str]
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    all_known = BASE_SPEC_FIELDS | extension_fields
    for key in fm:
        if key not in all_known:
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "1d.unknown-field",
                    f"field '{key}' is not in the base spec or any active adapter",
                    path=path,
                    source_url=SPEC_URL,
                )
            )
    return diags


def _check_body(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    path = skill.skill_md_path
    body = skill.body

    stripped = body.strip()
    if not stripped:
        diags.append(
            Diagnostic(
                Level.WARNING,
                "1e.body.empty",
                "SKILL.md body is empty (no instructions after frontmatter)",
                path=path,
                source_url=SPEC_URL,
            )
        )
        return diags

    first_line = stripped.split("\n")[0].strip()
    if not first_line.startswith("#"):
        diags.append(
            Diagnostic(
                Level.INFO,
                "1e.body.no-heading",
                "SKILL.md body does not start with a heading — consider adding a descriptive heading",
                path=path,
                source_url=SPEC_URL,
            )
        )

    line_count = stripped.count("\n") + 1
    if line_count > 500:
        diags.append(
            Diagnostic(
                Level.WARNING,
                "1e.body.length",
                f"SKILL.md body is {line_count} lines (spec recommends < 500)",
                path=path,
                source_url=SPEC_URL,
            )
        )

    if len(stripped) < 8000:
        return diags

    token_estimate = count_tokens(stripped)
    if token_estimate > 5000:
        diags.append(
            Diagnostic(
                Level.WARNING,
                "1e.body.tokens",
                f"SKILL.md body is ~{token_estimate} tokens (spec recommends < 5000)",
                path=path,
                source_url=SPEC_URL,
            )
        )
    elif token_estimate > 2000:
        diags.append(
            Diagnostic(
                Level.INFO,
                "1e.body.tokens",
                f"SKILL.md body is ~{token_estimate} tokens (spec recommends < 2000, warns at 5000)",
                path=path,
                source_url=SPEC_URL,
            )
        )

    return diags


def check_cross_skill(skills: list[SkillInfo]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    seen_names: dict[str, str] = {}
    seen_descriptions: dict[str, str] = {}

    for skill in skills:
        if skill.frontmatter is None:
            continue

        name = skill.frontmatter.get("name")
        if name is not None:
            name = str(name)
            if name in seen_names:
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "1g.duplicate-name",
                        f"skill name '{name}' is used by both {seen_names[name]} and {skill.skill_md_path}",
                        path=skill.skill_md_path,
                        source_url=SPEC_URL,
                    )
                )
            else:
                seen_names[name] = skill.skill_md_path

        desc = skill.frontmatter.get("description")
        if desc is not None:
            desc_str = str(desc).strip().lower()
            if desc_str and desc_str in seen_descriptions:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "1g.duplicate-description",
                        f"description is identical to skill at {seen_descriptions[desc_str]}",
                        path=skill.skill_md_path,
                        source_url=SPEC_URL,
                    )
                )
            elif desc_str:
                seen_descriptions[desc_str] = skill.skill_md_path

    return diags

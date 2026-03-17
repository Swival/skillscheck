from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Diagnostic, Level, SkillInfo


def load_json_object(
    path: Path,
    prefix: str,
    label: str,
    source_url: str,
) -> tuple[dict | None, list[Diagnostic]]:
    diags: list[Diagnostic] = []
    if not path.exists():
        diags.append(
            Diagnostic(
                Level.ERROR,
                f"{prefix}.missing",
                f"{label} not found",
                path=str(path),
                source_url=source_url,
            )
        )
        return None, diags
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        diags.append(
            Diagnostic(
                Level.ERROR,
                f"{prefix}.invalid",
                f"invalid JSON: {e}",
                path=str(path),
                source_url=source_url,
            )
        )
        return None, diags
    if not isinstance(data, dict):
        diags.append(
            Diagnostic(
                Level.ERROR,
                f"{prefix}.type",
                f"{label} must be a JSON object",
                path=str(path),
                source_url=source_url,
            )
        )
        return None, diags
    return data, diags


def check_field_types(
    skill: SkillInfo,
    fields: set[str],
    expected_type: type | tuple[type, ...],
    type_label: str,
    check_prefix: str,
    source_url: str,
    validator: Any = None,
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    fm = skill.frontmatter or {}
    for field in fields:
        val = fm.get(field)
        if val is None:
            continue
        if validator is not None:
            if not validator(val):
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        f"{check_prefix}.frontmatter.{field}-type",
                        f"'{field}' must be {type_label}, got {type(val).__name__}",
                        path=skill.skill_md_path,
                        source_url=source_url,
                    )
                )
        elif not isinstance(val, expected_type):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    f"{check_prefix}.frontmatter.{field}-type",
                    f"'{field}' must be {type_label}, got {type(val).__name__}",
                    path=skill.skill_md_path,
                    source_url=source_url,
                )
            )
    return diags

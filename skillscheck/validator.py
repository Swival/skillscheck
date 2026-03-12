"""Top-level validate() that ties everything together."""

from __future__ import annotations

from pathlib import Path
from typing import overload

from .agents import cross_agent_check, get_adapters
from .checks import spec, quality, disclosure
from .fixer import apply_fixes, has_fixable
from .models import ValidationResult
from .parser import discover_skills, parse_skill

MAX_FIX_PASSES = 5


@overload
def validate(
    root: Path,
    agent_names: list[str] | None = None,
    checks: list[str] | None = None,
    *,
    fix: bool = ...,
) -> ValidationResult | tuple[ValidationResult, list[str]]: ...


def validate(
    root: Path,
    agent_names: list[str] | None = None,
    checks: list[str] | None = None,
    fix: bool = False,
) -> ValidationResult | tuple[ValidationResult, list[str]]:
    result, skills = _run_checks(root, agent_names, checks)

    if not fix:
        return result

    all_fixes: list[str] = []
    for pass_num in range(MAX_FIX_PASSES):
        fixes = apply_fixes(skills, result.skills)
        if not fixes:
            break
        all_fixes.extend(fixes)
        result, skills = _run_checks(root, agent_names, checks)
    else:
        if has_fixable(skills, result.skills):
            all_fixes.append(
                f"warning: fix loop hit {MAX_FIX_PASSES}-pass limit; "
                "re-run --fix to continue"
            )

    return result, all_fixes


def _run_checks(
    root: Path,
    agent_names: list[str] | None,
    checks: list[str] | None,
) -> tuple[ValidationResult, list]:
    result = ValidationResult()
    run_checks = set(checks) if checks else {"spec", "quality", "disclosure", "agents"}

    skill_dirs = discover_skills(root)
    skills = [parse_skill(d) for d in skill_dirs]

    adapters = get_adapters(agent_names, root) if "agents" in run_checks else []
    extension_fields: set[str] = set()
    adapters_authorizing_list_tools: bool = False
    for adapter in adapters:
        fields = adapter.known_frontmatter_fields()
        extension_fields |= fields
        if adapter.allows_tools_list_syntax():
            adapters_authorizing_list_tools = True

    for skill in skills:
        result.ensure_skill(skill.dir_name)
        if "spec" in run_checks:
            for d in spec.check_skill(
                skill, extension_fields, adapters_authorizing_list_tools
            ):
                result.add_skill(skill.dir_name, "spec", d)

        if "quality" in run_checks:
            for d in quality.check_skill(skill):
                result.add_skill(skill.dir_name, "quality", d)

        if "disclosure" in run_checks:
            for d in disclosure.check_skill(skill):
                result.add_skill(skill.dir_name, "disclosure", d)

    if "spec" in run_checks:
        for d in spec.check_cross_skill(skills):
            result.add_skill("_cross-skill", "spec", d)

    if "agents" in run_checks:
        for adapter in adapters:
            for d in adapter.check(root, skills):
                result.add_agent(adapter.name, d)

        cross_diags = cross_agent_check(root, adapters)
        for d in cross_diags:
            result.add_agent("cross-agent", d)

    return result, skills

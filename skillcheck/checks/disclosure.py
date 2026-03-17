"""Progressive disclosure checks (4a-4c)."""

from __future__ import annotations

from pathlib import Path

from ..models import Diagnostic, Level, SPEC_URL, SkillInfo
from ..mdutil import extract_local_link_targets
from ..tokenutil import estimate_file_tokens


def check_skill(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if skill.parse_error:
        return diags

    diags.extend(_check_reference_sizing(skill))
    diags.extend(_check_nesting(skill))
    return diags


def _check_reference_sizing(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)

    for subdir_name in ("references", "scripts", "assets"):
        subdir = skill_dir / subdir_name
        if not subdir.is_dir():
            continue
        for fpath in subdir.rglob("*"):
            if not fpath.is_file():
                continue
            token_est = estimate_file_tokens(str(fpath))
            if token_est is not None and token_est > 10000:
                rel = fpath.relative_to(skill_dir)
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "4b.reference.large",
                        f"reference file '{rel}' is ~{token_est} tokens (consider splitting)",
                        path=str(fpath),
                        source_url=SPEC_URL,
                    )
                )

    return diags


def _check_nesting(skill: SkillInfo) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    skill_dir = Path(skill.dir_path)

    primary_links = extract_local_link_targets(skill.body)

    for link_target in primary_links:
        ref_path = skill_dir / link_target
        if not ref_path.is_file():
            continue
        if not ref_path.suffix.lower() == ".md":
            continue

        try:
            ref_content = ref_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        nested_links = extract_local_link_targets(ref_content)
        if nested_links:
            rel = ref_path.relative_to(skill_dir)
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "4c.nesting",
                    f"reference '{rel}' contains {len(nested_links)} link(s) to other local files — consider keeping references one level deep",
                    path=str(ref_path),
                    source_url=SPEC_URL,
                )
            )

    return diags

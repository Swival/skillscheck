from __future__ import annotations


from skillcheck.parser import parse_skill
from skillcheck.checks.disclosure import check_skill
from skillcheck.models import Level


def _has_check(diags, check_prefix):
    return any(d.check.startswith(check_prefix) for d in diags)


def _warnings(diags):
    return [d for d in diags if d.level == Level.WARNING]


def _infos(diags):
    return [d for d in diags if d.level == Level.INFO]


class TestReferenceSizing:
    def test_large_reference_warning(self, tmp_path):
        skill_dir = tmp_path / "big-ref"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: big-ref\ndescription: test. Use when testing.\n---\nBody."
        )
        (ref_dir / "large.md").write_text("word " * 10001)
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "4b.reference.large")

    def test_small_reference_no_warning(self, tmp_path):
        skill_dir = tmp_path / "small-ref"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: small-ref\ndescription: test. Use when testing.\n---\nBody."
        )
        (ref_dir / "small.md").write_text("A short reference.")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "4b.reference.large")

    def test_scripts_dir_checked(self, tmp_path):
        skill_dir = tmp_path / "scripts-ref"
        skill_dir.mkdir()
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: scripts-ref\ndescription: test. Use when testing.\n---\nBody."
        )
        (scripts_dir / "big.sh").write_text("echo hi\n" * 10001)
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "4b.reference.large")

    def test_parse_error_returns_empty(self, fixture_path):
        skill = parse_skill(fixture_path("missing-skillmd"))
        diags = check_skill(skill)
        assert len(diags) == 0


class TestNesting:
    def test_nested_links_info(self, tmp_path):
        skill_dir = tmp_path / "nested"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text(
            "# Guide\n\nSee also [another](another.md) for more."
        )
        (ref_dir / "another.md").write_text("# Another\n\nContent here.")
        (skill_dir / "SKILL.md").write_text(
            "---\nname: nested\ndescription: test. Use when testing.\n---\n\nSee [guide](references/guide.md)."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        infos = _infos(diags)
        assert _has_check(infos, "4c.nesting")

    def test_no_nesting_for_flat_refs(self, tmp_path):
        skill_dir = tmp_path / "flat"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text("# Guide\n\nJust content, no links.")
        (skill_dir / "SKILL.md").write_text(
            "---\nname: flat\ndescription: test. Use when testing.\n---\n\nSee [guide](references/guide.md)."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "4c.nesting")

    def test_external_links_in_refs_not_counted(self, tmp_path):
        skill_dir = tmp_path / "ext-ref"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text(
            "# Guide\n\nSee [external](https://example.com) for more."
        )
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ext-ref\ndescription: test. Use when testing.\n---\n\nSee [guide](references/guide.md)."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "4c.nesting")

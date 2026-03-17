from pathlib import Path

from skillcheck.fixer import (
    apply_fixes,
    _fix_name_lowercase,
    _fix_name_consecutive_hyphens,
    _fix_dir_match,
)
from skillcheck.models import SkillDiagnostics, Diagnostic, Level, ValidationResult
from skillcheck.parser import parse_skill
from skillcheck.validator import validate


def _make_skill(tmp_path, dir_name, name, description="A useful skill for testing"):
    skill_dir = tmp_path / "skills" / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# Test\n\nBody content here.\n",
        encoding="utf-8",
    )
    return parse_skill(skill_dir)


class TestFixNameLowercase:
    def test_lowercases_name(self, tmp_path):
        skill = _make_skill(tmp_path, "MySkill", "MySkill")
        result = _fix_name_lowercase(skill)
        assert result is not None
        assert "lowercased" in result
        assert "'myskill'" in result
        assert skill.frontmatter["name"] == "myskill"
        text = Path(skill.skill_md_path).read_text()
        assert "name: myskill" in text

    def test_noop_already_lowercase(self, tmp_path):
        skill = _make_skill(tmp_path, "my-skill", "my-skill")
        assert _fix_name_lowercase(skill) is None

    def test_noop_no_frontmatter(self, tmp_path):
        skill = _make_skill(tmp_path, "test", "test")
        skill.frontmatter = None
        assert _fix_name_lowercase(skill) is None


class TestFixNameConsecutiveHyphens:
    def test_fixes_double_hyphens(self, tmp_path):
        skill = _make_skill(tmp_path, "my--skill", "my--skill")
        result = _fix_name_consecutive_hyphens(skill)
        assert result is not None
        assert "'my-skill'" in result
        assert skill.frontmatter["name"] == "my-skill"
        text = Path(skill.skill_md_path).read_text()
        assert "name: my-skill" in text

    def test_fixes_triple_hyphens(self, tmp_path):
        skill = _make_skill(tmp_path, "my---skill", "my---skill")
        result = _fix_name_consecutive_hyphens(skill)
        assert result is not None
        assert skill.frontmatter["name"] == "my-skill"

    def test_noop_no_consecutive_hyphens(self, tmp_path):
        skill = _make_skill(tmp_path, "my-skill", "my-skill")
        assert _fix_name_consecutive_hyphens(skill) is None


class TestFixDirMatch:
    def test_renames_directory(self, tmp_path):
        skill = _make_skill(tmp_path, "wrong-name", "correct-name")
        old_dir = Path(skill.dir_path)
        assert old_dir.exists()

        result = _fix_dir_match(skill)
        assert result is not None
        assert "renamed" in result
        assert "'correct-name'" in result
        assert not old_dir.exists()
        assert (tmp_path / "skills" / "correct-name").exists()
        assert skill.dir_name == "correct-name"

    def test_noop_already_matches(self, tmp_path):
        skill = _make_skill(tmp_path, "my-skill", "my-skill")
        assert _fix_dir_match(skill) is None

    def test_skip_invalid_name(self, tmp_path):
        skill = _make_skill(tmp_path, "somedir", "-invalid")
        assert _fix_dir_match(skill) is None

    def test_skip_uppercase_name(self, tmp_path):
        skill = _make_skill(tmp_path, "somedir", "MySkill")
        assert _fix_dir_match(skill) is None

    def test_skip_target_exists(self, tmp_path):
        skill = _make_skill(tmp_path, "old-name", "new-name")
        (tmp_path / "skills" / "new-name").mkdir()
        assert _fix_dir_match(skill) is None


class TestApplyFixes:
    def test_no_fixable_issues(self, tmp_path):
        skill = _make_skill(tmp_path, "good-skill", "good-skill")
        sd = SkillDiagnostics()
        fixes = apply_fixes([skill], {"good-skill": sd})
        assert fixes == []

    def test_fixes_uppercase_name(self, tmp_path):
        skill = _make_skill(tmp_path, "MyTool", "MyTool")
        sd = SkillDiagnostics(
            spec=[
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    "name must be lowercase",
                    path=skill.skill_md_path,
                    fixable=True,
                ),
            ]
        )
        fixes = apply_fixes([skill], {"MyTool": sd})
        assert len(fixes) == 1
        assert "lowercased" in fixes[0]

    def test_fixes_dir_match(self, tmp_path):
        skill = _make_skill(tmp_path, "old-dir", "new-dir")
        sd = SkillDiagnostics(
            spec=[
                Diagnostic(
                    Level.ERROR,
                    "1b.name.dir-match",
                    "name 'new-dir' does not match directory name 'old-dir'",
                    path=skill.skill_md_path,
                    fixable=True,
                ),
            ]
        )
        fixes = apply_fixes([skill], {"old-dir": sd})
        assert len(fixes) == 1
        assert "renamed" in fixes[0]

    def test_fixes_consecutive_hyphens(self, tmp_path):
        skill = _make_skill(tmp_path, "my--tool", "my--tool")
        sd = SkillDiagnostics(
            spec=[
                Diagnostic(
                    Level.ERROR,
                    "1b.name.consecutive-hyphens",
                    "name must not contain consecutive hyphens (--)",
                    path=skill.skill_md_path,
                    fixable=True,
                ),
            ]
        )
        fixes = apply_fixes([skill], {"my--tool": sd})
        assert len(fixes) == 1
        assert "my-tool" in fixes[0]

    def test_skips_non_fixable(self, tmp_path):
        skill = _make_skill(tmp_path, "test", "test")
        sd = SkillDiagnostics(
            spec=[
                Diagnostic(
                    Level.ERROR,
                    "1b.name.format",
                    "name must not start with a hyphen",
                    path=skill.skill_md_path,
                    fixable=False,
                ),
            ]
        )
        fixes = apply_fixes([skill], {"test": sd})
        assert fixes == []


class TestValidateWithFix:
    def test_fix_mode_returns_tuple(self, tmp_path):
        _make_skill(tmp_path, "good", "good")
        result, fixes = validate(tmp_path, fix=True)
        assert isinstance(fixes, list)

    def test_fix_mode_fixes_uppercase(self, tmp_path):
        _make_skill(tmp_path, "MyTool", "MyTool")
        result, fixes = validate(tmp_path, fix=True)
        assert any("lowercased" in f for f in fixes)
        # After fix, the uppercase error should be gone
        all_diags = []
        for sd in result.skills.values():
            all_diags.extend(sd.spec)
        format_errors = [d for d in all_diags if d.check == "1b.name.format"]
        assert not format_errors

    def test_fix_mode_renames_directory(self, tmp_path):
        _make_skill(tmp_path, "wrong-dir", "correct-dir")
        result, fixes = validate(tmp_path, fix=True)
        assert any("renamed" in f for f in fixes)
        assert (tmp_path / "skills" / "correct-dir").exists()
        assert not (tmp_path / "skills" / "wrong-dir").exists()

    def test_fix_mode_combined(self, tmp_path):
        """Uppercase name + dir mismatch: both get fixed across passes."""
        _make_skill(tmp_path, "WrongDir", "MyTool")
        result, fixes = validate(tmp_path, fix=True)

        assert any("lowercased" in f for f in fixes)
        assert any("renamed" in f for f in fixes)

        assert (tmp_path / "skills" / "mytool").exists()
        assert not (tmp_path / "skills" / "WrongDir").exists()

        text = (tmp_path / "skills" / "mytool" / "SKILL.md").read_text()
        assert "name: mytool" in text

        all_diags = []
        for sd in result.skills.values():
            all_diags.extend(sd.spec)
        name_errors = [
            d for d in all_diags if d.check in ("1b.name.format", "1b.name.dir-match")
        ]
        assert not name_errors

    def test_no_fix_mode_returns_result_only(self, tmp_path):
        _make_skill(tmp_path, "good", "good")
        result = validate(tmp_path)
        assert isinstance(result, ValidationResult)


class TestCLIFix:
    def test_fix_flag_text_output(self, tmp_path):
        from click.testing import CliRunner
        from skillcheck.cli import main

        _make_skill(tmp_path, "old-name", "new-name")
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--fix"])
        assert "fixes applied" in result.output
        assert "renamed" in result.output
        assert "re-validation" in result.output

    def test_fix_flag_json_output(self, tmp_path):
        from click.testing import CliRunner
        from skillcheck.cli import main
        import json

        _make_skill(tmp_path, "old-name", "new-name")
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--fix", "--format", "json"])
        data = json.loads(result.output)
        assert "fixes" in data
        assert any("renamed" in f for f in data["fixes"])

    def test_fix_flag_no_fixable_issues(self, tmp_path):
        from click.testing import CliRunner
        from skillcheck.cli import main

        _make_skill(tmp_path, "good", "good")
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path), "--fix"])
        assert "fixes applied" not in result.output


class TestFixPassCap:
    def test_cap_emits_warning_without_mutating(self, tmp_path, monkeypatch):
        """When the fix loop hits the pass limit, it emits a warning
        without applying further fixes or leaving result out of sync."""
        import skillcheck.validator as v

        monkeypatch.setattr(v, "MAX_FIX_PASSES", 1)

        def noop_apply(skills, result_skills):
            return ["fake fix (no-op)"]

        monkeypatch.setattr(v, "apply_fixes", noop_apply)

        _make_skill(tmp_path, "BadName", "BadName")
        result, fixes = validate(tmp_path, fix=True)

        assert "fake fix (no-op)" in fixes
        assert any("pass limit" in f for f in fixes)

        assert (tmp_path / "skills" / "BadName").exists()
        text = (tmp_path / "skills" / "BadName" / "SKILL.md").read_text()
        assert "name: BadName" in text

    def test_has_fixable_does_not_mutate(self, tmp_path, monkeypatch):
        """has_fixable checks for remaining fixable diagnostics without
        applying any changes to disk or skill objects."""
        from skillcheck.fixer import has_fixable

        skill = _make_skill(tmp_path, "wrong-dir", "correct-dir")
        sd = SkillDiagnostics(
            spec=[
                Diagnostic(
                    Level.ERROR,
                    "1b.name.dir-match",
                    "name 'correct-dir' does not match directory name 'wrong-dir'",
                    path=skill.skill_md_path,
                    fixable=True,
                ),
            ]
        )

        assert has_fixable([skill], {"wrong-dir": sd})
        assert (tmp_path / "skills" / "wrong-dir").exists()
        assert not (tmp_path / "skills" / "correct-dir").exists()
        assert skill.dir_name == "wrong-dir"

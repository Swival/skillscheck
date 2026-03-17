from __future__ import annotations

import json


from skillcheck.validator import validate
from skillcheck.models import Level, SkillDiagnostics


def _all_diags(result):
    diags = []
    for sd in result.skills.values():
        diags.extend(sd.all())
    for v in result.agents.values():
        diags.extend(v)
    return diags


def _has_check(diags, check_prefix):
    return any(d.check.startswith(check_prefix) for d in diags)


def _errors(diags):
    return [d for d in diags if d.level == Level.ERROR]


class TestValidateEndToEnd:
    def test_valid_minimal_skill(self, fixture_path):
        result = validate(
            fixture_path("valid-minimal"), checks=["spec", "quality", "disclosure"]
        )
        all_d = _all_diags(result)
        errors = _errors(all_d)
        assert len(errors) == 0

    def test_valid_full_skill(self, fixture_path):
        result = validate(
            fixture_path("valid-full"), checks=["spec", "quality", "disclosure"]
        )
        all_d = _all_diags(result)
        errors = _errors(all_d)
        assert len(errors) == 0

    def test_missing_skillmd_detected(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "missing-skillmd").mkdir()
        result = validate(tmp_path, checks=["spec"])
        all_d = _all_diags(result)
        assert _has_check(all_d, "1a.presence")

    def test_multiple_skills_in_directory(self, tmp_path):
        for name in ["skill-a", "skill-b", "skill-c"]:
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Skill {name}. Use when testing.\n---\nBody."
            )
        result = validate(tmp_path, checks=["spec"])
        assert result.counts()["skills"] == 3
        errors = _errors(_all_diags(result))
        assert len(errors) == 0

    def test_exit_code_zero_for_valid(self, fixture_path):
        result = validate(fixture_path("valid-minimal"), checks=["spec"])
        assert result.exit_code() == 0

    def test_exit_code_one_for_errors(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "missing-skill").mkdir()
        result = validate(tmp_path, checks=["spec"])
        assert result.exit_code() == 1

    def test_strict_mode_fails_on_warnings(self, tmp_path):
        skill_dir = tmp_path / "short-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: short-desc\ndescription: Short.\n---\nBody content."
        )
        result = validate(tmp_path, checks=["quality"])
        assert result.exit_code(strict=False) == 0
        assert result.exit_code(strict=True) == 1

    def test_selective_checks(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A short desc\n---\nBody."
        )
        spec_result = validate(tmp_path, checks=["spec"])
        quality_result = validate(tmp_path, checks=["quality"])
        spec_checks = {d.check for d in _all_diags(spec_result)}
        quality_checks = {d.check for d in _all_diags(quality_result)}
        assert not any(c.startswith("2") for c in spec_checks)
        assert not any(c.startswith("1") for c in quality_checks)


class TestValidateWithAgents:
    def test_claude_adapter_integration(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill. Use when testing.\nagent: claude\n---\nBody."
        )
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "test", "version": "1.0", "description": "test"})
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "test", "plugins": []})
        )
        result = validate(tmp_path, checks=["spec", "agents"])
        assert "claude" in result.agents

    def test_gemini_adapter_integration(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill. Use when testing.\n---\nBody."
        )
        (tmp_path / "gemini-extension.json").write_text(
            json.dumps({"name": "test", "version": "1.0", "description": "test"})
        )
        result = validate(tmp_path, checks=["spec", "agents"])
        assert "gemini" in result.agents

    def test_no_agents_when_not_requested(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill. Use when testing.\n---\nBody."
        )
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "test", "version": "1.0", "description": "test"})
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "test", "plugins": []})
        )
        result = validate(tmp_path, checks=["spec"])
        assert len(result.agents) == 0

    def test_cross_agent_mismatch(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill. Use when testing.\n---\nBody."
        )
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "claude-name", "version": "1.0", "description": "test"})
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "claude-name", "plugins": []})
        )
        (tmp_path / "gemini-extension.json").write_text(
            json.dumps({"name": "gemini-name", "version": "1.0", "description": "test"})
        )
        (tmp_path / "GEMINI.md").write_text("context")
        result = validate(tmp_path, checks=["agents"])
        cross_diags = result.agents.get("cross-agent", [])
        assert _has_check(cross_diags, "3c.name-mismatch")

    def test_extension_fields_suppress_unknown(self, tmp_path):
        skill_dir = tmp_path / "with-agent-field"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: with-agent-field\ndescription: Uses agent field. Use when testing.\nagent: claude\n---\nBody."
        )
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "test", "version": "1.0", "description": "test"})
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "test", "plugins": []})
        )
        result = validate(tmp_path, checks=["spec", "agents"])
        all_d = _all_diags(result)
        unknown = [
            d for d in all_d if d.check == "1d.unknown-field" and "agent" in d.message
        ]
        assert len(unknown) == 0

    def test_allowed_tools_list_note_with_claude(self, tmp_path):
        skill_dir = tmp_path / "tools-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: tools-skill\ndescription: Uses allowed-tools list. Use when testing.\nallowed-tools:\n  - Read\n  - Write\n---\nBody."
        )
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "test", "version": "1.0", "description": "test"})
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "test", "plugins": []})
        )
        result = validate(tmp_path, checks=["spec", "agents"])
        all_d = _all_diags(result)
        list_notes = [d for d in all_d if d.check == "1c.allowed-tools.list-form"]
        assert len(list_notes) == 1

    def test_json_output_has_category_buckets(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Short.\n---\nBody."
        )
        result = validate(tmp_path, checks=["spec", "quality"])
        d = result.to_dict()
        skill_data = d["skills"]["my-skill"]
        assert isinstance(skill_data, dict)
        for key in skill_data:
            assert key in ("spec", "quality", "disclosure")


class TestValidationResult:
    def test_to_dict_structure(self, fixture_path):
        result = validate(fixture_path("valid-minimal"), checks=["spec"])
        d = result.to_dict()
        assert "skills" in d
        assert "agents" in d
        assert "summary" in d
        assert "skills" in d["summary"]
        assert "errors" in d["summary"]
        assert "warnings" in d["summary"]
        assert "info" in d["summary"]

    def test_counts(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "orphan-skill").mkdir()
        result = validate(tmp_path, checks=["spec"])
        c = result.counts()
        assert c["errors"] >= 1

    def test_add_skill_creates_entry(self):
        from skillcheck.models import ValidationResult, Diagnostic, Level

        result = ValidationResult()
        result.add_skill("test", "spec", Diagnostic(Level.ERROR, "test.check", "msg"))
        assert "test" in result.skills
        assert len(result.skills["test"].spec) == 1

    def test_add_skill_different_categories(self):
        from skillcheck.models import ValidationResult, Diagnostic, Level

        result = ValidationResult()
        result.add_skill(
            "test", "spec", Diagnostic(Level.ERROR, "1a.test", "spec error")
        )
        result.add_skill(
            "test", "quality", Diagnostic(Level.WARNING, "2a.test", "quality warning")
        )
        result.add_skill(
            "test", "disclosure", Diagnostic(Level.INFO, "4a.test", "disclosure info")
        )
        sd = result.skills["test"]
        assert len(sd.spec) == 1
        assert len(sd.quality) == 1
        assert len(sd.disclosure) == 1
        assert len(sd.all()) == 3

    def test_skill_diagnostics_to_dict(self):
        from skillcheck.models import Diagnostic, Level

        sd = SkillDiagnostics()
        sd.spec.append(Diagnostic(Level.ERROR, "1b.name", "bad name"))
        sd.quality.append(Diagnostic(Level.WARNING, "2a.short", "too short"))
        d = sd.to_dict()
        assert "spec" in d
        assert "quality" in d
        assert "disclosure" not in d

    def test_add_agent_creates_entry(self):
        from skillcheck.models import ValidationResult, Diagnostic, Level

        result = ValidationResult()
        result.add_agent("claude", Diagnostic(Level.WARNING, "test.check", "msg"))
        assert "claude" in result.agents
        assert len(result.agents["claude"]) == 1

    def test_diagnostic_to_dict(self):
        from skillcheck.models import Diagnostic, Level

        d = Diagnostic(
            Level.ERROR,
            "1b.name.missing",
            "name is missing",
            path="/test",
            line=5,
            source_url="http://example.com",
        )
        dd = d.to_dict()
        assert dd["level"] == "error"
        assert dd["check"] == "1b.name.missing"
        assert dd["message"] == "name is missing"
        assert dd["path"] == "/test"
        assert dd["line"] == 5
        assert dd["source_url"] == "http://example.com"

    def test_diagnostic_to_dict_minimal(self):
        from skillcheck.models import Diagnostic, Level

        d = Diagnostic(Level.INFO, "test", "msg")
        dd = d.to_dict()
        assert "path" not in dd
        assert "line" not in dd
        assert "source_url" not in dd

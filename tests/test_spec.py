from __future__ import annotations


from skillcheck.parser import parse_skill
from skillcheck.checks.spec import check_skill, check_cross_skill
from skillcheck.models import Level


def _diag_checks(diags):
    return [d.check for d in diags]


def _diag_levels(diags):
    return [d.level for d in diags]


def _has_check(diags, check_prefix):
    return any(d.check.startswith(check_prefix) for d in diags)


def _errors(diags):
    return [d for d in diags if d.level == Level.ERROR]


def _warnings(diags):
    return [d for d in diags if d.level == Level.WARNING]


def _infos(diags):
    return [d for d in diags if d.level == Level.INFO]


class TestPresence:
    def test_missing_skillmd(self, fixture_path):
        skill = parse_skill(fixture_path("missing-skillmd"))
        diags = check_skill(skill)
        assert len(_errors(diags)) == 1
        assert _has_check(diags, "1a.presence")

    def test_bad_frontmatter(self, fixture_path):
        skill = parse_skill(fixture_path("bad-frontmatter"))
        diags = check_skill(skill)
        assert len(_errors(diags)) == 1
        assert _has_check(diags, "1a.frontmatter")


class TestNameValidation:
    def test_valid_name(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        assert not _has_check(diags, "1b.name")

    def test_uppercase_name(self, fixture_path):
        skill = parse_skill(fixture_path("bad-name-uppercase"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.name.format")
        assert any("lowercase" in d.message for d in errors)

    def test_hyphen_start(self, fixture_path):
        skill = parse_skill(fixture_path("bad-name-hyphen-start"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.name.format")
        assert any("start with a hyphen" in d.message for d in errors)

    def test_consecutive_hyphens(self, fixture_path):
        skill = parse_skill(fixture_path("bad-name-consecutive"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.name.consecutive-hyphens")

    def test_name_dir_mismatch(self, fixture_path):
        skill = parse_skill(fixture_path("bad-name-mismatch"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.name.dir-match")
        assert any("does not match directory" in d.message for d in errors)

    def test_missing_name(self, tmp_path):
        skill_dir = tmp_path / "no-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: No name field here.\n---\nBody"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.name.missing")

    def test_empty_name(self, tmp_path):
        skill_dir = tmp_path / "empty-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: ""\ndescription: Empty name.\n---\nBody'
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.name.empty")

    def test_name_too_long(self, tmp_path):
        long_name = "a" * 65
        skill_dir = tmp_path / long_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {long_name}\ndescription: Too long.\n---\nBody"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.name.length")


class TestDescriptionValidation:
    def test_valid_description(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        assert not _has_check(diags, "1b.description")

    def test_missing_description(self, fixture_path):
        skill = parse_skill(fixture_path("missing-description"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.description.missing")

    def test_description_too_long(self, fixture_path):
        skill = parse_skill(fixture_path("description-too-long"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert _has_check(errors, "1b.description.length")

    def test_empty_description(self, tmp_path):
        skill_dir = tmp_path / "empty-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: empty-desc\ndescription: ""\n---\nBody'
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.description.empty")


class TestOptionalFields:
    def test_valid_optional_fields(self, fixture_path):
        skill = parse_skill(fixture_path("valid-full"))
        diags = check_skill(skill)
        errors = _errors(diags)
        assert not any(d.check.startswith("1c.") for d in errors)

    def test_allowed_tools_list_produces_info(self, fixture_path):
        skill = parse_skill(fixture_path("allowed-tools-list"))
        diags = check_skill(skill)
        infos = _infos(diags)
        assert _has_check(infos, "1c.allowed-tools.list-form")

    def test_metadata_must_be_mapping(self, tmp_path):
        skill_dir = tmp_path / "bad-meta"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-meta\ndescription: test. Use when testing.\nmetadata: not-a-dict\n---\nBody"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1c.metadata.type")

    def test_metadata_value_must_be_string(self, tmp_path):
        skill_dir = tmp_path / "bad-meta-val"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-meta-val\ndescription: test. Use when testing.\nmetadata:\n  key: 123\n---\nBody"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1c.metadata.value-type")

    def test_compatibility_too_long(self, tmp_path):
        skill_dir = tmp_path / "long-compat"
        skill_dir.mkdir()
        long_compat = "x" * 501
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: long-compat\ndescription: test. Use when testing.\ncompatibility: {long_compat}\n---\nBody"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1c.compatibility.length")


class TestUnknownFields:
    def test_unknown_fields_produce_info(self, fixture_path):
        skill = parse_skill(fixture_path("unknown-fields"))
        diags = check_skill(skill)
        infos = _infos(diags)
        assert _has_check(infos, "1d.unknown-field")
        unknown_messages = [d.message for d in infos if d.check == "1d.unknown-field"]
        assert any("custom-field" in m for m in unknown_messages)
        assert any("another-unknown" in m for m in unknown_messages)

    def test_known_extension_fields_not_flagged(self, fixture_path):
        skill = parse_skill(fixture_path("unknown-fields"))
        diags = check_skill(
            skill, known_extension_fields={"custom-field", "another-unknown"}
        )
        infos = _infos(diags)
        unknown_checks = [d for d in infos if d.check == "1d.unknown-field"]
        assert len(unknown_checks) == 0


class TestBody:
    def test_empty_body_warning(self, tmp_path):
        skill_dir = tmp_path / "no-body"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-body\ndescription: test. Use when testing.\n---\n"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "1e.body.empty")

    def test_long_body_warning(self, tmp_path):
        skill_dir = tmp_path / "long-body"
        skill_dir.mkdir()
        body = "\n".join(f"Line {i}" for i in range(501))
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: long-body\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "1e.body.length")

    def test_high_token_body_warning(self, tmp_path):
        skill_dir = tmp_path / "big-body"
        skill_dir.mkdir()
        body = "word " * 5001
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: big-body\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "1e.body.tokens")

    def test_moderate_token_body_info_includes_recommendation(self, tmp_path):
        skill_dir = tmp_path / "mid-body"
        skill_dir.mkdir()
        body = "word " * 2500
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: mid-body\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        infos = [d for d in diags if d.level.value == "info"]
        token_diags = [d for d in infos if d.check == "1e.body.tokens"]
        assert len(token_diags) == 1
        assert "recommends" in token_diags[0].message


class TestVersionField:
    def test_version_is_unknown_field(self, tmp_path):
        """version is not a base spec field — spec puts it under metadata."""
        skill_dir = tmp_path / "ver-top"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ver-top\ndescription: test. Use when testing.\nversion: 1.2.3\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        infos = _infos(diags)
        unknown = [
            d for d in infos if d.check == "1d.unknown-field" and "version" in d.message
        ]
        assert len(unknown) == 1

    def test_version_in_metadata_no_warning(self, tmp_path):
        skill_dir = tmp_path / "ver-meta"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\nname: ver-meta\ndescription: test. Use when testing.\nmetadata:\n  version: "1.0"\n---\n# Body'
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        unknown = [
            d for d in diags if d.check == "1d.unknown-field" and "version" in d.message
        ]
        assert len(unknown) == 0


class TestLicenseField:
    def test_spdx_license_accepted(self, tmp_path):
        skill_dir = tmp_path / "lic-spdx"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: lic-spdx\ndescription: test. Use when testing.\nlicense: MIT\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(_errors(diags), "1c.license")

    def test_proprietary_license_accepted(self, tmp_path):
        """Spec example: 'Proprietary. LICENSE.txt has complete terms'"""
        skill_dir = tmp_path / "lic-prop"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: lic-prop\ndescription: test. Use when testing.\nlicense: Proprietary. LICENSE.txt has complete terms\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        license_diags = [d for d in diags if "license" in d.check.lower()]
        assert len(license_diags) == 0

    def test_freeform_license_accepted(self, tmp_path):
        skill_dir = tmp_path / "lic-free"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: lic-free\ndescription: test. Use when testing.\nlicense: See LICENSE file\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        license_diags = [d for d in diags if "license" in d.check.lower()]
        assert len(license_diags) == 0


class TestPlaceholderDescription:
    def test_todo_placeholder(self, tmp_path):
        skill_dir = tmp_path / "ph-todo"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ph-todo\ndescription: TODO fill this in later\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.description.placeholder")

    def test_a_skill_that_placeholder(self, tmp_path):
        skill_dir = tmp_path / "ph-generic"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ph-generic\ndescription: A skill that does things\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.description.placeholder")

    def test_this_skill_placeholder(self, tmp_path):
        skill_dir = tmp_path / "ph-this"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ph-this\ndescription: This skill helps with stuff\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.description.placeholder")

    def test_ellipsis_placeholder(self, tmp_path):
        skill_dir = tmp_path / "ph-dots"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ph-dots\ndescription: '...'\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1b.description.placeholder")

    def test_real_description_no_placeholder(self, tmp_path):
        skill_dir = tmp_path / "ph-real"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ph-real\ndescription: Validates Fastly VCL configurations. Use when editing VCL files.\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1b.description.placeholder")


class TestBodyHeading:
    def test_body_starts_with_heading(self, tmp_path):
        skill_dir = tmp_path / "heading-ok"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: heading-ok\ndescription: test. Use when testing.\n---\n# My Skill\n\nInstructions here."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1e.body.no-heading")

    def test_body_starts_with_text_info(self, tmp_path):
        skill_dir = tmp_path / "no-heading"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-heading\ndescription: test. Use when testing.\n---\nJust text, no heading."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1e.body.no-heading")
        infos = _infos(diags)
        assert _has_check(infos, "1e.body.no-heading")

    def test_body_h2_heading(self, tmp_path):
        skill_dir = tmp_path / "h2-heading"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: h2-heading\ndescription: test. Use when testing.\n---\n## Subheading\n\nContent."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1e.body.no-heading")


class TestAllowedToolsStale:
    def test_known_tool_no_warning(self, tmp_path):
        skill_dir = tmp_path / "known-tool"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: known-tool\ndescription: test. Use when testing.\nallowed-tools: Read Write Bash\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1c.allowed-tools.unknown-tool")

    def test_unknown_tool_info(self, tmp_path):
        skill_dir = tmp_path / "stale-tool"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: stale-tool\ndescription: test. Use when testing.\nallowed-tools: Read FakeTool123\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "1c.allowed-tools.unknown-tool")
        tool_diags = [d for d in diags if d.check == "1c.allowed-tools.unknown-tool"]
        assert len(tool_diags) == 1
        assert "FakeTool123" in tool_diags[0].message

    def test_mcp_tool_recognized(self, tmp_path):
        skill_dir = tmp_path / "mcp-tool"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: mcp-tool\ndescription: test. Use when testing.\nallowed-tools: mcp__server__action\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1c.allowed-tools.unknown-tool")

    def test_unknown_tools_in_list_form(self, tmp_path):
        skill_dir = tmp_path / "list-stale"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: list-stale\ndescription: test. Use when testing.\nallowed-tools:\n  - Read\n  - BogusToolXYZ\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        tool_diags = [d for d in diags if d.check == "1c.allowed-tools.unknown-tool"]
        assert len(tool_diags) == 1
        assert "BogusToolXYZ" in tool_diags[0].message

    def test_parenthesized_tool_args_recognized(self, tmp_path):
        """Spec example: Bash(git:*) Bash(jq:*) Read"""
        skill_dir = tmp_path / "paren-tools"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: paren-tools\ndescription: test. Use when testing.\nallowed-tools: Bash(git:*) Bash(jq:*) Read\n---\n# Body"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "1c.allowed-tools.unknown-tool")


class TestCrossSkill:
    def test_duplicate_names(self, fixture_path):
        from skillcheck.models import SkillInfo

        s1 = SkillInfo(
            dir_name="skill-a",
            dir_path="/a",
            skill_md_path="/a/SKILL.md",
            frontmatter={"name": "my-skill"},
        )
        s2 = SkillInfo(
            dir_name="skill-b",
            dir_path="/b",
            skill_md_path="/b/SKILL.md",
            frontmatter={"name": "my-skill"},
        )
        diags = check_cross_skill([s1, s2])
        assert _has_check(diags, "1g.duplicate-name")

    def test_no_duplicates(self, fixture_path):
        from skillcheck.models import SkillInfo

        s1 = SkillInfo(
            dir_name="skill-a",
            dir_path="/a",
            skill_md_path="/a/SKILL.md",
            frontmatter={"name": "skill-a"},
        )
        s2 = SkillInfo(
            dir_name="skill-b",
            dir_path="/b",
            skill_md_path="/b/SKILL.md",
            frontmatter={"name": "skill-b"},
        )
        diags = check_cross_skill([s1, s2])
        assert not _has_check(diags, "1g.duplicate-name")

    def test_duplicate_description_warning(self):
        from skillcheck.models import SkillInfo

        s1 = SkillInfo(
            dir_name="skill-a",
            dir_path="/a",
            skill_md_path="/a/SKILL.md",
            frontmatter={"name": "skill-a", "description": "Same description text."},
        )
        s2 = SkillInfo(
            dir_name="skill-b",
            dir_path="/b",
            skill_md_path="/b/SKILL.md",
            frontmatter={"name": "skill-b", "description": "Same description text."},
        )
        diags = check_cross_skill([s1, s2])
        assert _has_check(diags, "1g.duplicate-description")

    def test_different_descriptions_no_warning(self):
        from skillcheck.models import SkillInfo

        s1 = SkillInfo(
            dir_name="skill-a",
            dir_path="/a",
            skill_md_path="/a/SKILL.md",
            frontmatter={"name": "skill-a", "description": "Handles Fastly VCL."},
        )
        s2 = SkillInfo(
            dir_name="skill-b",
            dir_path="/b",
            skill_md_path="/b/SKILL.md",
            frontmatter={"name": "skill-b", "description": "Handles DNS configs."},
        )
        diags = check_cross_skill([s1, s2])
        assert not _has_check(diags, "1g.duplicate-description")

    def test_duplicate_description_case_insensitive(self):
        from skillcheck.models import SkillInfo

        s1 = SkillInfo(
            dir_name="skill-a",
            dir_path="/a",
            skill_md_path="/a/SKILL.md",
            frontmatter={"name": "skill-a", "description": "My Skill Description"},
        )
        s2 = SkillInfo(
            dir_name="skill-b",
            dir_path="/b",
            skill_md_path="/b/SKILL.md",
            frontmatter={"name": "skill-b", "description": "my skill description"},
        )
        diags = check_cross_skill([s1, s2])
        assert _has_check(diags, "1g.duplicate-description")

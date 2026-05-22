from __future__ import annotations


from skillscheck.parser import parse_skill
from skillscheck.checks.quality import check_skill
from skillscheck.models import Level


def _has_check(diags, check_prefix):
    return any(d.check.startswith(check_prefix) for d in diags)


def _errors(diags):
    return [d for d in diags if d.level == Level.ERROR]


def _warnings(diags):
    return [d for d in diags if d.level == Level.WARNING]


class TestDescriptionQuality:
    def test_good_description_no_warning(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.short")

    def test_short_description_warning(self, tmp_path):
        skill_dir = tmp_path / "short-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: short-desc\ndescription: Short.\n---\nBody content."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2a.description.short")

    def test_no_when_hint_warning(self, tmp_path):
        skill_dir = tmp_path / "no-when"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-when\ndescription: A skill that does something interesting and helpful for the user.\n---\nBody content."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2a.description.no-when")

    def test_use_when_hint_no_warning(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.no-when")

    def test_user_centric_trigger_warning(self, tmp_path):
        skill_dir = tmp_path / "user-centric"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: user-centric\ndescription: Generate dashboards. Use this whenever the user mentions data visualization.\n---\nBody content."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2a.description.user-centric")

    def test_user_asks_trigger_warning(self, tmp_path):
        skill_dir = tmp_path / "user-asks"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: user-asks\ndescription: Use when the user asks about deployment pipelines.\n---\nBody content."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2a.description.user-centric")

    def test_agent_directed_no_user_centric_warning(self, tmp_path):
        skill_dir = tmp_path / "agent-directed"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: agent-directed\ndescription: Use when working with PDF files or converting documents to PDF format.\n---\nBody content."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.user-centric")

    def test_parse_error_returns_empty(self, fixture_path):
        skill = parse_skill(fixture_path("missing-skillmd"))
        diags = check_skill(skill)
        assert len(diags) == 0


class TestFileHygiene:
    def test_secret_filename_warning(self, tmp_path):
        skill_dir = tmp_path / "secret-file"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: secret-file\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / ".env").write_text("SECRET_KEY=abc")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.filename")

    def test_secret_pattern_warning(self, tmp_path):
        skill_dir = tmp_path / "secret-pattern"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: secret-pattern\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "my_secret_config.txt").write_text("data")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.filename")

    def test_binary_file_warning(self, tmp_path):
        skill_dir = tmp_path / "has-binary"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: has-binary\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "helper.exe").write_bytes(b"\x00\x01\x02")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.binary")

    def test_large_file_warning(self, tmp_path):
        skill_dir = tmp_path / "large-file"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: large-file\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "big.txt").write_text("x" * (101 * 1024))
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.large-file")

    def test_secret_content_warning(self, tmp_path):
        skill_dir = tmp_path / "secret-content"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: secret-content\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.json").write_text('{"key": "AKIAIOSFODNN7EXAMPLE"}')
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_env_local_warning(self, tmp_path):
        skill_dir = tmp_path / "env-local"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: env-local\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / ".env.local").write_text("SECRET=abc")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.filename")

    def test_env_production_warning(self, tmp_path):
        skill_dir = tmp_path / "env-prod"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: env-prod\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / ".env.production").write_text("SECRET=abc")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.filename")

    def test_gitlab_pat_content_warning(self, tmp_path):
        skill_dir = tmp_path / "gitlab-pat"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: gitlab-pat\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.yaml").write_text("token: glpat-xxxxxxxxxxxxxxxxxxxx")
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_slack_xoxb_content_warning(self, tmp_path):
        skill_dir = tmp_path / "slack-bot"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: slack-bot\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.json").write_text('{"token": "xoxb-123456-abcdef"}')
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_slack_xoxp_content_warning(self, tmp_path):
        skill_dir = tmp_path / "slack-user"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: slack-user\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.json").write_text('{"token": "xoxp-123456-abcdef"}')
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_slack_xapp_content_warning(self, tmp_path):
        skill_dir = tmp_path / "slack-app"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: slack-app\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.json").write_text('{"token": "xapp-123456-abcdef"}')
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_base64_private_key_content_warning(self, tmp_path):
        skill_dir = tmp_path / "b64-key"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: b64-key\ndescription: test. Use when testing.\n---\nBody"
        )
        (skill_dir / "config.txt").write_text(
            "key: LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0t"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2b.secrets.content")

    def test_clean_skill_no_hygiene_warnings(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        hygiene_warnings = [d for d in diags if d.check.startswith("2b.")]
        assert len(hygiene_warnings) == 0


class TestLinks:
    def test_broken_link_warning(self, fixture_path):
        skill = parse_skill(fixture_path("broken-link"))
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2c.broken-link")

    def test_valid_link_no_warning(self, fixture_path):
        skill = parse_skill(fixture_path("valid-full"))
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link")

    def test_external_links_ignored(self, tmp_path):
        skill_dir = tmp_path / "ext-links"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ext-links\ndescription: test. Use when testing.\n---\n\nSee [docs](https://example.com)."
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link")

    def test_links_in_code_blocks_ignored(self, tmp_path):
        skill_dir = tmp_path / "code-link"
        skill_dir.mkdir()
        body = "```\n[broken](nonexistent.md)\n```\n\nRegular text."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: code-link\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link")

    def test_broken_fragment_link_warning(self, tmp_path):
        skill_dir = tmp_path / "frag-broken"
        skill_dir.mkdir()
        body = "## Installation\n\nSee [usage](#usage-guide) for details."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-broken\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2c.broken-link.fragment")

    def test_valid_fragment_link_no_warning(self, tmp_path):
        skill_dir = tmp_path / "frag-valid"
        skill_dir.mkdir()
        body = "## Installation\n\nSee [install](#installation) for details."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-valid\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_broken_file_fragment_link_warning(self, tmp_path):
        skill_dir = tmp_path / "file-frag-broken"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text("## Getting Started\n\nContent here.")
        body = "See [setup](references/guide.md#setup-instructions) for details."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: file-frag-broken\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        warnings = _warnings(diags)
        assert _has_check(warnings, "2c.broken-link.fragment")

    def test_valid_file_fragment_link_no_warning(self, tmp_path):
        skill_dir = tmp_path / "file-frag-valid"
        skill_dir.mkdir()
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text("## Getting Started\n\nContent here.")
        body = "See [start](references/guide.md#getting-started) for details."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: file-frag-valid\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_setext_heading_fragment_no_warning(self, tmp_path):
        skill_dir = tmp_path / "frag-setext"
        skill_dir.mkdir()
        body = "Title\n=====\n\nSubtitle\n--------\n\nSee [title](#title) and [sub](#subtitle)."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-setext\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_broken_setext_heading_fragment_warning(self, tmp_path):
        skill_dir = tmp_path / "frag-setext-broken"
        skill_dir.mkdir()
        body = "Title\n=====\n\nSee [missing](#no-such-heading)."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-setext-broken\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2c.broken-link.fragment")

    def test_duplicate_heading_suffixed_anchors(self, tmp_path):
        skill_dir = tmp_path / "frag-dup"
        skill_dir.mkdir()
        body = "## Intro\n\nFirst.\n\n## Intro\n\nSecond.\n\n## Intro\n\nThird.\n\nSee [first](#intro), [second](#intro-1), and [third](#intro-2)."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-dup\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_atx_heading_above_horizontal_rule_no_phantom(self, tmp_path):
        skill_dir = tmp_path / "frag-atx-rule"
        skill_dir.mkdir()
        body = "## Title\n\n----\n\nSee [bad](#title-1)."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-atx-rule\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2c.broken-link.fragment")

    def test_duplicate_heading_unsuffixed_extra_warns(self, tmp_path):
        skill_dir = tmp_path / "frag-dup-bad"
        skill_dir.mkdir()
        body = "## Intro\n\nFirst.\n\n## Intro\n\nSecond.\n\nSee [bad](#intro-5)."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-dup-bad\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert _has_check(diags, "2c.broken-link.fragment")

    def test_fragment_in_code_block_ignored(self, tmp_path):
        skill_dir = tmp_path / "frag-code"
        skill_dir.mkdir()
        body = "```\n[broken](#nonexistent)\n```\n\nRegular text."
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: frag-code\ndescription: test. Use when testing.\n---\n{body}"
        )
        skill = parse_skill(skill_dir)
        diags = check_skill(skill)
        assert not _has_check(diags, "2c.broken-link.fragment")


def _infos(diags):
    return [d for d in diags if d.level == Level.INFO]


def _make_skill_dir(
    tmp_path,
    name,
    desc="A helpful skill. Use when testing.",
    body="# Title\n\nBody content.",
):
    """Create a skill directory and return its path. Call parse_skill() separately."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    import yaml

    fm = yaml.dump({"name": name, "description": desc}, default_flow_style=False)
    (skill_dir / "SKILL.md").write_text(f"---\n{fm}---\n{body}")
    return skill_dir


class TestKeywordStuffing:
    def test_quoted_string_stuffing_info(self, tmp_path):
        desc = '"deploy" "build" "test" "lint" "format" "check"'
        skill = parse_skill(_make_skill_dir(tmp_path, "kw-stuff", desc))
        diags = check_skill(skill)
        assert _has_check(_infos(diags), "2a.description.keyword-stuffing")

    def test_quoted_strings_with_prose_no_warning(self, tmp_path):
        desc = (
            'Handles deployment tasks including "deploy", "build", "test", '
            '"lint", and "format" operations. Use when working with CI/CD.'
        )
        skill = parse_skill(_make_skill_dir(tmp_path, "kw-prose", desc))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.keyword-stuffing")

    def test_few_quoted_strings_no_warning(self, tmp_path):
        desc = 'Supports "json" and "yaml" formats. Use when parsing config files.'
        skill = parse_skill(_make_skill_dir(tmp_path, "kw-few", desc))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.keyword-stuffing")

    def test_comma_list_stuffing_info(self, tmp_path):
        desc = "deploy, build, test, lint, format, check, validate, publish, release"
        skill = parse_skill(_make_skill_dir(tmp_path, "kw-comma", desc))
        diags = check_skill(skill)
        assert _has_check(_infos(diags), "2a.description.keyword-stuffing")

    def test_comma_list_with_long_segments_no_warning(self, tmp_path):
        desc = (
            "This skill handles complex deployment workflows, "
            "automated build pipelines for multiple architectures, "
            "comprehensive test suites with coverage reporting, "
            "code linting with custom rulesets, "
            "formatting across multiple languages, "
            "validation of configuration files, "
            "publishing to package registries, "
            "release management with changelogs, "
            "and rollback procedures for failed deployments. "
            "Use when managing CI/CD."
        )
        skill = parse_skill(_make_skill_dir(tmp_path, "kw-long-seg", desc))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.keyword-stuffing")

    def test_normal_description_no_warning(self, fixture_path):
        skill = parse_skill(fixture_path("valid-minimal"))
        diags = check_skill(skill)
        assert not _has_check(diags, "2a.description.keyword-stuffing")


class TestExtraneousFiles:
    def test_readme_at_root_info(self, tmp_path):
        d = _make_skill_dir(tmp_path, "has-readme")
        (d / "README.md").write_text("# About")
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2b.extraneous-file")

    def test_license_at_root_info(self, tmp_path):
        d = _make_skill_dir(tmp_path, "has-license")
        (d / "LICENSE").write_text("MIT")
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2b.extraneous-file")

    def test_makefile_at_root_info(self, tmp_path):
        d = _make_skill_dir(tmp_path, "has-makefile")
        (d / "Makefile").write_text("all:")
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2b.extraneous-file")

    def test_gitignore_at_root_info(self, tmp_path):
        d = _make_skill_dir(tmp_path, "has-gitignore")
        (d / ".gitignore").write_text("*.pyc")
        diags = check_skill(parse_skill(d))
        # .gitignore starts with "." — our check skips dotfiles
        assert not _has_check(diags, "2b.extraneous-file")

    def test_clean_skill_no_extraneous(self, fixture_path):
        diags = check_skill(parse_skill(fixture_path("valid-minimal")))
        assert not _has_check(diags, "2b.extraneous-file")

    def test_references_dir_not_flagged(self, tmp_path):
        d = _make_skill_dir(tmp_path, "has-refs")
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text("# Guide")
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2b.extraneous-file")


class TestUnclosedFences:
    def test_unclosed_backtick_fence_error(self, tmp_path):
        body = "# Title\n\n```python\nprint('hello')\n\nMore text."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "unclosed-bt", body=body))
        )
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_unclosed_tilde_fence_error(self, tmp_path):
        body = "# Title\n\n~~~\ncode here\n\nMore text."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "unclosed-tilde", body=body))
        )
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_closed_fence_no_error(self, tmp_path):
        body = "# Title\n\n```python\nprint('hello')\n```\n\nMore text."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "closed-fence", body=body))
        )
        assert not _has_check(diags, "2d.unclosed-fence")

    def test_multiple_closed_fences_no_error(self, tmp_path):
        body = "# Title\n\n```\ncode1\n```\n\n~~~\ncode2\n~~~\n\nDone."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "multi-fence", body=body))
        )
        assert not _has_check(diags, "2d.unclosed-fence")

    def test_no_fences_no_error(self, tmp_path):
        body = "# Title\n\nJust regular text."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "no-fence", body=body))
        )
        assert not _has_check(diags, "2d.unclosed-fence")

    def test_unclosed_fence_in_reference_file(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-unclosed", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text("# Guide\n\n```\nunclosed code\n")
        diags = check_skill(parse_skill(d))
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_closed_fence_in_reference_no_error(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-closed", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text("# Guide\n\n```\nclosed\n```\n")
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2d.unclosed-fence")

    def test_fence_line_number_includes_offset(self, tmp_path):
        body = "# Title\n\nSome text.\n\n```python\nunclosed"
        skill = parse_skill(_make_skill_dir(tmp_path, "fence-line", body=body))
        diags = [d for d in check_skill(skill) if d.check == "2d.unclosed-fence"]
        assert len(diags) == 1
        assert diags[0].line is not None
        assert diags[0].line > 5  # offset + body line

    def test_longer_closing_fence_accepted(self, tmp_path):
        body = "# Title\n\n```\ncode\n````\n\nText."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "long-close", body=body))
        )
        assert not _has_check(diags, "2d.unclosed-fence")

    def test_mismatched_fence_char_not_closed(self, tmp_path):
        body = "# Title\n\n```\ncode\n~~~\n\nText."
        diags = check_skill(
            parse_skill(_make_skill_dir(tmp_path, "mismatch-fence", body=body))
        )
        assert _has_check(_errors(diags), "2d.unclosed-fence")


class TestReferenceLinks:
    def test_broken_path_link_warning(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "broken-ref-link", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [more](./missing.md)."
        )
        diags = check_skill(parse_skill(d))
        warnings = _warnings(diags)
        broken = [d for d in warnings if d.check == "2c.broken-link"]
        assert any("missing.md" in d.message for d in broken)

    def test_self_fragment_broken_warning(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-self-frag", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\n## Intro\n\nSee [x](#nope)."
        )
        diags = check_skill(parse_skill(d))
        warnings = _warnings(diags)
        assert _has_check(warnings, "2c.broken-link.fragment")

    def test_cross_file_fragment_ok(self, tmp_path):
        body = (
            "# Title\n\nSee [a](references/a.md) and [b](references/b.md)."
        )
        d = _make_skill_dir(tmp_path, "cross-frag-ok", body=body)
        (d / "references").mkdir()
        (d / "references" / "a.md").write_text(
            "# A\n\nGo to [section](b.md#section-two)."
        )
        (d / "references" / "b.md").write_text(
            "# B\n\n## Section Two\n\nHello."
        )
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_cross_file_fragment_bad(self, tmp_path):
        body = (
            "# Title\n\nSee [a](references/a.md) and [b](references/b.md)."
        )
        d = _make_skill_dir(tmp_path, "cross-frag-bad", body=body)
        (d / "references").mkdir()
        (d / "references" / "a.md").write_text(
            "# A\n\nGo to [section](b.md#section-three)."
        )
        (d / "references" / "b.md").write_text(
            "# B\n\n## Section Two\n\nHello."
        )
        diags = check_skill(parse_skill(d))
        warnings = _warnings(diags)
        frag = [d for d in warnings if d.check == "2c.broken-link.fragment"]
        assert any("section-three" in d.message for d in frag)

    def test_escapes_skill_relative(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-escape-rel", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [outside](../../outside.md)."
        )
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2c.escapes-skill")
        assert not any(
            "../../outside.md" in x.message
            for x in diags
            if x.check == "2c.broken-link"
        )

    def test_escapes_skill_absolute(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-escape-abs", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [host](/etc/passwd)."
        )
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2c.escapes-skill")

    def test_scheme_relative_url_skipped(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-scheme-rel", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [host](//example.test/x)."
        )
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2c.escapes-skill")
        assert not _has_check(diags, "2c.broken-link")

    def test_external_url_in_reference_ignored(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-external", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [docs](https://example.com/x)."
        )
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2c.broken-link")
        assert not _has_check(diags, "2c.escapes-skill")

    def test_uppercase_external_scheme_ignored(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-upper-scheme", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [docs](HTTPS://example.com/x) "
            "and [mail](MAILTO:a@b.test)."
        )
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2c.broken-link")
        assert not _has_check(diags, "2c.escapes-skill")

    def test_fragment_link_escapes_skill_no_frag_diag(self, tmp_path):
        body = "# Title\n\nSee [guide](references/guide.md)."
        d = _make_skill_dir(tmp_path, "ref-frag-escape", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text(
            "# Guide\n\nSee [outside](../../outside.md#anchor)."
        )
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2c.escapes-skill")
        assert not _has_check(diags, "2c.broken-link.fragment")

    def test_link_to_sibling_directory_exists(self, tmp_path):
        body = "# Title\n\nSee [a](references/a.md), [s](scripts/s.sh)."
        d = _make_skill_dir(tmp_path, "ref-sibling", body=body)
        (d / "references").mkdir()
        (d / "scripts").mkdir()
        (d / "scripts" / "s.sh").write_text("echo hi")
        (d / "references" / "a.md").write_text(
            "# A\n\nRun [script](../scripts/s.sh)."
        )
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2c.broken-link")
        assert not _has_check(diags, "2c.escapes-skill")


class TestDisclosureFenceCoverage:
    def test_nested_reference_fence(self, tmp_path):
        body = "# Title\n\nSee [deep](references/sub/deep.md)."
        d = _make_skill_dir(tmp_path, "nested-fence", body=body)
        (d / "references" / "sub").mkdir(parents=True)
        (d / "references" / "sub" / "deep.md").write_text(
            "# Deep\n\n```\nunclosed\n"
        )
        diags = check_skill(parse_skill(d))
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_scripts_md_fence(self, tmp_path):
        body = "# Title\n\nSee [run](scripts/run.md)."
        d = _make_skill_dir(tmp_path, "scripts-fence", body=body)
        (d / "scripts").mkdir()
        (d / "scripts" / "run.md").write_text("# Run\n\n```\nunclosed\n")
        diags = check_skill(parse_skill(d))
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_assets_md_fence(self, tmp_path):
        body = "# Title\n\nSee [a](assets/notes.md)."
        d = _make_skill_dir(tmp_path, "assets-fence", body=body)
        (d / "assets").mkdir()
        (d / "assets" / "notes.md").write_text("# Notes\n\n```\nunclosed\n")
        diags = check_skill(parse_skill(d))
        assert _has_check(_errors(diags), "2d.unclosed-fence")

    def test_uppercase_md_suffix_fence(self, tmp_path):
        body = "# Title\n\nSee [g](references/Guide.MD)."
        d = _make_skill_dir(tmp_path, "uppercase-md", body=body)
        (d / "references").mkdir()
        (d / "references" / "Guide.MD").write_text(
            "# Guide\n\n```\nunclosed\n"
        )
        diags = check_skill(parse_skill(d))
        assert _has_check(_errors(diags), "2d.unclosed-fence")


class TestOrphanFiles:
    def test_referenced_file_no_warning(self, tmp_path):
        body = "# Title\n\nRun [extract](scripts/extract.py) to process."
        d = _make_skill_dir(tmp_path, "ref-file", body=body)
        (d / "scripts").mkdir()
        (d / "scripts" / "extract.py").write_text("print('hello')")
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2b.orphan")

    def test_unreferenced_file_info(self, tmp_path):
        body = "# Title\n\nJust instructions."
        d = _make_skill_dir(tmp_path, "orphan-file", body=body)
        (d / "scripts").mkdir()
        (d / "scripts" / "unused.py").write_text("print('hello')")
        diags = check_skill(parse_skill(d))
        assert _has_check(_infos(diags), "2b.orphan")

    def test_filename_mention_counts_as_reference(self, tmp_path):
        body = "# Title\n\nUse extract.py to process files."
        d = _make_skill_dir(tmp_path, "name-ref", body=body)
        (d / "scripts").mkdir()
        (d / "scripts" / "extract.py").write_text("print('hello')")
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2b.orphan")

    def test_empty_dirs_no_orphan(self, tmp_path):
        body = "# Title\n\nInstructions."
        d = _make_skill_dir(tmp_path, "empty-dirs", body=body)
        (d / "scripts").mkdir()
        (d / "references").mkdir()
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2b.orphan")

    def test_init_py_not_flagged(self, tmp_path):
        body = "# Title\n\nInstructions."
        d = _make_skill_dir(tmp_path, "init-py", body=body)
        (d / "scripts").mkdir()
        (d / "scripts" / "__init__.py").write_text("")
        diags = check_skill(parse_skill(d))
        assert not _has_check(diags, "2b.orphan")

    def test_multiple_dirs_mixed(self, tmp_path):
        body = "# Title\n\nSee [ref](references/guide.md). Also run helper.sh."
        d = _make_skill_dir(tmp_path, "multi-dir", body=body)
        (d / "references").mkdir()
        (d / "references" / "guide.md").write_text("# Guide")
        (d / "references" / "orphan.md").write_text("# Orphan")
        (d / "scripts").mkdir()
        (d / "scripts" / "helper.sh").write_text("echo hi")
        (d / "scripts" / "unused.sh").write_text("echo bye")
        diags = check_skill(parse_skill(d))
        orphans = [d for d in diags if d.check == "2b.orphan"]
        orphan_paths = [d.message for d in orphans]
        assert len(orphans) == 2
        assert any("orphan.md" in m for m in orphan_paths)
        assert any("unused.sh" in m for m in orphan_paths)

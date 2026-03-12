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

from __future__ import annotations

import json


import yaml

from skillcheck.agents.claude import ClaudeAdapter
from skillcheck.agents.codex import CodexAdapter
from skillcheck.agents.copilot import CopilotAdapter
from skillcheck.agents.cursor import CursorAdapter
from skillcheck.agents.gemini import GeminiAdapter
from skillcheck.agents.roo import RooAdapter
from skillcheck.agents.swival import SwivalAdapter
from skillcheck.agents.windsurf import WindsurfAdapter
from skillcheck.agents import get_adapters, cross_agent_check, ALL_ADAPTERS
from skillcheck.models import Level, SkillInfo


def _has_check(diags, check_prefix):
    return any(d.check.startswith(check_prefix) for d in diags)


def _errors(diags):
    return [d for d in diags if d.level == Level.ERROR]


def _warnings(diags):
    return [d for d in diags if d.level == Level.WARNING]


def _infos(diags):
    return [d for d in diags if d.level == Level.INFO]


def _make_claude_plugin(repo_root, plugin_data=None, marketplace_data=None):
    plugin_dir = repo_root / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    if plugin_data is not None:
        (plugin_dir / "plugin.json").write_text(json.dumps(plugin_data))
    if marketplace_data is not None:
        (plugin_dir / "marketplace.json").write_text(json.dumps(marketplace_data))
    return plugin_dir


def _make_gemini_ext(repo_root, ext_data=None):
    if ext_data is not None:
        (repo_root / "gemini-extension.json").write_text(json.dumps(ext_data))


class TestClaudeAdapter:
    def test_detect_present(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "test"}, {"name": "test", "plugins": []})
        adapter = ClaudeAdapter()
        assert adapter.detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        adapter = ClaudeAdapter()
        assert not adapter.detect(tmp_path)

    def test_valid_plugin(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "test-plugin", "description": "A test", "version": "1.0.0"},
            {"name": "test-plugin", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        errors = _errors(diags)
        assert len(errors) == 0

    def test_missing_plugin_json(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "t", "plugins": []})
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.missing")

    def test_missing_marketplace_json(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "t"}))
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.missing")

    def test_invalid_plugin_json(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{invalid json")
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "t", "plugins": []})
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.invalid")

    def test_invalid_marketplace_json(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "t"}))
        (plugin_dir / "marketplace.json").write_text("{bad")
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.invalid")

    def test_plugin_json_missing_name(self, tmp_path):
        _make_claude_plugin(
            tmp_path, {"description": "no name"}, {"name": "t", "plugins": []}
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.name")

    def test_marketplace_json_missing_name(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"plugins": []})
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.name")

    def test_marketplace_missing_plugins(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t"})
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.plugins")

    def test_marketplace_plugins_wrong_type(self, tmp_path):
        _make_claude_plugin(
            tmp_path, {"name": "t"}, {"name": "t", "plugins": "not-a-list"}
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.plugins-type")

    def test_plugin_json_unrecognized_fields(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "unknown_field": "val"},
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.fields")

    def test_consistency_name_mismatch(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "plugin-name"},
            {"name": "marketplace-name", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.consistency.name")

    def test_consistency_name_match(self, tmp_path):
        _make_claude_plugin(
            tmp_path, {"name": "same-name"}, {"name": "same-name", "plugins": []}
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert not _has_check(diags, "3a.consistency.name")

    def test_plugin_json_missing_version(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.version")

    def test_plugin_json_missing_description(self, tmp_path):
        _make_claude_plugin(
            tmp_path, {"name": "t", "version": "1.0"}, {"name": "t", "plugins": []}
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.description")

    def test_plugin_json_author_not_object(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {
                "name": "t",
                "version": "1.0",
                "description": "d",
                "author": "just-a-string",
            },
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.author-type")

    def test_plugin_json_author_missing_name(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {
                "name": "t",
                "version": "1.0",
                "description": "d",
                "author": {"email": "x@y.com"},
            },
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.author-name")

    def test_plugin_json_keywords_not_list(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {
                "name": "t",
                "version": "1.0",
                "description": "d",
                "keywords": "not-a-list",
            },
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(_errors(diags), "3a.plugin-json.keywords-type")

    def test_plugin_json_keywords_non_string_items_error(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d", "keywords": ["ok", 1]},
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(_errors(diags), "3a.plugin-json.keywords-items")

    def test_marketplace_missing_metadata(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.metadata")

    def test_marketplace_metadata_missing_description(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {"name": "t", "metadata": {}, "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.metadata-desc")

    def test_marketplace_missing_owner(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {"name": "t", "metadata": {"description": "d"}, "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.owner")

    def test_marketplace_owner_missing_name(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {"name": "t", "metadata": {"description": "d"}, "owner": {}, "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.owner-name")

    def test_plugin_json_missing_author(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d", "keywords": ["a"]},
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.author")

    def test_plugin_json_missing_keywords(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {
                "name": "t",
                "version": "1.0",
                "description": "d",
                "author": {"name": "X"},
            },
            {"name": "t", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.keywords")

    def test_marketplace_metadata_not_object(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {"name": "t", "metadata": "not-an-object", "plugins": []},
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.metadata-type")
        errors = _errors(diags)
        assert any(d.check == "3a.marketplace-json.metadata-type" for d in errors)

    def test_marketplace_owner_not_object(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {
                "name": "t",
                "metadata": {"description": "d"},
                "owner": "not-an-object",
                "plugins": [],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.owner-type")
        errors = _errors(diags)
        assert any(d.check == "3a.marketplace-json.owner-type" for d in errors)

    def test_marketplace_plugin_missing_source(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {
                "name": "t",
                "metadata": {"description": "d"},
                "owner": {"name": "Test"},
                "plugins": [{"name": "p"}],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.plugin-source")

    def test_marketplace_plugin_source_resolves(self, tmp_path):
        (tmp_path / "skills").mkdir()
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {
                "name": "t",
                "metadata": {"description": "d"},
                "owner": {"name": "Test"},
                "plugins": [{"name": "p", "source": "./skills"}],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert not _has_check(diags, "3a.marketplace-json.plugin-source-missing")

    def test_marketplace_plugin_source_not_string(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {
                "name": "t",
                "metadata": {"description": "d"},
                "owner": {"name": "Test"},
                "plugins": [{"name": "p", "source": 42}],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(_errors(diags), "3a.marketplace-json.plugin-source-type")

    def test_marketplace_plugin_source_missing_dir(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "t", "version": "1.0", "description": "d"},
            {
                "name": "t",
                "metadata": {"description": "d"},
                "owner": {"name": "Test"},
                "plugins": [{"name": "p", "source": "./nonexistent"}],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.plugin-source-missing")

    def test_consistency_description_mismatch(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "same", "version": "1.0", "description": "Plugin desc"},
            {
                "name": "same",
                "metadata": {"description": "Different desc"},
                "plugins": [],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.consistency.description")

    def test_consistency_version_mismatch(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "same", "version": "1.0", "description": "d"},
            {
                "name": "same",
                "version": "2.0",
                "metadata": {"description": "d"},
                "plugins": [],
            },
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.consistency.version")

    def test_known_frontmatter_fields(self):
        adapter = ClaudeAdapter()
        fields = adapter.known_frontmatter_fields()
        assert "agent" in fields
        assert "hooks" in fields
        assert "model" in fields

    def test_allows_tools_list_syntax_false(self):
        adapter = ClaudeAdapter()
        assert not adapter.allows_tools_list_syntax()

    def test_plugin_json_not_object(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps([1, 2, 3]))
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"name": "t", "plugins": []})
        )
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.plugin-json.type")

    def test_marketplace_json_not_object(self, tmp_path):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "t"}))
        (plugin_dir / "marketplace.json").write_text(json.dumps("a string"))
        adapter = ClaudeAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3a.marketplace-json.type")


class TestGeminiAdapter:
    def test_detect_present(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test"})
        adapter = GeminiAdapter()
        assert adapter.detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        adapter = GeminiAdapter()
        assert not adapter.detect(tmp_path)

    def test_valid_extension(self, tmp_path):
        _make_gemini_ext(
            tmp_path,
            {"name": "test-ext", "version": "1.0", "description": "Test extension"},
        )
        (tmp_path / "GEMINI.md").write_text("context")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        errors = _errors(diags)
        assert len(errors) == 0
        warnings = _warnings(diags)
        assert len(warnings) == 0

    def test_missing_version(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test"})
        (tmp_path / "GEMINI.md").write_text("context")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.version")

    def test_missing_description(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test", "version": "1.0"})
        (tmp_path / "GEMINI.md").write_text("context")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.description")

    def test_missing_extension_json(self, tmp_path):
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.missing")

    def test_invalid_json(self, tmp_path):
        (tmp_path / "gemini-extension.json").write_text("{bad")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.invalid")

    def test_not_object(self, tmp_path):
        (tmp_path / "gemini-extension.json").write_text(json.dumps([1, 2]))
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.type")

    def test_missing_name(self, tmp_path):
        _make_gemini_ext(tmp_path, {"description": "no name"})
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.name")

    def test_context_file_missing(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test", "contextFileName": "CUSTOM.md"})
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert _has_check(diags, "3b.gemini-ext.context-missing")

    def test_context_file_present(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test", "contextFileName": "CUSTOM.md"})
        (tmp_path / "CUSTOM.md").write_text("context")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert not _has_check(diags, "3b.gemini-ext.context-missing")

    def test_no_context_no_gemini_md(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test"})
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        infos = _infos(diags)
        assert _has_check(infos, "3b.gemini-ext.no-context")

    def test_no_context_but_gemini_md_exists(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "test"})
        (tmp_path / "GEMINI.md").write_text("context")
        adapter = GeminiAdapter()
        diags = adapter.check(tmp_path, [])
        assert not _has_check(diags, "3b.gemini-ext.no-context")

    def test_known_frontmatter_fields_empty(self):
        adapter = GeminiAdapter()
        assert adapter.known_frontmatter_fields() == set()


def _make_roo_repo(tmp_path):
    (tmp_path / ".roo" / "skills").mkdir(parents=True, exist_ok=True)


def _make_swival_repo(tmp_path, use_toml=False):
    if use_toml:
        (tmp_path / "swival.toml").write_text("")
    else:
        (tmp_path / ".swival").mkdir(parents=True, exist_ok=True)


class TestGetAdapters:
    def test_auto_detect_claude(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "claude" in names
        assert "gemini" not in names

    def test_auto_detect_gemini(self, tmp_path):
        _make_gemini_ext(tmp_path, {"name": "t"})
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "gemini" in names
        assert "claude" not in names

    def test_auto_detect_both(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        _make_gemini_ext(tmp_path, {"name": "t"})
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "claude" in names
        assert "gemini" in names

    def test_auto_detect_codex(self, tmp_path):
        _make_codex_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "codex" in names
        assert "claude" not in names

    def test_auto_detect_none(self, tmp_path):
        adapters = get_adapters(None, tmp_path)
        assert len(adapters) == 0

    def test_auto_detect_copilot(self, tmp_path):
        _make_copilot_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "copilot" in names
        assert "claude" not in names

    def test_explicit_all(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        _make_gemini_ext(tmp_path, {"name": "t"})
        _make_codex_repo(tmp_path)
        _make_copilot_repo(tmp_path)
        _make_cursor_repo(tmp_path)
        _make_windsurf_repo(tmp_path)
        _make_roo_repo(tmp_path)
        _make_swival_repo(tmp_path)
        adapters = get_adapters(["all"], tmp_path)
        assert len(adapters) == len(ALL_ADAPTERS)

    def test_explicit_all_only_detected(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        adapters = get_adapters(["all"], tmp_path)
        names = [a.name for a in adapters]
        assert "claude" in names
        assert "gemini" not in names

    def test_explicit_names(self, tmp_path):
        adapters = get_adapters(["claude"], tmp_path)
        assert len(adapters) == 1
        assert adapters[0].name == "claude"

    def test_explicit_unknown_name_ignored(self, tmp_path):
        adapters = get_adapters(["nonexistent"], tmp_path)
        assert len(adapters) == 0


class TestCrossAgentCheck:
    def test_consistent_metadata(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "my-skill", "version": "1.0.0", "description": "A skill"},
            {"name": "my-skill", "plugins": []},
        )
        _make_gemini_ext(
            tmp_path, {"name": "my-skill", "version": "1.0.0", "description": "A skill"}
        )
        adapters = get_adapters(["all"], tmp_path)
        diags = cross_agent_check(tmp_path, adapters)
        assert not _has_check(diags, "3c.name-mismatch")
        assert not _has_check(diags, "3c.version-mismatch")
        assert not _has_check(diags, "3c.description-mismatch")

    def test_inconsistent_names(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "claude-name", "version": "1.0.0"},
            {"name": "claude-name", "plugins": []},
        )
        _make_gemini_ext(tmp_path, {"name": "gemini-name", "version": "1.0.0"})
        adapters = get_adapters(["all"], tmp_path)
        diags = cross_agent_check(tmp_path, adapters)
        assert _has_check(diags, "3c.name-mismatch")

    def test_inconsistent_versions(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "same", "version": "1.0.0"},
            {"name": "same", "plugins": []},
        )
        _make_gemini_ext(tmp_path, {"name": "same", "version": "2.0.0"})
        adapters = get_adapters(["all"], tmp_path)
        diags = cross_agent_check(tmp_path, adapters)
        assert _has_check(diags, "3c.version-mismatch")

    def test_inconsistent_descriptions(self, tmp_path):
        _make_claude_plugin(
            tmp_path,
            {"name": "same", "description": "Claude description"},
            {"name": "same", "plugins": []},
        )
        _make_gemini_ext(
            tmp_path, {"name": "same", "description": "Gemini description"}
        )
        adapters = get_adapters(["all"], tmp_path)
        diags = cross_agent_check(tmp_path, adapters)
        assert _has_check(diags, "3c.description-mismatch")

    def test_single_adapter_no_cross_check(self, tmp_path):
        _make_claude_plugin(tmp_path, {"name": "t"}, {"name": "t", "plugins": []})
        adapters = get_adapters(["claude"], tmp_path)
        diags = cross_agent_check(tmp_path, adapters)
        assert len(diags) == 0


def _make_skill(tmp_path, name="my-skill", openai_yaml=None):
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {name}\ndescription: A test skill\n---\n# {name}\n"
    )
    if openai_yaml is not None:
        agents_dir = skill_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        (agents_dir / "openai.yaml").write_text(yaml.dump(openai_yaml))
    return SkillInfo(
        dir_name=name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
        frontmatter={"name": name, "description": "A test skill"},
        body=f"# {name}\n",
    )


def _make_codex_repo(tmp_path):
    (tmp_path / ".codex").mkdir(exist_ok=True)


class TestCodexAdapter:
    def test_detect_present(self, tmp_path):
        _make_codex_repo(tmp_path)
        assert CodexAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not CodexAdapter().detect(tmp_path)

    def test_no_openai_yaml_is_fine(self, tmp_path):
        skill = _make_skill(tmp_path)
        diags = CodexAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_valid_openai_yaml(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={
                "interface": {
                    "display_name": "My Skill",
                    "short_description": "Does things",
                    "default_prompt": "Do the thing",
                },
                "policy": {"allow_implicit_invocation": True},
            },
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0
        assert len(_warnings(diags)) == 0

    def test_invalid_yaml(self, tmp_path):
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-yaml\ndescription: x\n---\n"
        )
        agents_dir = skill_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "openai.yaml").write_text("{: invalid yaml")
        skill = SkillInfo(
            dir_name="bad-yaml",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter={"name": "bad-yaml", "description": "x"},
            body="",
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.invalid")

    def test_not_mapping(self, tmp_path):
        skill_dir = tmp_path / "not-map"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: not-map\ndescription: x\n---\n")
        agents_dir = skill_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "openai.yaml").write_text("- a list\n- not a map\n")
        skill = SkillInfo(
            dir_name="not-map",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter={"name": "not-map", "description": "x"},
            body="",
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.type")

    def test_unknown_top_level_fields(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"custom_thing": "val"})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.unknown-fields")

    def test_interface_not_mapping(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"interface": "nope"})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.interface-type")

    def test_interface_field_wrong_type(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"interface": {"display_name": 42}})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.interface-display_name-type")

    def test_interface_unknown_fields(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"interface": {"display_name": "OK", "custom": "val"}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.interface-unknown")

    def test_dependencies_not_mapping(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"dependencies": "nope"})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.dependencies-type")

    def test_dependencies_tools_not_list(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"dependencies": {"tools": "not-a-list"}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.dependencies-tools-type")

    def test_tool_not_mapping(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"dependencies": {"tools": ["not-a-dict"]}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.tool-type")

    def test_tool_missing_type_and_value(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={"dependencies": {"tools": [{"description": "something"}]}},
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.tool-missing-type")
        assert _has_check(diags, "3d.openai-yaml.tool-missing-value")

    def test_tool_unknown_type(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={"dependencies": {"tools": [{"type": "magic", "value": "x"}]}},
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.tool-unknown-type")

    def test_tool_valid(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={
                "dependencies": {
                    "tools": [
                        {"type": "cli", "value": "gh", "description": "GitHub CLI"},
                        {"type": "env_var", "value": "GITHUB_TOKEN"},
                    ]
                }
            },
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0
        assert len(_warnings(diags)) == 0

    def test_tool_unknown_fields(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={
                "dependencies": {
                    "tools": [{"type": "cli", "value": "gh", "extra": "field"}]
                }
            },
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.tool-unknown-fields")

    def test_policy_not_mapping(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"policy": "nope"})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.policy-type")

    def test_policy_aii_wrong_type(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"policy": {"allow_implicit_invocation": "yes"}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.policy-aii-type")

    def test_policy_valid(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"policy": {"allow_implicit_invocation": False}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0

    def test_permissions_not_mapping(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"permissions": "nope"})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-type")

    def test_permissions_unknown_fields(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"permissions": {"custom_perm": True}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(diags, "3d.openai-yaml.permissions-unknown")

    def test_permissions_network_not_mapping(self, tmp_path):
        skill = _make_skill(tmp_path, openai_yaml={"permissions": {"network": "yes"}})
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-network-type")

    def test_permissions_fs_not_mapping(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"permissions": {"file_system": "all"}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-fs-type")

    def test_permissions_fs_read_not_list(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"permissions": {"file_system": {"read": "./src"}}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-fs-read-type")

    def test_permissions_fs_write_not_list(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"permissions": {"file_system": {"write": "/tmp"}}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-fs-write-type")

    def test_permissions_macos_not_mapping(self, tmp_path):
        skill = _make_skill(
            tmp_path, openai_yaml={"permissions": {"macos": "read_only"}}
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3d.openai-yaml.permissions-macos-type")

    def test_permissions_valid(self, tmp_path):
        skill = _make_skill(
            tmp_path,
            openai_yaml={
                "permissions": {
                    "network": {"enabled": True},
                    "file_system": {"read": ["./src"], "write": ["./out"]},
                    "macos": {"macos_preferences": "read_only"},
                }
            },
        )
        diags = CodexAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0

    def test_detect_agents_dir(self, tmp_path):
        (tmp_path / ".agents").mkdir()
        assert CodexAdapter().detect(tmp_path)

    def test_detect_both_dirs(self, tmp_path):
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".agents").mkdir()
        assert CodexAdapter().detect(tmp_path)

    def test_known_frontmatter_fields_empty(self):
        assert CodexAdapter().known_frontmatter_fields() == set()

    def test_allows_tools_list_syntax_false(self):
        assert not CodexAdapter().allows_tools_list_syntax()


def _make_copilot_repo(tmp_path):
    (tmp_path / ".github" / "skills").mkdir(parents=True, exist_ok=True)


def _make_copilot_skill(tmp_path, name="my-skill", frontmatter=None):
    skill_dir = tmp_path / ".github" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = frontmatter or {"name": name, "description": "A test skill"}
    fm_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\n{fm_lines}\n---\n# {name}\n")
    return SkillInfo(
        dir_name=name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
        frontmatter=fm,
        body=f"# {name}\n",
    )


class TestCopilotAdapter:
    def test_detect_present(self, tmp_path):
        _make_copilot_repo(tmp_path)
        assert CopilotAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not CopilotAdapter().detect(tmp_path)

    def test_detect_github_without_skills(self, tmp_path):
        (tmp_path / ".github").mkdir()
        assert not CopilotAdapter().detect(tmp_path)

    def test_known_frontmatter_fields(self):
        fields = CopilotAdapter().known_frontmatter_fields()
        assert "argument-hint" in fields
        assert "user-invocable" in fields
        assert "disable-model-invocation" in fields

    def test_allows_tools_list_syntax_false(self):
        assert not CopilotAdapter().allows_tools_list_syntax()

    def test_valid_skill_no_diags(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "user-invocable": True,
                "argument-hint": "Enter a prompt",
                "disable-model-invocation": False,
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_user_invocable_wrong_type(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "user-invocable": "yes",
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3e.frontmatter.user-invocable-type")

    def test_disable_model_invocation_wrong_type(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "disable-model-invocation": "true",
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert _has_check(
            _errors(diags), "3e.frontmatter.disable-model-invocation-type"
        )

    def test_argument_hint_wrong_type(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "argument-hint": 42,
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3e.frontmatter.argument-hint-type")

    def test_no_extension_fields_no_diags(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_multiple_type_errors(self, tmp_path):
        skill = _make_copilot_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "user-invocable": "yes",
                "argument-hint": 123,
                "disable-model-invocation": "no",
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        errors = _errors(diags)
        assert len(errors) == 3

    def test_multiple_skills(self, tmp_path):
        skill1 = _make_copilot_skill(
            tmp_path,
            name="skill-a",
            frontmatter={
                "name": "skill-a",
                "description": "First",
                "user-invocable": "bad",
            },
        )
        skill2 = _make_copilot_skill(
            tmp_path,
            name="skill-b",
            frontmatter={
                "name": "skill-b",
                "description": "Second",
                "argument-hint": 99,
            },
        )
        diags = CopilotAdapter().check(tmp_path, [skill1, skill2])
        errors = _errors(diags)
        assert len(errors) == 2

    def test_none_frontmatter_no_crash(self, tmp_path):
        _make_copilot_repo(tmp_path)
        skill_dir = tmp_path / ".github" / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("no frontmatter at all")
        skill = SkillInfo(
            dir_name="broken",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter=None,
            parse_error="missing frontmatter",
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_non_copilot_skill_ignored(self, tmp_path):
        _make_copilot_repo(tmp_path)
        other_dir = tmp_path / "other-skill"
        other_dir.mkdir()
        (other_dir / "SKILL.md").write_text(
            "---\nname: other\ndescription: x\nuser-invocable: nope\n---\n"
        )
        skill = SkillInfo(
            dir_name="other-skill",
            dir_path=str(other_dir),
            skill_md_path=str(other_dir / "SKILL.md"),
            frontmatter={"name": "other", "description": "x", "user-invocable": "nope"},
            body="",
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_copilot_skill_checked_non_copilot_skipped(self, tmp_path):
        copilot_skill = _make_copilot_skill(
            tmp_path,
            name="cop-skill",
            frontmatter={
                "name": "cop-skill",
                "description": "Copilot skill",
                "user-invocable": "bad",
            },
        )
        other_dir = tmp_path / "root-skill"
        other_dir.mkdir()
        other_skill = SkillInfo(
            dir_name="root-skill",
            dir_path=str(other_dir),
            skill_md_path=str(other_dir / "SKILL.md"),
            frontmatter={
                "name": "root-skill",
                "description": "x",
                "user-invocable": "also bad",
            },
            body="",
        )
        diags = CopilotAdapter().check(tmp_path, [copilot_skill, other_skill])
        errors = _errors(diags)
        assert len(errors) == 1
        assert "cop-skill" in errors[0].path

    def test_skills_extra_dir_not_matched(self, tmp_path):
        _make_copilot_repo(tmp_path)
        extra_dir = tmp_path / ".github" / "skills-extra" / "not-copilot"
        extra_dir.mkdir(parents=True)
        skill = SkillInfo(
            dir_name="not-copilot",
            dir_path=str(extra_dir),
            skill_md_path=str(extra_dir / "SKILL.md"),
            frontmatter={
                "name": "not-copilot",
                "description": "x",
                "user-invocable": "bad",
            },
            body="",
        )
        diags = CopilotAdapter().check(tmp_path, [skill])
        assert len(diags) == 0


def _make_cursor_repo(tmp_path):
    (tmp_path / ".cursor" / "skills").mkdir(parents=True, exist_ok=True)


def _make_cursor_skill(tmp_path, name="my-skill", frontmatter=None, under_agents=False):
    if under_agents:
        skill_dir = tmp_path / ".agents" / "skills" / name
    else:
        skill_dir = tmp_path / ".cursor" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = frontmatter or {"name": name, "description": "A test skill"}
    fm_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\n{fm_lines}\n---\n# {name}\n")
    return SkillInfo(
        dir_name=name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
        frontmatter=fm,
        body=f"# {name}\n",
    )


class TestCursorAdapter:
    def test_detect_present(self, tmp_path):
        _make_cursor_repo(tmp_path)
        assert CursorAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not CursorAdapter().detect(tmp_path)

    def test_detect_cursor_dir_without_skills(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        assert CursorAdapter().detect(tmp_path)

    def test_detect_agents_skills_only(self, tmp_path):
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        assert CursorAdapter().detect(tmp_path)

    def test_known_frontmatter_fields(self):
        fields = CursorAdapter().known_frontmatter_fields()
        assert "disable-model-invocation" in fields

    def test_allows_tools_list_syntax_false(self):
        assert not CursorAdapter().allows_tools_list_syntax()

    def test_valid_skill_no_diags(self, tmp_path):
        skill = _make_cursor_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "disable-model-invocation": True,
            },
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_disable_model_invocation_wrong_type(self, tmp_path):
        skill = _make_cursor_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "disable-model-invocation": "true",
            },
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert _has_check(
            _errors(diags), "3f.frontmatter.disable-model-invocation-type"
        )

    def test_no_extension_fields_no_diags(self, tmp_path):
        skill = _make_cursor_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
            },
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_none_frontmatter_no_crash(self, tmp_path):
        _make_cursor_repo(tmp_path)
        skill_dir = tmp_path / ".cursor" / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("no frontmatter at all")
        skill = SkillInfo(
            dir_name="broken",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter=None,
            parse_error="missing frontmatter",
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_skill_under_agents_dir(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        skill = _make_cursor_skill(
            tmp_path,
            name="agents-skill",
            frontmatter={
                "name": "agents-skill",
                "description": "In .agents/skills/",
                "disable-model-invocation": "yes",
            },
            under_agents=True,
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert _has_check(
            _errors(diags), "3f.frontmatter.disable-model-invocation-type"
        )

    def test_non_cursor_skill_ignored(self, tmp_path):
        _make_cursor_repo(tmp_path)
        other_dir = tmp_path / "other-skill"
        other_dir.mkdir()
        skill = SkillInfo(
            dir_name="other-skill",
            dir_path=str(other_dir),
            skill_md_path=str(other_dir / "SKILL.md"),
            frontmatter={
                "name": "other",
                "description": "x",
                "disable-model-invocation": "bad",
            },
            body="",
        )
        diags = CursorAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0

    def test_cursorrules_deprecated_warning(self, tmp_path):
        _make_cursor_repo(tmp_path)
        (tmp_path / ".cursorrules").write_text("some old rules")
        diags = CursorAdapter().check(tmp_path, [])
        assert _has_check(_warnings(diags), "3f.cursorrules-deprecated")

    def test_no_cursorrules_no_warning(self, tmp_path):
        _make_cursor_repo(tmp_path)
        diags = CursorAdapter().check(tmp_path, [])
        assert not _has_check(_warnings(diags), "3f.cursorrules-deprecated")

    def test_auto_detect_cursor(self, tmp_path):
        _make_cursor_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "cursor" in names
        assert "claude" not in names


def _make_windsurf_repo(tmp_path):
    (tmp_path / ".windsurf").mkdir(parents=True, exist_ok=True)


class TestWindsurfAdapter:
    def test_detect_present(self, tmp_path):
        _make_windsurf_repo(tmp_path)
        assert WindsurfAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not WindsurfAdapter().detect(tmp_path)

    def test_detect_agents_skills_only(self, tmp_path):
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        assert WindsurfAdapter().detect(tmp_path)

    def test_detect_windsurfrules_only(self, tmp_path):
        (tmp_path / ".windsurfrules").write_text("legacy rules")
        assert WindsurfAdapter().detect(tmp_path)

    def test_known_frontmatter_fields_empty(self):
        assert WindsurfAdapter().known_frontmatter_fields() == set()

    def test_allows_tools_list_syntax_false(self):
        assert not WindsurfAdapter().allows_tools_list_syntax()

    def test_no_diags_clean_repo(self, tmp_path):
        _make_windsurf_repo(tmp_path)
        diags = WindsurfAdapter().check(tmp_path, [])
        assert len(diags) == 0

    def test_windsurfrules_deprecated_warning(self, tmp_path):
        _make_windsurf_repo(tmp_path)
        (tmp_path / ".windsurfrules").write_text("some old rules")
        diags = WindsurfAdapter().check(tmp_path, [])
        assert _has_check(_warnings(diags), "3g.windsurfrules-deprecated")

    def test_no_windsurfrules_no_warning(self, tmp_path):
        _make_windsurf_repo(tmp_path)
        diags = WindsurfAdapter().check(tmp_path, [])
        assert not _has_check(diags, "3g.windsurfrules-deprecated")

    def test_auto_detect_windsurf(self, tmp_path):
        _make_windsurf_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "windsurf" in names
        assert "claude" not in names


def _make_roo_skill(
    tmp_path, name="my-skill", frontmatter=None, under_agents=False, mode=None
):
    if under_agents:
        skill_dir = tmp_path / ".agents" / "skills" / name
    elif mode:
        skill_dir = tmp_path / ".roo" / f"skills-{mode}" / name
    else:
        skill_dir = tmp_path / ".roo" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = frontmatter or {"name": name, "description": "A test skill"}
    fm_lines = []
    for k, v in fm.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}:")
            for item in v:
                fm_lines.append(f"  - {item}")
        elif isinstance(v, bool):
            fm_lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            fm_lines.append(f"{k}: {v}")
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\n" + "\n".join(fm_lines) + f"\n---\n# {name}\n")
    return SkillInfo(
        dir_name=name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
        frontmatter=fm,
        body=f"# {name}\n",
    )


class TestRooAdapter:
    def test_detect_roo_dir(self, tmp_path):
        (tmp_path / ".roo").mkdir()
        assert RooAdapter().detect(tmp_path)

    def test_detect_roomodes(self, tmp_path):
        (tmp_path / ".roomodes").write_text("{}")
        assert RooAdapter().detect(tmp_path)

    def test_detect_roorules(self, tmp_path):
        (tmp_path / ".roorules").write_text("rules")
        assert RooAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not RooAdapter().detect(tmp_path)

    def test_known_frontmatter_fields(self):
        fields = RooAdapter().known_frontmatter_fields()
        assert "modeSlugs" in fields
        assert "mode" in fields

    def test_allows_tools_list_syntax_false(self):
        assert not RooAdapter().allows_tools_list_syntax()

    def test_valid_skill_no_diags(self, tmp_path):
        skill = _make_roo_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "modeSlugs": ["code", "debug"],
            },
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_mode_slugs_wrong_type(self, tmp_path):
        skill = _make_roo_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "modeSlugs": "code",
            },
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3h.frontmatter.modeSlugs-type")

    def test_mode_wrong_type(self, tmp_path):
        skill = _make_roo_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "mode": 42,
            },
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3h.frontmatter.mode-type")

    def test_mode_deprecated_info(self, tmp_path):
        skill = _make_roo_skill(
            tmp_path,
            frontmatter={
                "name": "my-skill",
                "description": "A test skill",
                "mode": "code",
            },
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_infos(diags), "3h.frontmatter.mode-deprecated")

    def test_roorules_deprecated_warning(self, tmp_path):
        _make_roo_repo(tmp_path)
        (tmp_path / ".roorules").write_text("old rules")
        diags = RooAdapter().check(tmp_path, [])
        assert _has_check(_warnings(diags), "3h.roorules-deprecated")

    def test_clinerules_deprecated_warning(self, tmp_path):
        _make_roo_repo(tmp_path)
        (tmp_path / ".clinerules").write_text("cline rules")
        diags = RooAdapter().check(tmp_path, [])
        assert _has_check(_warnings(diags), "3h.clinerules-deprecated")

    def test_no_deprecated_files_no_warning(self, tmp_path):
        _make_roo_repo(tmp_path)
        diags = RooAdapter().check(tmp_path, [])
        assert len(_warnings(diags)) == 0

    def test_skill_under_agents_dir(self, tmp_path):
        (tmp_path / ".roo").mkdir()
        skill = _make_roo_skill(
            tmp_path,
            name="agents-skill",
            frontmatter={
                "name": "agents-skill",
                "description": "In .agents/skills/",
                "modeSlugs": "not-a-list",
            },
            under_agents=True,
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3h.frontmatter.modeSlugs-type")

    def test_skill_under_mode_specific_dir(self, tmp_path):
        _make_roo_repo(tmp_path)
        skill = _make_roo_skill(
            tmp_path,
            name="code-skill",
            frontmatter={
                "name": "code-skill",
                "description": "In .roo/skills-code/",
                "modeSlugs": "not-a-list",
            },
            mode="code",
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_errors(diags), "3h.frontmatter.modeSlugs-type")

    def test_skill_under_agents_mode_dir(self, tmp_path):
        (tmp_path / ".roo").mkdir()
        skill_dir = tmp_path / ".agents" / "skills-debug" / "dbg"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: dbg\ndescription: test\nmode: debug\n---\nbody\n"
        )
        skill = SkillInfo(
            dir_name="dbg",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter={"name": "dbg", "description": "test", "mode": "debug"},
            body="body\n",
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert _has_check(_infos(diags), "3h.frontmatter.mode-deprecated")

    def test_non_roo_skill_ignored(self, tmp_path):
        _make_roo_repo(tmp_path)
        other_dir = tmp_path / "other-skill"
        other_dir.mkdir()
        skill = SkillInfo(
            dir_name="other-skill",
            dir_path=str(other_dir),
            skill_md_path=str(other_dir / "SKILL.md"),
            frontmatter={
                "name": "other",
                "description": "x",
                "modeSlugs": "bad",
            },
            body="",
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert len(_errors(diags)) == 0

    def test_none_frontmatter_no_crash(self, tmp_path):
        _make_roo_repo(tmp_path)
        skill_dir = tmp_path / ".roo" / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("no frontmatter")
        skill = SkillInfo(
            dir_name="broken",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter=None,
            parse_error="missing frontmatter",
        )
        diags = RooAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_auto_detect_roo(self, tmp_path):
        _make_roo_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "roo" in names
        assert "claude" not in names


def _make_swival_skill(tmp_path, name="my-skill", frontmatter=None, body=None):
    skill_dir = tmp_path / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = frontmatter or {"name": name, "description": "A test skill"}
    fm_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    body_text = body if body is not None else f"# {name}\n"
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\n{fm_lines}\n---\n{body_text}")
    return SkillInfo(
        dir_name=name,
        dir_path=str(skill_dir),
        skill_md_path=str(skill_md),
        frontmatter=fm,
        body=body_text,
    )


class TestSwivalAdapter:
    def test_detect_swival_dir(self, tmp_path):
        (tmp_path / ".swival").mkdir()
        assert SwivalAdapter().detect(tmp_path)

    def test_detect_swival_toml(self, tmp_path):
        (tmp_path / "swival.toml").write_text("")
        assert SwivalAdapter().detect(tmp_path)

    def test_detect_absent(self, tmp_path):
        assert not SwivalAdapter().detect(tmp_path)

    def test_known_frontmatter_fields_empty(self):
        assert SwivalAdapter().known_frontmatter_fields() == set()

    def test_allows_tools_list_syntax_false(self):
        assert not SwivalAdapter().allows_tools_list_syntax()

    def test_valid_skill_no_diags(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill = _make_swival_skill(tmp_path)
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_description_over_1024_warns(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill = _make_swival_skill(
            tmp_path,
            frontmatter={
                "name": "verbose",
                "description": "x" * 1025,
            },
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert _has_check(_warnings(diags), "3i.description-length")

    def test_description_at_1024_ok(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill = _make_swival_skill(
            tmp_path,
            frontmatter={
                "name": "just-right",
                "description": "x" * 1024,
            },
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert not _has_check(diags, "3i.description-length")

    def test_body_over_20000_warns(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill = _make_swival_skill(
            tmp_path,
            body="a" * 20001,
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert _has_check(_warnings(diags), "3i.body-length")

    def test_body_at_20000_ok(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill = _make_swival_skill(
            tmp_path,
            body="a" * 20000,
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert not _has_check(diags, "3i.body-length")

    def test_external_skill_still_checked(self, tmp_path):
        _make_swival_repo(tmp_path)
        other_dir = tmp_path / "custom-skills" / "verbose"
        other_dir.mkdir(parents=True)
        skill = SkillInfo(
            dir_name="verbose",
            dir_path=str(other_dir),
            skill_md_path=str(other_dir / "SKILL.md"),
            frontmatter={"name": "verbose", "description": "x" * 1025},
            body="a" * 20001,
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert _has_check(_warnings(diags), "3i.description-length")
        assert _has_check(_warnings(diags), "3i.body-length")

    def test_none_frontmatter_no_crash(self, tmp_path):
        _make_swival_repo(tmp_path)
        skill_dir = tmp_path / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("no frontmatter")
        skill = SkillInfo(
            dir_name="broken",
            dir_path=str(skill_dir),
            skill_md_path=str(skill_dir / "SKILL.md"),
            frontmatter=None,
            parse_error="missing frontmatter",
        )
        diags = SwivalAdapter().check(tmp_path, [skill])
        assert len(diags) == 0

    def test_detect_with_toml(self, tmp_path):
        _make_swival_repo(tmp_path, use_toml=True)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "swival" in names

    def test_auto_detect_swival(self, tmp_path):
        _make_swival_repo(tmp_path)
        adapters = get_adapters(None, tmp_path)
        names = [a.name for a in adapters]
        assert "swival" in names
        assert "claude" not in names

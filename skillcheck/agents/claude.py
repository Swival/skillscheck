"""Claude Code agent adapter (3a)."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Diagnostic, Level, SkillInfo
from ._util import load_json_object

EXTENSION_FIELDS = {
    "disable-model-invocation",
    "user-invocable",
    "argument-hint",
    "model",
    "context",
    "agent",
    "hooks",
}

PLUGIN_JSON_ALLOWED_FIELDS = {
    "name",
    "description",
    "version",
    "author",
    "keywords",
    "license",
    "repository",
    "homepage",
}


class ClaudeAdapter:
    name = "claude"
    source_url = "https://code.claude.com/docs/en/skills"

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / ".claude-plugin").is_dir()

    def known_frontmatter_fields(self) -> set[str]:
        return EXTENSION_FIELDS

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        plugin_dir = repo_root / ".claude-plugin"

        diags.extend(self._check_plugin_json(plugin_dir))
        diags.extend(self._check_marketplace_json(plugin_dir, root=repo_root))
        diags.extend(self._check_consistency(plugin_dir))
        return diags

    def _check_plugin_json(self, plugin_dir: Path) -> list[Diagnostic]:
        path = plugin_dir / "plugin.json"
        data, diags = load_json_object(
            path, "3a.plugin-json", "plugin.json", self.source_url
        )
        if data is None:
            return diags

        if "name" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.name",
                    "plugin.json missing 'name' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        if "version" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.version",
                    "plugin.json missing 'version' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        if "description" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.description",
                    "plugin.json missing 'description' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        author = data.get("author")
        if author is None:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.author",
                    "plugin.json missing 'author' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not isinstance(author, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.plugin-json.author-type",
                    "plugin.json 'author' must be an object with a 'name' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif "name" not in author:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.author-name",
                    "plugin.json 'author' object missing 'name' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        keywords = data.get("keywords")
        if keywords is None:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.keywords",
                    "plugin.json missing 'keywords' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not isinstance(keywords, list):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.plugin-json.keywords-type",
                    "plugin.json 'keywords' must be an array of strings",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not all(isinstance(k, str) for k in keywords):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.plugin-json.keywords-items",
                    "plugin.json 'keywords' array must contain only strings",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        bad_fields = set(data.keys()) - PLUGIN_JSON_ALLOWED_FIELDS
        if bad_fields:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.plugin-json.fields",
                    f"plugin.json has unrecognized fields: {', '.join(sorted(bad_fields))}",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        return diags

    def _check_marketplace_json(self, plugin_dir: Path, root: Path) -> list[Diagnostic]:
        path = plugin_dir / "marketplace.json"
        data, diags = load_json_object(
            path, "3a.marketplace-json", "marketplace.json", self.source_url
        )
        if data is None:
            return diags

        if "name" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.marketplace-json.name",
                    "marketplace.json missing 'name' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )

        metadata = data.get("metadata")
        if metadata is None:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.marketplace-json.metadata",
                    "marketplace.json missing 'metadata' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not isinstance(metadata, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.marketplace-json.metadata-type",
                    "marketplace.json 'metadata' must be an object",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        else:
            if "description" not in metadata:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "3a.marketplace-json.metadata-desc",
                        "marketplace.json 'metadata' missing 'description' field",
                        path=str(path),
                        source_url=self.source_url,
                    )
                )

        owner = data.get("owner")
        if owner is None:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.marketplace-json.owner",
                    "marketplace.json missing 'owner' field",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not isinstance(owner, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.marketplace-json.owner-type",
                    "marketplace.json 'owner' must be an object",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        else:
            if "name" not in owner:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "3a.marketplace-json.owner-name",
                        "marketplace.json 'owner' missing 'name' field",
                        path=str(path),
                        source_url=self.source_url,
                    )
                )

        if "plugins" not in data:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.marketplace-json.plugins",
                    "marketplace.json missing 'plugins' array",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        elif not isinstance(data["plugins"], list):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3a.marketplace-json.plugins-type",
                    "'plugins' must be an array",
                    path=str(path),
                    source_url=self.source_url,
                )
            )
        else:
            for i, plugin in enumerate(data["plugins"]):
                if not isinstance(plugin, dict):
                    diags.append(
                        Diagnostic(
                            Level.ERROR,
                            "3a.marketplace-json.plugin-type",
                            f"plugins[{i}] must be an object",
                            path=str(path),
                            source_url=self.source_url,
                        )
                    )
                    continue
                source = plugin.get("source")
                if source is None:
                    diags.append(
                        Diagnostic(
                            Level.WARNING,
                            "3a.marketplace-json.plugin-source",
                            f"plugins[{i}] missing 'source' field",
                            path=str(path),
                            source_url=self.source_url,
                        )
                    )
                elif not isinstance(source, str):
                    diags.append(
                        Diagnostic(
                            Level.ERROR,
                            "3a.marketplace-json.plugin-source-type",
                            f"plugins[{i}] 'source' must be a string, got {type(source).__name__}",
                            path=str(path),
                            source_url=self.source_url,
                        )
                    )
                else:
                    resolved = (root / source).resolve()
                    if not resolved.is_dir():
                        diags.append(
                            Diagnostic(
                                Level.ERROR,
                                "3a.marketplace-json.plugin-source-missing",
                                f"plugins[{i}] source '{source}' does not resolve to a directory",
                                path=str(path),
                                source_url=self.source_url,
                            )
                        )

        return diags

    def _check_consistency(self, plugin_dir: Path) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        pj = plugin_dir / "plugin.json"
        mj = plugin_dir / "marketplace.json"

        if not pj.exists() or not mj.exists():
            return diags

        try:
            pj_data = json.loads(pj.read_text())
            mj_data = json.loads(mj.read_text())
        except (json.JSONDecodeError, OSError):
            return diags

        if not isinstance(pj_data, dict) or not isinstance(mj_data, dict):
            return diags

        pj_name = pj_data.get("name", "")
        mj_name = mj_data.get("name", "")
        if pj_name and mj_name and pj_name != mj_name:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.consistency.name",
                    f"name mismatch: plugin.json='{pj_name}' marketplace.json='{mj_name}'",
                    path=str(plugin_dir),
                    source_url=self.source_url,
                )
            )

        pj_desc = pj_data.get("description", "")
        mj_meta = mj_data.get("metadata", {})
        mj_desc = mj_meta.get("description", "") if isinstance(mj_meta, dict) else ""
        if pj_desc and mj_desc and pj_desc != mj_desc:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.consistency.description",
                    "description mismatch: plugin.json vs marketplace.json metadata.description",
                    path=str(plugin_dir),
                    source_url=self.source_url,
                )
            )

        pj_version = pj_data.get("version", "")
        mj_version = mj_data.get("version", "")
        if pj_version and mj_version and pj_version != mj_version:
            diags.append(
                Diagnostic(
                    Level.WARNING,
                    "3a.consistency.version",
                    f"version mismatch: plugin.json='{pj_version}' marketplace.json='{mj_version}'",
                    path=str(plugin_dir),
                    source_url=self.source_url,
                )
            )

        return diags

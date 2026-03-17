"""OpenAI Codex agent adapter (3d).

Each skill can have an optional agents/openai.yaml sidecar with interface,
dependencies, policy, and permissions metadata.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..models import Diagnostic, Level, SkillInfo

CODEX_SOURCE_URL = "https://github.com/openai/codex"

INTERFACE_FIELDS = {
    "display_name",
    "short_description",
    "icon_small",
    "icon_large",
    "brand_color",
    "default_prompt",
}

TOOL_DEP_TYPES = {"env_var", "cli", "mcp"}
TOOL_DEP_FIELDS = {"type", "value", "description", "transport", "command", "url"}

PERMISSIONS_FIELDS = {"network", "file_system", "macos"}

TOP_LEVEL_FIELDS = {"interface", "dependencies", "policy", "permissions"}


class CodexAdapter:
    name = "codex"
    source_url = CODEX_SOURCE_URL

    def detect(self, repo_root: Path) -> bool:
        return (repo_root / ".codex").is_dir() or (repo_root / ".agents").is_dir()

    def known_frontmatter_fields(self) -> set[str]:
        return set()

    def allows_tools_list_syntax(self) -> bool:
        return False

    def check(self, repo_root: Path, skills: list[SkillInfo]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        for skill in skills:
            diags.extend(self._check_openai_yaml(skill))
        return diags

    def _check_openai_yaml(self, skill: SkillInfo) -> list[Diagnostic]:
        yaml_path = Path(skill.dir_path) / "agents" / "openai.yaml"
        if not yaml_path.exists():
            return []

        diags: list[Diagnostic] = []
        path_str = str(yaml_path)

        try:
            data = yaml.safe_load(yaml_path.read_text())
        except yaml.YAMLError as e:
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.invalid",
                    f"invalid YAML: {e}",
                    path=path_str,
                    source_url=self.source_url,
                )
            )
            return diags

        if not isinstance(data, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.type",
                    "openai.yaml must be a YAML mapping",
                    path=path_str,
                    source_url=self.source_url,
                )
            )
            return diags

        unknown = set(data.keys()) - TOP_LEVEL_FIELDS
        if unknown:
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "3d.openai-yaml.unknown-fields",
                    f"unrecognized top-level fields: {', '.join(sorted(unknown))}",
                    path=path_str,
                    source_url=self.source_url,
                )
            )

        diags.extend(self._check_interface(data.get("interface"), path_str))
        diags.extend(self._check_dependencies(data.get("dependencies"), path_str))
        diags.extend(self._check_policy(data.get("policy"), path_str))
        diags.extend(self._check_permissions(data.get("permissions"), path_str))

        return diags

    def _check_interface(self, iface, path: str) -> list[Diagnostic]:
        if iface is None:
            return []
        diags: list[Diagnostic] = []
        if not isinstance(iface, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.interface-type",
                    "'interface' must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )
            return diags

        unknown = set(iface.keys()) - INTERFACE_FIELDS
        if unknown:
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "3d.openai-yaml.interface-unknown",
                    f"unrecognized interface fields: {', '.join(sorted(unknown))}",
                    path=path,
                    source_url=self.source_url,
                )
            )

        for field in INTERFACE_FIELDS:
            val = iface.get(field)
            if val is not None and not isinstance(val, str):
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        f"3d.openai-yaml.interface-{field}-type",
                        f"interface.{field} must be a string",
                        path=path,
                        source_url=self.source_url,
                    )
                )

        return diags

    def _check_dependencies(self, deps, path: str) -> list[Diagnostic]:
        if deps is None:
            return []
        diags: list[Diagnostic] = []
        if not isinstance(deps, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.dependencies-type",
                    "'dependencies' must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )
            return diags

        tools = deps.get("tools")
        if tools is None:
            return diags
        if not isinstance(tools, list):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.dependencies-tools-type",
                    "'dependencies.tools' must be a list",
                    path=path,
                    source_url=self.source_url,
                )
            )
            return diags

        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "3d.openai-yaml.tool-type",
                        f"dependencies.tools[{i}] must be a mapping",
                        path=path,
                        source_url=self.source_url,
                    )
                )
                continue

            tool_type = tool.get("type")
            if tool_type is None:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "3d.openai-yaml.tool-missing-type",
                        f"dependencies.tools[{i}] missing 'type' field",
                        path=path,
                        source_url=self.source_url,
                    )
                )
            elif tool_type not in TOOL_DEP_TYPES:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "3d.openai-yaml.tool-unknown-type",
                        f"dependencies.tools[{i}] has unknown type '{tool_type}' (expected: {', '.join(sorted(TOOL_DEP_TYPES))})",
                        path=path,
                        source_url=self.source_url,
                    )
                )

            if "value" not in tool:
                diags.append(
                    Diagnostic(
                        Level.WARNING,
                        "3d.openai-yaml.tool-missing-value",
                        f"dependencies.tools[{i}] missing 'value' field",
                        path=path,
                        source_url=self.source_url,
                    )
                )

            unknown = set(tool.keys()) - TOOL_DEP_FIELDS
            if unknown:
                diags.append(
                    Diagnostic(
                        Level.INFO,
                        "3d.openai-yaml.tool-unknown-fields",
                        f"dependencies.tools[{i}] has unrecognized fields: {', '.join(sorted(unknown))}",
                        path=path,
                        source_url=self.source_url,
                    )
                )

        return diags

    def _check_policy(self, policy, path: str) -> list[Diagnostic]:
        if policy is None:
            return []
        diags: list[Diagnostic] = []
        if not isinstance(policy, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.policy-type",
                    "'policy' must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )
            return diags

        aii = policy.get("allow_implicit_invocation")
        if aii is not None and not isinstance(aii, bool):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.policy-aii-type",
                    "policy.allow_implicit_invocation must be a boolean",
                    path=path,
                    source_url=self.source_url,
                )
            )

        return diags

    def _check_permissions(self, perms, path: str) -> list[Diagnostic]:
        if perms is None:
            return []
        diags: list[Diagnostic] = []
        if not isinstance(perms, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.permissions-type",
                    "'permissions' must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )
            return diags

        unknown = set(perms.keys()) - PERMISSIONS_FIELDS
        if unknown:
            diags.append(
                Diagnostic(
                    Level.INFO,
                    "3d.openai-yaml.permissions-unknown",
                    f"unrecognized permissions fields: {', '.join(sorted(unknown))}",
                    path=path,
                    source_url=self.source_url,
                )
            )

        network = perms.get("network")
        if network is not None and not isinstance(network, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.permissions-network-type",
                    "permissions.network must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )

        fs = perms.get("file_system")
        if fs is not None:
            if not isinstance(fs, dict):
                diags.append(
                    Diagnostic(
                        Level.ERROR,
                        "3d.openai-yaml.permissions-fs-type",
                        "permissions.file_system must be a mapping",
                        path=path,
                        source_url=self.source_url,
                    )
                )
            else:
                for key in ("read", "write"):
                    val = fs.get(key)
                    if val is not None and not isinstance(val, list):
                        diags.append(
                            Diagnostic(
                                Level.ERROR,
                                f"3d.openai-yaml.permissions-fs-{key}-type",
                                f"permissions.file_system.{key} must be a list",
                                path=path,
                                source_url=self.source_url,
                            )
                        )

        macos = perms.get("macos")
        if macos is not None and not isinstance(macos, dict):
            diags.append(
                Diagnostic(
                    Level.ERROR,
                    "3d.openai-yaml.permissions-macos-type",
                    "permissions.macos must be a mapping",
                    path=path,
                    source_url=self.source_url,
                )
            )

        return diags

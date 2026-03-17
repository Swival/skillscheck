# skillcheck

A linter for agent skill definitions. It validates skill directories against the [agentskills.io specification](https://agentskills.io/specification) and tests compatibility with every major AI coding agent: Claude Code, OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI, Roo Code, Swival, and Windsurf.

If you publish skills for AI agents, skillcheck catches problems before your users do. It checks frontmatter fields, naming conventions, directory structure, description quality, secret leaks, broken links, token budgets, and the agent-specific config files that each platform expects. When it finds something wrong, it tells you exactly what and where, with a check ID you can look up.

Also available as a [VSCode extension](https://marketplace.visualstudio.com/items?itemName=jedisct1.agent-skill-lint) ("Agent Skill Lint") for real-time feedback while editing.

## Installation

```sh
uvx skillcheck /path/to/skills-repo
```

No configuration files needed. Point it at a directory containing skills and it figures out the rest.

## What it checks

skillcheck organizes its diagnostics into four categories.

**Spec compliance** validates the core structure mandated by the agentskills.io specification: frontmatter presence and syntax, required fields like `name` and `description`, naming rules (lowercase, no leading or trailing hyphens, no consecutive hyphens), directory-name consistency, body length and token counts, allowed-tools validation against known tool names, and cross-skill duplicate detection.

**Quality** looks at things the spec does not cover but that matter in practice. It warns when descriptions are too short or lack "use when" hints that help agents trigger the skill correctly. It flags user-centric phrasing, placeholder text, leaked secrets (AWS keys, GitHub tokens, private keys, `.env` files), binary files, and oversized assets. It also walks every local markdown link and verifies the target exists, including fragment anchors.

**Progressive disclosure** checks that reference files stay within reasonable token budgets and that the reference tree does not nest too deeply, following the specification's guidance on keeping skills scannable.

**Agent compatibility** is where skillcheck goes furthest. Each of the eight supported agents has its own adapter that understands the platform's conventions:

- **Claude Code** validates `plugin.json` and `marketplace.json` structure and cross-checks fields for consistency
- **Cursor** validates `.cursor/` configuration
- **Gemini CLI** checks `gemini-extension.json` fields and metadata
- **GitHub Copilot** checks `copilot.yaml` and `.copilot/` directory layout
- **OpenAI Codex** validates `openai.yaml` sidecars, interface, dependencies, and permissions
- **Roo Code** validates `.roo/` and `.roomodes`, warns on deprecated `.roorules` and `.clinerules`
- **Swival** checks `.agents/` directory structure
- **Windsurf** validates `.windsurf/` config, warns on deprecated `.windsurfrules`

skillcheck auto-detects which agents are relevant based on the repository structure, or you can specify them explicitly.

## Options

```text
--agents claude,codex,copilot,cursor,gemini,roo,swival,windsurf
```

Run checks for specific agents. By default, skillcheck auto-detects which agents apply based on the files it finds. Pass `all` to check every agent regardless.

```text
--check agents,disclosure,quality,spec
```

Run only specific check categories.

```text
--fix
```

Auto-fix issues that have safe mechanical fixes: lowercasing names, collapsing consecutive hyphens, renaming directories to match the name field.

```text
--format json
```

Produce JSON output for CI pipelines and editor integrations.

```text
--strict
```

Treat warnings as errors and exit with code 1.

## Exit codes

| Condition                | Exit code |
| :----------------------- | :-------- |
| No errors                | 0         |
| Errors found             | 1         |
| `--strict` with warnings | 1         |

## CI integration

skillcheck works well in CI pipelines. Use `--format json` to get structured output and `--strict` to fail the build on warnings. A typical GitHub Actions step:

```yaml
- name: Lint skills
  run: uvx skillcheck ./skills --strict
```

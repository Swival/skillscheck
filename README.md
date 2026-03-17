# skillcheck - a linter for SKILL.md files

A CLI tool that validates agent skill directories against the [agentskills.io specification](https://agentskills.io/specification) and checks compatibility with AI coding agents (Claude Code, Codex, Copilot, Cursor, Gemini CLI, Roo Code, Swival, Windsurf).

## Installation / Usage

```sh
uvx skillcheck /path/to/skills-repo
```

### Options

- `--agents claude,codex,copilot,cursor,gemini,roo,swival,windsurf`: run specific agent adapter checks (auto-detects if omitted, or `all`)
- `--check agents,disclosure,quality,spec`: run specific check categories
- `--fix`: auto-fix issues that have safe mechanical fixes (lowercase names, collapse consecutive hyphens, rename directories to match name field)
- `--format json`: JSON output for CI pipelines
- `--strict`: treat warnings as errors (exit 1)

### Check categories

- `agents`: agent-specific config validation (Claude plugin.json, Codex openai.yaml, Copilot/Cursor/Gemini extension.json, Roo/Swival/Windsurf conventions)
- `disclosure`: progressive disclosure (reference file sizing, nesting depth)
- `quality`: description quality, file hygiene, broken links, secret detection
- `spec`: core specification compliance (frontmatter fields, naming, directory structure)

### Exit codes

| Condition                | Exit code |
| :----------------------- | :-------- |
| No errors                | 0         |
| Errors found             | 1         |
| `--strict` with warnings | 1         |

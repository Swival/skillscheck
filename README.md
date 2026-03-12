# skillscheck - a linter for SKILL.md files

A CLI tool that validates agent skill directories against the [agentskills.io specification](https://agentskills.io/specification) and checks compatibility with AI coding agents (Claude Code, Gemini CLI, Codex, Copilot, Cursor, Roo Code, Windsurf, Swival).

## Installation / Usage

```sh
uvx skillscheck /path/to/skills-repo
```

### Options

- `--format json`: JSON output for CI pipelines
- `--strict`: treat warnings as errors (exit 1)
- `--fix`: auto-fix issues that have safe mechanical fixes (lowercase names, collapse consecutive hyphens, rename directories to match name field)
- `--agents claude,gemini,codex,copilot,cursor,roo,windsurf,swival`: run specific agent adapter checks (auto-detects if omitted, or `all`)
- `--check spec,quality,disclosure,agents`: run specific check categories

### Check categories

- `spec`: core specification compliance (frontmatter fields, naming, directory structure)
- `quality`: description quality, file hygiene, broken links, secret detection
- `disclosure`: progressive disclosure (reference file sizing, nesting depth)
- `agents`: agent-specific config validation (Claude plugin.json, Gemini extension.json, Codex openai.yaml, Copilot/Cursor/Roo/Windsurf/Swival conventions)

### Exit codes

| Condition                | Exit code |
| :----------------------- | :-------- |
| No errors                | 0         |
| Errors found             | 1         |
| `--strict` with warnings | 1         |

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Level(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


CATEGORIES = ("spec", "quality", "disclosure")

SPEC_URL = "https://agentskills.io/specification"


@dataclass
class Diagnostic:
    level: Level
    check: str
    message: str
    path: str = ""
    line: int | None = None
    source_url: str = ""
    fixable: bool = False

    def to_dict(self) -> dict:
        d: dict = {
            "level": self.level.value,
            "check": self.check,
            "message": self.message,
        }
        if self.path:
            d["path"] = self.path
        if self.line is not None:
            d["line"] = self.line
        if self.source_url:
            d["source_url"] = self.source_url
        if self.fixable:
            d["fixable"] = True
        return d


@dataclass
class SkillDiagnostics:
    spec: list[Diagnostic] = field(default_factory=list)
    quality: list[Diagnostic] = field(default_factory=list)
    disclosure: list[Diagnostic] = field(default_factory=list)

    def all(self) -> list[Diagnostic]:
        return self.spec + self.quality + self.disclosure

    def to_dict(self) -> dict:
        d: dict = {}
        for cat in CATEGORIES:
            items = getattr(self, cat)
            if items:
                d[cat] = [diag.to_dict() for diag in items]
        return d


@dataclass
class SkillInfo:
    dir_name: str
    dir_path: str
    skill_md_path: str
    frontmatter: dict | None = None
    body: str = ""
    body_line_offset: int = 0
    parse_error: str | None = None


@dataclass
class ValidationResult:
    skills: dict[str, SkillDiagnostics] = field(default_factory=dict)
    agents: dict[str, list[Diagnostic]] = field(default_factory=dict)

    def ensure_skill(self, name: str) -> SkillDiagnostics:
        if name not in self.skills:
            self.skills[name] = SkillDiagnostics()
        return self.skills[name]

    def add_skill(self, name: str, category: str, diag: Diagnostic) -> None:
        sd = self.ensure_skill(name)
        getattr(sd, category).append(diag)

    def add_agent(self, name: str, diag: Diagnostic) -> None:
        self.agents.setdefault(name, []).append(diag)

    def counts(self) -> dict[str, int]:
        all_diags: list[Diagnostic] = []
        for sd in self.skills.values():
            all_diags.extend(sd.all())
        for v in self.agents.values():
            all_diags.extend(v)
        return {
            "skills": sum(1 for k in self.skills if not k.startswith("_")),
            "errors": sum(1 for d in all_diags if d.level == Level.ERROR),
            "warnings": sum(1 for d in all_diags if d.level == Level.WARNING),
            "info": sum(1 for d in all_diags if d.level == Level.INFO),
        }

    def exit_code(self, strict: bool = False) -> int:
        c = self.counts()
        if c["errors"] > 0:
            return 1
        if strict and c["warnings"] > 0:
            return 1
        return 0

    def to_dict(self) -> dict:
        result: dict = {"skills": {}, "agents": {}}
        for name, sd in self.skills.items():
            result["skills"][name] = sd.to_dict()
        for name, diags in self.agents.items():
            result["agents"][name] = [d.to_dict() for d in diags]
        result["summary"] = self.counts()
        return result

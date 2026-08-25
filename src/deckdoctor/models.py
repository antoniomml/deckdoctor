from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "pass"
    INFO = "info"
    WARNING = "warning"
    FAIL = "fail"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"


class EvidenceSource(str, Enum):
    SYSTEMD = "systemd"
    JOURNAL = "journal"
    FILESYSTEM = "filesystem"
    FLATPAK = "flatpak"
    NETWORK = "network"
    STEAM_METADATA = "steam_metadata"
    DECKY_METADATA = "decky_metadata"
    OS_METADATA = "os_metadata"
    SOCKETS = "sockets"
    LOCALHOST = "localhost"


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: Status
    finding: str
    explanation: str = ""
    recommendation: str = ""
    evidence: list[str] = field(default_factory=list)
    source: EvidenceSource = EvidenceSource.FILESYSTEM
    severity: Severity = Severity.NONE
    confidence: Confidence | None = None
    fact_kind: str = "fact"  # fact | likely | unknown
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.check_id,
            "title": self.title,
            "status": self.status.value,
            "severity": self.severity.value,
            "finding": self.finding,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "evidence": list(self.evidence),
            "source": self.source.value,
            "confidence": self.confidence.value if self.confidence else None,
            "fact_kind": self.fact_kind,
            "extra": self.extra,
        }


@dataclass
class Diagnosis:
    title: str
    summary: str
    recommendation: str
    related_checks: list[str]
    confidence: Confidence
    fact_kind: str  # fact | likely
    severity: Severity = Severity.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "related_checks": list(self.related_checks),
            "confidence": self.confidence.value,
            "fact_kind": self.fact_kind,
            "severity": self.severity.value,
        }


@dataclass
class Report:
    version: str
    generated_at: str
    results: list[CheckResult]
    diagnoses: list[Diagnosis]
    facts: dict[str, Any] = field(default_factory=dict)

    @property
    def problems(self) -> list[CheckResult]:
        return [r for r in self.results if r.status in {Status.FAIL, Status.WARNING}]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "facts": self.facts,
            "results": [r.to_dict() for r in self.results],
            "diagnoses": [d.to_dict() for d in self.diagnoses],
            "problem_count": len(self.problems),
        }

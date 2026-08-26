from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult


@runtime_checkable
class Check(Protocol):
    id: str
    title: str
    requires_network: bool

    def run(self, ctx: DiagnosticContext) -> CheckResult: ...


@dataclass(frozen=True)
class FnCheck:
    """Adapter so module-level ``run`` functions satisfy :class:`Check`."""

    id: str
    title: str
    requires_network: bool
    _fn: Callable[[DiagnosticContext], CheckResult]

    def run(self, ctx: DiagnosticContext) -> CheckResult:
        return self._fn(ctx)

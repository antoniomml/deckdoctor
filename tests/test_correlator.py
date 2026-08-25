from __future__ import annotations

from deckdoctor.correlator import correlate
from deckdoctor.facts import Facts
from deckdoctor.models import CheckResult, EvidenceSource, Status


def _res(check_id: str, status: Status = Status.PASS) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        title=check_id,
        status=status,
        finding=check_id,
        source=EvidenceSource.FILESYSTEM,
    )


def test_rate_limit_incomplete_install() -> None:
    facts = Facts(
        decky_incomplete=True,
        plugin_loader_present=False,
        decky_installed=True,
        github_remaining=0,
    )
    diags = correlate([], facts)
    assert any("rate limit" in d.title.lower() or "Incomplete" in d.title for d in diags)


def test_unit_429() -> None:
    facts = Facts(decky_unit_is_429=True)
    diags = correlate([], facts)
    assert any("429" in d.title or "429" in d.summary for d in diags)


def test_port_conflict() -> None:
    facts = Facts(plugin_loader_present=True, port_8080_conflict=True)
    diags = correlate([], facts)
    assert any("8080" in d.title for d in diags)


def test_autoflatpaks_remote() -> None:
    facts = Facts(autoflatpaks_installed=True, autoflatpaks_remote_list_failed=True)
    diags = correlate([], facts)
    assert any("AutoFlatpaks" in d.title for d in diags)


def test_steam_beta_likely() -> None:
    facts = Facts(
        plugin_loader_present=True,
        decky_service_active="active",
        cef_json_ok=True,
        steam_channel="beta",
        decky_log_signatures=[],
    )
    results = [_res("DECKY-LOGS", Status.PASS)]
    diags = correlate(results, facts)
    assert any("Steam" in d.title or "frontend" in d.title.lower() for d in diags)


def test_spanish_diagnosis_title() -> None:
    facts = Facts(decky_incomplete=True, plugin_loader_present=False, decky_installed=True)
    diags = correlate([], facts, locale="es")
    assert diags
    assert "incompleta" in diags[0].title.lower() or "Instalación" in diags[0].title

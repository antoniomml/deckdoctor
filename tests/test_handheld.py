from __future__ import annotations

import json
from pathlib import Path

import pytest

from deckdoctor.checks import handheld, host_capabilities, steam_game, steam_libraries, sys_os_updater
from deckdoctor.cli import main
from deckdoctor.command import CommandResult
from deckdoctor.fixes import FakeFixExecutor, apply_plans, collect_plans
from deckdoctor.models import Status
from deckdoctor.runner import diagnose
from deckdoctor.steam import library_roots, parse_vdf
from deckdoctor.workflows import SYMPTOMS, compare
from tests.conftest import make_ctx, make_home


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_keyvalues_escaping_comments_and_nesting() -> None:
    data = parse_vdf('"Root" { // ignored\n "path" "a\\\\b" "item" { "name" "a\\\"b" } }')
    assert data == {'root': {'path': 'a\\b', 'item': {'name': 'a"b'}}}


@pytest.mark.parametrize('text', ['"a" {', '"a"', '}', '"a" }', '"a" {' * 34])
def test_keyvalues_rejects_broken_metadata(text: str) -> None:
    with pytest.raises(ValueError):
        parse_vdf(text)


def test_missing_library_retained_and_duplicate_symlink_collapsed(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    alias = tmp_path / 'alias'
    alias.symlink_to(ctx.steam_root, target_is_directory=True)
    missing = tmp_path / 'unplugged'
    write(ctx.steam_root / 'steamapps/libraryfolders.vdf',
          f'"libraryfolders" {{ "0" {{ "path" "{alias}" }} "1" {{ "path" "{missing}" }} }}')
    roots, readable = library_roots(ctx)
    assert readable and len(roots) == 2
    check = steam_libraries.run(ctx)
    assert check.status == Status.WARNING
    assert any(row['path'] == str(missing) and row['state'] == 'missing_or_unreadable'
               for row in check.extra['libraries'])


def test_unreadable_library_catalog_never_passes(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    write(ctx.steam_root / 'steamapps/libraryfolders.vdf', '"libraryfolders" {')
    assert steam_libraries.run(ctx).status == Status.UNKNOWN


def test_game_metadata_and_proton_override(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.appid = 42
    write(ctx.steam_root / 'steamapps/appmanifest_42.acf',
          '"AppState" { "appid" "42" "name" "Example" "installdir" "Example" "StateFlags" "4" }')
    (ctx.steam_root / 'steamapps/common/Example').mkdir(parents=True)
    write(ctx.steam_root / 'config/config.vdf',
          '"InstallConfigStore" { "Software" { "Valve" { "Steam" { "CompatToolMapping" { "42" { "name" "proton_experimental" } } } } } }')
    check = steam_game.run(ctx)
    assert check.status == Status.INFO
    assert check.extra['compat_tool_override'] == 'proton_experimental'
    assert check.extra['prefix_present'] is False
    assert 'PROTON_LOG=1 %command%' in check.recommendation


@pytest.mark.parametrize('installdir', ['../escape', '/tmp', '..', '.'])
def test_game_does_not_follow_manifest_path_traversal(tmp_path: Path, installdir: str) -> None:
    ctx = make_ctx(tmp_path)
    ctx.appid = 42
    write(ctx.steam_root / 'steamapps/appmanifest_42.acf',
          f'"AppState" {{ "appid" "42" "installdir" "{installdir}" }}')
    assert steam_game.run(ctx).status == Status.WARNING


def test_game_missing_manifest_is_unknown(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.appid = 42
    assert steam_game.run(ctx).status == Status.UNKNOWN


def test_flatpak_steam_root(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.home = tmp_path / 'flatpak-home'
    root = ctx.home / '.var/app/com.valvesoftware.Steam/.local/share/Steam'
    root.mkdir(parents=True)
    assert ctx.steam_root == root


def test_hardware_snapshots_do_not_claim_functionality(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    write(ctx.sys_root / 'class/power_supply/BAT1/type', 'Battery\n')
    write(ctx.sys_root / 'class/power_supply/BAT1/capacity', '80\n')
    write(ctx.proc_root / 'bus/input/devices', 'N: Name="Gamepad"\nH: Handlers=event1 js0\n')
    assert handheld.battery(ctx).extra['batteries'][0]['capacity'] == '80'
    assert handheld.controllers(ctx).status == Status.INFO
    assert handheld.controllers(ctx).extra['devices'][0]['name'] == 'Gamepad'
    assert handheld.resume(ctx).status == Status.UNKNOWN


def test_capabilities_use_installed_tools_not_distro_assumptions(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, os_release='ID=bazzite\n')
    ctx.which = lambda tool: '/usr/bin/inputplumber' if tool == 'inputplumber' else None
    data = host_capabilities.run(ctx).extra
    assert data['tools']['inputplumber']
    assert data['tools']['hhd'] is None


def test_updater_inaccessible_bus_is_unknown(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.facts.is_steamos = True
    ctx.runner.add(['atomupd-manager', 'get-update-status'],
                   CommandResult((), -11, '', "assertion 'G_IS_DBUS_CONNECTION (connection)' failed"))
    assert sys_os_updater.run(ctx).status == Status.UNKNOWN


def test_stale_fix_is_not_applied(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, home=make_home(tmp_path, cef=False))
    plans = [p for p in collect_plans(ctx, diagnose(ctx)) if p.id == 'cef-debug']
    assert plans
    (ctx.steam_root / '.cef-enable-remote-debugging').touch()
    executor = FakeFixExecutor()
    results = apply_plans(ctx, plans, executor)
    assert not results[0].ok
    assert executor.calls == []


def test_comparison_excludes_unknown_and_rejects_different_scope(tmp_path: Path) -> None:
    report = diagnose(make_ctx(tmp_path, only_ids=SYMPTOMS['library']))
    previous = report.to_dict()
    disk = next(r for r in report.results if r.check_id == 'SYS-DISK')
    disk.status = Status.FAIL
    assert compare(report, previous)[0]['after'] == 'fail'
    disk.status = Status.UNKNOWN
    assert compare(report, previous) == []
    previous['facts'] = {**previous['facts'], 'appid': 42}
    with pytest.raises(ValueError, match='appid'):
        compare(report, previous)


def test_cli_workflow_json_and_comparison(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path)
    monkeypatch.setattr('deckdoctor.cli.build_context', lambda **kwargs: make_ctx(tmp_path, home=home, only_ids=kwargs['only_ids']))
    path = tmp_path / 'report.json'
    assert main(['--symptom', 'library', '--json', '-o', str(path)]) == 0
    data = json.loads(path.read_text())
    assert data['facts']['scope'] == sorted(SYMPTOMS['library'])
    capsys.readouterr()
    assert main(['--symptom', 'library', '--json', '--compare', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['comparison'] == []


@pytest.mark.parametrize('args', [['--appid', '0'], ['--symptom', 'game'], ['--symptom', 'library', '--only', 'SYS-DISK'], ['--appid', '42', '--symptom', 'battery']])
def test_invalid_workflow_arguments(args: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


def test_audio_displays_and_pressure_are_observations(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    write(ctx.sys_root / 'class/drm/card0-HDMI-A-1/status', 'connected\n')
    write(ctx.sys_root / 'class/drm/card0-HDMI-A-1/modes', '1920x1080\n')
    write(ctx.proc_root / 'pressure/cpu', 'some avg10=0.00 avg60=0.00 avg300=0.00 total=1')
    ctx.runner.add(['pactl', 'info'], CommandResult((), 0, 'Server Name: PulseAudio (on PipeWire)\nDefault Sink: example', ''))
    assert handheld.displays(ctx).extra['connectors'][0]['modes'] == ['1920x1080']
    assert handheld.audio(ctx).status == Status.INFO
    assert handheld.performance(ctx).status == Status.INFO


def test_repair_command_success_is_separate_from_verification(tmp_path: Path) -> None:
    from deckdoctor.fixes import verify_results
    from deckdoctor.models import FixPlan, FixResult

    report = diagnose(make_ctx(tmp_path))
    plan = FixPlan('example', '', '', '', '', ['SYS-DISK'])
    command = FixResult('example', True, 'command completed')
    disk = next(r for r in report.results if r.check_id == 'SYS-DISK')
    for status, expected in [(Status.PASS, True), (Status.FAIL, False), (Status.UNKNOWN, None), (Status.SKIPPED, None)]:
        disk.status = status
        verify_results([plan], [command], report)
        assert command.ok and command.verified is expected


def test_malformed_quote_and_oversized_metadata(tmp_path: Path) -> None:
    from deckdoctor.steam import metadata

    with pytest.raises(ValueError):
        parse_vdf('"a" "unterminated')
    ctx = make_ctx(tmp_path)
    path = tmp_path / 'large.vdf'
    write(path, '"a" "b" ' * 100)
    assert metadata(ctx, path, max_bytes=10) is None


def test_narrow_summary_wraps_and_shows_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from deckdoctor.renderer import render_cli

    monkeypatch.setenv('COLUMNS', '50')
    report = diagnose(make_ctx(tmp_path, only_ids=frozenset({'SYS-DISK'}), ascii_mode=True))
    text = render_cli(report)
    assert 'Scope: SYS-DISK' in text
    assert max(map(len, text.splitlines())) <= 50


def test_json_fix_has_one_report_and_verified_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path, cef=False)
    monkeypatch.setattr('deckdoctor.cli.build_context', lambda **kwargs: make_ctx(tmp_path, home=home, only_ids=kwargs['only_ids']))
    monkeypatch.setattr('deckdoctor.cli.apply_plans', lambda ctx, plans, **kwargs: apply_plans(ctx, plans, FakeFixExecutor(), **kwargs))
    assert main(['fix', 'cef-debug', '--json', '--yes']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['repair_results'][0]['ok'] is True
    assert payload['repair_results'][0]['verified'] is True


def test_null_comparison_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('deckdoctor.cli.build_context', lambda **kwargs: make_ctx(tmp_path, only_ids=kwargs['only_ids']))
    path = tmp_path / 'null.json'
    path.write_text('null')
    with pytest.raises(SystemExit) as exc:
        main(['--compare', str(path)])
    assert exc.value.code == 2

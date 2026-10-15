from __future__ import annotations

from typing import Any

from deckdoctor.models import Report
from deckdoctor.sanitizer import Sanitizer

_BASE = {'HOST-CAPABILITIES', 'SYS-OS-VERSION', 'SYS-DISK', 'STEAM-CLIENT'}
SYMPTOMS: dict[str, frozenset[str]] = {
    'dock': frozenset({'HOST-CAPABILITIES', 'HW-DISPLAY', 'HW-AUDIO'}),
    'audio': frozenset({'HOST-CAPABILITIES', 'HW-AUDIO'}),
    'performance': frozenset(_BASE | {'HW-PERFORMANCE', 'HW-BATTERY', 'HW-THERMAL'}),
    'decky': frozenset(_BASE | {'DECKY-INSTALL', 'DECKY-SERVICE', 'DECKY-PORTS', 'DECKY-LOGS', 'DECKY-FRONTEND', 'NET-GITHUB'}),
    'updates': frozenset(_BASE | {'SYS-OS-CHANNEL', 'SYS-OS-UPDATER', 'SYS-OS-REBOOT', 'SYS-OVERLAY', 'SYS-TIME', 'FP-BASIC', 'FP-UPDATES', 'FP-EOL'}),
    'library': frozenset(_BASE | {'STEAM-LIBRARIES', 'STEAM-STORAGE'}),
    'game': frozenset(_BASE | {'STEAM-LIBRARIES', 'STEAM-GAME'}),
    'controller': frozenset(_BASE | {'HW-INPUT'}),
    'battery': frozenset({'HOST-CAPABILITIES', 'HW-BATTERY', 'HW-THERMAL'}),
    'resume': frozenset({'HOST-CAPABILITIES', 'HW-BATTERY', 'HW-INPUT', 'HW-RESUME'}),
}


def compare(report: Report, previous: Any, sanitizer: Sanitizer | None = None) -> list[dict[str, Any]]:
    if not isinstance(previous, dict) or not isinstance(previous.get('results'), list):
        raise ValueError('Expected a DeckDoctor JSON report with results')
    facts = previous.get('facts')
    if not isinstance(facts, dict):
        raise ValueError('Previous report has no scope metadata')
    for key in ('appid', 'symptom', 'scope', 'network_enabled'):
        if facts.get(key) != report.facts.get(key):
            raise ValueError(f'Cannot compare reports with different {key}')
    if previous.get('locale') != report.locale:
        raise ValueError('Cannot compare reports in different languages')
    rows = previous['results']
    if any(not isinstance(row, dict) or not isinstance(row.get('id'), str) or
           row.get('status') not in {'pass', 'info', 'warning', 'fail', 'unknown', 'skipped'} for row in rows):
        raise ValueError('Invalid check result in previous report')
    before = {row['id']: row for row in rows}
    changes = []
    verified = {'pass', 'info', 'warning', 'fail'}
    current = report.to_dict()
    if sanitizer is not None:
        current = sanitizer.apply_obj(current)
    for row in current['results']:
        old = before.get(row['id'])
        if old and old['status'] in verified and row['status'] in verified:
            if any(old.get(key) != row.get(key) for key in ('status', 'finding', 'extra')):
                changes.append({'id': row['id'], 'before': old['status'], 'after': row['status'],
                                'finding_before': old.get('finding'), 'finding_after': row['finding'],
                                'observations_before': old.get('extra'), 'observations_after': row.get('extra')})
    return changes

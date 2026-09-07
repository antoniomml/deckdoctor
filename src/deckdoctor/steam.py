"""Bounded readers for Steam's text KeyValues metadata; never execute its contents."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from deckdoctor.context import DiagnosticContext

_TOKEN = re.compile(r'//[^\n]*|"((?:\\.|[^"\\])*)"|([{}])|([^\s{}"]+)')


def parse_vdf(text: str) -> dict[str, Any]:
    tokens = []
    end = 0
    for match in _TOKEN.finditer(text):
        if text[end:match.start()].strip():
            raise ValueError("Invalid KeyValues token")
        end = match.end()
        if match.group(0).startswith('//'):
            continue
        quoted, brace, bare = match.groups()
        tokens.append((re.sub(r'\\(["\\])', r'\1', quoted) if quoted is not None else brace or bare, brace is not None))
    if text[end:].strip():
        raise ValueError("Invalid trailing KeyValues token")
    pos = 0

    def block(depth: int = 0) -> dict[str, Any]:
        nonlocal pos
        if depth > 32:
            raise ValueError('KeyValues nesting too deep')
        data: dict[str, Any] = {}
        while pos < len(tokens):
            key, structural = tokens[pos]
            pos += 1
            if structural and key == '}':
                if depth == 0:
                    raise ValueError('Unexpected closing brace')
                return data
            if structural or pos >= len(tokens):
                raise ValueError('Invalid KeyValues key/value')
            value, structural = tokens[pos]
            pos += 1
            if structural:
                if value != '{':
                    raise ValueError('Missing KeyValues value')
                data[key.lower()] = block(depth + 1)
            else:
                data[key.lower()] = value
        if depth:
            raise ValueError('Unclosed KeyValues block')
        return data

    return block()


def metadata(ctx: DiagnosticContext, path: Path, max_bytes: int = 1_000_000) -> dict[str, Any] | None:
    text = ctx.read_text(path, max_bytes=max_bytes + 1)
    if text is None or len(text.encode("utf-8")) > max_bytes:
        return None
    try:
        return parse_vdf(text)
    except ValueError:
        return None


def library_roots(ctx: DiagnosticContext) -> tuple[list[Path], bool]:
    root = ctx.steam_root
    data = metadata(ctx, root / 'steamapps/libraryfolders.vdf')
    folders = (data or {}).get('libraryfolders')
    roots = [root] if ctx.exists(root / 'steamapps') else []
    if isinstance(folders, dict):
        for key, item in folders.items():
            if not key.isdigit():
                continue
            raw = item.get('path') if isinstance(item, dict) else item
            if isinstance(raw, str) and Path(raw).is_absolute():
                roots.append(Path(raw))
    unique: dict[str, Path] = {}
    for path in roots:
        try:
            unique.setdefault(str(path.resolve()), path)
        except OSError:
            unique.setdefault(str(path), path)
    return list(unique.values()), isinstance(folders, dict)

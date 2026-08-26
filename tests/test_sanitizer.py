from __future__ import annotations

from deckdoctor.sanitizer import Sanitizer


def test_sanitizer_replaces_home_user_host_email_ip_mac_steam_secrets() -> None:
    san = Sanitizer(user="antonio", home="/home/antonio", hostname="kitchen-deck")
    raw = """
user antonio on kitchen-deck
path /home/antonio/homebrew/services/PluginLoader
mail antonio@example.com
lan 192.168.1.27 and also 10.0.0.5
mac 00:11:22:33:44:55
steam 76561198000000000
token ghp_abcdefghijklmnopqrstuvwxyz0123456789
bearer Bearer eyJhbGciOiJIUzI1NiJ9.aaa.bbb
url https://user:hunter2@github.com/foo.git
AWS AKIAIOSFODNN7EXAMPLE
API_KEY=supersecretvalue
-----BEGIN OPENSSH PRIVATE KEY-----
abcdef
-----END OPENSSH PRIVATE KEY-----
"""
    out = san.apply(raw)
    assert "antonio" not in out
    assert "/home/antonio" not in out
    assert "/home/<USER>" in out
    assert "<USER>" in out
    assert "kitchen-deck" not in out
    assert "<HOSTNAME>" in out
    assert "<EMAIL>" in out
    assert "<PRIVATE_IP_1>" in out
    assert "<PRIVATE_IP_2>" in out
    assert "192.168.1.27" not in out
    assert "<MAC>" in out
    assert "76561198000000000" not in out
    assert "<STEAM_ID>" in out
    assert "ghp_" not in out
    assert "hunter2" not in out
    assert "supersecretvalue" not in out
    assert "<SSH_KEY>" in out
    assert "BEGIN OPENSSH" not in out


def test_sanitizer_ip_replacements_are_stable() -> None:
    san = Sanitizer(user="deck", home="/home/deck", hostname="host")
    once = san.apply("a 192.168.0.9 b 192.168.0.9 c 10.1.1.1")
    twice = san.apply("again 192.168.0.9")
    assert once.count("<PRIVATE_IP_1>") == 2
    assert "<PRIVATE_IP_2>" in once
    assert "<PRIVATE_IP_1>" in twice


def test_sanitizer_redacts_private_ipv6() -> None:
    san = Sanitizer(user="deck", home="/home/deck", hostname="host")
    out = san.apply("ula fd12:3456:789a:1::1 link fe80::1 loop ::1")
    assert "fd12:3456:789a:1::1" not in out
    assert "fe80::1" not in out
    assert "<PRIVATE_IP_" in out


def test_apply_obj_does_not_break_json_types() -> None:
    san = Sanitizer(user="antonio", home="/home/antonio", hostname="steamdeck")
    payload = {"user": "antonio", "ok": True, "count": 2, "nested": ["antonio", 1]}
    out = san.apply_obj(payload)
    assert out["ok"] is True
    assert out["count"] == 2
    assert out["user"] == "<USER>"
    assert out["nested"][1] == 1


def test_generic_hostname_is_not_redacted() -> None:
    san = Sanitizer(user="deck", home="/home/deck", hostname="steamdeck")
    out = san.apply("SteamOS variant steamdeck on host steamdeck")
    assert "steamdeck" in out
    assert "<HOSTNAME>" not in out


def test_short_username_is_not_replaced() -> None:
    san = Sanitizer(user="ab", home="/home/ab", hostname="xy")
    out = san.apply("ab xy stay")
    assert "ab" in out
    assert "xy" in out

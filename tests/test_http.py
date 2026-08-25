from __future__ import annotations

from deckdoctor.http import FakeHttpClient, HttpClient, host_allowed


def test_host_allowlist() -> None:
    assert host_allowed("https://github.com/foo")
    assert host_allowed("http://127.0.0.1:8080/json")
    assert host_allowed("https://plugins.deckbrew.xyz/plugins")
    assert not host_allowed("https://evil.example/x")


def test_http_client_blocks_unknown_host() -> None:
    client = HttpClient()
    res = client.request("GET", "https://evil.example/secret")
    assert res.error == "host_not_allowed"
    assert not res.ok


def test_fake_http_also_honours_allowlist() -> None:
    fake = FakeHttpClient()
    res = fake.request("GET", "https://evil.example/")
    assert res.error == "host_not_allowed"

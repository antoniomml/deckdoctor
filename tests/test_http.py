from __future__ import annotations

import os

from deckdoctor.http import FakeHttpClient, HttpClient, host_allowed, ssl_context, system_ca_file


def test_ssl_context_builds() -> None:
    ctx = ssl_context()
    assert ctx is not None
    ca = system_ca_file()
    if ca:
        assert os.path.isfile(ca)


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

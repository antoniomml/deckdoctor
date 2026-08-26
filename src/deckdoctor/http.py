from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from deckdoctor import __version__

_CA_FILES = (
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/cert.pem",
)


def system_ca_file() -> str | None:
    """OS trust store. Frozen binaries often ship an empty or stale CA bundle."""
    extra = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    env_ok = extra and "/_MEI" not in extra.replace("\\", "/")
    ordered = ((extra,) if env_ok else ()) + _CA_FILES
    for path in ordered:
        if path and os.path.isfile(path):
            return path
    return None


def ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    cafile = system_ca_file()
    if cafile:
        try:
            context.load_verify_locations(cafile=cafile)
        except OSError:
            pass
    capath = "/etc/ssl/certs"
    if os.path.isdir(capath):
        try:
            context.load_verify_locations(capath=capath)
        except OSError:
            pass
    return context


ALLOWED_HOSTS = frozenset(
    {
        "github.com",
        "api.github.com",
        "plugins.deckbrew.xyz",
        "127.0.0.1",
        "localhost",
        "::1",
    }
)


def host_allowed(url: str, allowed: frozenset[str] = ALLOWED_HOSTS) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host in allowed


@dataclass
class HttpResult:
    url: str
    method: str
    status: int | None
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    final_url: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 400 and self.error is None

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body)


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not host_allowed(newurl):
            raise urllib.error.URLError(f"redirect host not allowed: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClient:
    """Tiny HTTPS client. No cookies, no retries storm, User-Agent identified."""

    user_agent = f"DeckDoctor/{__version__} (local diagnostic; no telemetry)"
    allowed_hosts: frozenset[str] = ALLOWED_HOSTS

    def request(
        self,
        method: str,
        url: str,
        *,
        timeout: float = 10.0,
        follow_redirects: bool = True,
    ) -> HttpResult:
        if not host_allowed(url, self.allowed_hosts):
            return HttpResult(url=url, method=method.upper(), status=None, error="host_not_allowed")
        if timeout <= 0:
            return HttpResult(url=url, method=method.upper(), status=None, error="timeout")
        req = urllib.request.Request(url, method=method.upper())
        req.add_header("User-Agent", self.user_agent)
        req.add_header("Accept", "*/*")
        context = ssl_context()
        handlers: list[urllib.request.BaseHandler] = [
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPHandler(),
        ]
        if follow_redirects:
            handlers.append(_AllowlistRedirect())
        else:

            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
                    return None

            handlers.append(_NoRedirect())
        opener = urllib.request.build_opener(*handlers)
        try:
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read(1_000_000).decode("utf-8", errors="replace")
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return HttpResult(
                    url=url,
                    method=method.upper(),
                    status=getattr(resp, "status", None) or resp.getcode(),
                    body=body,
                    headers=headers,
                    final_url=resp.geturl(),
                )
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read(1_000_000).decode("utf-8", errors="replace")
            except OSError:
                body = ""
            headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
            return HttpResult(
                url=url,
                method=method.upper(),
                status=exc.code,
                body=body,
                headers=headers,
                error=None if 300 <= exc.code < 400 else f"http_{exc.code}",
                final_url=exc.headers.get("location") if exc.headers else None,
            )
        except urllib.error.URLError as exc:
            return HttpResult(
                url=url,
                method=method.upper(),
                status=None,
                error=str(exc.reason) if getattr(exc, "reason", None) else str(exc),
            )
        except TimeoutError:
            return HttpResult(url=url, method=method.upper(), status=None, error="timeout")
        except OSError as exc:
            return HttpResult(url=url, method=method.upper(), status=None, error=str(exc))


class FakeHttpClient(HttpClient):
    def __init__(self) -> None:
        self.mapping: dict[tuple[str, str], HttpResult] = {}
        self.calls: list[tuple[str, str]] = []

    def add(self, method: str, url: str, result: HttpResult) -> None:
        self.mapping[(method.upper(), url)] = result

    def request(
        self,
        method: str,
        url: str,
        *,
        timeout: float = 10.0,
        follow_redirects: bool = True,
    ) -> HttpResult:
        key = (method.upper(), url)
        self.calls.append(key)
        if not host_allowed(url, self.allowed_hosts):
            return HttpResult(url=url, method=method.upper(), status=None, error="host_not_allowed")
        if key in self.mapping:
            return self.mapping[key]
        return HttpResult(url=url, method=method.upper(), status=None, error="not mocked")

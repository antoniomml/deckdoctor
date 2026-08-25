from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


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


class HttpClient:
    """Tiny HTTPS client. No cookies, no retries storm, User-Agent identified."""

    user_agent = "DeckDoctor/0.1 (local diagnostic; no telemetry)"

    def request(
        self,
        method: str,
        url: str,
        *,
        timeout: float = 10.0,
        follow_redirects: bool = True,
    ) -> HttpResult:
        req = urllib.request.Request(url, method=method.upper())
        req.add_header("User-Agent", self.user_agent)
        req.add_header("Accept", "*/*")
        context = ssl.create_default_context()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPHandler(),
        )
        if not follow_redirects:
            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
                    return None

            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context),
                urllib.request.HTTPHandler(),
                _NoRedirect(),
            )
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
            except Exception:
                body = ""
            headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
            # 3xx without follow still lands here for NoRedirect
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
        if key in self.mapping:
            return self.mapping[key]
        return HttpResult(url=url, method=method.upper(), status=None, error="not mocked")

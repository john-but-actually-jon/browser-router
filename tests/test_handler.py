import http.client
import threading
from http.server import HTTPServer
from unittest.mock import MagicMock
from urllib.parse import urlencode

import pytest

from browser_router import handler
from browser_router.handler import Handler


@pytest.fixture
def popen(monkeypatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(handler.subprocess, "Popen", mock)
    return mock


@pytest.fixture
def server(monkeypatch, config, popen):
    monkeypatch.setattr(handler, "get_config", lambda: config)
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def open_url(server: HTTPServer, url: str, ctx: str | None = None) -> int:
    params = {"url": url}
    if ctx is not None:
        params["ctx"] = ctx
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        conn.request("GET", f"/open?{urlencode(params)}")
        return conn.getresponse().status
    finally:
        conn.close()


def opened_profile(popen: MagicMock) -> str:
    popen.assert_called_once()
    cmd = popen.call_args.args[0]
    return next(
        arg.removeprefix("--profile-directory=")
        for arg in cmd
        if arg.startswith("--profile-directory=")
    )


def test_matching_ruleset_opens_ruleset_profile(server, popen):
    status = open_url(
        server, "https://login.microsoftonline.com/oauth", ctx="client-ctx"
    )

    assert status == 204
    assert opened_profile(popen) == "Profile 3"


def test_unknown_ctx_falls_back_to_default_profile(server, popen):
    status = open_url(
        server, "https://login.microsoftonline.com/oauth", ctx="unknown-ctx"
    )

    assert status == 204
    assert opened_profile(popen) == "Default"


def test_missing_ctx_falls_back_to_default_profile(server, popen):
    status = open_url(server, "https://accounts.google.com/o/oauth2")

    assert status == 204
    assert opened_profile(popen) == "Default"


def test_ctx_with_non_matching_domain_falls_back_to_default_profile(server, popen):
    status = open_url(server, "https://accounts.google.com/o/oauth2", ctx="client-ctx")

    assert status == 204
    assert opened_profile(popen) == "Default"

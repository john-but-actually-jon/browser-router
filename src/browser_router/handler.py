import subprocess
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from browser_router.config import Config, get_config
from browser_router.intlogging import get_logger

logger = get_logger(__name__)


def url_overlap(url, candidates: list[str]) -> bool:
    """
    Check if the URL overlaps with any of the candidates
    """
    overlap = False

    for candidate in candidates:
        if url == candidate or candidate in url:
            overlap = True
            break

    return overlap


class Handler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # BaseHTTPRequestHandler handles the request inside __init__, so config
        # must be set before calling super().__init__().
        self.config: Config = get_config()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        self.path = u.path
        self.url = q.get("url", [""])[0]
        self.host = urlparse(self.url).hostname or ""

        _ctx = q.get("ctx", [""])[0]
        self.ruleset = next(
            (
                rs
                for rs in self.config.rulesets
                if rs.routing_identifier == _ctx and url_overlap(self.host, rs.domains)
            ),
            None,
        )
        if self.ruleset is None:
            logger.warning(f"No ruleset found for {self.url} - {_ctx}")

        logger.debug(f"[GET] {self.url} - {_ctx}")
        ok = self._url_is_valid()
        if ok:
            self.open_url()
        else:
            logger.warning(f"Bad URL - {self.url}")
        self.send_response(204 if ok else 403)
        self.end_headers()

    def _url_is_valid(self) -> bool:
        """
        Check if this GET request is a valid request
        """
        return (
            self.path == "/open"
            and self.url.startswith("https://")
            and any(
                self.host == h or self.host.endswith("." + h)
                for h in self.config.domains
            )
        )

    def _is_passthrough(self) -> bool:
        """
        Check if this GET request requires special routing
        """
        return self.host not in self.config.domains

    def open_url(self) -> None:
        if self.ruleset is None:
            logger.debug(f"Opening url {self.url} without ruleset")
            profile_directory = self.config.default_profile
        else:
            logger.debug(f"Opening url {self.url} with ruleset {self.ruleset.name}")
            profile_directory = self.ruleset.profile

        if sys.platform == "darwin":
            cmd = [
                "open",
                "-na",
                "Google Chrome",
                "--args",
                f"--profile-directory={profile_directory}",
                self.url,
            ]
        else:
            cmd = [
                "google-chrome",
                f"--profile-directory={profile_directory}",
                self.url,
            ]
        subprocess.Popen(cmd)

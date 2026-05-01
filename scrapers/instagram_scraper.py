from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import instaloader
from instaloader.exceptions import InstaloaderException, LoginException
from instaloader.instaloadercontext import InstaloaderContext, RateController

from config.settings import Settings, settings as default_settings
from extraction.schemas import RawContent
from scrapers.base import BaseScraper

_HANDLE_RE = re.compile(r"@([A-Za-z0-9._]+)")
_CHECKPOINT_URL_RE = re.compile(
    r"Point your browser to (\S+?)\s+-\s+follow",
    re.IGNORECASE | re.DOTALL,
)


def expand_instagram_checkpoint_url(login_message: str) -> str | None:
    """Turn relative checkpoint paths in Instaloader errors into a full https URL."""
    m = _CHECKPOINT_URL_RE.search(login_message)
    if not m:
        return None
    path = m.group(1).strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"https://www.instagram.com{path}"


def parse_instagram_handle(raw: str | None) -> str:
    """Pull a handle from messy CSV cells like markdown links containing @name."""
    if not raw or not str(raw).strip():
        return ""
    text = str(raw).strip()
    m = _HANDLE_RE.search(text)
    if m:
        return m.group(1)
    text = text.lstrip("@")
    if re.fullmatch(r"[A-Za-z0-9._]+", text):
        return text
    return ""


class SlowRateController(RateController):
    """Extra delay before GraphQL calls; helps avoid Instagram's short-term 401 rate limits."""

    def __init__(self, context: InstaloaderContext, extra_seconds: float):
        super().__init__(context)
        self._extra_seconds = extra_seconds

    def wait_before_query(self, query_type: str) -> None:
        if self._extra_seconds > 0 and query_type not in ("iphone", "other"):
            self.sleep(self._extra_seconds)
        super().wait_before_query(query_type)


def build_instaloader(s: Settings | None = None) -> instaloader.Instaloader:
    """
    Configure Instaloader for Instagram's current restrictions.

    Anonymous browsing of profile feeds often returns 403/401 on graphql/query;
    use INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD or a saved session file.
    """
    s = s or default_settings
    extra = getattr(s, "INSTAGRAM_EXTRA_QUERY_SLEEP", 0.0)
    rate_controller = (
        (lambda ctx: SlowRateController(ctx, extra_seconds=extra)) if extra > 0 else None
    )

    L = instaloader.Instaloader(
        sleep=True,
        quiet=False,
        max_connection_attempts=3,
        request_timeout=120.0,
        rate_controller=rate_controller,
    )

    username = (s.INSTAGRAM_USERNAME or "").strip()
    password = (s.INSTAGRAM_PASSWORD or "").strip()
    session_file = (s.INSTAGRAM_SESSION_FILE or "").strip()

    if username:
        loaded = False
        if session_file:
            path = Path(session_file)
            if path.is_file():
                try:
                    L.load_session_from_file(username, str(path))
                    loaded = True
                except (OSError, InstaloaderException):
                    loaded = False
        if not loaded:
            try:
                L.load_session_from_file(username)
            except (FileNotFoundError, OSError, InstaloaderException):
                pass

        if (
            not L.context.is_logged_in
            and password
            and not s.INSTAGRAM_SESSION_ONLY
        ):
            try:
                L.login(username, password)
            except LoginException as err:
                full = expand_instagram_checkpoint_url(str(err))
                hint = (
                    "\n\nInstagram requires a one-time security check in the browser "
                    "(checkpoint). This is normal for automated login.\n"
                )
                if full:
                    hint += f"  Open this URL while logged into the same Instagram account:\n  {full}\n"
                hint += (
                    "\nAfter you finish verification, run again. "
                    "Set INSTAGRAM_SESSION_FILE=.instagram-session (for example) "
                    "so a successful login is saved and you rarely need the password.\n"
                    "\nAlternative: in a terminal run `instaloader -l YOUR_USERNAME` "
                    "once (interactive), complete any prompts, then set "
                    "INSTAGRAM_SESSION_ONLY=true and point INSTAGRAM_SESSION_FILE "
                    "to that saved session file.\n"
                )
                raise LoginException(f"{err}{hint}") from err
            if session_file:
                path = Path(session_file)
                path.parent.mkdir(parents=True, exist_ok=True)
                L.save_session_to_file(str(path))

    return L


class InstagramScraper(BaseScraper):
    """Fetch recent posts for an organization; outputs RawContent for the LLM layer."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        max_posts: int = 30,
        days_back: int = 14,
    ):
        self.settings = settings or default_settings
        self.max_posts = max_posts
        self.days_back = days_back

    def scrape(self, org: dict[str, Any]) -> list[RawContent]:
        handle = parse_instagram_handle(
            org.get("Instagram") or org.get("instagram") or org.get("instagram_handle")
        )
        if not handle:
            return []

        organizer = (
            org.get("Name")
            or org.get("name")
            or org.get("Organization")
            or handle
        )

        L = build_instaloader(self.settings)
        profile = instaloader.Profile.from_username(L.context, handle)

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.days_back)
        out: list[RawContent] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for i, post in enumerate(profile.get_posts()):
            if i >= self.max_posts:
                break
            post_dt = post.date_utc
            if post_dt.tzinfo is None:
                post_dt = post_dt.replace(tzinfo=timezone.utc)
            if post_dt < cutoff:
                break
            caption = post.caption or ""
            out.append(
                RawContent(
                    organizer=str(organizer),
                    text=caption,
                    image_url=post.url,
                    source_url=f"https://www.instagram.com/p/{post.shortcode}/",
                    source_platform="instagram",
                    scraped_at=now_iso,
                )
            )

        return out

"""Client for the Gremlin tank monitor consumer API.

Unofficial: this is the backend that Angus Energy's "GREMLIN Tank Monitoring"
mobile app talks to. There is no public documentation; the routes below were
taken from the app itself.

    POST /consumer/signIn   {"username", "password"} -> {"token", "user": {...}}
    GET  /consumer/api      -> {"tanks": [{"key", "name", "serialNum",
                                "lastDeliveryDate", "nextDeliveryDate",
                                "geometry": {"calcTankSize", ...}}, ...]}
    GET  /consumer/api/tanks/<key>/levels?startDate=MM/DD/YYYY&endDate=MM/DD/YYYY
                            -> {"levels": [{"percent", "volume", "change",
                                "readingDate"}, ...]}

Authenticated calls send the token in an ``x-access-token`` header. A tank
monitor reports once a day, and ``readingDate`` is a calendar date stamped
``T00:00:00.000Z``, so it is parsed as a date, not an instant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import aiohttp

BASE_URL = "https://api-v1.brite2.com"
TIMEOUT = aiohttp.ClientTimeout(total=30)
LEVEL_WINDOW_DAYS = 7


class GremlinError(Exception):
    """The API answered with something unusable."""


class GremlinAuthError(GremlinError):
    """The username or password was rejected."""


class GremlinConnectionError(GremlinError):
    """The API could not be reached."""


@dataclass(frozen=True, slots=True)
class Reading:
    """One daily tank reading."""

    reading_date: date
    percent: float | None
    volume: float | None
    change: float | None


@dataclass(frozen=True, slots=True)
class Tank:
    """A monitored tank and its latest reading."""

    key: int
    name: str
    serial: str | None
    capacity: float | None
    last_delivery: date | None
    next_delivery: date | None
    latest: Reading | None


def _date(value: Any) -> date | None:
    """Parse the leading YYYY-MM-DD of an API timestamp."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class GremlinApi:
    """Signs in and reads tanks for one consumer account."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        headers = {"x-access-token": token} if token else {}
        try:
            async with self._session.request(
                method,
                BASE_URL + path,
                headers=headers,
                json=json,
                params=params,
                timeout=TIMEOUT,
            ) as resp:
                body = await resp.json(content_type=None) if resp.status == 200 else None
                return resp.status, body
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise GremlinConnectionError(f"{method} {path}: {err}") from err

    async def async_sign_in(self) -> tuple[str, str]:
        """Sign in; return (token, user id)."""
        status, body = await self._request(
            "POST",
            "/consumer/signIn",
            json={"username": self._username, "password": self._password},
        )
        if status == 401:
            raise GremlinAuthError("Invalid username or password")
        if status != 200 or not isinstance(body, dict) or not body.get("token"):
            raise GremlinError(f"Sign-in failed: HTTP {status}")
        user = body.get("user") or {}
        return body["token"], str(user.get("userId") or self._username)

    async def _get(
        self, path: str, token: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        status, body = await self._request("GET", path, token=token, params=params)
        if status != 200 or not isinstance(body, dict):
            raise GremlinError(f"GET {path}: HTTP {status}")
        return body

    async def async_get_tanks(self, today: date) -> list[Tank]:
        """Sign in fresh and return every tank on the account."""
        token, _ = await self.async_sign_in()
        account = await self._get("/consumer/api", token)
        window = {
            "startDate": (today - timedelta(days=LEVEL_WINDOW_DAYS)).strftime("%m/%d/%Y"),
            "endDate": today.strftime("%m/%d/%Y"),
        }
        tanks: list[Tank] = []
        for raw in account.get("tanks") or []:
            key = raw.get("key")
            if key is None:
                continue
            levels = await self._get(f"/consumer/api/tanks/{key}/levels", token, window)
            readings = [
                Reading(
                    reading_date=day,
                    percent=_float(lvl.get("percent")),
                    volume=_float(lvl.get("volume")),
                    change=_float(lvl.get("change")),
                )
                for lvl in levels.get("levels") or []
                if (day := _date(lvl.get("readingDate"))) is not None
            ]
            geometry = raw.get("geometry") or {}
            tanks.append(
                Tank(
                    key=int(key),
                    name=str(raw.get("name") or f"Tank {key}"),
                    serial=str(raw["serialNum"]) if raw.get("serialNum") else None,
                    capacity=_float(geometry.get("calcTankSize")),
                    last_delivery=_date(raw.get("lastDeliveryDate")),
                    next_delivery=_date(raw.get("nextDeliveryDate")),
                    latest=max(readings, key=lambda r: r.reading_date, default=None),
                )
            )
        return tanks

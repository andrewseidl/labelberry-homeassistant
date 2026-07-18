"""Typed async client for the LabelBerry HTTP API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from .const import REQUEST_TIMEOUT_SECONDS


class LabelBerryApiError(Exception):
    """Base class for LabelBerry client errors."""


class LabelBerryConnectionError(LabelBerryApiError):
    """The LabelBerry server could not be reached."""


class LabelBerryResponseError(LabelBerryApiError):
    """The LabelBerry server returned an incompatible response."""


class LabelBerryBackendError(LabelBerryApiError):
    """A structured LabelBerry backend error."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True, slots=True)
class LabelBerryStatus:
    """Printer status returned by LabelBerry."""

    connected: bool
    tape_width_mm: float | None
    backend: str


@dataclass(frozen=True, slots=True)
class QueuedJob:
    """Accepted LabelBerry print job."""

    id: str
    status: str
    copies: int
    error: str | None


def _queued_job(payload: Any, operation: str) -> QueuedJob:
    """Validate and return one queued print job."""
    if not isinstance(payload, dict):
        raise LabelBerryResponseError(f"{operation} response must be a JSON object")

    job_id = payload.get("id")
    status = payload.get("status")
    response_copies = payload.get("copies")
    error = payload.get("error")
    if not isinstance(job_id, str) or not isinstance(status, str):
        raise LabelBerryResponseError(f"{operation} response has invalid id or status")
    if isinstance(response_copies, bool) or not isinstance(response_copies, int):
        raise LabelBerryResponseError(f"{operation} response copies must be an integer")
    if error is not None and not isinstance(error, str):
        raise LabelBerryResponseError(f"{operation} response error must be a string or null")

    return QueuedJob(job_id, status, response_copies, error)


def normalize_base_url(value: str) -> str:
    """Normalize and validate a LabelBerry HTTP(S) base URL."""
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("LabelBerry URL must use HTTP or HTTPS and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("LabelBerry URL must not contain credentials")

    try:
        port = parsed.port
    except ValueError as err:
        raise ValueError("LabelBerry URL contains an invalid port") from err

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = f"{host}:{port}" if port is not None else host
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


class LabelBerryClient:
    """Async client for one LabelBerry server."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self.base_url = normalize_base_url(base_url)

    async def async_get_status(self) -> LabelBerryStatus:
        """Return validated printer status."""
        payload = await self._async_request_json("GET", "/api/status", expected_status=200)
        if not isinstance(payload, dict):
            raise LabelBerryResponseError("status response must be a JSON object")

        connected = payload.get("connected")
        tape_width = payload.get("tape_width_mm")
        backend = payload.get("backend")
        if type(connected) is not bool:
            raise LabelBerryResponseError("status connected must be a boolean")
        if tape_width is not None and (
            isinstance(tape_width, bool) or not isinstance(tape_width, (int, float))
        ):
            raise LabelBerryResponseError("status tape_width_mm must be numeric or null")
        if not isinstance(backend, str):
            raise LabelBerryResponseError("status backend must be a string")

        return LabelBerryStatus(
            connected=connected,
            tape_width_mm=float(tape_width) if tape_width is not None else None,
            backend=backend,
        )

    async def async_quick_print(
        self,
        text: str,
        *,
        copies: int = 1,
        left: str | None = None,
        right: str | None = None,
    ) -> QueuedJob:
        """Queue one quick-print request without retrying it."""
        request: dict[str, Any] = {"text": text, "copies": copies}
        if left is not None:
            request["left"] = left
        if right is not None:
            request["right"] = right

        payload = await self._async_request_json(
            "POST", "/api/quick-print", expected_status=201, json=request
        )
        return _queued_job(payload, "quick-print")

    async def async_print_template(
        self,
        template: str,
        variables: dict[str, str],
        *,
        copies: int = 1,
    ) -> QueuedJob:
        """Queue one template-print request without retrying it."""
        payload = await self._async_request_json(
            "POST",
            "/api/templates/print",
            expected_status=201,
            json={"name": template, "variables": variables, "copies": copies},
        )
        return _queued_job(payload, "template-print")

    async def _async_request_json(
        self,
        method: str,
        path: str,
        *,
        expected_status: int,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Request and decode one LabelBerry JSON response."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async with self._session.request(
                    method, f"{self.base_url}{path}", json=json
                ) as response:
                    try:
                        payload = await response.json(content_type=None)
                    except (TypeError, ValueError) as err:
                        raise LabelBerryResponseError("LabelBerry returned invalid JSON") from err

                    if response.status != expected_status:
                        if (
                            isinstance(payload, dict)
                            and isinstance(payload.get("code"), str)
                            and isinstance(payload.get("message"), str)
                        ):
                            raise LabelBerryBackendError(
                                payload["code"], payload["message"], response.status
                            )
                        raise LabelBerryResponseError(
                            f"LabelBerry returned unexpected HTTP {response.status}"
                        )
                    return payload
        except (aiohttp.ClientError, TimeoutError) as err:
            raise LabelBerryConnectionError(f"Unable to reach {self.base_url}") from err

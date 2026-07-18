import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.labelberry.api import (
    LabelBerryBackendError,
    LabelBerryClient,
    LabelBerryConnectionError,
    LabelBerryResponseError,
    LabelBerryStatus,
    QueuedJob,
    normalize_base_url,
)

BASE_URL = "http://labelberry.local:8000"
STATUS_URL = f"{BASE_URL}/api/status"
PRINT_URL = f"{BASE_URL}/api/quick-print"
TEMPLATE_PRINT_URL = f"{BASE_URL}/api/templates/print"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" HTTP://Example.COM:8000/prefix/?x=1#f ", "http://example.com:8000/prefix"),
        ("https://example.com/", "https://example.com"),
        ("http://[::1]:8000/base///", "http://[::1]:8000/base"),
    ],
)
def test_normalize_base_url(value: str, expected: str) -> None:
    assert normalize_base_url(value) == expected


@pytest.mark.parametrize("value", ["ftp://labelberry.local", "http:///missing", "not-a-url"])
def test_normalize_base_url_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_base_url(value)


async def test_get_status_returns_typed_data(hass, aioclient_mock) -> None:
    aioclient_mock.get(
        STATUS_URL,
        json={"connected": True, "tape_width_mm": 12.0, "backend": "usb"},
    )
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    status = await client.async_get_status()

    assert status == LabelBerryStatus(connected=True, tape_width_mm=12.0, backend="usb")


async def test_quick_print_preserves_multiline_and_unicode_flanks(hass, aioclient_mock) -> None:
    aioclient_mock.post(
        PRINT_URL,
        json={"id": "abc123", "status": "queued", "copies": 2, "error": None},
        status=201,
    )
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    job = await client.async_quick_print("Cold\nWash", copies=2, left="🧺", right="🌬️")

    assert aioclient_mock.mock_calls[-1][2] == {
        "text": "Cold\nWash",
        "copies": 2,
        "left": "🧺",
        "right": "🌬️",
    }
    assert job == QueuedJob(id="abc123", status="queued", copies=2, error=None)


async def test_quick_print_omits_missing_flanks(hass, aioclient_mock) -> None:
    aioclient_mock.post(
        PRINT_URL,
        json={"id": "abc123", "status": "queued", "copies": 1, "error": None},
        status=201,
    )
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    await client.async_quick_print("Pantry", copies=1)

    assert aioclient_mock.mock_calls[-1][2] == {"text": "Pantry", "copies": 1}


async def test_template_print_preserves_unicode_variables(hass, aioclient_mock) -> None:
    aioclient_mock.post(
        TEMPLATE_PRINT_URL,
        json={"id": "abc123", "status": "queued", "copies": 2, "error": None},
        status=201,
    )
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    job = await client.async_print_template("Leftovers", {"food": "Crème 🫐\nA=B"}, copies=2)

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[-1][2] == {
        "name": "Leftovers",
        "variables": {"food": "Crème 🫐\nA=B"},
        "copies": 2,
    }
    assert job == QueuedJob(id="abc123", status="queued", copies=2, error=None)


@pytest.mark.parametrize("status", [307, 308])
async def test_template_print_does_not_follow_redirects_or_replay_post(status) -> None:
    redirected_url = f"{BASE_URL}/redirected/templates/print"

    class Response:
        def __init__(self, response_status, payload):
            self.status = response_status
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def json(self, *, content_type=None):
            return self._payload

    class RedirectingSession:
        def __init__(self):
            self.calls = []

        def request(self, method, url, **kwargs):
            self.calls.append((method, url, kwargs))
            if kwargs.get("allow_redirects", True):
                self.calls.append((method, redirected_url, kwargs))
                return Response(
                    201,
                    {"id": "duplicate", "status": "queued", "copies": 1, "error": None},
                )
            return Response(status, {"detail": "redirect refused"})

    session = RedirectingSession()
    client = LabelBerryClient(session, BASE_URL)

    with pytest.raises(LabelBerryResponseError):
        await client.async_print_template("Pantry", {})

    assert len(session.calls) == 1
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1] == TEMPLATE_PRINT_URL
    assert session.calls[0][2]["allow_redirects"] is False


@pytest.mark.parametrize(
    "response",
    [
        [],
        {"id": 1, "status": "queued", "copies": 1, "error": None},
        {"id": "abc123", "status": None, "copies": 1, "error": None},
        {"id": "abc123", "status": "queued", "copies": True, "error": None},
        {"id": "abc123", "status": "queued", "copies": 1, "error": 1},
    ],
)
@pytest.mark.parametrize("operation", ["quick", "template"])
async def test_print_operations_reject_invalid_job_shapes(
    hass, aioclient_mock, response, operation
) -> None:
    url = PRINT_URL if operation == "quick" else TEMPLATE_PRINT_URL
    aioclient_mock.post(url, json=response, status=201)
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(LabelBerryResponseError):
        if operation == "quick":
            await client.async_quick_print("Pantry")
        else:
            await client.async_print_template("Pantry", {})


async def test_structured_backend_error_is_preserved(hass, aioclient_mock) -> None:
    aioclient_mock.post(
        PRINT_URL,
        json={"code": "render_error", "message": "too wide"},
        status=422,
    )
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(LabelBerryBackendError) as caught:
        await client.async_quick_print("wide")

    assert caught.value.code == "render_error"
    assert caught.value.message == "too wide"
    assert caught.value.status == 422


@pytest.mark.parametrize(
    "response",
    [
        {"connected": 1, "tape_width_mm": 12, "backend": "usb"},
        {"connected": True, "tape_width_mm": "12", "backend": "usb"},
        {"connected": True, "tape_width_mm": 12, "backend": None},
    ],
)
async def test_get_status_rejects_invalid_shapes(hass, aioclient_mock, response) -> None:
    aioclient_mock.get(STATUS_URL, json=response)
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(LabelBerryResponseError):
        await client.async_get_status()


async def test_non_json_response_is_invalid(hass, aioclient_mock) -> None:
    aioclient_mock.get(STATUS_URL, text="not json")
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(LabelBerryResponseError):
        await client.async_get_status()


@pytest.mark.parametrize("error", [aiohttp.ClientConnectionError(), TimeoutError()])
async def test_connection_failures_are_typed_and_not_retried(hass, aioclient_mock, error) -> None:
    aioclient_mock.get(STATUS_URL, exc=error)
    client = LabelBerryClient(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(LabelBerryConnectionError):
        await client.async_get_status()

    assert aioclient_mock.call_count == 1

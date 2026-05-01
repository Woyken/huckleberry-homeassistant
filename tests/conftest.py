"""Pytest fixtures for Huckleberry integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from huckleberry_api.firebase_types import (
    FirebaseChildDocument,
    FirebaseUserChildRef,
    FirebaseUserDocument,
)


def _make_user_document(*child_refs: FirebaseUserChildRef) -> FirebaseUserDocument:
    """Build a minimal FirebaseUserDocument."""
    return FirebaseUserDocument(
        email="test@example.com",
        childList=list(child_refs),
    )


def _make_child_ref(cid: str, nickname: str | None = None) -> FirebaseUserChildRef:
    """Build a minimal FirebaseUserChildRef."""
    return FirebaseUserChildRef(cid=cid, nickname=nickname)


def _make_child_document(
    name: str,
    birthdate: str | None = None,
    gender: str | None = None,
) -> FirebaseChildDocument:
    """Build a minimal FirebaseChildDocument."""
    return FirebaseChildDocument(
        childsName=name,
        birthdate=birthdate,
        gender=gender,
    )


CHILD_REFS_SINGLE = [_make_child_ref("child_1")]
CHILD_DOCS_SINGLE = {"child_1": _make_child_document("Test Child", "2023-01-01", "M")}

CHILD_REFS_MULTI = [
    _make_child_ref("child_1"),
    _make_child_ref("child_2"),
    _make_child_ref("child_3"),
]
CHILD_DOCS_MULTI = {
    "child_1": _make_child_document("First Child", "2023-01-01", "M"),
    "child_2": _make_child_document("Second Child", "2023-06-15", "F"),
    "child_3": _make_child_document("Third Child", "2024-03-20", "M"),
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


def _build_mock_api(
    child_refs: list[FirebaseUserChildRef],
    child_docs: dict[str, FirebaseChildDocument],
) -> MagicMock:
    """Build a mock HuckleberryAPI backed by async mocks."""
    mock = MagicMock()
    mock.authenticate = AsyncMock()
    mock.ensure_session = AsyncMock()
    mock.get_user = AsyncMock(return_value=_make_user_document(*child_refs))
    mock.get_child = AsyncMock(side_effect=lambda cid: child_docs.get(cid))

    mock.setup_sleep_listener = AsyncMock()
    mock.setup_feed_listener = AsyncMock()
    mock.setup_health_listener = AsyncMock()
    mock.setup_diaper_listener = AsyncMock()
    mock.setup_child_listener = AsyncMock()
    mock.stop_all_listeners = AsyncMock()

    mock.start_sleep = AsyncMock()
    mock.pause_sleep = AsyncMock()
    mock.resume_sleep = AsyncMock()
    mock.cancel_sleep = AsyncMock()
    mock.complete_sleep = AsyncMock()

    mock.start_nursing = AsyncMock()
    mock.pause_nursing = AsyncMock()
    mock.resume_nursing = AsyncMock()
    mock.switch_nursing_side = AsyncMock()
    mock.cancel_nursing = AsyncMock()
    mock.complete_nursing = AsyncMock()

    mock.log_diaper = AsyncMock()
    mock.log_potty = AsyncMock()
    mock.log_growth = AsyncMock()
    mock.log_bottle = AsyncMock()

    mock.list_sleep_intervals = AsyncMock(return_value=[])
    mock.list_feed_intervals = AsyncMock(return_value=[])
    mock.list_diaper_intervals = AsyncMock(return_value=[])
    mock.list_health_entries = AsyncMock(return_value=[])

    mock.user_uid = "test_user_uid"

    return mock


@pytest.fixture
def mock_huckleberry_api():
    """Mock the Huckleberry API."""
    return _build_mock_api(CHILD_REFS_SINGLE, CHILD_DOCS_SINGLE)


@pytest.fixture
def mock_huckleberry_api_multiple_children():
    """Mock the Huckleberry API with multiple children."""
    return _build_mock_api(CHILD_REFS_MULTI, CHILD_DOCS_MULTI)


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.huckleberry.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup

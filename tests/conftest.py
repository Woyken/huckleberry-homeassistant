"""Pytest fixtures for Huckleberry integration tests."""

from __future__ import annotations

import sys
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    """Allow Windows' Proactor loop creation under pytest-socket.

    On Windows, asyncio's Proactor event loop creates an internal socket pair
    during initialization. Home Assistant's test tooling blocks socket creation
    via pytest-socket, which causes event loop creation to crash.

    We enable sockets only while the pytest-asyncio `event_loop` fixture is being
    created, then restore the prior socket restrictions immediately after.
    """

    if sys.platform != "win32" or fixturedef.argname != "event_loop":
        yield
        return

    try:
        from pytest_socket import enable_socket
    except ImportError:  # pragma: no cover
        yield
        return

    prev_socket = socket.socket
    prev_connect = socket.socket.connect
    enable_socket()
    try:
        yield
    finally:
        socket.socket = prev_socket
        socket.socket.connect = prev_connect


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_huckleberry_api():
    """Mock the Huckleberry API."""
    mock = MagicMock()
    mock.user_uid = "test_user_uid"
    mock.authenticate = AsyncMock()
    mock.get_user = AsyncMock(
        return_value=SimpleNamespace(
            childList=[
                SimpleNamespace(
                    cid="child_1",
                    nickname="Test Child",
                    picture=None,
                    color=None,
                )
            ]
        )
    )
    mock.get_child = AsyncMock(
        return_value=SimpleNamespace(
            childsName="Test Child",
            birthdate="2023-01-01",
            gender="M",
            picture=None,
            color=None,
            createdAt=None,
            nightStart=None,
            morningCutoff=None,
            naps=None,
            categories=None,
        )
    )
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
    mock.log_growth = AsyncMock()
    mock.log_bottle = AsyncMock()
    mock.setup_sleep_listener = AsyncMock()
    mock.setup_feed_listener = AsyncMock()
    mock.setup_health_listener = AsyncMock()
    mock.setup_diaper_listener = AsyncMock()
    mock.stop_all_listeners = AsyncMock()
    mock.ensure_session = AsyncMock()
    mock.list_sleep_intervals = AsyncMock(return_value=[])
    mock.list_feed_intervals = AsyncMock(return_value=[])
    mock.list_diaper_intervals = AsyncMock(return_value=[])
    mock.list_health_entries = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_huckleberry_api_multiple_children():
    """Mock the Huckleberry API with multiple children."""
    mock = MagicMock()
    mock.user_uid = "test_user_uid"
    mock.authenticate = AsyncMock()
    mock.get_user = AsyncMock(
        return_value=SimpleNamespace(
            childList=[
                SimpleNamespace(cid="child_1", nickname="First Child", picture=None, color=None),
                SimpleNamespace(cid="child_2", nickname="Second Child", picture=None, color=None),
                SimpleNamespace(cid="child_3", nickname="Third Child", picture=None, color=None),
            ]
        )
    )
    child_docs = {
        "child_1": SimpleNamespace(
            childsName="First Child",
            birthdate="2023-01-01",
            gender="M",
            picture=None,
            color=None,
            createdAt=None,
            nightStart=None,
            morningCutoff=None,
            naps=None,
            categories=None,
        ),
        "child_2": SimpleNamespace(
            childsName="Second Child",
            birthdate="2023-06-15",
            gender="F",
            picture=None,
            color=None,
            createdAt=None,
            nightStart=None,
            morningCutoff=None,
            naps=None,
            categories=None,
        ),
        "child_3": SimpleNamespace(
            childsName="Third Child",
            birthdate="2024-03-20",
            gender="M",
            picture=None,
            color=None,
            createdAt=None,
            nightStart=None,
            morningCutoff=None,
            naps=None,
            categories=None,
        ),
    }
    mock.get_child = AsyncMock(side_effect=lambda child_uid: child_docs[child_uid])
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
    mock.log_growth = AsyncMock()
    mock.log_bottle = AsyncMock()
    mock.setup_sleep_listener = AsyncMock()
    mock.setup_feed_listener = AsyncMock()
    mock.setup_health_listener = AsyncMock()
    mock.setup_diaper_listener = AsyncMock()
    mock.stop_all_listeners = AsyncMock()
    mock.ensure_session = AsyncMock()
    mock.list_sleep_intervals = AsyncMock(return_value=[])
    mock.list_feed_intervals = AsyncMock(return_value=[])
    mock.list_diaper_intervals = AsyncMock(return_value=[])
    mock.list_health_entries = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.huckleberry.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup

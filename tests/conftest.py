"""Pytest fixtures for Huckleberry integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_huckleberry_api():
    """Mock the Huckleberry API."""
    mock = MagicMock()
    mock.authenticate = MagicMock()
    mock.get_children = MagicMock(
        return_value=[
            {
                "uid": "child_1",
                "name": "Test Child",
                "birthday": "2023-01-01",
                "gender": "boy",
                "profilePictureUrl": None,
            }
        ]
    )
    mock.setup_realtime_listener = MagicMock()
    mock.setup_feed_listener = MagicMock()
    mock.setup_health_listener = MagicMock()
    mock.setup_diaper_listener = MagicMock()
    mock.stop_all_listeners = MagicMock()
    mock.log_bottle_feeding = MagicMock()
    return mock


@pytest.fixture
def mock_huckleberry_api_multiple_children():
    """Mock the Huckleberry API with multiple children."""
    mock = MagicMock()
    mock.authenticate = MagicMock()
    mock.get_children = MagicMock(
        return_value=[
            {
                "uid": "child_1",
                "name": "First Child",
                "birthday": "2023-01-01",
                "gender": "boy",
                "profilePictureUrl": None,
            },
            {
                "uid": "child_2",
                "name": "Second Child",
                "birthday": "2023-06-15",
                "gender": "girl",
                "profilePictureUrl": None,
            },
            {
                "uid": "child_3",
                "name": "Third Child",
                "birthday": "2024-03-20",
                "gender": "boy",
                "profilePictureUrl": None,
            },
        ]
    )
    mock.setup_realtime_listener = MagicMock()
    mock.setup_feed_listener = MagicMock()
    mock.setup_health_listener = MagicMock()
    mock.setup_diaper_listener = MagicMock()
    mock.stop_all_listeners = MagicMock()
    mock.log_bottle_feeding = MagicMock()
    return mock

@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.huckleberry.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup

"""Test the last solid food meal sensor."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from huckleberry_api.firebase_types import (
    FirebaseFeedDocumentData,
    FirebaseFeedPrefs,
    FirebaseLastSolidData,
    SolidsFoodEntry,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huckleberry.const import DOMAIN


@pytest.fixture
async def solids_feed_callback(hass: HomeAssistant, mock_huckleberry_api_multiple_children):
    """Set up sensors and return the first child's feed listener callback."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api_multiple_children,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return mock_huckleberry_api_multiple_children.setup_feed_listener.call_args_list[0].args[1]


@pytest.mark.parametrize("reaction", ["LOVED", "MEH", "HATED", "ALLERGIC"])
async def test_solids_sensor(hass: HomeAssistant, solids_feed_callback, reaction):
    """Feed listener updates expose meal data for the correct child."""
    solids_feed_callback(FirebaseFeedDocumentData(prefs=FirebaseFeedPrefs(
        lastSolid=FirebaseLastSolidData(
            start=1700000000,
            foods={
                "apple": SolidsFoodEntry(id="apple", created_name="Apple", source="curated"),
                "porridge": SolidsFoodEntry(id="porridge", created_name="Porridge", source="custom"),
            },
            notes="Lunch",
            reactions={"LOVED": False, reaction: True},
        ),
    )))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.first_child_solids")
    assert state is not None
    expected_time = datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    assert state.state == expected_time
    assert state.attributes["device_class"] == "timestamp"
    assert state.attributes["time"] == expected_time
    assert state.attributes["foods"] == ["Apple", "Porridge"]
    assert state.attributes["notes"] == "Lunch"
    assert state.attributes["reaction"] == reaction
    assert "reactions" not in state.attributes

    registry_entry = er.async_get(hass).async_get("sensor.first_child_solids")
    assert registry_entry is not None
    assert registry_entry.unique_id == "child_1_solids"
    for child in ("second_child", "third_child"):
        other = hass.states.get(f"sensor.{child}_solids")
        assert other is not None
        assert other.state == "unknown"
        assert "foods" not in other.attributes

    # A later meal without optional details must clear the previous attributes.
    solids_feed_callback(FirebaseFeedDocumentData(prefs=FirebaseFeedPrefs(
        lastSolid=FirebaseLastSolidData(start=1700001000),
    )))
    await hass.async_block_till_done()
    state = hass.states.get("sensor.first_child_solids")
    assert state is not None
    assert state.state == datetime.fromtimestamp(1700001000, tz=timezone.utc).isoformat()
    for attribute in ("foods", "notes", "reaction"):
        assert attribute not in state.attributes


@pytest.mark.parametrize("feed", [
    None,
    FirebaseFeedDocumentData(),
    FirebaseFeedDocumentData(prefs=FirebaseFeedPrefs()),
    FirebaseFeedDocumentData(prefs=FirebaseFeedPrefs(lastSolid=FirebaseLastSolidData())),
])
async def test_solids_sensor_missing_data(hass: HomeAssistant, solids_feed_callback, feed):
    """Missing feed data or meal timestamps leave the sensor unknown."""
    if feed is not None:
        solids_feed_callback(feed)
        await hass.async_block_till_done()
    state = hass.states.get("sensor.first_child_solids")
    assert state is not None
    assert state.state == "unknown"
    for attribute in ("time", "foods", "notes", "reaction"):
        assert attribute not in state.attributes


async def test_solids_sensor_empty_details(hass: HomeAssistant, solids_feed_callback):
    """Empty foods and unselected reactions do not invent meal details."""
    solids_feed_callback(FirebaseFeedDocumentData(prefs=FirebaseFeedPrefs(
        lastSolid=FirebaseLastSolidData(start=1700000000, foods={}, reactions={"MEH": False}),
    )))
    await hass.async_block_till_done()
    state = hass.states.get("sensor.first_child_solids")
    assert state is not None
    assert state.attributes["foods"] == []
    assert "reaction" not in state.attributes

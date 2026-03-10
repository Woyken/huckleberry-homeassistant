import pytest
import os
import logging
import pytest_socket
from homeassistant.core import HomeAssistant
from custom_components.huckleberry.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

_LOGGER = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_live_connection(hass: HomeAssistant, socket_enabled):
    """Test live connection to Huckleberry API."""

    # Explicitly allow Google hosts
    pytest_socket.socket_allow_hosts(["127.0.0.1", "identitytoolkit.googleapis.com", "firestore.googleapis.com", "oauth2.googleapis.com"])

    email = os.environ.get("HUCKLEBERRY_EMAIL")
    password = os.environ.get("HUCKLEBERRY_PASSWORD")

    if not email or not password:
        pytest.skip("HUCKLEBERRY_EMAIL and HUCKLEBERRY_PASSWORD must be set")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": email,
            "password": password
        }
    )
    entry.add_to_hass(hass)

    # Setup the integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check if we have any sensors
    sensors = hass.states.async_entity_ids("sensor")
    _LOGGER.error(f"Available sensors: {sensors}")

    # We expect at least the children count sensor
    children_sensor = "sensor.huckleberry_children"
    if children_sensor not in sensors:
        pytest.fail("Children sensor not found")

    state = hass.states.get(children_sensor)
    assert state is not None
    assert state.state != "unavailable"
    assert int(state.state) > 0

    # Check child profile sensor
    # We don't know the child name in advance easily without parsing the children sensor,
    # but we saw 'sensor.testificate' in the logs.
    # Let's dynamically find it.

    child_profile_sensor = None
    for sensor in sensors:
        if sensor != "sensor.huckleberry_children" and not sensor.endswith("_growth") and not sensor.endswith("_last_diaper"):
            child_profile_sensor = sensor
            break

    if child_profile_sensor:
        state = hass.states.get(child_profile_sensor)
        assert state is not None
        assert state.state != "unavailable"
        # The state should be the child's name
        assert len(state.state) > 0

    # Check growth sensor
    growth_sensor = None
    for sensor in sensors:
        if sensor.endswith("_growth"):
            growth_sensor = sensor
            break

    if growth_sensor:
        state = hass.states.get(growth_sensor)
        assert state is not None
        # It might be "No data" or a timestamp, but shouldn't be unavailable
        assert state.state != "unavailable"

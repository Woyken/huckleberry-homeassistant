"""Test Huckleberry services."""
from unittest.mock import ANY, patch
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from huckleberry_api.firebase_types import (
    FirebaseCuratedFoodDocument,
    FirebaseCustomFoodTypeDocument,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_services(hass: HomeAssistant, mock_huckleberry_api):
    """Test all services."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Create a device to target
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test_child_uid")},
        name="Test Child"
    )

    # Test start_sleep
    await hass.services.async_call(
        DOMAIN, "start_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.start_sleep.assert_called_with("test_child_uid")

    # Test pause_sleep
    await hass.services.async_call(
        DOMAIN, "pause_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.pause_sleep.assert_called_with("test_child_uid")

    # Test resume_sleep
    await hass.services.async_call(
        DOMAIN, "resume_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.resume_sleep.assert_called_with("test_child_uid")

    # Test cancel_sleep
    await hass.services.async_call(
        DOMAIN, "cancel_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.cancel_sleep.assert_called_with("test_child_uid")

    # Test complete_sleep
    await hass.services.async_call(
        DOMAIN, "complete_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.complete_sleep.assert_called_with("test_child_uid")

    # Test start_nursing (left)
    await hass.services.async_call(
        DOMAIN, "start_nursing", {"device_id": device.id, "side": "left"}, blocking=True
    )
    mock_huckleberry_api.start_nursing.assert_called_with("test_child_uid", "left")

    # Test start_nursing (right)
    await hass.services.async_call(
        DOMAIN, "start_nursing", {"device_id": device.id, "side": "right"}, blocking=True
    )
    mock_huckleberry_api.start_nursing.assert_called_with("test_child_uid", "right")

    # Test pause_nursing
    await hass.services.async_call(
        DOMAIN, "pause_nursing", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.pause_nursing.assert_called_with("test_child_uid")

    # Test resume_nursing
    await hass.services.async_call(
        DOMAIN, "resume_nursing", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.resume_nursing.assert_called_with("test_child_uid", None)

    # Test switch_nursing_side
    await hass.services.async_call(
        DOMAIN, "switch_nursing_side", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.switch_nursing_side.assert_called_with("test_child_uid")

    # Test cancel_nursing
    await hass.services.async_call(
        DOMAIN, "cancel_nursing", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.cancel_nursing.assert_called_with("test_child_uid")

    # Test complete_nursing
    await hass.services.async_call(
        DOMAIN, "complete_nursing", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.complete_nursing.assert_called_with("test_child_uid")

    # Test log_diaper_pee
    await hass.services.async_call(
        DOMAIN, "log_diaper_pee", {"device_id": device.id, "pee_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="pee",
        pee_amount="medium",
        diaper_rash=False,
        notes=None,
    )

    # Test log_diaper_poo
    await hass.services.async_call(
        DOMAIN, "log_diaper_poo", {"device_id": device.id, "poo_amount": "big", "color": "brown", "consistency": "solid"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="poo",
        poo_amount="big",
        color="brown",
        consistency="solid",
        diaper_rash=False,
        notes=None,
    )

    # Test log_diaper_both
    await hass.services.async_call(
        DOMAIN, "log_diaper_both", {"device_id": device.id, "pee_amount": "little", "poo_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="both",
        pee_amount="little",
        poo_amount="medium",
        color=None,
        consistency=None,
        diaper_rash=False,
        notes=None,
    )

    # Test log_diaper_dry
    await hass.services.async_call(
        DOMAIN, "log_diaper_dry", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="dry",
        diaper_rash=False,
        notes=None,
    )

    # Test log_potty_pee
    await hass.services.async_call(
        DOMAIN, "log_potty_pee", {"device_id": device.id, "pee_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_potty.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="pee",
        pee_amount="medium",
        how_it_happened="wentPotty",
        notes=None,
    )

    # Test log_potty_poo
    await hass.services.async_call(
        DOMAIN, "log_potty_poo", {"device_id": device.id, "poo_amount": "big", "color": "brown", "consistency": "solid"}, blocking=True
    )
    mock_huckleberry_api.log_potty.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="poo",
        poo_amount="big",
        color="brown",
        consistency="solid",
        how_it_happened="wentPotty",
        notes=None,
    )

    # Test log_potty_both
    await hass.services.async_call(
        DOMAIN, "log_potty_both", {"device_id": device.id, "pee_amount": "little", "poo_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_potty.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="both",
        pee_amount="little",
        poo_amount="medium",
        color=None,
        consistency=None,
        how_it_happened="wentPotty",
        notes=None,
    )

    # Test log_potty_dry
    await hass.services.async_call(
        DOMAIN, "log_potty_dry", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.log_potty.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        mode="dry",
        how_it_happened="satButDry",
        notes=None,
    )

    # Test log_growth
    await hass.services.async_call(
        DOMAIN, "log_growth", {"device_id": device.id, "weight": 10.5, "height": 75.0, "head": 45.0, "units": "metric"}, blocking=True
    )
    mock_huckleberry_api.log_growth.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        weight=10.5,
        height=75.0,
        head=45.0,
        units="metric",
    )

    # Test log_bottle
    await hass.services.async_call(
        DOMAIN, "log_bottle", {"device_id": device.id, "amount": 4.0, "bottle_type": "formula", "units": "oz"}, blocking=True
    )
    mock_huckleberry_api.log_bottle.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        amount=4.0,
        bottle_type="Formula",
        units="oz",
    )

    # Test log_bottle with app-specific bottle type values
    await hass.services.async_call(
        DOMAIN, "log_bottle", {"device_id": device.id, "amount": 120.0, "bottle_type": "Breast Milk", "units": "ml"}, blocking=True
    )
    mock_huckleberry_api.log_bottle.assert_called_with(
        "test_child_uid",
        start_time=ANY,
        amount=120.0,
        bottle_type="Breast Milk",
        units="ml",
    )

    # Configure mock food catalogs
    mock_huckleberry_api.list_solids_curated_foods.return_value = [
        FirebaseCuratedFoodDocument(
            id="banana_curated",
            name="Banana",
            source="curated",
            aka=["plantain"],
        ),
        FirebaseCuratedFoodDocument(
            id="apple_curated",
            name="Apple",
            source="curated",
        ),
    ]
    mock_huckleberry_api.list_solids_custom_foods.return_value = [
        FirebaseCustomFoodTypeDocument(
            id="custom_oatmeal_id",
            name="Oatmeal",
            source="custom",
            archived=False,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            type="solids",
            image="",
        )
    ]

    # Test log_solids - curated food matching (by name and alias)
    await hass.services.async_call(
        DOMAIN,
        "log_solids",
        {"device_id": device.id, "foods": ["Banana", "plantain"]},
        blocking=True,
    )
    call_args = mock_huckleberry_api.log_solids.call_args
    assert call_args.args == ("test_child_uid",)
    assert call_args.kwargs["notes"] == ""
    assert call_args.kwargs["reaction"] is None
    assert len(call_args.kwargs["foods"]) == 2
    assert call_args.kwargs["foods"][0].id == "banana_curated"
    assert call_args.kwargs["foods"][0].name == "Banana"
    assert call_args.kwargs["foods"][0].source == "curated"
    assert call_args.kwargs["foods"][1].id == "banana_curated"
    assert call_args.kwargs["foods"][1].name == "Banana"
    assert call_args.kwargs["foods"][1].source == "curated"
    mock_huckleberry_api.create_solids_custom_food.assert_not_called()

    # Test log_solids - custom food reuse
    await hass.services.async_call(
        DOMAIN,
        "log_solids",
        {"device_id": device.id, "foods": ["oatmeal"]},
        blocking=True,
    )
    call_args = mock_huckleberry_api.log_solids.call_args
    assert len(call_args.kwargs["foods"]) == 1
    assert call_args.kwargs["foods"][0].id == "custom_oatmeal_id"
    assert call_args.kwargs["foods"][0].name == "Oatmeal"
    assert call_args.kwargs["foods"][0].source == "custom"
    mock_huckleberry_api.create_solids_custom_food.assert_not_called()

    # Test log_solids - new custom food creation with lowercase reaction (UI)
    await hass.services.async_call(
        DOMAIN,
        "log_solids",
        {
            "device_id": device.id,
            "foods": ["Dragon Fruit"],
            "notes": "Loved it",
            "reaction": "loved",
        },
        blocking=True,
    )
    mock_huckleberry_api.create_solids_custom_food.assert_called_once_with(
        "test_child_uid", "Dragon Fruit"
    )
    call_args = mock_huckleberry_api.log_solids.call_args
    assert call_args.kwargs["notes"] == "Loved it"
    assert call_args.kwargs["reaction"] == "LOVED"
    assert len(call_args.kwargs["foods"]) == 1
    assert call_args.kwargs["foods"][0].id == "custom_dragon_fruit"
    assert call_args.kwargs["foods"][0].name == "Dragon Fruit"
    assert call_args.kwargs["foods"][0].source == "custom"

    # Test log_solids - empty foods list rejected
    import pytest as _pytest
    with _pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN,
            "log_solids",
            {"device_id": device.id, "foods": []},
            blocking=True,
        )

async def test_service_no_target_raises(hass: HomeAssistant, mock_huckleberry_api):
    """Test that calling a service without device_id raises an error."""
    import pytest

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Calling without device_id should raise (schema requires device_id)
    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN, "start_sleep", {}, blocking=True
        )

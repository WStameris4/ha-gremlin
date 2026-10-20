"""Setup and sensor tests."""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gremlin.const import DOMAIN

from .conftest import ACCOUNT, ACCOUNT_URL, LEVELS_URL, SIGN_IN, SIGN_IN_URL, TANK_KEY

PREFIX = "sensor.propane_1_x_120_gal_ag"


@pytest.mark.freeze_time("2026-10-20 15:00:00-04:00")
async def test_sensors(
    hass: HomeAssistant,
    api_ok: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    # Newest reading wins regardless of the order the API lists them in.
    assert hass.states.get(f"{PREFIX}_level").state == "52.0"
    assert hass.states.get(f"{PREFIX}_level").attributes["unit_of_measurement"] == "%"
    assert hass.states.get(f"{PREFIX}_volume").state == "62.1485"
    assert hass.states.get(f"{PREFIX}_capacity").state == "119.5164"
    assert hass.states.get(f"{PREFIX}_last_reading").state == "2026-10-19"
    assert hass.states.get(f"{PREFIX}_last_delivery").state == "2026-01-21"
    assert hass.states.get(f"{PREFIX}_next_delivery_estimate").state == "2028-05-09"

    assert entity_registry.async_get(f"{PREFIX}_level").unique_id == f"{TANK_KEY}_level"
    [device] = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    assert device.identifiers == {(DOMAIN, str(TANK_KEY))}
    assert device.serial_number == "123456789012345"
    assert device.manufacturer == "Angus Energy"

    # Every authenticated call carries the token; the levels window is the
    # last 7 days in the app's MM/DD/YYYY format.
    calls = {str(c[1].with_query(None)): c for c in api_ok.mock_calls}
    levels_call = calls[LEVELS_URL]
    assert levels_call[1].query == {"startDate": "10/13/2026", "endDate": "10/20/2026"}
    assert levels_call[3]["x-access-token"] == SIGN_IN["token"]
    assert calls[ACCOUNT_URL][3]["x-access-token"] == SIGN_IN["token"]


@pytest.mark.freeze_time("2026-10-20 15:00:00-04:00")
async def test_metric_install_converts_gallons(
    hass: HomeAssistant, api_ok: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    hass.config.units = METRIC_SYSTEM
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    volume = hass.states.get(f"{PREFIX}_volume")
    assert volume.attributes["unit_of_measurement"] == "L"
    assert float(volume.state) == pytest.approx(62.1485 * 3.785411784)
    assert hass.states.get(f"{PREFIX}_level").state == "52.0"


async def test_bad_password_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    aioclient_mock.post(SIGN_IN_URL, status=401, json={"msg": "Invalid username or password."})
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_api_down_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    aioclient_mock.post(SIGN_IN_URL, json=SIGN_IN)
    aioclient_mock.get(ACCOUNT_URL, status=500)
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time("2026-10-20 15:00:00-04:00")
async def test_tank_without_readings(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    aioclient_mock.post(SIGN_IN_URL, json=SIGN_IN)
    aioclient_mock.get(ACCOUNT_URL, json=ACCOUNT)
    aioclient_mock.get(LEVELS_URL, json={"tankKey": str(TANK_KEY), "levels": []})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(f"{PREFIX}_level").state == "unknown"
    assert hass.states.get(f"{PREFIX}_last_delivery").state == "2026-01-21"

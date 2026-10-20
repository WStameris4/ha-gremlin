"""Fixtures for the Gremlin tests. All data is made up."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gremlin.api import BASE_URL
from custom_components.gremlin.const import DOMAIN

USERNAME = "someone"
PASSWORD = "hunter2"
USER_ID = "0123456789abcdef01234567"
TANK_KEY = 1001

SIGN_IN_URL = f"{BASE_URL}/consumer/signIn"
ACCOUNT_URL = f"{BASE_URL}/consumer/api"
LEVELS_URL = f"{BASE_URL}/consumer/api/tanks/{TANK_KEY}/levels"

SIGN_IN = {
    "token": "t" * 171,
    "remoteToken": "",
    "vendorURL": "",
    "expires": "2026-10-21T19:00:00.000Z",
    "user": {"userId": USER_ID, "dealerId": "d" * 24, "subscriberId": "s" * 24},
}
ACCOUNT = {
    "customerKey": 1,
    "accountNum": "00000",
    "customerName": "TEST CUSTOMER",
    "tanks": [
        {
            "key": TANK_KEY,
            "name": "PROPANE 1 X 120 GAL AG",
            "lastDeliveryDate": "2026-01-21T00:00:00.000Z",
            "nextDeliveryDate": "2028-05-09T00:00:00.000Z",
            "serialNum": "123456789012345",
            "geometry": {"shape": 5, "calcTankSize": 119.5164, "safeCapacity": 100},
        }
    ],
}
LEVELS = {
    "tankKey": str(TANK_KEY),
    "levels": [
        {"volume": 63.0, "change": 0, "percent": 53, "readingDate": "2026-10-18T00:00:00.000Z"},
        {"volume": 62.1485, "change": -0.85, "percent": 52, "readingDate": "2026-10-19T00:00:00.000Z"},
        {"volume": 64.0, "change": 0, "percent": 54, "readingDate": "2026-10-17T00:00:00.000Z"},
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Load custom_components/ in every test."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured account."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=USERNAME,
        unique_id=USER_ID,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )


@pytest.fixture
def api_ok(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """The API answering normally."""
    aioclient_mock.post(SIGN_IN_URL, json=SIGN_IN)
    aioclient_mock.get(ACCOUNT_URL, json=ACCOUNT)
    aioclient_mock.get(LEVELS_URL, json=LEVELS)
    return aioclient_mock

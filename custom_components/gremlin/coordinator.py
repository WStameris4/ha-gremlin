"""Polling coordinator for the Gremlin integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import GremlinApi, GremlinAuthError, GremlinError, Tank
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type GremlinConfigEntry = ConfigEntry[GremlinCoordinator]


class GremlinCoordinator(DataUpdateCoordinator[dict[int, Tank]]):
    """Fetches every tank on the account, keyed by tank key."""

    config_entry: GremlinConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: GremlinConfigEntry, api: GremlinApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[int, Tank]:
        try:
            tanks = await self.api.async_get_tanks(dt_util.now().date())
        except GremlinAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GremlinError as err:
            raise UpdateFailed(str(err)) from err
        return {tank.key: tank for tank in tanks}

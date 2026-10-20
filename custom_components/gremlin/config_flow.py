"""Config flow for the Gremlin integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import GremlinApi, GremlinAuthError, GremlinError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


class GremlinConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in with the account used in the GREMLIN mobile app."""

    VERSION = 1

    async def _validate(
        self, username: str, password: str, errors: dict[str, str]
    ) -> str | None:
        """Return the account's user id, or fill in errors."""
        api = GremlinApi(async_get_clientsession(self.hass), username, password)
        try:
            _, user_id = await api.async_sign_in()
        except GremlinAuthError:
            errors["base"] = "invalid_auth"
        except GremlinError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error signing in to Gremlin")
            errors["base"] = "unknown"
        else:
            return user_id
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id = await self._validate(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD], errors
            )
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, {CONF_USERNAME: (user_input or {}).get(CONF_USERNAME)}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the password stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id = await self._validate(
                entry.data[CONF_USERNAME], user_input[CONF_PASSWORD], errors
            )
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

"""Adding a kiosk: found on the network (or typed in), then paired through its dashboard login."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import secrets
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import KioskApi, KioskApiError, KioskBusy
from .const import CONF_TOKEN, DEFAULT_PORT, DOMAIN, LOGGER
from .pairing import async_expect_pairing, async_forget_pairing

# How long the flow waits for the kiosk's dashboard to be logged in; the
# kiosk app keeps a request open for the same five minutes.
PAIR_TIMEOUT = 300


class PairingFailed(Exception):
    """Carries the translation key of the error to show."""


class KioskConfigFlow(ConfigFlow, domain=DOMAIN):
    """Discover or enter a kiosk, then pair through the kiosk's dashboard login."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._name: str = "Kiosk"
        self._pair_task: asyncio.Task[dict[str, Any]] | None = None
        self._paired: dict[str, Any] | None = None
        self._error: str | None = None

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """The kiosk app announced itself on the network."""
        device_id = discovery_info.properties.get("id")
        if not device_id:
            return self.async_abort(reason="not_supported")
        # Prefer IPv4: the tablet also announces link-local IPv6 addresses.
        host = next((str(a) for a in discovery_info.ip_addresses if a.version == 4), discovery_info.host)
        port = discovery_info.port or DEFAULT_PORT
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
        self._host, self._port = host, port
        self._name = discovery_info.name.removesuffix("." + discovery_info.type).strip() or self._name
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_pair()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Added by hand, with the address the app shows in its settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = user_input[CONF_PORT]
            try:
                info = await KioskApi(async_get_clientsession(self.hass), self._host, self._port).info()
            except KioskApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
                self._name = info.get("name") or self._name
                return await self.async_step_pair()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Required(CONF_PORT, default=self._port): int,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The tablet forgot this Home Assistant: pair again."""
        self._host = entry_data[CONF_HOST]
        self._port = entry_data[CONF_PORT]
        self._name = self._get_reauth_entry().title
        return await self.async_step_pair()

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Explain what happens next; Submit starts the pairing."""
        if user_input is not None:
            return await self.async_step_wait()
        errors = {"base": self._error} if self._error else {}
        self._error = None
        return self.async_show_form(
            step_id="pair",
            description_placeholders={"name": self._name, "host": self._host},
            errors=errors,
        )

    async def async_step_wait(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Wait until the kiosk confirms through its dashboard login."""
        if self._pair_task is None:
            self._pair_task = self.hass.async_create_task(self._async_pair())
        if not self._pair_task.done():
            return self.async_show_progress(
                step_id="wait",
                progress_action="wait_for_login",
                progress_task=self._pair_task,
                description_placeholders={"name": self._name},
            )
        task, self._pair_task = self._pair_task, None
        try:
            self._paired = task.result()
        except PairingFailed as err:
            self._error = str(err)
            return self.async_show_progress_done(next_step_id="pair")
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._paired is not None
        data = {CONF_HOST: self._host, CONF_PORT: self._port, CONF_TOKEN: self._paired["token"]}
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)
        return self.async_create_entry(title=self._name, data=data)

    async def _async_pair(self) -> dict[str, Any]:
        nonce = secrets.token_urlsafe(32)
        confirmed = async_expect_pairing(self.hass, nonce)
        api = KioskApi(async_get_clientsession(self.hass), self._host, self._port)
        try:
            try:
                await api.pair(self.hass.config.location_name or "Home Assistant", self._home_assistant_url(), nonce)
            except KioskBusy as err:
                raise PairingFailed("busy") from err
            except KioskApiError as err:
                raise PairingFailed("cannot_connect") from err
            try:
                async with asyncio.timeout(PAIR_TIMEOUT):
                    result = await confirmed
            except TimeoutError as err:
                raise PairingFailed("timeout") from err
        finally:
            async_forget_pairing(self.hass, nonce)
        if result.get("id") != self.unique_id:
            raise PairingFailed("wrong_device")
        LOGGER.info("Kiosk %s paired, confirmed by user %s", self._name, result.get("user"))
        return result

    def _home_assistant_url(self) -> str | None:
        """Home Assistant's own address, so a new kiosk opens it without typing a URL."""
        try:
            return get_url(self.hass, allow_external=False)
        except NoURLAvailableError:
            return None

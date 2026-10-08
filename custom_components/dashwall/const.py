"""Constants for the Dashwall kiosk integration."""

from __future__ import annotations

import logging

DOMAIN = "dashwall"
LOGGER = logging.getLogger(__package__)

DEFAULT_PORT = 2971
CONF_TOKEN = "token"

# The kiosk app's API version this integration speaks (see /api/info "api").
API_VERSION = 1

MANUFACTURER = "Dashwall"

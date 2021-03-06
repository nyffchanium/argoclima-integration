NAME = "Argoclima"
VERSION = "1.0.1"
ISSUE_URL = "https://github.com/nyffchanium/argoclima-integration/issues"

DOMAIN = "argoclima"
DOMAIN_DATA = f"{DOMAIN}_data"
MANUFACTURER = "Argoclima S.p.A."

# Configuration and options
CONF_DEVICE_TYPE = "device"
CONF_NAME = "name"
CONF_HOST = "host"

# Internal stuff
ARGO_DEVICE_ULISSE_ECO = "Ulisse 13 DCI Eco WiFi"
ARGO_DEVICES = [ARGO_DEVICE_ULISSE_ECO]
API_UPDATE_ATTEMPTS = 3

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

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
CONF_PORT = "port"
CONF_ROLE = "role"
CONF_CPU_ID = "cpu_id"
CONF_HUB_ID = "hub_id"
CONF_DEVICES = "devices"

ENTRY_ROLE_DEVICE = "device"
ENTRY_ROLE_HUB = "hub"
HOST_ONLY_CPU_ID_PREFIX = "host:"

DUMMY_SERVER_TITLE = "Argoclima Dummy Server"
DUMMY_SERVER_BIND_HOST = "0.0.0.0"
DUMMY_SERVER_DEFAULT_PORT = 8080
DUMMY_SERVER_DEVICE_IDENTIFIER_PREFIX = "dummy_server_hub"
DUMMY_SERVER_UNIQUE_ID_PREFIX = "dummy_server"

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

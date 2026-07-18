from homeassistant.const import Platform

DOMAIN = "labelberry"
CONF_URL = "url"
SERVICE_PRINT_LABEL = "print_label"
SERVICE_PRINT_TEMPLATE = "print_template"
PLATFORMS = [Platform.SENSOR]
REQUEST_TIMEOUT_SECONDS = 10
SCAN_INTERVAL_SECONDS = 30

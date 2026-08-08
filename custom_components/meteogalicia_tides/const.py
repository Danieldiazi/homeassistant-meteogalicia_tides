"""Constants for the MeteoGalicia_Tides integration."""

from datetime import timedelta

DOMAIN = "meteogalicia_tides"
INTEGRATION_NAME = "MeteoGalicia_Tides"
CONF_ID_PORT = "id_port"
CONF_SCAN_INTERVAL = "scan_interval"
PLATFORMS = ["sensor"]
TIMEOUT = 60
MAX_BACKOFF_MULTIPLIER = 16
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 86400
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
HORA_FIELD = "@hora"
ESTADO_FIELD = "@estado"
ALTURA_FIELD = "@altura"
ID_TIPO_MAREA_FIELD = "@idTipoMarea"

"""Constants for the Gremlin integration."""

from datetime import timedelta

DOMAIN = "gremlin"

# Monitors report once a day; polling more often only finds the same reading.
UPDATE_INTERVAL = timedelta(hours=3)

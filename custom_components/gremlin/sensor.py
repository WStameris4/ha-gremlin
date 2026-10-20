"""Sensors for Gremlin tank monitors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Tank
from .const import DOMAIN
from .coordinator import GremlinConfigEntry, GremlinCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GremlinSensorDescription(SensorEntityDescription):
    """Describes a Gremlin sensor."""

    value_fn: Callable[[Tank], float | date | None]


SENSORS: tuple[GremlinSensorDescription, ...] = (
    GremlinSensorDescription(
        key="level",
        translation_key="level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda t: t.latest.percent if t.latest else None,
    ),
    GremlinSensorDescription(
        key="volume",
        translation_key="volume",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda t: t.latest.volume if t.latest else None,
    ),
    GremlinSensorDescription(
        key="capacity",
        translation_key="capacity",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda t: t.capacity,
    ),
    GremlinSensorDescription(
        key="last_reading",
        translation_key="last_reading",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda t: t.latest.reading_date if t.latest else None,
    ),
    GremlinSensorDescription(
        key="last_delivery",
        translation_key="last_delivery",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda t: t.last_delivery,
    ),
    GremlinSensorDescription(
        key="next_delivery",
        translation_key="next_delivery",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda t: t.next_delivery,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GremlinConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a set of sensors for every tank on the account."""
    coordinator = entry.runtime_data
    async_add_entities(
        GremlinSensor(coordinator, key, description)
        for key in coordinator.data
        for description in SENSORS
    )


class GremlinSensor(CoordinatorEntity[GremlinCoordinator], SensorEntity):
    """One value of one tank."""

    _attr_has_entity_name = True
    entity_description: GremlinSensorDescription

    def __init__(
        self,
        coordinator: GremlinCoordinator,
        tank_key: int,
        description: GremlinSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._tank_key = tank_key
        tank = coordinator.data[tank_key]
        self._attr_unique_id = f"{tank_key}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(tank_key))},
            name=tank.name,
            manufacturer="Angus Energy",
            model="GREMLIN tank monitor",
            serial_number=tank.serial,
        )

    @property
    def available(self) -> bool:
        """Unavailable if the tank vanished from the account."""
        return super().available and self._tank_key in self.coordinator.data

    @property
    def native_value(self) -> float | date | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data[self._tank_key])

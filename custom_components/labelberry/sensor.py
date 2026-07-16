"""Status sensor for LabelBerry."""

from typing import override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LabelBerryConfigEntry
from .const import CONF_URL, DOMAIN
from .coordinator import LabelBerryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LabelBerryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the LabelBerry status sensor."""
    async_add_entities([LabelBerryStatusSensor(entry)])


class LabelBerryStatusSensor(CoordinatorEntity[LabelBerryCoordinator], SensorEntity):
    """Represent the status of one LabelBerry server and printer."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["connected", "disconnected"]

    def __init__(self, entry: LabelBerryConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    @override
    def native_value(self) -> str:
        return "connected" if self.coordinator.data.connected else "disconnected"

    @property
    @override
    def extra_state_attributes(self) -> dict[str, float | str | None]:
        return {
            "tape_width_mm": self.coordinator.data.tape_width_mm,
            "backend": self.coordinator.data.backend,
        }

    @property
    @override
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="LabelBerry",
            manufacturer="LabelBerry",
            configuration_url=self._entry.data[CONF_URL],
        )

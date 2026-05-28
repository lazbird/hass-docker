"""Support for Lecoo aiot binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

from tuya_device_handlers.definition.binary_sensor import (
    TuyaBinarySensorDefinition,
    get_default_definition,
)
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LECOO_DISCOVERY_NEW, DeviceCategory, DPCode
from .coordinator import LecooConfigEntry
from .entity import LecooEntity


@dataclass(frozen=True)
class LecooBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Lecoo aiot binary sensor."""

    # DPCode, to use. If None, the key will be used as DPCode
    dpcode: DPCode | None = None

    # Value or values to consider binary sensor to be "on"
    on_value: bool | float | int | str | set[bool | float | int | str] = True

    # For DPType.BITMAP, the bitmap_key is used to extract the bit mask
    bitmap_key: str | None = None


# Commonly used sensors
TAMPER_BINARY_SENSOR = LecooBinarySensorEntityDescription(
    key=DPCode.TEMPER_ALARM,
    name="Tamper",
    device_class=BinarySensorDeviceClass.TAMPER,
    entity_category=EntityCategory.DIAGNOSTIC,
)


# All descriptions can be found here. Mostly the Boolean data types in the
# default status set of each category (that don't have a set instruction)
# end up being a binary sensor.
BINARY_SENSORS: dict[DeviceCategory, tuple[LecooBinarySensorEntityDescription, ...]] = {
    DeviceCategory.CO2BJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CO2_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.COBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CO_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="1",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CO_STATUS,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.CS: (
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.FAULT}_water_full",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="water_full",
            translation_key="tankfull",
        ),
        LecooBinarySensorEntityDescription(
            key="tankfull",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="tankfull",
            translation_key="tankfull",
        ),
        LecooBinarySensorEntityDescription(
            key="defrost",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="defrost",
            translation_key="defrost",
        ),
        LecooBinarySensorEntityDescription(
            key="wet",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="wet",
            translation_key="wet",
        ),
    ),
    DeviceCategory.CWWSQ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.FEED_STATE,
            translation_key="feeding",
            on_value="feeding",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    DeviceCategory.DGNBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.GAS_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.GAS,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CH4_SENSOR_STATE,
            translation_key="methane",
            device_class=BinarySensorDeviceClass.GAS,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.VOC_STATE,
            translation_key="voc",
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.PM25_STATE,
            translation_key="pm25",
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CO_STATE,
            translation_key="carbon_monoxide",
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CO2_STATE,
            translation_key="carbon_dioxide",
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CH2O_STATE,
            translation_key="formaldehyde",
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.DOORCONTACT_STATE,
            device_class=BinarySensorDeviceClass.DOOR,
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.WATERSENSOR_STATE,
            device_class=BinarySensorDeviceClass.MOISTURE,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.PRESSURE_STATE,
            translation_key="pressure",
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.SMOKE_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.SMOKE,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.HPS: (
        LecooBinarySensorEntityDescription(
            key=DPCode.PRESENCE_STATE,
            device_class=BinarySensorDeviceClass.OCCUPANCY,
            on_value={"presence", "small_move", "large_move", "peaceful"},
        ),
    ),
    DeviceCategory.JQBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CH2O_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.JWBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CH4_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.GAS,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.LDCG: (
        LecooBinarySensorEntityDescription(
            key=DPCode.TEMPER_ALARM,
            device_class=BinarySensorDeviceClass.TAMPER,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.MC: (
        LecooBinarySensorEntityDescription(
            key=DPCode.STATUS,
            device_class=BinarySensorDeviceClass.DOOR,
            on_value={"open", "opened"},
        ),
    ),
    DeviceCategory.MCS: (
        LecooBinarySensorEntityDescription(
            key=DPCode.DOORCONTACT_STATE,
            device_class=BinarySensorDeviceClass.DOOR,
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.SWITCH,  # Used by non-standard contact sensor implementations
            device_class=BinarySensorDeviceClass.DOOR,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.MK: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CLOSED_OPENED_KIT,
            device_class=BinarySensorDeviceClass.LOCK,
            on_value={"AQAB"},
        ),
    ),
    DeviceCategory.MSP: (
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.FAULT}_full_fault",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="full_fault",
            translation_key="bag_full",
        ),
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.FAULT}_box_out",
            dpcode=DPCode.FAULT,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            bitmap_key="box_out",
            translation_key="cover_off",
        ),
    ),
    DeviceCategory.PIR: (
        LecooBinarySensorEntityDescription(
            key=DPCode.PIR,
            device_class=BinarySensorDeviceClass.MOTION,
            on_value="pir",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.PM2_5: (
        LecooBinarySensorEntityDescription(
            key=DPCode.PM25_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.QXJ: (TAMPER_BINARY_SENSOR,),
    DeviceCategory.RQBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.GAS_SENSOR_STATUS,
            device_class=BinarySensorDeviceClass.GAS,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.GAS_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.GAS,
            on_value="1",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.SGBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.SJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.WATERSENSOR_STATE,
            device_class=BinarySensorDeviceClass.MOISTURE,
            on_value={"1", "alarm"},
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.SOS: (
        LecooBinarySensorEntityDescription(
            key=DPCode.SOS_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.VOC: (
        LecooBinarySensorEntityDescription(
            key=DPCode.VOC_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.WG2: (
        LecooBinarySensorEntityDescription(
            key=DPCode.MASTER_STATE,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ),
    DeviceCategory.WK: (
        LecooBinarySensorEntityDescription(
            key=DPCode.VALVE_STATE,
            translation_key="valve",
            on_value="open",
        ),
    ),
    DeviceCategory.WKF: (
        LecooBinarySensorEntityDescription(
            key=DPCode.WINDOW_STATE,
            device_class=BinarySensorDeviceClass.WINDOW,
            on_value="opened",
        ),
    ),
    DeviceCategory.WSDCG: (TAMPER_BINARY_SENSOR,),
    DeviceCategory.YLCG: (
        LecooBinarySensorEntityDescription(
            key=DPCode.PRESSURE_STATE,
            on_value="alarm",
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.YWBJ: (
        LecooBinarySensorEntityDescription(
            key=DPCode.SMOKE_SENSOR_STATUS,
            device_class=BinarySensorDeviceClass.SMOKE,
            on_value="alarm",
        ),
        LecooBinarySensorEntityDescription(
            key=DPCode.SMOKE_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.SMOKE,
            on_value={"1", "alarm"},
        ),
        TAMPER_BINARY_SENSOR,
    ),
    DeviceCategory.ZD: (
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.SHOCK_STATE}_vibration",
            dpcode=DPCode.SHOCK_STATE,
            device_class=BinarySensorDeviceClass.VIBRATION,
            on_value="vibration",
        ),
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.SHOCK_STATE}_drop",
            dpcode=DPCode.SHOCK_STATE,
            translation_key="drop",
            on_value="drop",
        ),
        LecooBinarySensorEntityDescription(
            key=f"{DPCode.SHOCK_STATE}_tilt",
            dpcode=DPCode.SHOCK_STATE,
            translation_key="tilt",
            on_value="tilt",
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LecooConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Lecoo aiot binary sensor dynamically through Lecoo aiot discovery."""
    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Lecoo aiot binary sensor."""
        entities: list[LecooBinarySensorEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if descriptions := BINARY_SENSORS.get(device.category):
                entities.extend(
                    LecooBinarySensorEntity(device, manager, description, definition)
                    for description in descriptions
                    if (
                        definition := get_default_definition(
                            device,
                            description.dpcode or description.key,
                            description.bitmap_key,
                            description.on_value,
                        )
                    )
                )

        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, LECOO_DISCOVERY_NEW, async_discover_device)
    )


class LecooBinarySensorEntity(LecooEntity, BinarySensorEntity):
    """Lecoo aiot Binary Sensor Entity."""

    entity_description: LecooBinarySensorEntityDescription

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: LecooBinarySensorEntityDescription,
        definition: TuyaBinarySensorDefinition,
    ) -> None:
        """Init Lecoo aiot binary sensor."""
        super().__init__(device, device_manager, description)
        self._dpcode_wrapper = definition.binary_sensor_wrapper

    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self._read_wrapper(self._dpcode_wrapper)

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Lecoo aiot device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        return not self._dpcode_wrapper.skip_update(
            self.device, updated_status_properties, dp_timestamps
        )

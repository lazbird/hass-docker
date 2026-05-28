"""Support for Lecoo aiot event entities."""

from __future__ import annotations

from dataclasses import dataclass

from tuya_device_handlers.definition.event import (
    TuyaEventDefinition,
    get_default_definition,
)
from tuya_device_handlers.device_wrapper.common import DPCodeTypeInformationWrapper
from tuya_device_handlers.device_wrapper.event import (
    Base64Utf8RawEventWrapper,
    Base64Utf8StringEventWrapper,
    SimpleEventEnumWrapper,
)
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LECOO_DISCOVERY_NEW, DeviceCategory, DPCode
from .coordinator import LecooConfigEntry
from .entity import LecooEntity


@dataclass(frozen=True)
class LecooEventEntityDescription(EventEntityDescription):
    """Describe a Lecoo aiot Event entity."""

    wrapper_class: type[DPCodeTypeInformationWrapper] = SimpleEventEnumWrapper


# All descriptions can be found here. Mostly the Enum data types in the
# default status set of each category (that don't have a set instruction)
# end up being events.
EVENTS: dict[DeviceCategory, tuple[LecooEventEntityDescription, ...]] = {
    DeviceCategory.SP: (
        LecooEventEntityDescription(
            key=DPCode.ALARM_MESSAGE,
            device_class=EventDeviceClass.DOORBELL,
            translation_key="doorbell_message",
            wrapper_class=Base64Utf8StringEventWrapper,
        ),
        LecooEventEntityDescription(
            key=DPCode.DOORBELL_PIC,
            device_class=EventDeviceClass.DOORBELL,
            translation_key="doorbell_picture",
            wrapper_class=Base64Utf8RawEventWrapper,
        ),
    ),
    DeviceCategory.WXKG: (
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE1,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "1"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE2,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "2"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE3,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "3"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE4,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "4"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE5,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "5"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE6,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "6"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE7,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "7"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE8,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "8"},
        ),
        LecooEventEntityDescription(
            key=DPCode.SWITCH_MODE9,
            device_class=EventDeviceClass.BUTTON,
            translation_key="numbered_button",
            translation_placeholders={"button_number": "9"},
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LecooConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Lecoo aiot events dynamically through Lecoo aiot discovery."""
    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Lecoo aiot binary sensor."""
        entities: list[LecooEventEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if descriptions := EVENTS.get(device.category):
                entities.extend(
                    LecooEventEntity(device, manager, description, definition)
                    for description in descriptions
                    if (
                        definition := get_default_definition(
                            device, description.key, description.wrapper_class
                        )
                    )
                )

        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, LECOO_DISCOVERY_NEW, async_discover_device)
    )


class LecooEventEntity(LecooEntity, EventEntity):
    """Lecoo aiot Event Entity."""

    entity_description: EventEntityDescription

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: EventEntityDescription,
        definition: TuyaEventDefinition,
    ) -> None:
        """Init Lecoo aiot event entity."""
        super().__init__(device, device_manager, description)
        self._dpcode_wrapper = definition.event_wrapper
        self._attr_event_types = definition.event_wrapper.options

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Lecoo aiot device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        if self._dpcode_wrapper.skip_update(
            self.device, updated_status_properties, dp_timestamps
        ) or not (event_data := self._dpcode_wrapper.read_device_status(self.device)):
            return False

        event_type, event_attributes = event_data
        self._trigger_event(event_type, event_attributes)
        return True

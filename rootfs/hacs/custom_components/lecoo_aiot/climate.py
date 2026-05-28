"""Support for Lecoo aiot Climate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from tuya_device_handlers.definition.climate import (
    TuyaClimateDefinition,
    get_default_definition,
)
from tuya_device_handlers.helpers.homeassistant import (
    TuyaClimateHVACMode,
    TuyaClimateSwingMode,
    TuyaUnitOfTemperature,
)
from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.climate import (
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_ON,
    SWING_VERTICAL,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LECOO_DISCOVERY_NEW, DeviceCategory
from .coordinator import LecooConfigEntry
from .entity import LecooEntity

_LECOO_TO_HA_HVACMODE_MAPPINGS = {
    TuyaClimateHVACMode.OFF: HVACMode.OFF,
    TuyaClimateHVACMode.HEAT: HVACMode.HEAT,
    TuyaClimateHVACMode.COOL: HVACMode.COOL,
    TuyaClimateHVACMode.FAN_ONLY: HVACMode.FAN_ONLY,
    TuyaClimateHVACMode.DRY: HVACMode.DRY,
    TuyaClimateHVACMode.HEAT_COOL: HVACMode.HEAT_COOL,
    TuyaClimateHVACMode.AUTO: HVACMode.AUTO,
}
_HA_TO_LECOO_HVACMODE_MAPPINGS = {v: k for k, v in _LECOO_TO_HA_HVACMODE_MAPPINGS.items()}

_LECOO_TO_HA_SWING_MAPPINGS = {
    TuyaClimateSwingMode.BOTH: SWING_BOTH,
    TuyaClimateSwingMode.HORIZONTAL: SWING_HORIZONTAL,
    TuyaClimateSwingMode.OFF: SWING_OFF,
    TuyaClimateSwingMode.ON: SWING_ON,
    TuyaClimateSwingMode.VERTICAL: SWING_VERTICAL,
}
_HA_TO_LECOO_SWING_MAPPINGS = {v: k for k, v in _LECOO_TO_HA_SWING_MAPPINGS.items()}

_HA_TO_LECOO_TEMPERATURE = {
    UnitOfTemperature.CELSIUS: TuyaUnitOfTemperature.CELSIUS,
    UnitOfTemperature.FAHRENHEIT: TuyaUnitOfTemperature.FAHRENHEIT,
}


@dataclass(frozen=True, kw_only=True)
class LecooClimateEntityDescription(ClimateEntityDescription):
    """Describe an Lecoo aiot climate entity."""

    switch_only_hvac_mode: HVACMode


CLIMATE_DESCRIPTIONS: dict[DeviceCategory, LecooClimateEntityDescription] = {
    DeviceCategory.DBL: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.KT: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.COOL,
    ),
    DeviceCategory.QN: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.RS: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
    DeviceCategory.WK: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.HEAT_COOL,
    ),
    DeviceCategory.WKF: LecooClimateEntityDescription(
        key="",
        switch_only_hvac_mode=HVACMode.HEAT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LecooConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Lecoo aiot climate dynamically through Lecoo aiot discovery."""
    manager = entry.runtime_data.manager

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Lecoo aiot climate."""
        entities: list[LecooClimateEntity] = []
        for device_id in device_ids:
            device = manager.device_map[device_id]
            if (description := CLIMATE_DESCRIPTIONS.get(device.category)) and (
                definition := get_default_definition(
                    device,
                    _HA_TO_LECOO_TEMPERATURE.get(
                        hass.config.units.temperature_unit,
                        TuyaUnitOfTemperature.CELSIUS,
                    ),
                )
            ):
                entities.append(
                    LecooClimateEntity(device, manager, description, definition)
                )
        async_add_entities(entities)

    async_discover_device([*manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, LECOO_DISCOVERY_NEW, async_discover_device)
    )


class LecooClimateEntity(LecooEntity, ClimateEntity):
    """Lecoo aiot Climate Device."""

    entity_description: LecooClimateEntityDescription
    _attr_name = None
    _attr_target_temperature_step = 1.0

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: LecooClimateEntityDescription,
        definition: TuyaClimateDefinition,
    ) -> None:
        """Determine which values to use."""
        super().__init__(device, device_manager, description)
        self._current_humidity_wrapper = definition.current_humidity_wrapper
        self._current_temperature = definition.current_temperature_wrapper
        self._fan_mode_wrapper = definition.fan_mode_wrapper
        self._hvac_mode_wrapper = definition.hvac_mode_wrapper
        self._preset_wrapper = definition.preset_wrapper
        self._set_temperature = definition.set_temperature_wrapper
        self._swing_wrapper = definition.swing_wrapper
        self._switch_wrapper = definition.switch_wrapper
        self._target_humidity_wrapper = definition.target_humidity_wrapper
        self._attr_temperature_unit = definition.temperature_unit

        # Get integer type data for the dpcode to set temperature, use
        # it to define min, max & step temperatures
        if definition.set_temperature_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_max_temp = definition.set_temperature_wrapper.max_value
            self._attr_min_temp = definition.set_temperature_wrapper.min_value
            self._attr_target_temperature_step = (
                definition.set_temperature_wrapper.value_step
            )

        # Determine HVAC modes
        self._attr_hvac_modes = []
        if definition.hvac_mode_wrapper:
            self._attr_hvac_modes = [HVACMode.OFF]
            for lecoo_mode in cast(
                list[TuyaClimateHVACMode], definition.hvac_mode_wrapper.options
            ):
                if (
                    ha_mode := _LECOO_TO_HA_HVACMODE_MAPPINGS.get(lecoo_mode)
                ) and ha_mode != HVACMode.OFF:
                    # OFF is always added first
                    self._attr_hvac_modes.append(ha_mode)

        elif definition.switch_wrapper:
            self._attr_hvac_modes = [
                HVACMode.OFF,
                description.switch_only_hvac_mode,
            ]

        # Determine preset modes (ignore if empty options)
        if definition.preset_wrapper and definition.preset_wrapper.options:
            self._attr_hvac_modes.append(description.switch_only_hvac_mode)
            self._attr_preset_modes = definition.preset_wrapper.options
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE

        # Determine dpcode to use for setting the humidity
        if definition.target_humidity_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
            self._attr_min_humidity = round(
                definition.target_humidity_wrapper.min_value
            )
            self._attr_max_humidity = round(
                definition.target_humidity_wrapper.max_value
            )

        # Determine fan modes
        if definition.fan_mode_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
            self._attr_fan_modes = definition.fan_mode_wrapper.options

        # Determine swing modes
        if definition.swing_wrapper:
            self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = [
                ha_swing_mode
                for lecoo_swing_mode in cast(
                    list[TuyaClimateSwingMode], definition.swing_wrapper.options
                )
                if (ha_swing_mode := _LECOO_TO_HA_SWING_MAPPINGS.get(lecoo_swing_mode))
            ]

        if definition.switch_wrapper:
            self._attr_supported_features |= (
                ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        commands = []
        if self._switch_wrapper:
            commands.extend(
                self._switch_wrapper.get_update_commands(
                    self.device, hvac_mode != HVACMode.OFF
                )
            )
        if (
            self._hvac_mode_wrapper
            and (lecoo_mode := _HA_TO_LECOO_HVACMODE_MAPPINGS.get(hvac_mode))
            and lecoo_mode in self._hvac_mode_wrapper.options
        ):
            commands.extend(
                self._hvac_mode_wrapper.get_update_commands(self.device, lecoo_mode)
            )
        await self._async_send_commands(commands)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""
        await self._async_send_wrapper_updates(self._preset_wrapper, preset_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._async_send_wrapper_updates(self._fan_mode_wrapper, fan_mode)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        await self._async_send_wrapper_updates(self._target_humidity_wrapper, humidity)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        if lecoo_mode := _HA_TO_LECOO_SWING_MAPPINGS.get(swing_mode):
            await self._async_send_wrapper_updates(self._swing_wrapper, lecoo_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self._async_send_wrapper_updates(
            self._set_temperature, kwargs[ATTR_TEMPERATURE]
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._read_wrapper(self._current_temperature)

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._read_wrapper(self._current_humidity_wrapper)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature currently set to be reached."""
        return self._read_wrapper(self._set_temperature)

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity currently set to be reached."""
        return self._read_wrapper(self._target_humidity_wrapper)

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac mode."""
        # If the switch is off, hvac mode is off.
        switch_status: bool | None
        if (switch_status := self._read_wrapper(self._switch_wrapper)) is False:
            return HVACMode.OFF

        # If we don't have a mode wrapper, return switch only mode.
        if self._hvac_mode_wrapper is None:
            if switch_status is True:
                return self.entity_description.switch_only_hvac_mode
            return None

        # If we do have a mode wrapper, check if the mode maps to an HVAC mode.
        lecoo_mode = self._read_wrapper(self._hvac_mode_wrapper)
        return _LECOO_TO_HA_HVACMODE_MAPPINGS.get(lecoo_mode) if lecoo_mode else None

    @property
    def preset_mode(self) -> str | None:
        """Return preset mode."""
        return self._read_wrapper(self._preset_wrapper)

    @property
    def fan_mode(self) -> str | None:
        """Return fan mode."""
        return self._read_wrapper(self._fan_mode_wrapper)

    @property
    def swing_mode(self) -> str | None:
        """Return swing mode."""
        lecoo_value = self._read_wrapper(self._swing_wrapper)
        return _LECOO_TO_HA_SWING_MAPPINGS.get(lecoo_value) if lecoo_value else None

    async def async_turn_on(self) -> None:
        """Turn the device on, retaining current HVAC (if supported)."""
        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self) -> None:
        """Turn the device on, retaining current HVAC (if supported)."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)

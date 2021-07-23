#!/usr/bin/env python3

from  intesisbox.pa_aw_mbs import AquareaModbus
from  intesisbox.pa_aw_mbs import Mode
from  intesisbox.pa_aw_mbs import OnOff
from  intesisbox.pa_aw_mbs import Working
import sys
from datetime import datetime

def main():
    aquarea = AquareaModbus(port='/dev/aquarea', slave=2)
    print(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}. ModBus device {aquarea.slave}")

    log.info("Connecting...")
    aquarea.connect()
    aquarea.poll_data()
    log.info("Disconnecting...")
    aquarea.close()
    log.info("Disconnected")

    #---------------------------------------------------------------------------# 
    # Print values
    #---------------------------------------------------------------------------# 
    log.info(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}.")
    log.info(f"ModBus device {aquarea.slave}")
    log.info('Power:........................................... %s' % aquarea.system)
    log.info('Outdoor temperature:............................. %.1f °C' % aquarea.otudoor_temp)
    log.info('Outgoing Water Temperature:...................... %.1f °C' % aquarea.water_out_temp)
    log.info('Ingoing Water Temperature:....................... %.1f °C' % aquarea.water_in_temp)
    log.info('Operating Mode:.................................. %s' % aquarea.mode)
    log.info('Config Mode:..................................... %s' % aquarea.config_mode)
    log.info('Climate Working Mode:............................ %s' % aquarea.working)
    log.info('Outdoor Temp for Heating at Low Water Temp:...... %.1f °C' % aquarea.heat_low_outdoor_set_temperature)
    log.info('Water Setpoint for Heating at Low Outdoor Temp:.. %.1f °C' % aquarea.heat_low_water_set_temperature)
    log.info('Outdoor Temp for Heating at High Water Temp:..... %.1f °C' % aquarea.heat_high_outdoor_set_temperature)
    log.info('Water Setpoint for Heating at High Outdoor Temp:. %.1f °C' % aquarea.heat_high_water_set_temperature)
    log.info('Water Current Thermoshift:....................... %.1f °C' % aquarea.water_thermo_shift)
    log.info('Outdoor Temp for Heating off (Max):.............. %.1f °C' % aquarea.heat_temperature_max)
    #log.info('Outdoor Temp for Heating off (Min):............. %d' % aquarea.heat_temperature_min)
    #log.info('Outdoor Temp for Heating off (Min):............. %.1f °C' % aquarea.heat_out_temp_min)
    log.info('Outdoor Temp for Heater On:...................... %.1f °C' % aquarea.heater_setpoint_temp)
    #log.info('Heater Capacity Selection:...................... %s' % hex(aquarea.heater_capacity))
    #log.info('Max Heater Capacity:............................ %d' % aquarea.heater_max_capacity)
    log.info('Cooling Setpoint Temperature:.................... %.1f °C' % aquarea.cool_setpoint_temp)
    log.info('Heating Setpoint Temperature:.................... %.1f °C' % aquarea.heat_setpoint_temp)
    #log.info('Auto Heat to Cool Temperature:.................. %.1f °C' % aquarea.auto_heat_to_cool_temp)
    #log.info('Auto Cool to Heat Temperature:.................. %.1f °C' % aquarea.auto_cool_to_heat_temp)
    #log.info('Auto Config Mode:............................... %s' % aquarea.auto_mode)
    log.info('Tank On/Off:..................................... %s' % aquarea.tank_mode)
    log.info('Tank Working Mode:............................... %s' % aquarea.tank_working)
    log.info('Tank Water Temperature:.......................... %.1f °C' % aquarea.tank_water_temp)
    log.info('Tank Water Setpoint Temp:........................ %.1f °C' % aquarea.tank_setpoint_temp)
    log.info('Heat-up Interval:................................ %d min' % aquarea.heat_interval)
    log.info('Operation Interval:.............................. %d min' % aquarea.operation_interval)
    log.info('Booster Delay Time:.............................. %d min' % aquarea.booster_delay)
    #log.info('Sterilization Boiling Temp:..................... %.1f °C' % aquarea.tank_ster_temp)
    #log.info('Sterilization Continuing Time:.................. %d min' % aquarea.tank_ster_time)
    #log.info('Heat mode consumption:.......................... %d Wh' % aquarea.heat_wh)
    #log.info('Cool mode consumption:.......................... %d Wh' % aquarea.cool_wh)
    #log.info('Tank mode consumption:.......................... %d Wh' % aquarea.tank_wh)
    log.info('Error Code:...................................... %s' % aquarea.error)
    log.info('Error Code History:.............................. %s' % aquarea.error_history)
    log.info('Warning Tank Temp. Status:....................... %s' % aquarea.tank_warn)
    log.info('Defrost Status:.................................. %s' % aquarea.defrost)
    log.info('Solar Status:.................................... %s' % aquarea.solar)
    log.info('Booster Status:.................................. %s' % aquarea.booster)
    log.info('Compressor Frequency:............................ %d Hz' % aquarea.compressor)
    log.info('Compressor Hours:................................ %d h' % aquarea.compressor_hour)
    log.info('Heater When Heat:................................ %s' % aquarea.heater_when_heat)
    log.info('Heater Status:................................... %s' % aquarea.heater_status)
    log.info('Heater Mode:..................................... %s' % aquarea.heater_mode)
    log.info('Alarm Status:.................................... %s' % aquarea.alarm_status)
    log.info('Room thermostat:................................. %s' % aquarea.room_thermostat)
    log.info('Tank Connection:................................. %s' % aquarea.tank_connection)
    log.info('Solar Priority:.................................. %s' % aquarea.solar_priority)
    log.info('Heating Priority:................................ %s' % aquarea.heating_priority)
    #log.info('Cooling Priority:................................ %s' % aquarea.cooling_priority)
    log.info('Sterilization:................................... %s' % aquarea.sterilization)
    log.info('Climate Preset Heat Thermoshift (ECO):........... %s' % aquarea.thermoshift_heat_eco)
    log.info('Climate Preset Heat Thermoshift (POWERFUL):...... %s' % aquarea.thermoshift_heat_powerful)
    log.info('Climate Preset Cool Thermoshift (ECO):........... %s' % aquarea.thermoshift_cool_eco)
    log.info('Climate Preset Cool Thermoshift (POWERFUL):...... %s' % aquarea.thermoshift_cool_powerful)
    log.info('Preset Tank Thermoshift (ECO):................... %s' % aquarea.thermoshift_tank_eco)
    log.info('Preset Tank Thermoshift (POWERFUL):.............. %s' % aquarea.thermoshift_tank_powerful)


if __name__ == "__main__":
    import logging
    import logging.config

    logging.config.fileConfig("/usr/local/etc/aquarea/pa_aw_mbs_log_config.ini", disable_existing_loggers=False)
    log = logging.getLogger("aquarea_info")

    main()
#!/usr/bin/env python3

from  intesisbox.pa_aw_mbs import AquareaModbus
from  intesisbox.pa_aw_mbs import Mode
from  intesisbox.pa_aw_mbs import OnOff
from  intesisbox.pa_aw_mbs import Working
import sys
import argparse
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import time
from datetime import datetime
from enum import Enum

class Domoticz:
    
    broker = None
    port = None
    temp_idx = None
    tank_set_point_idx = None
    water_set_point_idx = None
    ext_temp_idx = None
    out_temp_idx = None
    in_temp_idx = None
    power_idx = None
    mode_idx = None
    freq_idx = None

    def __init__(self, broker, port, log):
        self.broker = broker
        self.port = port
        self.log = log

    def send(self, aquarea):
        mode_t = Mode[aquarea.mode].value * 10
        self.log.debug(f"mode = {aquarea.mode}, mode.value = {mode_t}")
        #power = aquarea.get_item_value("system", aquarea.system)
        power = OnOff[aquarea.system].value
        self.log.debug(f"system = {aquarea.system}, system.value = {power}")
        tank_temp = aquarea.tank_water_temp
        self.log.debug(f"tank_water_temp = {tank_temp}")
        tank_set_point = aquarea.tank_setpoint_temp
        self.log.debug(f"tank_setpoint_temp = {tank_set_point}")
        outdoor_temp = aquarea.otudoor_temp
        self.log.debug(f"otudoor_temp = {outdoor_temp}")
        water_outlet_temp = aquarea.water_out_temp
        self.log.debug(f"water_out_temp = {water_outlet_temp}")
        water_inlet_temp = aquarea.water_in_temp
        self.log.debug(f"water_in_temp = {water_inlet_temp}")
        freq = aquarea.compressor
        self.log.debug(f"compressor = {freq}")
        
        TOPIC = "domoticz/in"
        ROW1 = "{\"idx\":%d,\"nvalue\":0,\"svalue\":\"%s\"}"
        ROW2 = "{\"type\":\"command\",\"param\":\"udevice\",\"idx\":%d,\"nvalue\":%d,\"parsetrigger\":\"false\"}"
        ROW3 = "{\"type\":\"command\",\"param\":\"udevice\",\"idx\":%d,\"nvalue\":%d,\"svalue\":\"%d\",\"parsetrigger\":\"false\"}"

        if (Mode[aquarea.mode] == Mode.Tank or power == 0):
            msgs = [{'topic':TOPIC, 'payload':ROW1 % (self.temp_idx, str(tank_temp))},
                    (TOPIC, ROW1 % (self.tank_set_point_idx, str(tank_set_point)), 0, False),
                    (TOPIC, ROW1 % (self.ext_temp_idx, str(outdoor_temp)), 0, False),
                    (TOPIC, ROW2 % (self.power_idx, power), 0, False),
                    (TOPIC, ROW1 % (self.freq_idx, freq), 0, False),
                    (TOPIC, ROW3 % (self.mode_idx, power, mode_t), 0, False)
                   ]
        elif (power == 1 and (Mode[aquarea.mode] == Mode.Heat or Mode[aquarea.mode] == Mode.Heat_Tank  or 
                                Mode[aquarea.mode] == Mode.Cool_Tank or Mode[aquarea.mode] == Mode.Cool)):
            if (Mode[aquarea.mode] == Mode.Heat or Mode[aquarea.mode] == Mode.Heat_Tank):
                water_target_temp = aquarea.heat_setpoint_temp
                self.log.debug(f"heat_setpoint_temp = {water_target_temp}")

                msgs = [{'topic':TOPIC, 'payload':ROW1 % (self.temp_idx, str(tank_temp))},
                        (TOPIC, ROW1 % (self.tank_set_point_idx, str(tank_set_point)), 0, False),
                        (TOPIC, ROW1 % (self.water_set_point_idx, str(water_target_temp)), 0, False),
                        (TOPIC, ROW1 % (self.ext_temp_idx, str(outdoor_temp)), 0, False),
                        (TOPIC, ROW1 % (self.out_temp_idx, str(water_outlet_temp)), 0, False),
                        (TOPIC, ROW2 % (self.power_idx, power), 0, False),
                        (TOPIC, ROW1 % (self.freq_idx, freq), 0, False),
                        (TOPIC, ROW1 % (self.in_temp_idx, str(water_inlet_temp)), 0, False),
                        (TOPIC, ROW3 % (self.mode_idx, power, mode_t), 0, False)
                       ]
            else:
                water_target_temp = aquarea.cool_setpoint_temp
                self.log.debug(f"cool_setpoint_temp = {water_target_temp}")

                msgs = [{'topic':TOPIC, 'payload':ROW1 % (self.temp_idx, str(tank_temp))},
                        (TOPIC, ROW1 % (self.tank_set_point_idx, str(tank_set_point)), 0, False),
                        (TOPIC, ROW1 % (self.water_set_point_idx, str(water_target_temp)), 0, False),
                        (TOPIC, ROW1 % (self.ext_temp_idx, str(outdoor_temp)), 0, False),
                        (TOPIC, ROW1 % (self.out_temp_idx, str(water_outlet_temp)), 0, False),
                        (TOPIC, ROW2 % (self.power_idx, power), 0, False),
                        (TOPIC, ROW1 % (self.freq_idx, freq), 0, False),
                        (TOPIC, ROW1 % (self.in_temp_idx, str(water_inlet_temp)), 0, False),
                        (TOPIC, ROW3 % (self.mode_idx, power, mode_t), 0, False)
                       ]
                       
        self.log.info(msgs)
         
        self.log.info(self.broker)
        rc = publish.multiple(msgs, hostname=self.broker, port=self.port, client_id="pa_aw_mbs")
        self.log.info("Publish: %s" % (rc))

def init_argparse() -> argparse.ArgumentParser:
    
    parser = argparse.ArgumentParser(description="Send commands to Aqurea device via Modbus"
                                        ,add_help=True
                                    )
    parser.add_argument("--power", choices=["Off", "On"], help="Trun device power")
    parser.add_argument("--mode", choices=["Heat", "Heat+Tank", "Tank", "Cool+Tank", "Cool"], help="Set device operation mode")
    parser.add_argument("--cool_set_point", choices=range(5, 21), type=int, help="Set cool set point")
    parser.add_argument("--tank_set_point", choices=range(40, 53), type=int, help="Set tank set point")
    parser.add_argument("--tank_working", choices=["Normal", "Eco", "Powerful"], help="Set tank working mode")
    parser.add_argument("--climate_working", choices=["Normal", "Eco", "Powerful"], help="Set heat/cool working mode")
    parser.add_argument("--reset_error", choices=[1,2], type=int, help="Reset error (1=actual, 2=history)")
    parser.add_argument("--tank_powerful", choices=range(0, 11), type=int, help="Set Tank Thermoshift (POWERFUL) temperature")
    parser.add_argument("--tank_eco", choices=range(0, 11), type=int, help="Set Tank Thermoshift (ECO) temperature")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--domoticz", action="store_true", help="Send data to domoticz via MQTT (defalut)", dest='domoticz', default=True)
    group.add_argument("--no-domoticz", action="store_false", help="Do not send data to domoticz via MQTT", dest='domoticz')
    parser.add_argument('--version', action='version', version='%(prog)s v1.0')
    return parser

def main():
    parser = init_argparse()
    args = parser.parse_args()
    
    if args.domoticz:
        log = logging.getLogger("aquarea_domoticz")
    else:
        log = logging.getLogger("aquarea")

    aquarea = AquareaModbus(port='/dev/aquarea', slave=2)
    print(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}. ModBus device {aquarea.slave}")

    if args.power:
        mode = args.power
        aquarea.system = mode
        log.info(f"Command = Power {mode}")
    
    if args.mode:
        mode = args.mode
        aquarea.mode = mode
        log.info(f"Command = Mode {mode}")
    
    if args.cool_set_point:
        set_point = args.cool_set_point
        aquarea.cool_setpoint_temp = set_point
        log.info(f"Command = Cool set point {set_point}")
    
    if args.tank_set_point:
        set_point = args.tank_set_point
        aquarea.tank_setpoint_temp = set_point
        log.info(f"Command = Tank set point {set_point}")
    
    if args.tank_working:
        mode = args.tank_working
        aquarea.tank_working = mode
        log.info(f"Command = Tank working {mode}")

    if args.climate_working:
        mode = args.climate_working
        aquarea.working = mode
        log.info(f"Command = Heat/Cool working {mode}")

    if args.tank_powerful:
        value = args.tank_powerful
        aquarea.thermoshift_tank_powerful = value
        log.info(f"Command = Tank Thermoshift (POWERFUL) temperature {value}")

    if args.tank_eco:
        value = args.tank_eco
        aquarea.thermoshift_tank_eco = value
        log.info(f"Command = Tank Thermoshift (ECO) temperature {value}")

    if args.reset_error:
        mode = args.reset_error
        if mode == 1:
            aquarea.error_reset_1("Go")
        else:
            aquarea.error_reset_2("Go")
        log.info(f"Command = Reset Error {mode}")

    log.info("Connecting...")
    aquarea.connect()
    if aquarea.qsize > 0:
        log.info(f"Sending commands {aquarea.qsize}...")
        aquarea.send_cmd()
        aquarea.close()
        time.sleep(5)
        aquarea.connect()
    log.info(f"Reading data...")
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

    if args.domoticz:
        ''' Semd data to domoticz '''
        #---------------------------------------------------------------------------# 
        # To Domoticz via MQTT
        #---------------------------------------------------------------------------# 
        log.info('Domoticz via MQTT -----------------------------------')
        broker = "192.168.2.32"
        port = 1883
        domoticz = Domoticz(broker, port, log)
        domoticz.temp_idx = 8
        domoticz.tank_set_point_idx = 9
        domoticz.water_set_point_idx = 13
        domoticz.ext_temp_idx = 12
        domoticz.out_temp_idx = 10
        domoticz.in_temp_idx = 11
        domoticz.power_idx = 14
        domoticz.mode_idx = 73
        domoticz.freq_idx = 74

        domoticz.send(aquarea)
        log.info('Domoticz via MQTT -----------------------------------')

if __name__ == "__main__":
    import logging
    import logging.config

    logging.config.fileConfig("/usr/local/etc/aquarea/pa_aw_mbs_log_config.ini", disable_existing_loggers=False)
    log = logging.getLogger("aquarea")

    main()
#!/usr/bin/env python3

from intesisbox.pa_aw_mbs import AquareaModbus
from intesisbox.pa_aw_mbs import Mode
from intesisbox.pa_aw_mbs import OnOff
from intesisbox.pa_aw_mbs import Working
from intesisbox.pa_aw_mbs import ThreeWayValve
from urllib.request import urlopen
import json as js
import sys
import argparse
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import time
from datetime import datetime
from enum import Enum

def init_argparse() -> argparse.ArgumentParser:
    
    parser = argparse.ArgumentParser(description="Send commands to Aqurea device via Modbus"
                                        ,add_help=True
                                        )
    main_group = parser.add_mutually_exclusive_group()
    
    main_group.add_argument("--restart", choices=[1, 5, 10], type=int, help="Trun device power off then on waitng n sec")
    main_group.add_argument('--version', action='version', version='%(prog)s v1.0')

    sec_group = main_group.add_argument_group('sec_group','Secondary group')   
    sec_group.add_argument("--power", choices=["Off", "On"], help="Trun device power")
    sec_group.add_argument("--mode", choices=["Heat", "Heat_Tank", "Tank", "Cool_Tank", "Cool"], help="Set device operation mode")
    sec_group.add_argument("--cool_set_point", choices=range(5, 21), type=int, help="Set cool set point")
    sec_group.add_argument("--tank_set_point", choices=range(40, 53), type=int, help="Set tank set point")
    sec_group.add_argument("--tank_working", choices=["Normal", "Eco", "Powerful"], help="Set tank working mode")
    sec_group.add_argument("--climate_working", choices=["Normal", "Eco", "Powerful"], help="Set heat/cool working mode")
    sec_group.add_argument("--reset_error", choices=[1,2], type=int, help="Reset error (1=actual, 2=history)")
    sec_group.add_argument("--tank_powerful", choices=range(0, 11), type=int, help="Set Tank Thermoshift (POWERFUL) temperature")
    sec_group.add_argument("--tank_eco", choices=range(0, 11), type=int, help="Set Tank Thermoshift (ECO) temperature")
    sec_group.add_argument("--water_shift", choices=range(-5, 6), type=int, help="Set Water Current Thermoshift")
    sec_group.add_argument("--generic_command", help="Set a generic command", dest='command')
    sec_group.add_argument("--generic_value", help="Set a generic value for command", dest='value')

    ter_group = sec_group.add_mutually_exclusive_group()
    ter_group.add_argument("--domoticz", action="store_true", help="Send data to domoticz via MQTT (defalut)", dest='domoticz', default=True)
    ter_group.add_argument("--no-domoticz", action="store_false", help="Do not send data to domoticz via MQTT", dest='domoticz')
    
    return parser

def main():
    parser = init_argparse()
    args = parser.parse_args()

    aquarea = AquareaModbus(port='/dev/aquarea', slave=2, timeout=5, write_timeout=5, lockwait=10, retry=5)
    print(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}. ModBus device {aquarea.slave}")
    aquarea.connect()
    aquarea.poll_data()
    aquarea.close()

    if args.domoticz is not None:
        log = logging.getLogger("aquarea_domoticz")
    else:
        log = logging.getLogger("aquarea")

    if args.restart is not None:
        log.info("Restarting...")
        off = OnOff.Off.name
        on = OnOff.On.name
        aquarea.system = off
        log.info(f"Command = Power {off}...")
        aquarea.connect()
        aquarea.send_cmd()
        aquarea.close()
        time.sleep(args.restart)
        aquarea.system = on
        log.info(f"Command = Power {on}...")
        aquarea.connect()
        aquarea.send_cmd()
        aquarea.close()
        log.info("done!")
    else:
        if args.power is not None:
            mode = args.power
            aquarea.system = mode
            log.info(f"Command = Power {mode}")
        
        if args.mode is not None:
            mode = args.mode
            aquarea.mode = mode
            log.info(f"Command = Mode {mode}")
        
        if args.cool_set_point is not None:
            set_point = args.cool_set_point
            aquarea.cool_setpoint_temp = set_point
            log.info(f"Command = Cool set point {set_point}")
        
        if args.tank_set_point is not None:
            set_point = args.tank_set_point
            aquarea.tank_setpoint_temp = set_point
            log.info(f"Command = Tank set point {set_point}")
        
        if args.tank_working is not None:
            mode = args.tank_working
            aquarea.tank_working = mode
            log.info(f"Command = Tank working {mode}")

        if args.water_shift is not None:
            shift = args.water_shift
            aquarea.water_thermo_shift = shift
            log.debug(f"Command = Water thermo shift {shift}")

        if args.climate_working is not None:
            mode = args.climate_working
            aquarea.working = mode
            log.info(f"Command = Heat/Cool working {mode}")
            log.info(f"aquarea.system = {aquarea.system}, aquarea.mode = {aquarea.mode} ")
            
            #if (Mode[aquarea.mode] in [Mode.Heat, Mode.Heat_Tank, Mode.Cool_Tank, Mode.Cool]):
            shift = 0
            if (aquarea.config_mode == Mode.Cool.name):
                if (mode == Working.Eco.name):
                    shift = aquarea.thermoshift_cool_eco
                elif (mode == Working.Powerful.name):
                    shift = -1 * aquarea.thermoshift_cool_powerful
            else:
                if (mode == Working.Eco.name):
                    shift = -1 * aquarea.thermoshift_heat_eco
                elif (mode == Working.Powerful.name):
                    shift = aquarea.thermoshift_heat_powerful
            aquarea.water_thermo_shift = shift
            log.info(f"Water thermo shift = {shift}")

        if args.tank_powerful is not None:
            value = args.tank_powerful
            aquarea.thermoshift_tank_powerful = value
            log.info(f"Command = Tank Thermoshift (POWERFUL) temperature {value}")

        if args.tank_eco is not None:
            value = args.tank_eco
            aquarea.thermoshift_tank_eco = value
            log.info(f"Command = Tank Thermoshift (ECO) temperature {value}")

        if args.reset_error is not None:
            mode = args.reset_error
            if mode == 1:
                aquarea.error_reset_1("Go")
            else:
                aquarea.error_reset_2("Go")
            log.info(f"Command = Reset Error {mode}")

        if bool(args.command) ^ bool(args.value):
            parser.error('--generic_command and --generic_value must be given together')
        else:
            if args.command is not None:
                command = args.command
                value = args.value
                log.info(f"Command = {command} -> {value}")
                aquarea.set_value(command, value)

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

    values = aquarea.get_all_valid_values()

    log.info("".ljust(56, '-'))
    for name in values:
        desc = values[name]["desc"]
        value = values[name]["value"]
        msg = desc.ljust(55, '.')
        log.info(f"{msg}: {value}")
    log.info("".ljust(56, '-'))

    if args.domoticz and not args.restart:
        ''' Semd data to domoticz '''
        #---------------------------------------------------------------------------# 
        # To Domoticz via MQTT
        #---------------------------------------------------------------------------# 
        log.info('Domoticz via MQTT -----------------------------------')
        broker = "192.168.2.32"
        port = 1883
        domoticz = Domoticz(broker, port, log)
        domoticz.temp_idx               = 8
        domoticz.tank_set_point_idx     = 76
        domoticz.water_set_point_idx    = 13
        domoticz.ext_temp_idx           = 12
        domoticz.out_temp_idx           = 10
        domoticz.in_temp_idx            = 11
        domoticz.power_idx              = 14
        domoticz.mode_idx               = 73
        domoticz.freq_idx               = 74
        domoticz.booster_idx            = 342
        domoticz.working_idx            = 339
        domoticz.tank_working_idx       = 341
        domoticz.dhw_out_temp_idx       = 343
        domoticz.dhw_in_temp_idx        = 344
        domoticz.water_thermo_shift_idx = 345

        domoticz.send(aquarea)
        log.info('Domoticz via MQTT -----------------------------------')

        log.info('MQTT -----------------------------------')
        broker = "192.168.2.32"
        port = 1883
        mqtt = MQTT(broker, port, log)
        mqtt.send(aquarea)
        log.info('MQTT -----------------------------------')


def thrree_way_direction():

    status = None
    state = None
    url = "http://192.168.4.45/status"
    last_direction = None
    try:
       response = urlopen(url)
       data_json = js.loads(response.read())
       state = data_json["rollers"][0]["state"]
       last_direction =  data_json["rollers"][0]["last_direction"]

       #print(F"state = {state}, last_direction = {last_direction}")
    except:
       print(F"An exception occurred opening {url}") 

    direction = None
    if last_direction == state:
        direction = last_direction
    else:
        direction = state

    if direction == 'close':
        status = ThreeWayValve.CLIMATE
    elif direction == 'open':
        status = ThreeWayValve.DHW
    else:
        status = ThreeWayValve.UNKNOWN

    #print(F"status = {status}")

    return status


class Domoticz:
    
    broker = None
    port = None
    temp_idx = None
    tank_set_point_idx = None
    water_set_point_idx = None
    ext_temp_idx = None
    out_temp_idx = None
    in_temp_idx = None
    dhw_out_temp_idx = None
    dhw_in_temp_idx = None
    power_idx = None
    mode_idx = None
    freq_idx = None
    booster_idx = None
    working_idx = None
    tank_working_idx = None
    water_thermo_shift_idx = None

    def __init__(self, broker, port, log):
        self.broker = broker
        self.port = port
        self.log = log

    def send(self, aquarea):
        mode_t = Mode[aquarea.mode].value * 10
        self.log.debug(f"mode = {aquarea.mode}, mode.value = {mode_t}")
        power = OnOff[aquarea.system].value
        self.log.debug(f"system = {aquarea.system}, system.value = {power}")
        if power == 0:
            mode_t = 0
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
        booster = OnOff[aquarea.booster].value
        self.log.debug(f"booster = {aquarea.booster}, booster.value = {booster}")
        working = Working[aquarea.working].value
        working_t = working * 10
        working_n = 0 if working == 0 else 1
        self.log.debug(f"working = {aquarea.working}, working.value = {working}")
        water_thermo_shift = aquarea.water_thermo_shift
        self.log.debug(f"water_thermo_shift = {water_thermo_shift}")
        tank_working = Working[aquarea.tank_working].value
        tank_working_t = tank_working * 10
        tank_working_n = 0 if tank_working == 0 else 1
        direction = None
        if OnOff[aquarea.tank_connection] == OnOff.On:
            direction = thrree_way_direction()

        self.log.debug(f"tank_working = {aquarea.tank_working}, tank_working.value = {tank_working}")
        self.log.debug(f"3-way valve = {direction}")
        
        TOPIC = "domoticz/in"
        ROW1 = "{\"idx\":%d,\"nvalue\":0,\"svalue\":\"%s\"}"
        ROW2 = "{\"type\":\"command\",\"param\":\"udevice\",\"idx\":%d,\"nvalue\":%d,\"parsetrigger\":\"false\"}"
        ROW3 = "{\"type\":\"command\",\"param\":\"udevice\",\"idx\":%d,\"nvalue\":%d,\"svalue\":\"%d\",\"parsetrigger\":\"false\"}"
        ROW4 = "{\"idx\":%d,\"nvalue\":%d}"
        ROW5 = "{\"type\":\"command\",\"param\":\"udevice\",\"idx\":%d,\"nvalue\":%d,\"svalue\":\"%d\"}"

        MSG = [{'topic':TOPIC, 'payload':ROW1 % (self.temp_idx, str(tank_temp)), 'qos':0, 'retain':False},
                       (TOPIC,           ROW1 % (self.tank_set_point_idx, str(tank_set_point)), 0, False),
                       (TOPIC,           ROW1 % (self.ext_temp_idx, str(outdoor_temp)), 0, False),
                       (TOPIC,           ROW1 % (self.freq_idx, freq), 0, False),
                       (TOPIC,           ROW1 % (self.booster_idx, booster), 0, False),
                       (TOPIC,           ROW2 % (self.power_idx, power), 0, False),
                       (TOPIC,           ROW3 % (self.mode_idx, power, mode_t), 0, False),
                       #(TOPIC,           ROW3 % (self.working_idx, working, working_t), 0, False),
                       (TOPIC,           ROW5 % (self.working_idx, working_n, working_t), 0, False),
                       #(TOPIC,           ROW3 % (self.tank_working_idx, tank_working, tank_working_t), 0, False),
                       (TOPIC,           ROW5 % (self.tank_working_idx, tank_working_n, tank_working_t), 0, False),

              ]

        if (Mode[aquarea.mode] == Mode.Tank or power == 0 or direction == ThreeWayValve.DHW):

            self.log.debug(f"Maybe DHW")

            if ((Mode[aquarea.mode] == Mode.Tank or direction == ThreeWayValve.DHW) and freq > 0):

                self.log.debug(f"Sending DHW temperature")
                MSG.extend([(TOPIC, ROW1 % (self.dhw_out_temp_idx, str(water_outlet_temp)), 0, False)])
                MSG.extend([(TOPIC, ROW1 % (self.dhw_in_temp_idx, str(water_inlet_temp)), 0, False)])

        elif (power == 1 and (Mode[aquarea.mode] in [Mode.Heat, Mode.Heat_Tank, Mode.Cool_Tank, Mode.Cool])):
            
            MSG.extend([(TOPIC, ROW1 % (self.out_temp_idx, str(water_outlet_temp)), 0, False)])
            MSG.extend([(TOPIC, ROW1 % (self.in_temp_idx, str(water_inlet_temp)), 0, False)])
            MSG.extend([(TOPIC, ROW1 % (self.water_thermo_shift_idx, str(water_thermo_shift)), 0, False)])

            if (Mode[aquarea.mode] in [Mode.Heat, Mode.Heat_Tank]):
                water_target_temp = aquarea.heat_setpoint_temp
                self.log.debug(f"heat_setpoint_temp = {water_target_temp}")
                MSG.extend([(TOPIC, ROW1 % (self.water_set_point_idx, str(water_target_temp)), 0, False)])
            else:
                water_target_temp = aquarea.cool_setpoint_temp
                self.log.debug(f"cool_setpoint_temp = {water_target_temp}")
                MSG.extend([(TOPIC, ROW1 % (self.water_set_point_idx, str(water_target_temp)), 0, False)])
        
        self.log.info(MSG)
         
        self.log.info(self.broker)
        rc = publish.multiple(MSG, hostname=self.broker, port=self.port, client_id="pa_aw_mbs")
        self.log.info("Publish: %s" % (rc))

class MQTT:
    
    broker = None
    port = None
    log = None

    def __init__(self, broker, port, log):
        self.broker = broker
        self.port = port
        self.log = log

    def sensor(self, name, key, value, unit, device_class, state_class, icon, sensor):

        topic0 = f"homeassistant/{sensor}/aquarea_{key}"
        topic = f"{topic0}/config"
        payload = {
            "name": f"{name}",
            "state_topic": f"{topic0}/state",
            "unique_id": f"aquarea_{key}",
            "force_update": "true",
        }
        if unit and unit != "bool":
            payload["unit_of_measurement"] = f"{unit}"
        if device_class:
            payload["device_class"] = device_class
        if state_class:
            payload["state_class"] = state_class
        if icon:
            payload.update({"icon": icon})

        payload["device"] = {
            "name": "aquarea",
            "identifiers": ["T-CAP 9 kW Monobloc"],
            "model": "WH-MXC09D3E5",
            "manufacturer": "Panasonic",
        }
        value_ = value
        if sensor == "binary_sensor":
          if value == 0:
            value_ = "OFF"
          else:
            value_ = "ON"
        payloads = js.dumps(payload)
        conf_msg = {"topic": topic, "payload": payloads}
        topic = f"{topic0}/state"
        val_msg = {"topic": topic, "payload": value_}
        return conf_msg, val_msg

    def send(self, aquarea):

        MSG = []
        value_msgs = []

        # Tank Temp
        tank_temp = aquarea.tank_water_temp
        self.log.debug(f"tank_water_temp = {tank_temp}")
        conf_msg, val_msg = self.sensor("Tank Water Temperature", "tank_water_temp", tank_temp, "°C", "temperature", None, "mdi:water-thermometer", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Tank Set Point
        tank_set_point = aquarea.tank_setpoint_temp
        self.log.debug(f"tank_setpoint_temp = {tank_set_point}")
        conf_msg, val_msg = self.sensor("Tank Water Setpoint Temp", "tank_setpoint_temp", tank_set_point, "°C", "temperature", None, "mdi:thermometer-water", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Outdoor temp
        outdoor_temp = aquarea.otudoor_temp
        self.log.debug(f"otudoor_temp = {outdoor_temp}")
        conf_msg, val_msg = self.sensor("Outdoor temperature", "outdoor_temp", outdoor_temp, "°C", "temperature", None, "mdi:sun-thermometer-outline", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Outgoing Water Temperature
        water_outlet_temp = aquarea.water_out_temp
        self.log.debug(f"water_out_temp = {water_outlet_temp}")

        # Ingoing Water Temperature
        water_inlet_temp = aquarea.water_in_temp
        self.log.debug(f"water_in_temp = {water_inlet_temp}")

        # Compressor frequency
        freq = aquarea.compressor
        self.log.debug(f"compressor = {freq}")
        conf_msg, val_msg = self.sensor("Compressor Frequency", "compressor", freq, "Hz", "frequency", None, "mdi:sine-wave", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Water termo shift
        water_thermo_shift = aquarea.water_thermo_shift
        self.log.debug(f"water_thermo_shift = {water_thermo_shift}")

        # Mode
        mode_t = Mode[aquarea.mode].value * 10
        self.log.debug(f"mode = {aquarea.mode}, mode.value = {mode_t}")
        conf_msg, val_msg = self.sensor("Operating Mode", "operation_mode", aquarea.mode, None, None, None, "mdi:cog-outline", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Power
        power = OnOff[aquarea.system].value
        self.log.debug(f"system = {aquarea.system}, system.value = {power}")
        if power == 0:
            mode_t = 0
        conf_msg, val_msg = self.sensor("Power", "power", power, "bool", None, None, "mdi:power", "binary_sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Booster
        booster = OnOff[aquarea.booster].value
        self.log.debug(f"booster = {aquarea.booster}, booster.value = {booster}")
        conf_msg, val_msg = self.sensor("Booster Status", "booster", booster, "bool", None, None, None, "binary_sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Working
        working = Working[aquarea.working].value
        working_t = working * 10
        working_n = 0 if working == 0 else 1
        self.log.debug(f"working = {aquarea.working}, working.value = {working}")
        conf_msg, val_msg = self.sensor("Climate", "working", aquarea.working, None, None, None, "mdi:cog-outline", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        # Tank Working
        tank_working = Working[aquarea.tank_working].value
        tank_working_t = tank_working * 10
        tank_working_n = 0 if tank_working == 0 else 1

        self.log.debug(f"working = {aquarea.working}, working.value = {working}")
        conf_msg, val_msg = self.sensor("Tank Climate", "tank_working", aquarea.tank_working, None, None, None, "mdi:cog-outline", "sensor")
        MSG.append(conf_msg)
        value_msgs.append(val_msg)

        direction = None
        if OnOff[aquarea.tank_connection] == OnOff.On:
            direction = thrree_way_direction()

        self.log.debug(f"tank_working = {aquarea.tank_working}, tank_working.value = {tank_working}")
        self.log.debug(f"3-way valve = {direction}")

        if (Mode[aquarea.mode] == Mode.Tank or power == 0 or direction == ThreeWayValve.DHW):

            self.log.debug(f"Maybe DHW")

            if ((Mode[aquarea.mode] == Mode.Tank or direction == ThreeWayValve.DHW) and freq > 0):

                self.log.debug(f"Sending DHW temperature")
                conf_msg, val_msg = self.sensor("DHW Outgoing Water Temperature", "dhw_water_out_temp", water_outlet_temp, "°C", "temperature", None, "mdi:water-plus", "sensor")
                MSG.append(conf_msg)
                value_msgs.append(val_msg)
                conf_msg, val_msg = self.sensor("DHW Ingoing Water Temperature", "dhw_water_in_temp", water_inlet_temp, "°C", "temperature", None, "mdi:water-minus", "sensor")
                MSG.append(conf_msg)
                value_msgs.append(val_msg)

        elif (power == 1 and (Mode[aquarea.mode] in [Mode.Heat, Mode.Heat_Tank, Mode.Cool_Tank, Mode.Cool])):

            conf_msg, val_msg = self.sensor("Outgoing Water Temperature", "water_out_temp", water_outlet_temp, "°C", "temperature", None, "mdi:water-plus", "sensor")
            MSG.append(conf_msg)
            value_msgs.append(val_msg)
            conf_msg, val_msg = self.sensor("Ingoing Water Temperature", "_water_in_temp", water_inlet_temp, "°C", "temperature", None, "mdi:water-minus", "sensor")
            MSG.append(conf_msg)
            value_msgs.append(val_msg)
            conf_msg, val_msg = self.sensor("Water Current Thermoshift", "water_thermo_shift", water_thermo_shift, "°C", "temperature", None, "mdi:thermometer-chevron-up", "sensor")
            MSG.append(conf_msg)
            value_msgs.append(val_msg)

            if (Mode[aquarea.mode] in [Mode.Heat, Mode.Heat_Tank]):
                water_target_temp = aquarea.heat_setpoint_temp
                self.log.debug(f"heat_setpoint_temp = {water_target_temp}")
                conf_msg, val_msg = self.sensor("Heating Setpoint Temperature", "heat_setpoint_temp", water_target_temp, "°C", "temperature", None, "mdi:thermometer-auto", "sensor")
                MSG.append(conf_msg)
                value_msgs.append(val_msg)
            else:
                water_target_temp = aquarea.cool_setpoint_temp
                self.log.debug(f"cool_setpoint_temp = {water_target_temp}")
                conf_msg, val_msg = self.sensor("Cooling Setpoint Temperature", "cool_setpoint_temp", water_target_temp, "°C", "temperature", None, "mdi:thermometer-auto", "sensor")
                MSG.append(conf_msg)
                value_msgs.append(val_msg)


        # Publish to MQTT
        self.log.info(MSG)
        rc = publish.multiple(MSG, hostname=self.broker, port=self.port, client_id="pa_aw_mbs")
        self.log.info("Publish: %s" % (rc))
        time.sleep(0.5)
        self.log.info(value_msgs)
        rc = publish.multiple(value_msgs, hostname=self.broker, port=self.port, client_id="pa_aw_mbs")
        self.log.info("Publish: %s" % (rc))


if __name__ == "__main__":
    import logging
    import logging.config
    from os import path

    log_file_path = path.join(path.dirname(path.abspath(__file__)), 'pa_aw_mbs_log_config.ini')
    logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
    log = logging.getLogger("aquarea")

    main()

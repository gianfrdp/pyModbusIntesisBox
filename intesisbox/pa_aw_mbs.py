'''
PA-AW-MBS-1: Modbus RTU (EIA485) Interface for Panasonic Aquarea series (no H series) using pyModbus
'''
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from enum import Enum
import math
import queue
import logging
log = logging.getLogger(__name__)

INTESIS_NULL = 0x8000
DEG = "(°C)"
HZ = "(Hz)"
MIN = "(min)"
WH = "(Wh)"

READ = 0x1
WRITE = 0x2
READ_WRITE = 0x1 | 0x2

INTESISBOX_MAP = {
    # General System Control
    0:  {"name": "system", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Power', "access": READ_WRITE},
    1:  {"name": "otudoor_temp", "type": "temp", "desc": f'Outdoor temperature {DEG}', "access": READ},
    2:  {"name": "water_out_temp", "type": "temp", "desc": f'Outgoing Water Temperature {DEG}', "access": READ},
    3:  {"name": "water_in_temp", "type": "temp", "desc": f'Ingoing Water Temperature {DEG}', "access": READ},
    4:  {"name": "mode", "values": {0: "None", 1: "Heat", 2: "Heat+Tank", 3: "Tank", 4: "Cool+Tank", 5: "Cool"}, "type": "int", "desc": 'Operating Mode', "access": READ_WRITE},
    # Climate Configuration
    10: {"name": "config_mode", "values": {0: "Off", 1: "Heat", 2: "Cool"}, "type": "int", "desc": 'Climate Mode (heat/cool)', "access": READ},
    11: {"name": "working", "values": {0: "Normal", 1: "Eco", 2: "Powerful"}, "type": "int", "desc": 'Climate Working Mode', "access": READ_WRITE},
    12: {"name": "heat_low_outdoor_set_temperature", "type": "temp", "desc": f'Outdoor Temp for Heating at Low Water Temp {DEG}', "access": READ_WRITE},
    13: {"name": "heat_high_outdoor_set_temperature", "type": "temp", "desc": f'Water Setpoint for Heating at Low Outdoor Temp {DEG}', "access": READ_WRITE},
    14: {"name": "heat_low_water_set_temperature", "type": "temp", "desc": f'Outdoor Temp for Heating at High Water Temp {DEG}', "access": READ_WRITE},
    15: {"name": "heat_high_water_set_temperature", "type": "temp", "desc": f'Water Setpoint for Heating at High Outdoor Temp {DEG}', "access": READ_WRITE},
    16: {"name": "water_thermo_shift", "type": "temp", "desc": f'Water Current Thermoshift {DEG}', "access": READ_WRITE},
    17: {"name": "heat_temperature_max", "type": "temp", "desc": f'Outdoor Temp for Heating off (Max) {DEG}', "access": READ_WRITE},
    18: {"name": "heat_temperature_min", "values": {0: "Disabled", 1: "Enabled"}, "type": "int", "desc": 'Outdoor Temp for Heating off (Min) mode', "access": READ},
    19: {"name": "heat_out_temp_min", "type": "temp", "desc": f'Outdoor Temp for Heating off (Min) {DEG}', "access": READ},
    20: {"name": "heater_setpoint_temp", "type": "temp", "desc": f'Outdoor Temp for Heater On {DEG}', "access": READ},
    21: {"name": "heater_capacity", "values": {0x55: "0 KW", 0x58: "3 KW", 0x5b: "6 KW", 0x5e: "9 KW"}, "type": "int", "desc": 'Heater Capacity Selection', "access": READ_WRITE},
    22: {"name": "heater_max_capacity", "type": "int", "desc": 'Max Heater Capacity', "access": READ},
    23: {"name": "cool_setpoint_temp", "type": "temp", "desc": f'Cooling Setpoint Temperature {DEG}', "access": READ_WRITE},
    24: {"name": "heat_setpoint_temp", "type": "temp", "desc": f'Heating Setpoint Temperature {DEG}', "access": READ},
    25: {"name": "auto_heat_to_cool_temp", "type": "temp", "desc": f'Auto Heat to Cool Temperature {DEG}', "access": READ},
    26: {"name": "auto_cool_to_heat_temp", "type": "temp", "desc": f'Auto Cool to Heat Temperature {DEG}', "access": READ},
    27: {"name": "auto_mode", "values": {0: "Off", 1: "Heat", 2: "Cool"}, "type": "int", "desc": 'Auto Config Mode', "access": READ},
    # Tank Configuration
    30: {"name": "tank_mode", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Tank On/Off', "access": READ},
    31: {"name": "tank_working", "values": {0: "Normal", 1: "Eco", 2: "Powerful"}, "type": "int", "desc": 'Tank Working Mode', "access": READ_WRITE},
    32: {"name": "tank_water_temp", "type": "temp", "desc": f'Tank Water Temperature {DEG}', "access": READ},
    33: {"name": "tank_setpoint_temp", "type": "temp", "desc": f'Tank Water Setpoint Temp {DEG}', "access": READ_WRITE},
    34: {"name": "heat_interval", "type": "int", "desc": 'Heat-up Interval', "access": READ_WRITE},
    35: {"name": "operation_interval", "type": "min", "desc": f'Operation Interval {MIN}', "access": READ_WRITE},
    36: {"name": "booster_delay", "type": "int", "desc": 'Booster Delay Time', "access": READ_WRITE},
    37: {"name": "sterilization_on", "type": "int", "desc": 'Sterilization On', "access": WRITE},
    38: {"name": "tank_ster_temp", "type": "temp", "desc": f'Sterilization Boiling Temp {DEG}', "access": READ_WRITE},
    39: {"name": "tank_ster_time", "type": "int", "desc": 'Sterilization Continuing Time', "access": READ},
    # Consumption
    47: {"name": "heat_wh", "type": "int", "desc": f'Heat mode consumption {WH}', "access": READ},
    48: {"name": "cool_wh", "type": "int", "desc": f'Cool mode consumption {WH}', "access": READ},
    49: {"name": "tank_wh", "type": "int", "desc": f'Tank mode consumption {WH}', "access": READ},
    # Maintenance
    50: {"name": "test_mode_1", "type": "int", "desc": 'Test mode 1', "access": WRITE},
    51: {"name": "test_mode_2", "type": "int", "desc": 'Test Mode 2', "access": WRITE},
    52: {"name": "error", "type": "err", "desc": 'Error', "access": READ},
    53: {"name": "error_history", "type": "err", "desc": 'Historical Error', "access": READ},
    54: {"name": "error_reset_1", "type": "int", "desc": 'Error Reset 1', "access": WRITE},
    55: {"name": "error_reset_2", "type": "int", "desc": 'Error Reset 2', "access": WRITE},
    56: {"name": "tank_warn", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Warning Tank Temp. Status', "access": READ},
    57: {"name": "defrost", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Defrost Status', "access": READ},
    58: {"name": "solar", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Solar Status', "access": READ},
    59: {"name": "booster", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Booster Status', "access": READ},
    60: {"name": "compressor", "type": "int", "desc": f'Compressor Frequency {HZ}', "access": READ},
    61: {"name": "compressor_hour", "type": "int", "desc": 'Compressor Hours', "access": READ_WRITE},
    62: {"name": "pump_down", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Pump Down', "access": READ},
    63: {"name": "force_mode", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Force Mode', "access": READ_WRITE},
    64: {"name": "force_deice", "type": "int", "desc": 'Force Deice', "access": WRITE},
    65: {"name": "service", "values": {0x00: "Normal", 0x01: "Service pumpdown", 0x02: "Service pump"}, "type": "int", "desc": 'Service', "access": READ_WRITE},
    66: {"name": "quiet", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Quiet Mode', "access": READ_WRITE},
    67: {"name": "heater_when_heat", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Heater When Heat', "access": READ_WRITE},
    68: {"name": "heater_status", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Heater Status', "access": READ},
    69: {"name": "heater_mode", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Heater Mode', "access": READ},
    70: {"name": "alarm_status", "values": {0: "No alarm", 1: "Alarm"}, "type": "int", "desc": 'Alarm Status', "access": READ},
    71: {"name": "dry_concrete_temp", "type": "temp", "desc": 'Dry Concrete Temp', "access": READ},
    72: {"name": "air_purge", "values": {0: "Off", 1: "On"}, "type": "int", "desc": 'Air Purge', "access": READ_WRITE},
    73: {"name": "pump_speed", "type": "int", "desc": 'Pump Speed', "access": READ_WRITE},
    74: {"name": "erp_operation", "type": "int", "desc": 'ERP Operation', "access": READ_WRITE},
    75: {"name": "erp_param", "values": {0: "Hz", 1: "Td", 2: "FM", 3: "I1"}, "type": "int", "desc": 'ERP PArameters', "access": READ},
    76: {"name": "erp_data", "type": "int", "desc": 'ERP Data', "access": READ},
    77: {"name": "slow_fast_test", "values": {0: "Normal", 1: "Slow Time", 2: "Fast Time", 3: "Slow Day", 4: "Fast Day"}, "type": "int", "desc": '', "access": READ},
    # Unit Configuration
    80: {"name": "room_thermostat", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Room thermostat', "access": READ},
    81: {"name": "tank_connection", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Tank Connection', "access": READ},
    82: {"name": "solar_priority", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Solar Priority', "access": READ},
    83: {"name": "heating_priority", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Heating Priority', "access": READ},
    84: {"name": "cooling_priority", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Cooling Priority', "access": READ},
    85: {"name": "sterilization", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Sterilization', "access": READ},
    86: {"name": "base_pan_heater", "values": {0x55: "Type A", 0xAA: "Type B"}, "type": "int", "desc": 'Base Pan Heater', "access": READ},
    87: {"name": "anti_freezing", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Anti freezing', "access": READ},
    88: {"name": "booster_heater", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Booster Heater', "access": READ},
    89: {"name": "cool_mode_selection", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Cool Mode Selected', "access": READ},
    90: {"name": "base_pan_heater_selection", "values": {0x55: "Off", 0xAA: "On"}, "type": "int", "desc": 'Base Pan Heater Selected', "access": READ},
    # System Configuration
    1000: {"name": "thermoshift_heat_eco", "type": "temp", "desc": f'Climate Preset Heat Thermoshift (ECO) {DEG}', "access": READ_WRITE},
    1001: {"name": "thermoshift_heat_powerful", "type": "temp", "desc": f'Climate Preset Heat Thermoshift (POWERFUL) {DEG}', "access": READ_WRITE},
    1002: {"name": "thermoshift_cool_eco", "type": "temp", "desc": f'Climate Preset Cool Thermoshift (ECO) {DEG}', "access": READ_WRITE},
    1003: {"name": "thermoshift_cool_powerful", "type": "temp", "desc": f'Climate Preset Cool Thermoshift (POWERFUL) {DEG}', "access": READ_WRITE},
    1004: {"name": "thermoshift_tank_eco", "type": "temp", "desc": f'Preset Tank Thermoshift (ECO) {DEG}', "access": READ_WRITE},
    1005: {"name": "thermoshift_tank_powerful", "type": "temp", "desc": f'Preset Tank Thermoshift (POWERFUL) {DEG}', "access": READ_WRITE},
    1006: {"name": "sync", "values": {0: "Off", 1: "Trigger"}, "type": "int", "desc": 'Sync', "access": READ_WRITE},
    1007: {"name": "led", "values": {0: "Disabled", 1: "Enabled"}, "type": "int", "desc": 'LED', "access": READ_WRITE}
}

ERROR_MAP = {
      0 : { 'code': 'H00', 'desc': 'No abnormality detected'},
      2 : { 'code': 'H91', 'desc': 'Tank booster heater OLP abnormality'},
     13 : { 'code': 'F38', 'desc': 'Unknown'},
     20 : { 'code': 'H90', 'desc': 'Indoor / outdoor abnormal communication'},
     36 : { 'code': 'H99', 'desc': 'Indoor heat exchanger freeze prevention'},
     38 : { 'code': 'H72', 'desc': 'Tank temperature sensor abnormality'},
     42 : { 'code': 'H12', 'desc': 'Indoor / outdoor capacity unmatched'},
    156 : { 'code': 'H76', 'desc': 'Indoor - control panel communication abnormality'},
    193 : { 'code': 'F12', 'desc': 'Pressure switch activate'},
    195 : { 'code': 'F14', 'desc': 'Outdoor compressor abnormal rotation'},
    196 : { 'code': 'F15', 'desc': 'Outdoor fan motor lock abnormality'},
    197 : { 'code': 'F16', 'desc': 'Total running current protection'},
    200 : { 'code': 'F20', 'desc': 'Outdoor compressor overheating protection'},
    202 : { 'code': 'F22', 'desc': 'IPM overheating protection'},
    203 : { 'code': 'F23', 'desc': 'Outdoor DC peak detection'},
    204 : { 'code': 'F24', 'desc': 'Refrigerant cycle abnormality'},
    205 : { 'code': 'F27', 'desc': 'Pressure switch abnormality'},
    207 : { 'code': 'F46', 'desc': 'Outdoor current transformer open circuit'},
    208 : { 'code': 'F36', 'desc': 'Outdoor air temperature sensor abnormality'},
    209 : { 'code': 'F37', 'desc': 'Indoor water inlet temperature sensor abnormality'},
    210 : { 'code': 'F45', 'desc': 'Indoor water outlet temperature sensor abnormality'},
    212 : { 'code': 'F40', 'desc': 'Outdoor discharge pipe temperature sensor abnormality'},
    214 : { 'code': 'F41', 'desc': 'PFC control'},
    215 : { 'code': 'F42', 'desc': 'Outdoor heat exchanger temperature sensor abnormality'},
    216 : { 'code': 'F43', 'desc': 'Outdoor defrost temperature sensor abnormality'},
    222 : { 'code': 'H95', 'desc': 'Indoor / outdoor wrong connection'},
    224 : { 'code': 'H15', 'desc': 'Outdoor compressor temperature sensor abnormality'},
    225 : { 'code': 'H23', 'desc': 'Indoor refrigerant liquid temperature sensor abnormality'},
    226 : { 'code': 'H24', 'desc': 'Unknown'},
    227 : { 'code': 'H38', 'desc': 'Indoor / outdoor mismatch'},
    228 : { 'code': 'H61', 'desc': 'Unknown'},
    229 : { 'code': 'H62', 'desc': 'Water flow switch abnormality'},
    230 : { 'code': 'H63', 'desc': 'Refrigerant low pressure abnormality'},
    231 : { 'code': 'H64', 'desc': 'Refrigerant high pressure abnormality'},
    232 : { 'code': 'H42', 'desc': 'Compressor low pressure abnormality'},
    233 : { 'code': 'H98', 'desc': 'Outdoor high pressure overload protection'},
    234 : { 'code': 'F25', 'desc': 'Cooling / heating cycle changeover abnormality'},
    235 : { 'code': 'F95', 'desc': 'Cooling high pressure overload protection'},
    236 : { 'code': 'H70', 'desc': 'Indoor backup heater OLP abnormality'},
    237 : { 'code': 'F48', 'desc': 'Outdoor EVA outlet temperature sensor abnormality'},
    238 : { 'code': 'F49', 'desc': 'Outdoor bypass outlet temperature sensor abnormality'},
  65535 : { 'code': 'N/A', 'desc': 'Communication error between PA-IntesisHome'}
}

COMMAND_MAP = {
    "system":                            { "reg":  0, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "mode":                              { "reg":  4, "values": { "Heat": 1, "Heat+Tank": 2, "Tank": 3, "Cool+Tank": 4, "Cool": 5 }, "type": "int" },
    "working":                           { "reg": 11, "values": { "Normal": 0, "Eco": 1, "Powerful": 2 }, "type": "int" },
    "heat_low_outdoor_set_temperature":  { "reg": 12, "min": -15, "max": 15, "type": "temp" },
    "heat_high_outdoor_set_temperature": { "reg": 13, "min": -15, "max": 15, "type": "temp" },
    "heat_low_water_set_temperature":    { "reg": 14, "min": 25, "max": 55, "type": "temp" },
    "heat_high_water_set_temperature":   { "reg": 15, "min": 25, "max": 55, "type": "temp" },
    "water_thermo_shift":                { "reg": 16, "min": -5, "max": 5, "type": "temp" },
    "heat_temperature_max":              { "reg": 17, "min": 5, "max": 35, "type": "temp" },
    "heater_setpoint_temp":              { "reg": 20, "min": -15, "max": 20, "type": "temp" },
    "cool_setpoint_temp":                { "reg": 23, "min": 5, "max": 20, "type": "temp" },
    "tank_working":                      { "reg": 31, "values": { "Normal": 0, "Eco": 1, "Powerful": 2 }, "type": "int" },
    "tank_setpoint_temp":                { "reg": 33, "min": 40, "max": 75, "type": "temp" },
    "heat_interval":                     { "reg": 34, "min": 5, "max": 95, "type": "int" },
    "operation_interval":                { "reg": 35, "min": 1, "max": 20, "type": "min" },
    "booster_delay":                     { "reg": 36, "min": 20, "max": 95, "type": "int" },
    "sterilization_on":                  { "reg": 37, "values": { "On": 0xAA }, "type": "int" },
    "tank_ster_temp":                    { "reg": 38, "min": 40, "max": 75, "type": "temp" },
    "test_mode_1":                       { "reg": 50, "values": { "Go": 1 }, "type": "int" },
    "test_mode_2":                       { "reg": 51, "values": { "Go": 1 }, "type": "int" },
    "error_reset_1":                     { "reg": 54, "values": { "Go": 1 }, "type": "int" },
    "error_reset_2":                     { "reg": 55, "values": { "Go": 1 }, "type": "int" },
    "compressor_hour":                   { "reg": 61, "min": 0, "max": 65535, "type": "int" },
    "force_mode":                        { "reg": 63, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "force_deice":                       { "reg": 64, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "service":                           { "reg": 65, "values": { "Normal": 0x00, "Service pumpdown": 0x01, "Service pump": 0x02 }, "type": "int" },
    "quiet":                             { "reg": 66, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "heater_when_heat":                  { "reg": 67, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "air_purge":                         { "reg": 72, "values": { "Off": 0, "On": 1 }, "type": "int" },
    "pump_speed":                        { "reg": 73, "min": 1, "max": 7, "type": "int" },
    "erp_operation":                     { "reg": 74, "min": 0, "max": 80, "type": "int" },
    "thermoshift_heat_eco":              { "reg": 1000, "min": 0, "max": 5, "type": "temp" },
    "thermoshift_heat_powerful":         { "reg": 1001, "min": 0, "max": 5, "type": "temp" },
    "thermoshift_cool_eco":              { "reg": 1002, "min": 0, "max": 5, "type": "temp" },
    "thermoshift_cool_powerful":         { "reg": 1003, "min": 0, "max": 5, "type": "temp" },
    "thermoshift_tank_eco":              { "reg": 1004, "min": 0, "max": 10, "type": "temp" },
    "thermoshift_tank_powerful":         { "reg": 1005, "min": 0, "max": 10, "type": "temp" },
    "sync":                              { "reg": 1006, "values": { "Trigger": 1 }, "type": "int" },
    "led":                               { "reg": 1007, "values": { "Disabled": 0, "Enabled": 1 }, "type": "int" }
}

class Mode(Enum):
    Nothing = 0
    Heat = 1
    Heat_Tank = 2
    Tank = 3
    Cool_Tank = 4
    Cool = 5

class OnOff(Enum):
    Off = 0
    On = 1

class Working(Enum):
    Normal = 0
    Eco = 1
    Powerful = 2

class AquareaModbus:

    def __init__(self, port='/dev/ttyUSB0', slave=1, stopbits=1, bytesize=8, parity='N', baudrate=9600, 
                    timeout=1, byteorder=Endian.Big, wordorder=Endian.Big, unit=10):

        self.__slave = slave
        self.__port = port
        self.__stopbits = stopbits
        self.__bytesize = bytesize
        self.__parity = parity
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__byteorder = byteorder
        self.__wordorder = wordorder
        self.__unit = unit
        self.__data = {}
        self.__mq = queue.Queue()
        self.__is_connected = False
        log.debug("slave = %d, port = %s, stopbits = %d, bytesize = %d, parity = %s, baudrate = %d, timeout = %d, byteorder = %s, wordorder = %s, unit = %d" % (self.__slave, self.__port, self.__stopbits, self.__bytesize, self.__parity, self.__baudrate, self.__timeout, self.__byteorder, self.__wordorder, self.__unit))

    def connect(self):
        self.__client = ModbusSerialClient(method='rtu', port=self.__port, stopbits=self.__stopbits, bytesize=self.__bytesize, 
                                            parity=self.__parity, baudrate=self.__baudrate, timeout=self.__timeout, unit=self.__slave)
        self.__client.connect()
        self.__is_connected = True

    def close(self):
        self.__client.close()
        self.__is_connected = False

    @property
    def version(self):
        return "0.4"

    @property
    def slave(self):
        """ Modbus Slave ID """
        return self.__slave
    
    @property
    def qsize(self):
        return self.__mq.qsize()

    @property
    def is_connected(self) -> bool:
        return self.__is_connected

    # 3.2.1 General System Control ****************************************************************************
    @property
    def system(self):
        """ [System On/Off] 0: Off 1: On [0-R/W] """
        return self.__get_int_value("system")

    @system.setter
    def system(self, value):
        self.__set_gen_mode("system", value)

    @property
    def otudoor_temp(self):
        """ [Outdoor Temperature] -127°C to 127°C (x1 or x10 values) [1-R] """
        return self.__get_temp_value("otudoor_temp")

    @property
    def water_out_temp(self):
        """ [Outgoing Water Temperature] 0°C to 127°C (x1 or x10 values) [2-R] """
        return self.__get_temp_value("water_out_temp")

    @property
    def water_in_temp(self):
        """ [Ingoing Water Temperature] 0°C to 127°C (x1 or x10 values) [3-R] """
        return self.__get_temp_value("water_in_temp")

    @property
    def mode(self):
        """ [Operating mode] 0: None 4, 1: Heat, 2: Heat/Tank, 3: Tank, 4: Cool/Tank, 5: Cool [4-R/W] """
        return self.__get_int_value("mode")

    @mode.setter
    def mode(self, value):
        self.__set_gen_mode("mode", value)

    # 3.2.2 Climate Configuration ****************************************************************************
    @property
    def config_mode(self):
        """ [Climate Operating mode] 0: Off, 1: Heat, 2: Cool [10-R] """
        return self.__get_int_value("config_mode")

    @property
    def working(self):
        """ [Working Mode] 0: Normal, 1: Eco, 2: Powerful [11-R/W] """
        return self.__get_int_value("working")

    @working.setter
    def working(self, value):
        self.__set_gen_mode("working", value)

    @property
    def heat_low_outdoor_set_temperature(self):
        """ [Outdoor Temp for Heating at Low Water Temp] -15°C to 15°C [12-R/W] """
        return self.__get_temp_value("heat_low_outdoor_set_temperature")

    @heat_low_outdoor_set_temperature.setter
    def heat_low_outdoor_set_temperature(self, value):
        self.__set_in_range_value("heat_low_outdoor_set_temperature", value)

    @property
    def heat_high_outdoor_set_temperature(self):
        """ [Outdoor Temp for Heating at High Water Temp] -15°C to 15°C [13-R/W] """
        return self.__get_temp_value("heat_high_outdoor_set_temperature")

    @heat_high_outdoor_set_temperature.setter
    def heat_high_outdoor_set_temperature(self, value):
        self.__set_in_range_value("heat_high_outdoor_set_temperature", value)

    @property
    def heat_low_water_set_temperature(self):
        """ [Water Setpoint for Heating at Low Outdoor Temp] 25°C to 55°C [14-R/W] """
        return self.__get_temp_value("heat_low_water_set_temperature")

    @heat_low_water_set_temperature.setter
    def heat_low_water_set_temperature(self, value):
        self.__set_in_range_value("heat_low_water_set_temperature", value)

    @property
    def heat_high_water_set_temperature(self):
        """ [Water Setpoint for Heating at High Outdoor Temp] 25°C to 55°C [15-R/W] """
        return self.__get_temp_value("heat_high_water_set_temperature")

    @heat_high_water_set_temperature.setter
    def heat_high_water_set_temperature(self, value):
        self.__set_in_range_value("heat_high_water_set_temperature", value)

    @property
    def water_thermo_shift(self):
        """ [Water Current Thermoshift] -5°C to 5°C [16-R/W] """
        return self.__get_temp_value("water_thermo_shift")

    @water_thermo_shift.setter
    def water_thermo_shift(self, value):
        self.__set_in_range_value("water_thermo_shift", value)

    @property
    def heat_temperature_max(self):
        """ [Outdoor Temp for Heating off (Max)] 5°C to 35°C (x1 or x10 values) [17-R/W] """
        return self.__get_temp_value("heat_temperature_max")

    @heat_temperature_max.setter
    def heat_temperature_max(self, value):
        self.__set_in_range_value("heat_temperature_max", value)

    @property
    def heater_setpoint_temp(self):
        """ [Outdoor Temp for Heater On] -15°C to 20°C (x1 or x10 values) [20-R/W] """
        return self.__get_temp_value("heater_setpoint_temp")

    @heater_setpoint_temp.setter
    def heater_setpoint_temp(self, value):
        self.__set_in_range_value("heater_setpoint_temp", value)

    @property
    def cool_setpoint_temp(self):
        """ [Cooling Setpoint Temperature] 5°C to 20°C (x1 or x10 values) [23-R/W] """
        return self.__get_temp_value("cool_setpoint_temp")

    @cool_setpoint_temp.setter
    def cool_setpoint_temp(self, value):
        self.__set_in_range_value("cool_setpoint_temp", value)

    @property
    def heat_setpoint_temp(self):
        """ [Heating Setpoint Temperature] 20°C to 70°C (x1 or x10 values) [24-R] """
        return self.__get_temp_value("heat_setpoint_temp")

    # 3.2.3 Tank Configuration ****************************************************************************
    @property
    def tank_mode(self):
        """ [Tank On/Off] 0: Off, 1: On [30-R] """
        return self.__get_temp_value("tank_mode")

    @property
    def tank_working(self):
        """ [Tank Working Mode] 0: Normal, 1: Eco, 2: Powerful [31-R/W] """
        return self.__get_temp_value("tank_working")

    @tank_working.setter
    def tank_working(self, value):
        self.__set_gen_mode("tank_working", value)

    @property
    def tank_water_temp(self):
        """ [Water Temp] 0°C to 127°C (x1 or x10 values) [32-R] """
        return self.__get_temp_value("tank_water_temp")

    @property
    def tank_setpoint_temp(self):
        """ [Water Setpoint Temp] 40°C to 75°C (x1 or x10 values) [33-R/W] """
        return self.__get_temp_value("tank_setpoint_temp")

    @tank_setpoint_temp.setter
    def tank_setpoint_temp(self, value):
        self.__set_in_range_value("tank_setpoint_temp", value)

    @property
    def heat_interval(self):
        """ [Heat-up Interval] 5 to 95 Min [34-R/W] """
        return self.__get_int_value("heat_interval")

    @property
    def operation_interval(self):
        """ [Operation Interval] 1 to 20, (1=30Min, 2=1h, 3:1h 30min, 20=10h) [35-R/W] """
        return self.__get_int_value("operation_interval")

    @property
    def booster_delay(self):
        """ [Booster Delay Time] 20 to 95 Min [36-R/W] """
        return self.__get_int_value("booster_delay")

    @property
    def tank_ster_temp(self):
        """ [Sterilization Boiling Temp] 40°C to 75°C (x1 or x10 values) [38-R/W] """
        return self.__get_temp_value("tank_ster_temp")

    # 3.2.4 Consumption ****************************************************************************
    @property
    def heat_wh(self):
        """ [Heat mode consumption] 0 to 65535 Wh [47-R] """
        return self.__get_temp_value("heat_wh")

    @property
    def cool_wh(self):
        """ [Cool mode consumption] 0 to 65535 Wh [48-R] """
        return self.__get_temp_value("cool_wh")

    @property
    def tank_wh(self):
        """ [Tank mode consumption] 0 to 65535 Wh [49-R] """
        return self.__get_temp_value("tank_wh")

    # 3.2.5 Maintenance ****************************************************************************
    @property
    def error(self):
        """ [Error Code from Indoor Unit] [52-R] """
        error_code = self.__get_int_value("error")
        remote_code = ERROR_MAP[error_code]["code"]
        error_desc = ERROR_MAP[error_code]["desc"]
        return ("%s: %s" % (remote_code, error_desc))

    @property
    def error_history(self):
        """ [Error History Code from Indoor Unit] [53-R] """
        error_code = self.__get_int_value("error_history")
        remote_code = ERROR_MAP[error_code]["code"]
        error_desc = ERROR_MAP[error_code]["desc"]
        return ("%s: %s" % (remote_code, error_desc))

    def error_reset_1(self, value):
        self.__set_gen_mode("error_reset_1", value)

    def error_reset_2(self, value):
        self.__set_gen_mode("error_reset_2", value)

    @property
    def tank_warn(self):
        """ [Warning Tank Temp. Status] 0: off, 1: On [56-R] """
        return self.__get_int_value("tank_warn")

    @property
    def defrost(self):
        """ [Defrost Status] 0: off, 1: On [57-R] """
        return self.__get_int_value("defrost")

    @property
    def solar(self):
        """ [Solar Status] 0: off, 1: On [58-R] """
        return self.__get_int_value("solar")

    @property
    def booster(self):
        """ [Booster Status] 0: off, 1: On [59-R] """
        return self.__get_int_value("booster")

    @property
    def compressor(self):
        """ [Compressor Frequency] 0 to 255 Hz [60-R] """
        return self.__get_int_value("compressor")

    @property
    def compressor_hour(self):
        """ [Compressor Operating Hours] 0 to 65535 h [61-R/W] """
        return self.__get_int_value("compressor_hour")

    @property
    def pump_down(self):
        """ [Pump Down] 0:Off, 1: On [62-R] """
        return self.__get_int_value("pump_down")

    @property
    def force_mode(self):
        """ [Force Mode < 5sec] 0:Off, 1: On [63-R/W] """
        return self.__get_int_value("force_mode")

    @property
    def service(self):
        """ [Service SW Code] 0x00: Normal, 0x01: Service pumpdown, 0x02: Service pump [65-R/W] """
        return self.__get_int_value("service")

    @property
    def quiet(self):
        """ [Quiet Mode] 0:Off, 1: On [66-R/W] """
        return self.__get_int_value("quiet")

    @quiet.setter
    def quiet(self, value):
        self.__set_gen_mode("quiet", value)

    @property
    def heater_when_heat(self):
        """ [Heater When Heat] 0:Off, 1: On [67-R/W] """
        return self.__get_int_value("heater_when_heat")

    @property
    def heater_status(self):
        """ [Heater Status] 0:Off, 1: On [68-R] """
        return self.__get_int_value("heater_status")

    @property
    def heater_mode(self):
        """ [Heater Mode] 0:Off, 1: On [69-R] """
        return self.__get_int_value("heater_mode")

    @property
    def alarm_status(self):
        """ [Heater Mode] 0: No alarm, 1: Alarm [70-R] """
        return self.__get_int_value("alarm_status")

    @property
    def dry_concrete_temp(self):
        """ [Dry Concrete Temperature] 25°C to 65°C (x1 or x10 values) [71-R] """
        return self.__get_temp_value("dry_concrete_temp")

    @property
    def air_purge(self):
        """ [Air Purge] 0:Off, 1: On [72-R/W] """
        return self.__get_int_value("air_purge")

    @property
    def pump_speed(self):
        """ [Pump Speed] 1 to 7 [73-R/W] """
        return self.__get_int_value("pump_speed")

    @property
    def erp_operation(self):
        """ [ERP Operation] 0: Normal, 1 to 80 [74-R/W] """
        return self.__get_int_value("erp_operation")

    @property
    def erp_param(self):
        """ [ERP PArameters] 0: Hz, 1: Td, 2: FM, 3: I1 [75-R] """
        return self.__get_int_value("erp_param")

    @property
    def erp_data(self):
        """ [ERP Data] 0: Normal, 1 to 80 [76-R] """
        return self.__get_int_value("erp_data")

    @property
    def slow_fast_test(self):
        """ [Slow/Fast test] 0: Normal, 1: Slow Time, 2: Fast Time, 3: Slow Day, 4: Fast Day [77-R] """
        return self.__get_int_value("slow_fast_test")

    # 3.2.6 Unit Configuration ****************************************************************************
    @property
    def room_thermostat(self):
        """ [Room Thermostat] 0x55: Off, 0xAA: On [80-R] """
        return self.__get_int_value("room_thermostat")

    @property
    def tank_connection(self):
        """ [Tank Connection] 0x55: Off, 0xAA: On [81-R] """
        return self.__get_int_value("tank_connection")

    @property
    def solar_priority(self):
        """ [Solar Priority] 0x55: Off, 0xAA: On [82-R] """
        return self.__get_int_value("solar_priority")

    @property
    def heating_priority(self):
        """ [Heating Priority] 0x55: Off, 0xAA: On [83-R] """
        return self.__get_int_value("heating_priority")

    @property
    def cooling_priority(self):
        """ [Cooling Priority] 0x55: Off, 0xAA: On [84-R] """
        return self.__get_int_value("cooling_priority")

    @property
    def sterilization(self):
        """ [Sterilization] 0x55: Off, 0xAA: On [85-R] """
        return self.__get_int_value("sterilization")

    @property
    def base_pan_heater(self):
        """ [Base Pan Heater] 0x55: Off, 0xAA: On [86-R] """
        return self.__get_int_value("base_pan_heater")

    @property
    def anti_freezing(self):
        """ [Anti Freezing] 0x55: Off, 0xAA: On [87-R] """
        return self.__get_int_value("anti_freezing")

    @property
    def booster_heater(self):
        """ [Booster Heater] 0x55: Off, 0xAA: On [88-R] """
        return self.__get_int_value("booster_heater")

    @property
    def cool_mode_selection(self):
        """ [Cool Mode Selection] 0x55: Off, 0xAA: On [89-R] """
        return self.__get_int_value("cool_mode_selection")

    @property
    def base_pan_heater_selection(self):
        """ [Base Pan Heater Selection] 0x55: Off, 0xAA: On [90-R] """
        return self.__get_int_value("base_pan_heater_selection")

    # 3.2.7 System Configuration ****************************************************************************
    @property
    def thermoshift_heat_eco(self):
        """ [Decrease Climate Preset Heat Thermoshift (ECO)] 0°C to 5°C (x1 or x10 values) [1000-R/W] """
        return self.__get_temp_value("thermoshift_heat_eco")

    @thermoshift_heat_eco.setter
    def thermoshift_heat_eco(self, value):
        self.__set_in_range_value("thermoshift_heat_eco", value)

    @property
    def thermoshift_heat_powerful(self):
        """ [Increase Climate Preset Heat Thermoshift (POWERFUL)] 0°C to 5°C (x1 or x10 values) [1001-R/W] """
        return self.__get_temp_value("thermoshift_heat_powerful")

    @thermoshift_heat_powerful.setter
    def thermoshift_heat_powerful(self, value):
        self.__set_in_range_value("thermoshift_heat_powerful", value)

    @property
    def thermoshift_cool_eco(self):
        """ [Decrease Climate Preset Cool Thermoshift (ECO)] 0°C to 5°C (x1 or x10 values) [1002-R/W] """
        return self.__get_temp_value("thermoshift_cool_eco")

    @thermoshift_cool_eco.setter
    def thermoshift_cool_eco(self, value):
        self.__set_in_range_value("thermoshift_cool_eco", value)

    @property
    def thermoshift_cool_powerful(self):
        """ [Increase Climate Preset Cool Thermoshift (POWERFUL)] 0°C to 5°C (x1 or x10 values) [1003-R/W] """
        return self.__get_temp_value("thermoshift_cool_powerful")
    
    @thermoshift_cool_powerful.setter
    def thermoshift_cool_powerful(self, value):
        self.__set_in_range_value("thermoshift_cool_powerful", value)

    @property
    def thermoshift_tank_eco(self):
        """ [Decrease Climate Preset Tank Thermoshift (ECO)] 0°C to 10°C (x1 or x10 values) [1004-R/W] """
        return self.__get_temp_value("thermoshift_tank_eco")

    @thermoshift_tank_eco.setter
    def thermoshift_tank_eco(self, value):
        self.__set_in_range_value("thermoshift_tank_eco", value)

    @property
    def thermoshift_tank_powerful(self):
        """ [Increase Climate Preset Tank Thermoshift (POWERFUL)] 0°C to 10°C (x1 or x10 values) [1005-R/W] """
        return self.__get_temp_value("thermoshift_tank_powerful")

    @thermoshift_tank_powerful.setter
    def thermoshift_tank_powerful(self, value):
        self.__set_in_range_value("thermoshift_tank_powerful", value)

    @property
    def sync(self):
        """ [Trigger Synchronization] 1: Trigger [1006-R/W] """
        return self.__get_int_value("sync")

    @property
    def led(self):
        """ [LED Flashing enablement] 0: Disabled, 1: Enabled [1007-R/W] """
        return self.__get_int_value("led")


    def poll_data(self):
        """ Read data from Modbus and pull into internal variables """
        if self.__is_connected:
            rr = self.__client.read_holding_registers(address=0, count=91, unit=self.__slave)
            log.debug("registers < 1000 = %s" % rr.registers)

            for reg in INTESISBOX_MAP:
                if reg < 1000 and (INTESISBOX_MAP[reg]["access"] & READ):
                    self.__get_device_value(rr, reg)

            rr = self.__client.read_holding_registers(address=1000, count=8, unit=self.__slave)
            log.debug("registers <= 1000 = %s" % rr.registers)
            for reg in INTESISBOX_MAP:
                if reg >= 1000 and (INTESISBOX_MAP[reg]["access"] & READ):
                    self.__get_device_value(rr, reg, offset=1000)
            log.debug("_data = %s" % self.__data)

    def get_item_value(self, name, value):
        """ Get numeric value from name and string value """
        data = None
        res = None
        if name in self.__data:
            data = self.__data.get(name+".value")
            log.debug(f"data = {data}")
            res = data
            log.debug(f"{name}.{value} = {res}")
        else:
            log.debug(f"No data for {name},{value}")
        return res

    def get_all_valid_values(self):
        result = {}
        for name in self.__data:
            if name != None and not ("." in name) and self.__data[name] != None:
                DATA = {}
                DATA["value"] = self.__data[name]
                DATA["desc"] = INTESISBOX_MAP[self.__data[name+".reg"]]["desc"]
                log.debug("DATA = ")
                log.debug(DATA)
                result[name] = DATA
        return result

    def send_cmd(self):
        """ Send message Queue to Modbus device """
        if self.__is_connected:
            while (self.__mq.qsize() != 0):
                REG = self.__mq.get()
                reg = REG["reg"]
                value = REG["value"]
                rq = self.__client.write_register(address=reg, value=REG["value"], unit=self.__slave)
                if rq.isError():
                    raise Exception(f"Cannot send address={reg}, value={value}, unit={self.__slave}")
            log.info("No more commnad to send")

    ''' ------------------------------------------------------------------------------------------------------------
    Private methods 
    ------------------------------------------------------------------------------------------------------------ '''

    def __get_device_value(self, instance, reg, offset=0):
        """Internal method to load single register value"""
        log.debug("reg = %d" % reg)
        uid = reg - offset
        if reg in INTESISBOX_MAP:
            log.debug("INTESISBOX_MAP[%d] = %s" % (reg, INTESISBOX_MAP[reg]))
            # If the value is null (32768), set as None
            value = self.__get_data(instance, uid, 1)
            log.debug("HEX value[%d] = 0x%x" % (reg, value))
            log.debug(f"INTESISBOX_MAP[{reg}] = {INTESISBOX_MAP[reg]}")
            MAP    = INTESISBOX_MAP[reg]
            # Mapped value
            NAME   = MAP["name"]
            # Numeric value
            VALUE  = NAME+".value"
            # Original mapped value
            MVALUE = NAME+".mvalue"
            # Original value
            OVALUE = NAME+".ovalue"
            #log.debug(f"MAP({reg}) = {MAP}")
            REG = NAME+".reg"
            
            if value == INTESIS_NULL:
                self.__data[NAME]   = None
                self.__data[VALUE]  = None
                self.__data[OVALUE] = None
                self.__data[MVALUE] = None
                self.__data[REG] = reg
                log.debug("NULL value[%d]" % reg)
            else:
                if MAP["type"] == "int":
                    value = self.__get_int(instance, uid, 1)
                    log.debug("int value[%d] = %d" % (reg, value))
                elif MAP["type"] == "temp":
                    value = self.__get_temp(instance, uid, 1)
                    log.debug("temp value[%d] = %.1f" % (reg, value))
                elif MAP["type"] == "min":
                    value = self.__get_interval(self.__get_int(instance, uid, 1))
                    log.debug("min value[%d] = %d" % (reg, value))
                elif MAP["type"] == "err":
                    int_value = self.__get_interval(self.__get_int(instance, uid, 1))
                    code = ERROR_MAP[int_value]["code"]
                    desc = ERROR_MAP[int_value]["desc"]
                    value = code + ": " + desc
                    log.debug("err value[%d] = %s" % (reg, value))
                else:
                    value = self.__get_int(instance, reg, 1)
                    log.debug("unknown value[%d] = %d" % (reg, value))
                
                self.__data[VALUE] = value
                self.__data[OVALUE] = value
                self.__data[REG] = reg

                # Translate known regs to configuration item names
                value_map = MAP.get("values")
                if value_map:
                    mvalue = value_map.get(value, value)
                    log.debug("value_map value[%d] = %s" % (reg, mvalue))
                    self.__data[NAME] = mvalue
                    self.__data[MVALUE] = mvalue
                else:
                    self.__data[NAME] = value
                    self.__data[MVALUE] = value
                    log.debug("generic value[%d] = %s" % (reg, value))
            log.debug("_data[%d] = {name=%s, name.mvalue=%s, name.value=%s, name.ovalue=%s}" % 
                (reg, self.__data[NAME], self.__data[MVALUE], self.__data[VALUE], self.__data[OVALUE]))
        else:
            # Log unknown UIDs
            self.__data[f"unknown_reg_{reg}"] = None
            self.__data[f"unknown_reg_{reg}"+".value"] = None
            self.__data[f"unknown_reg_{reg}"+".reg"] = reg

    def __get_temp(self, instance, start, count) -> float:
        """Internal method to get temperature value from registers"""
        if not instance.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                instance.registers[start:(start+count)],
                byteorder=self.__byteorder, wordorder=self.__wordorder
            )   
            return float(decoder.decode_16bit_int() / self.__unit)
        else:
            return INTESIS_NULL

    def __get_int(self, instance, start, count) -> int:
        """Internal method to get 16 bit signed integer value from registers"""
        if not instance.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                instance.registers[start:(start+count)],
                byteorder=self.__byteorder, wordorder=self.__wordorder
            )
            value = decoder.decode_16bit_int()
            return value
        else:
            return INTESIS_NULL

    def __get_data(self, instance, start, count):
        """Internal method to get value from registers"""
        if not instance.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                instance.registers[start:(start+count)],
                byteorder=self.__byteorder, wordorder=self.__wordorder
            )
            value = decoder.decode_16bit_uint()
            return value
        else:
            return INTESIS_NULL

    def __get_interval(self, value):
        """Internal method to get calculate minute intervals"""
        return value * 30

    def __get_gen_value(self, name) -> str:
        """Internal method for getting generic value"""
        value = None
        if name in self.__data:
            value = self.__data.get(name)
            log.debug(f"{name} = {value}")
        else:
            log.debug(f"No value for {name}")
        return value

    def __get_int_value(self, name) -> int:
        """Internal method for getting int value"""
        value = self.__get_gen_value(name)
        if (isinstance(value, int)):
            int_val = int(value)
            return int_val
        else:
            return value

    def __get_temp_value(self, name) -> float:
        """Internal method for getting float value"""
        value = self.__get_gen_value(name)
        if (isinstance(value, float)):
            float_val = float(value)
            return float_val
        else:
            return value

    def __set_value(self, reg, value):
        """Internal method to send a register value"""
        is_temp = bool(INTESISBOX_MAP[reg]["type"] == "temp")
        is_int  = bool(INTESISBOX_MAP[reg]["type"] == "int")
        is_min  = bool(INTESISBOX_MAP[reg]["type"] == "min")

        if is_temp:
            svalue = value * self.__unit
        elif is_min:
            svalue = value * 30
        else:
            svalue = value
        log.debug(f"reg = {reg}, value = {value}, svalue = {svalue}")
        # Add svalue in FIFO
        REG = {"reg": reg, "value": svalue}
        self.__mq.put(REG)
        log.debug("Message Queue item:")
        log.debug(REG)

    def __set_gen_value(self, name, value):
        """Internal method for setting the generic value"""
        if type in COMMAND_MAP:
            self._set_value(
                COMMAND_MAP[name]["reg"], value
            )

    def __set_gen_mode(self, name, mode):
        """Internal method for setting the generic mode (type in {operating_mode, climate_working_mode, tank, etc.}) with a string value"""
        if mode in COMMAND_MAP[name]["values"]:
            reg = COMMAND_MAP[name]["reg"]
            value = COMMAND_MAP[name]["values"][mode]
            log.debug(f"reg = {reg}, mode = {mode}, value = {value}")
            self.__set_value(reg, value)

    def __set_in_range_value(self, name, value):
        """Internal method to set value in a range."""
        min_value = int(COMMAND_MAP[name]["min"])
        max_value = int(COMMAND_MAP[name]["max"])

        if min_value <= value <= max_value:
            self.__set_value(COMMAND_MAP[name]["reg"], value)
        else:
            raise ValueError(
                "Value for %s has to be in range [%d,%d]" % name, min_value, max_value
            )
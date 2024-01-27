#!/usr/bin/env python3

from intesisbox.pa_aw_mbs import AquareaModbus
from intesisbox.pa_aw_mbs import Mode
from intesisbox.pa_aw_mbs import OnOff
from intesisbox.pa_aw_mbs import Working
from intesisbox.pa_aw_mbs import ThreeWayValve
from paho.mqtt.client import Client
from paho.mqtt import publish
import json
import time
import uuid

_TOPIC = 'aquarea/+/cmd'
_broker = "192.168.2.32"
_port = 1883

counter = 0

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        log.debug("mqtt2aquarea ---------------------------")
        log.debug("connected OK")
        client.subscribe(_TOPIC, 1)
    else:
        log.debug("Bad connection Returned code=",rc)
        client.bad_connection_flag=True


def on_disconnect(client, userdata, rc):
    log.debug("disconnecting reason  "  +str(rc))

def poll(aquarea):

    aquarea.connect()
    aquarea.poll_data()
    aquarea.close()


def cmd(aquarea):
    aquarea.connect()
    if aquarea.qsize > 0:
        log.debug(f"Sending commands {aquarea.qsize}...")
        aquarea.send_cmd()
        aquarea.close()
        time.sleep(5)
        aquarea.connect()
        aquarea.poll_data()
        aquarea.close()

def sensor(name, key, value, unit, device_class, state_class, icon, sensor, options):

    topic0 = f"homeassistant/{sensor}/aquarea_{key}"
    topic1 = f"aquarea/{key}"
    topic = f"{topic0}/config"
    cmd_topic = f"{topic1}/cmd"
    state_topic = f"{topic1}/state"
    payload = {
        "name": f"{name}",
        "state_topic": f"{topic1}/state",
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
    if options:
       payload.update({"options": options})
    if sensor in ["switch", "select", "button", "light"]:
       payload.update({"command_topic": cmd_topic})

    payload["device"] = {
        "name": "aquarea",
        "identifiers": ["1DC91213A0"],
        "model": "WH-MXC09D3E5",
        "manufacturer": "Panasonic",
    }
    value_ = value
    if sensor == "binary_sensor":
      if value == 0 or value == "Off":
        value_ = "OFF"
      else:
        value_ = "ON"
    payloads = js.dumps(payload)
    conf_msg = {"topic": topic, "payload": payloads}
    val_msg = {"topic": state_topic, "payload": value_}
    return conf_msg, val_msg


### topic message
def on_message(mosq, obj, msg):

    MSG = []
    value_msgs = []

    aquarea = AquareaModbus(port='/dev/aquarea', slave=2, timeout=5, write_timeout=5, lockwait=10, retry=5)

    decoded_message = str(msg.payload.decode("utf-8"))
    topic = msg.topic
    log.debug(F'topic: {topic}, qos: {msg.qos}, payload: {decoded_message}')

    if topic == 'aquarea/power/cmd':
        _power = decoded_message
        log.debug(F'topic: {topic}, qos: {msg.qos}, payload: {decoded_message}')
        poll(aquarea)
        log.info(F"_power = {decoded_message}, aquarea.system = {aquarea.system}")
        aquarea.system = _power
        if aquarea.qsize > 0:
            cmd(aquarea)
            conf_msg, val_msg = sensor("Power", "power", _power, "bool", None, None, "mdi:power", "switch", None)
            MSG.append(conf_msg)
            value_msgs.append(val_msg)

    if topic == 'aquarea/operation_mode/cmd':
        _mode = decoded_message
        log.debug(F'topic: {topic}, qos: {msg.qos}, payload: {decoded_message}')
        poll(aquarea)
        log.info(F"_mode = {decoded_message}, aquarea.mode = {aquarea.mode}")
        aquarea.mode = _mode
        if aquarea.qsize > 0:
            cmd(aquarea)
            options = ["Heat", "Heat_Tank", "Tank", "Cool_Tank", "Cool"]
            conf_msg, val_msg = self.sensor("Operating Mode", "operation_mode", _mode, None, None, None, "mdi:cog-outline", "select")
            MSG.append(conf_msg)
            value_msgs.append(val_msg)

    if topic == 'aquarea/working/cmd':
        _working = decoded_message
        log.debug(F'topic: {topic}, qos: {msg.qos}, payload: {decoded_message}')
        poll(aquarea)
        log.info(F"_working = {decoded_message}, aquarea.working = {aquarea.working}")
        aquarea.working = _working
        if aquarea.qsize > 0:
            cmd(aquarea)
            options = ["Eco", "Normal", "Powerful"]
            conf_msg, val_msg = self.sensor("Climate", "working", _working, None, None, None, "mdi:cog-outline", "select", options)
            MSG.append(conf_msg)
            value_msgs.append(val_msg)


    if topic == 'aquarea/tank_working/cmd':
        _tank_working = decoded_message
        log.debug(F'topic: {topic}, qos: {msg.qos}, payload: {decoded_message}')
        poll(aquarea)
        log.info(F"_tank_working = {decoded_message}, aquarea.tank_working = {aquarea.tank_working}")
        aquarea.tank_working = _tank_working
        if aquarea.qsize > 0:
            cmd(aquarea)
            options = ["Eco", "Normal", "Powerful"]
            conf_msg, val_msg = self.sensor("Tank Climate", "tank_working", _tank_working, None, None, None, "mdi:cog-outline", "select", options)
            MSG.append(conf_msg)
            value_msgs.append(val_msg)

    # Publish to MQTT
    log.debug(MSG)
    if len(MSG) > 0:
        rc = publish.multiple(MSG, hostname=self.broker, port=self.port, client_id="mqtt2aquarea")
        log.debug("Publish: %s" % (rc))
        time.sleep(0.5)
    log.debug(value_msgs)
    if len(value_msgs) > 0:
        rc = publish.multiple(value_msgs, hostname=_broker, port=_port, client_id="mqtt2aquarea")
        log.debug("Publish: %s" % (rc))

    poll(aquarea)



def main():

    client = Client(client_id = "mqtt2aquarea_" + str(uuid.uuid1()))

    client.on_connect = on_connect
    client.on_message = on_message
    #client.enable_logger(log)
    client.connect(host=_broker, port=_port, keepalive=60)
    
    #client.loop_start()
    #try:
    #    while True:
    #        time.sleep(1)
    #except KeyboardInterrupt:
    #    print ("exiting")
    #    client.disconnect()
    #    client.loop_stop()
    
    try:
        client.loop_forever(timeout=1.0, max_packets=1, retry_first_connection=False)
    except KeyboardInterrupt:
        print ("exiting")
        client.disconnect()


if __name__ == "__main__":

    import logging
    import logging.config
    from os import path

    log_file_path = path.join(path.dirname(path.abspath(__file__)), 'mqtt2aquarea_log_config.ini')
    logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
    log = logging.getLogger("mqtt2aquarea")
    log.debug("Start")

    main()

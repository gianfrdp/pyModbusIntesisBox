#!/usr/bin/env python
"""
Pymodbus Synchronous Serial Forwarder
--------------------------------------------------------------------------
We basically set the context for the tcp serial server to be that of a
serial client! This is just an example of how clever you can be with
the data context (basically anything can become a modbus device).
"""
# --------------------------------------------------------------------------- # 
# import the various server implementations
# --------------------------------------------------------------------------- # 
from pymodbus.server.sync import StartTcpServer as StartServer
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from pymodbus.datastore.remote import RemoteSlaveContext
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.constants import Endian

import argparse

# --------------------------------------------------------------------------- # 
# configure the service logging
# --------------------------------------------------------------------------- # 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

def init_argparse() -> argparse.ArgumentParser:
    
    parser = argparse.ArgumentParser(description="Modbus <-> TCP gateway for Aquarea PA-AW-MBS-1"
                                        ,add_help=True
                                    )
    parser.add_argument("--device", help="Modbus serial device (default /dev/aquarea)", default="/dev/aquarea")
    parser.add_argument("--slave", help="Modbus salve ID (default 2)", type=int, default=2)
    parser.add_argument("--baud", choices=[2400,4800,9600,19200], type=int, help="Serial baudrate (default 9600)", default=9600)
    parser.add_argument("--stop", choices=[1,2], help="Stop bit (default 1)", type=int, default=1)
    parser.add_argument("--port", type=int, help="TCP port (default 5020)", default=5020)
    parser.add_argument('--version', action='version', version='%(prog)s v1.0')
    return parser

def run_serial_forwarder(slave, device, baudrate, stopbits, port):
    # ----------------------------------------------------------------------- #
    # initialize the datastore(serial client)
    # Note this would send the requests on the serial client with address = 0

    # ----------------------------------------------------------------------- #
    client = ModbusClient(method='rtu', port=device, stopbits=stopbits, 
                    bytesize=8, parity='N', baudrate=baudrate, 
                    timeout=1, byteorder=Endian.Big, wordorder=Endian.Big)
    # If required to communicate with a specified client use unit=<unit_id>
    # in RemoteSlaveContext
    # For e.g to forward the requests to slave with unit address 1 use
    # store = RemoteSlaveContext(client, unit=1)
    store = RemoteSlaveContext(client, unit=slave)
    context = ModbusServerContext(slaves=store, single=True)
    print(f"PA-AW-MBS-1 RTU / TCP gateway")
    print(f"slave = {slave}, device = {device}, baudrate = {baudrate}, stopbits = {stopbits}, port={port}")

    # ----------------------------------------------------------------------- #
    # run the server you want
    # ----------------------------------------------------------------------- #
    StartServer(context, address=("0.0.0.0", port))

def main():
    parser = init_argparse()
    args = parser.parse_args()
    run_serial_forwarder(slave=args.slave, device=args.device, baudrate=args.baud, stopbits=args.stop, port=args.port)

if __name__ == "__main__":
    main()

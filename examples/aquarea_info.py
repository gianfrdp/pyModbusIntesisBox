#!/usr/bin/env python3

from  intesisbox.pa_aw_mbs import AquareaModbus
from  intesisbox.pa_aw_mbs import Mode
from  intesisbox.pa_aw_mbs import OnOff
from  intesisbox.pa_aw_mbs import Working
import sys
from datetime import datetime

def main():
    aquarea = AquareaModbus(port='/dev/aquarea', slave=2, timeout=5, lockwait=10, retry=5)
    print(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}. ModBus device {aquarea.slave}")

    print("Connecting...")
    aquarea.connect()
    aquarea.poll_data()
    print("Disconnecting...")
    aquarea.close()
    print("Disconnected")

    #---------------------------------------------------------------------------# 
    # Print values
    #---------------------------------------------------------------------------# 
    print(f"Aquarea PA-AW-MBS-1 Version {aquarea.version}.")
    print(f"ModBus device {aquarea.slave}")
    values = aquarea.get_all_valid_values()

    print("".ljust(56, '-'))
    for name in values:
        desc = values[name]["desc"]
        value = values[name]["value"]
        msg = desc.ljust(55, '.')
        print(f"{msg}: {value}")
    print("".ljust(56, '-'))

    # print('Power:........................................... %s' % aquarea.system)
    # print('Outdoor temperature:............................. %.1f °C' % aquarea.otudoor_temp)

if __name__ == "__main__":
    import logging
    import logging.config
    from os import path

    log_file_path = path.join(path.dirname(path.abspath(__file__)), 'pa_aw_mbs_log_config.ini')
    logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
    log = logging.getLogger("aquarea_info")

    main()
# pyModbusIntesisBox
This project is a python3 library for interfacing with the IntesisBox PA-AW-MBS-1 (no H generation) Modbus RTU  controller using pyModbus.

[Datasheet ](https://www.intesis.com/docs/librariesprovider11/other-documentation/intesisbox-deprecated/intesisbox_pa-aw-mbs-1_datasheet_en_d.pdf)
[Installation ](https://www.intesis.com/docs/librariesprovider11/other-documentation/intesisbox-deprecated/intesisbox_pa-aw-mbs-1_installation_manual_en_d.pdf)
[Compatibility ](https://www.intesis.com/docs/librariesprovider11/other-documentation/intesisbox-deprecated/intesishome_pa-aw-xxx-1_compatibility_d.pdf)
[Protocol Manua l](https://www.intesis.com/docs/librariesprovider11/other-documentation/intesisbox-deprecated/intesisbox_pa-aw-mbs-1_user_manual_en_d.pdf)

## Installation
```shell

git clone git@github.com:gianfrdp/pyModbusIntesisBox.git
cd pyModbusIntesisBox
python3 setup.py build

python3 setup.py install --user
or
sudo python3 setup.py install
```

## Read/Write properties
### Read

 - aquarea.poll_data()

then use

 - aqaurea.system
 - aquarea.mode
 - aquarea.tank_setpoint_temp
 - ...

### Change values/modes

Simply set values properties and call

 - auarea.system = "On"
 - aquarea.mode = "Tank"
 - aquarea.tank_setpoint_temp = 48
 - aquarea.send_cmd()

## Library basic example
```python
from  intesisbox.pa_aw_mbs import AquareaModbus

def main():
    aquarea = AquareaModbus(port='/dev/ttyUSB0', slave=1, stopbits=1, bytesize=8, parity='N', baudrate=9600)

    printf("Connecting...")
    aquarea.connect()
    printf("Polling data...")
    aquarea.poll_data()
    '''
      use as needed aquarea properties, such as: aquarea.system aquarea.mode, etc
    '''
    printf("Disconnecting...")
    aquarea.close()

if __name__ == "__main__":
    main()

```

in examples directory there are some exapmles:

- aquarea_info.py: read only program to read put on log all values
- aquarea.py: read/write program that sends also some values to [domoticz](https://www.domoticz.com/)
- aquarea.cron: sample cron file containng a year scheduling for Aquarea using aquarea.py

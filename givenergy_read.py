import datetime
from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.inverter import Model
from givenergy_modbus.model.plant import Plant

import arrow
import time
import json
import sys
client = GivEnergyClient(host="192.168.1.147")

p = Plant(number_batteries=1)
client.refresh_plant(p, full_refresh=True)

inverter = p.inverter.dict()
battery = p.batteries[0].dict()

print ("----------------------------------------")
print ("Inverter Data")
print ("----------------------------------------")
# print the inverter data key:value pairs
for key, value in inverter.items():
    print(f"{key}: {value}")


print ()
print ("----------------------------------------")
print ("Battery Data")
print ("----------------------------------------")
# print the battery data key:value pairs
for key, value in battery.items():
    print(f"{key}: {value}")

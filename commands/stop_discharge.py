import datetime
from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.inverter import Model
from givenergy_modbus.model.plant import Plant

import arrow
import time
import json
import sys
client = GivEnergyClient(host="192.168.1.147")

client.set_mode_storage((datetime.time(hour=00, minute=00), datetime.time(hour=00, minute=00)),None,True)

#client.set_mode_dynamic()

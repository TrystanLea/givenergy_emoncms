import datetime
from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.inverter import Model
from givenergy_modbus.model.plant import Plant

import time
import json
import sys
import requests
import configparser
import logging
import redis
import nmap_oem

redis_client = redis.Redis(host='localhost', port=6379, db=0)

logging.basicConfig(filename='/var/log/emoncms/givenergy.log', level=logging.INFO, format='%(asctime)s %(message)s')

#log to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)


# get script directory
script_dir = sys.path[0]

# load config.ini
config = configparser.ConfigParser()
config.read(script_dir+'/config.ini')

emoncms_host = config['emoncms']['host']
emoncms_apikey = config['emoncms']['apikey']

givenergy_host = None
if 'host' in config['givenergy']:
    givenergy_host = config['givenergy']['host']

if 'mac' in config['givenergy']:
    network_range = nmap_oem.get_network_range()
    if network_range:
        print(f"Determined network range: {network_range}")
        devices = nmap_oem.nmap(network_range)
        for device in devices:
            mac_address = nmap_oem.get_mac_address(device['ip'])
            if mac_address == config['givenergy']['mac']:
                print(f"Found {mac_address} at IP: {device['ip']}")
                logging.info(f"Found {mac_address} at IP: {device['ip']}")
                givenergy_host = device['ip']
                break

if givenergy_host is None:
    sys.exit(0)

last_time = time.time() - 10

schedule = [
    {"time":"00:00", "state":"off"},
    {"time":"01:00", "state":"charge"},
    {"time":"05:00", "state":"off"},
    {"time":"16:00", "state":"discharge"},
    {"time":"19:00", "state":"off"}
]

# If retry count reaches 6 (1 minute), restart the script
retry_count = 0

while (True):
    time.sleep(0.1)

    # Every 5 seconds, get the current plant status
    if (time.time() - last_time >= 10):
        last_time = time.time()

        if retry_count >= 6:
            logging.error("Restarting the script")
            sys.exit(0)

        logging.info("Requesting data")
        try:
            client = GivEnergyClient(host=givenergy_host)
            p = Plant(number_batteries=1)
            client.refresh_plant(p, full_refresh=True)

            inverter = p.inverter.dict()
            battery = p.batteries[0].dict()
            
            if 'p_load_demand' in inverter:

                # prepare the data to be sent to the servers
                data_to_send = {
                    "node": "givenergy",
                    
                    "charge_status":inverter['charge_status'],
                    "system_mode":inverter['system_mode'],
                    "battery_power_mode":inverter['battery_power_mode'],
                    
                    "p_load_demand": inverter['p_load_demand'],
                    "p_battery": inverter['p_battery'],
                    "p_grid_out": inverter['p_grid_out'],
                    "p_inverter_out": inverter['p_inverter_out'],
                    "p_pv1": inverter['p_pv1'],
                    "p_pv2": inverter['p_pv2'],
                    "battery_percent": inverter['battery_percent'],
                    "v_battery_cells_sum": battery['v_battery_cells_sum'],
                    "battery_soc": battery['battery_soc']
                }
                # pretty print the data
                logging.info(json.dumps(data_to_send, indent=4))

                if config['emoncms']['redis_enable'] == '1':
                    redis_client.rpush('emonhub:sub', json.dumps(data_to_send))
                    redis_client.set('battery_percent',inverter['battery_percent'])

                # sent the data to local emoncms server
                if config['emoncms']['http_enable'] == '1':
                    try:
                        url = emoncms_host+"/input/post.json?node=givenergy&json=" + json.dumps(data_to_send) + "&apikey=" + emoncms_apikey
                        result = requests.get(url)
                        # print result 
                        logging.info(result.text)

                    except Exception as e:
                        logging.error(e)
                        pass

                # Control the battery
                hour = datetime.datetime.now().hour
                minute = datetime.datetime.now().minute
                # format 00:00
                hmstr = "{:02d}:{:02d}".format(hour, minute)
                current_time = hour + minute/60

                state = "off"
                cost = 0

                # load agile schedule
                schedule = json.loads(redis_client.get('agile_schedule'))

                for s in schedule:
                    # convert the time string to float
                    # s_time = int(s["time"].split(":")[0]) + int(s["time"].split(":")[1])/60
                    # if current_time >= s_time:
                    #     state = s["state"]
                    if time.time() >= s["timestamp"]:
                        state = s["state"]
                        cost = s["cost"]


                # get the current state of the battery
                current_state = "off"
                # if the charge slot is set to 00:00 - 23:59, then the battery is charging
                dts = inverter['charge_slot_1'][0]
                dte = inverter['charge_slot_1'][1]
                if dts.hour == 0 and dts.minute == 0 and dte.hour == 23 and dte.minute == 59:
                    current_state = "charging"
                # if the charge slot is set to 00:00 - 00:00, AND the battery power mode is 1, then the battery is discharging
                elif data_to_send["battery_power_mode"] == 1:
                    current_state = "discharging"

                # print the current time, state, and current state
                logging.info("Current time: "+str(hmstr)+" State: "+str(state)+" Current state: "+str(current_state)+" Cost: "+str(cost))

                

                if current_state != "charging" and state == "charge":
                    logging.info("Starting battery charge")
                    client = GivEnergyClient(host=givenergy_host)
                    client.set_charge_slot_1((datetime.time(hour=00, minute=00), datetime.time(hour=23, minute=59)))

                if current_state != "discharging" and state == "discharge":
                    logging.info("Starting battery discharge")
                    client = GivEnergyClient(host=givenergy_host)
                    client.set_charge_slot_1((datetime.time(hour=00, minute=00), datetime.time(hour=00, minute=00)))
                    time.sleep(1)
                    client = GivEnergyClient(host=givenergy_host)
                    client.set_mode_dynamic()

                if current_state != "off" and state == "off":
                    logging.info("Stopping battery charge & discharge")
                    client = GivEnergyClient(host=givenergy_host)
                    client.set_charge_slot_1((datetime.time(hour=00, minute=00), datetime.time(hour=00, minute=00)))
                    time.sleep(1)
                    client = GivEnergyClient(host=givenergy_host)
                    client.set_mode_storage((datetime.time(hour=00, minute=00), datetime.time(hour=00, minute=00)),None,True)

        except Exception as e: 
            logging.error(e)
            retry_count += 1
            pass
    





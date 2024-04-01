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

redis_client = redis.Redis(host='localhost', port=6379, db=0)

logging.basicConfig(filename='/var/log/emoncms/givenergy.log', level=logging.ERROR, format='%(asctime)s %(message)s')

# get script directory
script_dir = sys.path[0]

# load config.ini
config = configparser.ConfigParser()
config.read(script_dir+'/config.ini')

emoncms_host = config['emoncms']['host']
emoncms_apikey = config['emoncms']['apikey']
givenergy_host = config['givenergy']['host']

last_time = time.time() - 10

while (True):
    time.sleep(0.1)

    # Every 5 seconds, get the current plant status
    if (time.time() - last_time >= 10):
        last_time = time.time()

        logging.info("Requesting data")
        try:
            client = GivEnergyClient(host=givenergy_host)
            p = Plant(number_batteries=1)
            client.refresh_plant(p, full_refresh=True)

            inverter = p.inverter.dict()
            battery = p.batteries[0].dict()
            
            if 'p_load_demand' in inverter:

                # prepare the data to be sent to the server
                data_to_send = {
                    "node": "givenergy",
                    
                    "p_load_demand": inverter['p_load_demand'],
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

        except Exception as e:
            logging.error(e)
            pass
    





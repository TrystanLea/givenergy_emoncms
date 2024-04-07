# Description: This script will calculate the optimal schedule for charging and discharging the battery
#              based on the Agile tariff. It will store the schedule in the Redis database for the main
#              service to read and act upon.

# Import the required libraries
import requests
import redis
import json
from datetime import datetime
import time
import sys
import math
import configparser

# Connect to the Redis server
r = redis.Redis(host='localhost', port=6379, db=0)

# -------------------------------------------------------
# 1) Parse configuration
# -------------------------------------------------------
# get script directory
script_dir = sys.path[0]
# load config.ini
config = configparser.ConfigParser()
config.read(script_dir+'/config.ini')

# -------------------------------------------------------
# 2) Get the battery state of charge, this is read by the main service
#    We will use this to determine the change time required to get back to target soc 
# -------------------------------------------------------
battery_soc = r.get('battery_percent')
if battery_soc:
    battery_soc = int(r.get('battery_percent'))
    print("Battery soc: "+str(battery_soc)+"%")
else:
    battery_soc = 0
    
# -------------------------------------------------------
# 3) Calculate time to charge, charge rate is about 24%/hour
# -------------------------------------------------------
charge_rate_prc_hour = 24
prc_to_charge = int(config['agile']['target_soc']) - battery_soc
if prc_to_charge>0:
    charge_half_hours = math.ceil(2 * (prc_to_charge / charge_rate_prc_hour))
else:
    charge_half_hours = 0
    
print ("Half hours to charge: "+str(charge_half_hours))
    
# -------------------------------------------------------
# 4) Load the Agile tariff data
# -------------------------------------------------------
# Retry 6 times
for i in range(6):
    try:
        # Load the data from the API
        tariff = config['agile']['tariff'].strip()
        region = config['agile']['region'].strip()
        url = "https://api.octopus.energy/v1/products/"+tariff+"/electricity-tariffs/E-1R-"+tariff+"-"+region+"/standard-unit-rates/"
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code != 200:
            print("Failed to get Agile tariff data")
            time.sleep(60)
            continue

        data = response.json()
        if 'results' not in data:
            print("Failed to get Agile tariff data")
            time.sleep(60)
            continue
        # If we got here, we have the data
        break
    except:
        print("Failed to get Agile tariff data, retrying")
        time.sleep(60)

# If we failed to get the data, exit
if 'results' not in data:
    print("Failed to get Agile tariff data")
    sys.exit(1)

# -------------------------------------------------------
# 5) Process the data
# -------------------------------------------------------
data_ts = []
for item in data['results']:
    # Convert the date to a timestamp    
    timestamp = int(datetime.timestamp(datetime.strptime(item['valid_from'],"%Y-%m-%dT%H:%M:%S%z")))

    # skip if older than now
    if timestamp >= time.time()-1800:
        data_ts.append([timestamp, item['value_exc_vat'], 0])
        
# Sort the data by timestamp
data_ts.sort()
# limit array length to 48 half hours
if len(data_ts) > 48:
    data_ts = data_ts[:48]

# Sort by value
# cheapest to most expensive
data_ts.sort(key=lambda x: x[1])

# -------------------------------------------------------
# 6) Select charge slots
# -------------------------------------------------------
# For calculating the average charge price
sum_charge_price = 0
sum_charge_price_n = 0

# If we need to charge
if charge_half_hours>0:
    # Mark the cheapest half hours for charging
    for item in data_ts[:charge_half_hours]:
        # Mark as charge
        item[2] = 1
        # Add to sum
        sum_charge_price += item[1]
        sum_charge_price_n += 1
        
# Calculate the average charge price
if sum_charge_price_n>0:
    average_charge_price = sum_charge_price / sum_charge_price_n
else:
    average_charge_price = 11
    
print("Average charge price: "+str(average_charge_price))

# -------------------------------------------------------
# 7) Calculate minimum discharge price
# -------------------------------------------------------
minimum_discharge_price = average_charge_price
if minimum_discharge_price>0:
    round_trip_efficiency = float(config['agile']['round_trip_efficiency'])
    minimum_discharge_price = minimum_discharge_price * (1/round_trip_efficiency)

# If the battery costs £5000 and has a lifespan of 7500 cycles of 8 kWh that's a cost of 8.3p/kWh
# If the battery costs £5000 and has a lifespan of 20 years and is cycled approx 5 kWh every day, that's 13.7p/kWh
# I've gone for something in the middle here as the minimum discharge price uplift
minimum_discharge_price = minimum_discharge_price + float(config['agile']['unit_cost_of_storage'])

print("Minimum discharge price: "+str(minimum_discharge_price))

# -------------------------------------------------------
# 8) Select discharge slots
# -------------------------------------------------------
# Mark half hours with a price higher than the minimum discharge price
for item in data_ts:
    if item[1] >= minimum_discharge_price:
        # Mark as discharge
        item[2] = 2


# -------------------------------------------------------
# 9) Build the schedule
# -------------------------------------------------------
schedule = []
for item in data_ts:
    cost = item[1]

    if item[2] == 1:
        state = "charge"
    elif item[2] == 2:
        state = "discharge"
    else:
        state = "off"

    schedule.append({"timestamp":item[0], "cost": cost, "state":state})

# sort by timestamp
schedule.sort(key=lambda x: x["timestamp"])

# Print the schedule
for s in schedule:
    print(datetime.fromtimestamp(s["timestamp"]), s["cost"], s["state"])

# If we are not in dry run mode, save the schedule to Redis
# This will be read by the main service
if not int(config['agile']['dry_run']):
    print ("Saving schedule to redis")
    r.set('agile_schedule', json.dumps(schedule))

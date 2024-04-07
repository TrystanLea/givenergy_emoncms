import requests
import redis
import json
from datetime import datetime
import time
import sys
import math

tariff = 'AGILE-23-12-06'
region = 'A'

# Connect to the Redis server
r = redis.Redis(host='localhost', port=6379, db=0)

# Target soc
target_soc = 90

# 1) Get the battery state of charge, this is read by the main service
#    We will use this to determine the change time required to get back to target soc 
battery_soc = r.get('battery_percent')
if battery_soc:
    battery_soc = int(r.get('battery_percent'))
    # print(battery_soc)
else:
    battery_soc = 0
    
battery_soc = 60
    
# Calculate time to charge, charge rate is about 24%/hour
charge_rate_prc_hour = 24
prc_to_charge = target_soc - battery_soc
if prc_to_charge>0:
    charge_half_hours = math.ceil(2 * (prc_to_charge / charge_rate_prc_hour))
else:
    charge_half_hours = 0
    
print ("Half hours to charge: "+str(charge_half_hours))
    
# Check if the data is in the cache
if r.exists('agile_data'):
    # If it is, load the data from the cache
    data = json.loads(r.get('agile_data'))
    print('Data loaded from cache')
else:
    # Load the data from the API
    url = "https://api.octopus.energy/v1/products/"+tariff+"/electricity-tariffs/E-1R-"+tariff+"-"+region+"/standard-unit-rates/"
    response = requests.get(url)
    data = response.json()

    # store data in redis for 1 hour
    r.setex('agile_data', 3600, json.dumps(data))

data_ts = []
for item in data['results']:
    # Convert the date to a timestamp    
    timestamp = int(datetime.timestamp(datetime.strptime(item['valid_from'],"%Y-%m-%dT%H:%M:%S%z")))

    # skip if older than now
    if timestamp >= time.time()-1800:
        data_ts.append([timestamp, item['value_exc_vat'], 0])
        
# Sort the data by timestamp
data_ts.sort()
# limit array length to 12
if len(data_ts) > 48:
    data_ts = data_ts[:48]

# Sort by value
data_ts.sort(key=lambda x: x[1])

sum_charge_price = 0
sum_charge_price_n = 0

# If we need to charge
if charge_half_hours>0:
    # Mark 8 cheapest
    for item in data_ts[:charge_half_hours]:
        item[2] = 1
        sum_charge_price += item[1]
        sum_charge_price_n += 1
        
if sum_charge_price_n>0:
    average_charge_price = sum_charge_price / sum_charge_price_n
else:
    average_charge_price = 11
    
print("Average charge price: "+str(average_charge_price))

minimum_discharge_price = average_charge_price
if minimum_discharge_price>0:
    # assume conservative 75% round trip efficiency
    minimum_discharge_price = minimum_discharge_price * 1.25

# If the battery costs £5000 and has a lifespan of 7500 cycles of 8 kWh that's a cost of 8.3p/kWh
# If the battery costs £5000 and has a lifespan of 20 years and is cycled approx 5 kWh every day, that's 13.7p/kWh
# I've gone for something in the middle here as the minimum discharge price uplift
minimum_discharge_price = minimum_discharge_price + 11

print("Minimum discharge price: "+str(minimum_discharge_price))
    
# Mark 8 most expensive
for item in data_ts:
    if item[1] >= minimum_discharge_price:
        item[2] = 2

schedule = []

for item in data_ts:
    cost = item[1]
    # delivered_cost = (cost * 1.25) + 6.25
    # print(datetime.fromtimestamp(item[0]), cost, item[2])

    if item[2] == 1:
        state = "charge"
    elif item[2] == 2:
        state = "discharge"
    else:
        state = "off"

    schedule.append({"timestamp":item[0], "cost": cost, "state":state})

# sort by timestamp
schedule.sort(key=lambda x: x["timestamp"])

for s in schedule:
    print(datetime.fromtimestamp(s["timestamp"]), s["cost"], s["state"])

r.set('agile_schedule', json.dumps(schedule))

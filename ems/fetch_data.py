import time
import requests
import json
import sys
import configparser
import random

# get script directory
script_dir = sys.path[0]

# load config.ini
config = configparser.ConfigParser()
config.read(script_dir+'/config.ini')

emoncms_apikey = config['config']['emoncms_apikey']
givenergy_ems_ip = config['config']['givenergy_ems_ip']

# Define URLs
source_url = f"https://{givenergy_ems_ip}/action/getSysSummaryInfoAction?name=User"
target_url = f"https://emoncms.org/input/post?node=givenergy&apikey={emoncms_apikey}"

# Disable SSL warnings (useful for local HTTPS requests with self-signed certs)
requests.packages.urllib3.disable_warnings()

def fetch_data():
    try:
        global source_url
        # add random=0.8519328280130646 to the end of the URL to prevent caching
        url = source_url + "&random=" + str(random.random())
        print ("source_url: ", url)

        response = requests.get(url, verify=False, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "msg" in data:
            return data["msg"]
        else:
            print("Unexpected response format:", data)
            return None
    except requests.RequestException as e:
        print("Error fetching data:", e)
        return None

def send_to_emoncms(data):
    try:
        json_payload = json.dumps(data)
        full_url = f"{target_url}&fulljson={json_payload}"
        response = requests.get(full_url)
        response.raise_for_status()
        print("Data sent successfully:", response.text)
    except requests.RequestException as e:
        print("Error sending data:", e)

def main():
    while True:
        data = fetch_data()
        if data:
            send_to_emoncms(data)
        time.sleep(10)

if __name__ == "__main__":
    main()
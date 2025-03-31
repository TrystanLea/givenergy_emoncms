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
username = config['config']['givenergy_ems_user']
password = config['config']['givenergy_ems_pass']

# Define URLs
login_url = f"https://{givenergy_ems_ip}/action/userLoginAction?name={username}&password={password}"
source_url = f"https://{givenergy_ems_ip}/action/getSysSummaryInfoAction?name={username}"
target_url = f"https://emoncms.org/input/post?node=givenergy&apikey={emoncms_apikey}"

# Disable SSL warnings (useful for local HTTPS requests with self-signed certs)
requests.packages.urllib3.disable_warnings()

def givenergy_ems_login():
    global login_url

    try:
        print("Logging in...")
        loging_url_with_random = login_url + "&random=" + str(random.random())
        login_response = requests.get(loging_url_with_random, verify=False, timeout=5)
        login_response.raise_for_status()
        login_data = login_response.json()

        print("login_data: ", login_data)

        if "msg" in login_data:
            if "authority" in data["msg"]:
                if data["msg"]["authority"] == 1:
                    print("Login successful")
                    return True
            # If we get here, login failed    
            print("Login failed:", login_data)
            return False
        else:
            print("Unexpected login response format:", login_data)
            return False
    except requests.RequestException as e:
        print("Error fetching data:", e)
        return False


def fetch_data():
    try:
        global source_url, login_url  
        # add random=0.8519328280130646 to the end of the URL to prevent caching
        url = source_url + "&random=" + str(random.random())
        print ("source_url: ", url)

        response = requests.get(url, verify=False, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "msg" in data:
            # Check if logged out
            # {'msg': {'name': 'Installer', 'authority': 0}, 'code': 47, 'eorr_msg': 'erro'}
            # check for authority key and value 0
            if "authority" in data["msg"]:
                if data["msg"]["authority"] == 0:
                    print("Logged out, logging in again...")
                    givenergy_ems_login()
                    return None

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

    givenergy_ems_login()

    while True:
        data = fetch_data()
        if data:
            send_to_emoncms(data)
        time.sleep(10)

if __name__ == "__main__":
    main()
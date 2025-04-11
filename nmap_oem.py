import subprocess
import re
import ipaddress
import json
import requests
from typing import Optional, List, Dict, Tuple

def get_local_ip() -> Optional[str]:
    try:
        output = subprocess.check_output("ip -4 addr show scope global | grep inet | awk '{print $2}' | cut -d'/' -f1 | head -n 1", shell=True)
        return output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_subnet_mask(ip: str) -> Optional[str]:
    try:
        output = subprocess.check_output(f"ip -4 addr show scope global | grep inet | grep '{ip}' | awk '{{print $2}}' | cut -d'/' -f2 | head -n 1", shell=True)
        cidr = output.decode().strip()
        return cidr_to_netmask(int(cidr))
    except subprocess.CalledProcessError:
        return None

def cidr_to_netmask(cidr: int) -> str:
    mask = ipaddress.IPv4Network(f"0.0.0.0/{cidr}").netmask
    return str(mask)

def get_network_range() -> Optional[str]:
    local_ip = get_local_ip()
    subnet_mask = get_subnet_mask(local_ip) if local_ip else None
    if local_ip and subnet_mask:
        network = ipaddress.IPv4Network(f"{local_ip}/{subnet_mask}", strict=False)
        return str(network)
    return None

def nmap(network_range: str) -> List[Dict[str, Optional[str]]]:
    command = f"nmap -sP {network_range}"
    result = subprocess.check_output(command, shell=True).decode()
    
    lines = result.split('\n')
    devices = []

    for line in lines:

        if 'Nmap scan report for' in line:
            # Filter out 'Nmap scan report for'
            line = line.strip()
            line = line.replace('Nmap scan report for ', '')

            # remove all non numeric and non . characters
            ip = re.sub(r'[^\d\.]', '', line)

            devices.append({'ip': ip})

    return devices

def get_mac_address(ip: str) -> Optional[str]:
    try:
        subprocess.check_output(f"ping -c 1 {ip}", shell=True)  # Update ARP cache
        output = subprocess.check_output(f"arp -n {ip}", shell=True).decode()
        mac_match = re.search(r'([a-fA-F0-9:]{17})', output)
        return mac_match.group(1) if mac_match else None
    except subprocess.CalledProcessError:
        return None

def get_manufacturer(mac: str) -> Optional[str]:

    # check if none
    if mac is None:
        return None
        
    oui = mac.replace(':', '')[:6]
    try:
        response = requests.get(f"https://api.macvendors.com/{oui}")
        return response.text if response.status_code == 200 else None
    except requests.RequestException:
        return None

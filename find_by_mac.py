import nmap_oem

mac = '98:d8:63:22:e6:3d'

network_range = nmap_oem.get_network_range()

ip = None

if network_range:
    print(f"Determined network range: {network_range}")
    devices = nmap_oem.nmap(network_range)
    for device in devices:
        mac_address = nmap_oem.get_mac_address(device['ip'])
        if mac_address == mac:
            print(f"Found {mac} at IP: {device['ip']}")
            ip = device['ip']
            break

print (ip)

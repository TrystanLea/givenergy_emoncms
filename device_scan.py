import nmap_oem

network_range = nmap_oem.get_network_range()

ip = None

if network_range:
    print(f"Determined network range: {network_range}")
    devices = nmap_oem.nmap(network_range)

    # Loop through devices
    for device in devices:
        # Get MAC address & Manufacturer
        mac_address = nmap_oem.get_mac_address(device['ip'])
        manufacturer = nmap_oem.get_manufacturer(mac_address)
        # Print ip, mac_address, and manufacturer
        print(f"IP: {device['ip']}, MAC: {mac_address}, Manufacturer: {manufacturer}")
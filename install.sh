#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

sudo apt-get update
sudo apt-get install -y nmap


# It's probably better to fix this by using python venv
if [ -e /usr/lib/python3.11/EXTERNALLY-MANAGED ]; then
    sudo rm -rf /usr/lib/python3.11/EXTERNALLY-MANAGED
    echo "Removed pip3 external management warning."
fi

# 1. Install dependencies
pip3 install givenergy-modbus

# 1. Create givenergy emoncms service
cat <<EOF > givenergy_emoncms.service
[Unit]
Description=givenergy_emoncms service
StartLimitIntervalSec=5

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/emoncms/modules/givenergy_emoncms/givenergy_run_simple_schedule.py
User=pi
Restart=always
RestartSec=30s

# View with: sudo journalctl -f -u givenergy_emoncms -o cat
SyslogIdentifier=givenergy_emoncms

[Install]
WantedBy=multi-user.target
EOF

service=givenergy_emoncms
# Remove old service if exists
if [ -f /lib/systemd/system/$service.service ]; then
    echo "- reinstalling $service.service"
    sudo systemctl stop $service.service
    sudo systemctl disable $service.service
    sudo rm /lib/systemd/system/$service.service
else
    echo "- installing $service.service"
fi

sudo mv $DIR/$service.service /lib/systemd/system

sudo systemctl enable $service.service
sudo systemctl restart $service.service

state=$(systemctl show $service | grep ActiveState)
echo "- Service $state"


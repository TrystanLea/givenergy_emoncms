# GivEnergy to Emoncms 

A simple script to read and post data from a givenergy inverter and battery to emoncms

## Install

1\. Install `givenergy-modbus` library:

    pip3 install givenergy-modbus

2\. Copy `example.config.ini` and rename to `config.ini`. Configure emoncms apikey and givenergy inverter ip address.

3\. Install background service script. Run `./install.sh`.
# GivEnergy to Emoncms 

**givenergy_run_read_only.py**<br>
A simple script to read and post data from a givenergy inverter and battery to emoncms.

**givenergy_run_simple_schedule.py**<br>
As above but also reads in a charge/discharge schedule compiled using the *agile_scheduler.py* script.

**agile_scheduler.py**<br>
A simple battery charge/discharge scheduling program based on Octopus Agile day ahead tariff forecast. 

**Redis required:**<br>
The schedule created by *agile_scheduler.py* is transfered to *givenergy_run_simple_schedule.py* via redis which is a dependency for these scripts.
*agile_scheduler.py* also accesses the battery state of charge via a redis key populated from *givenergy_run_simple_schedule.py*.
Redis dependencies are available on the standard OpenEnergyMonitor emonSD image.

## Install

1\. Install `givenergy-modbus` library:

    pip3 install givenergy-modbus

2\. Copy `example.config.ini` and rename to `config.ini`. Configure emoncms apikey and givenergy inverter ip address.

3\. Modify `install.sh` to run either `givenergy_run_read_only.py` or `givenergy_run_simple_schedule.py` as required.

4\. Install background service script. Run `./install.sh`.

## Install Agile scheduler

Run `agile_scheduler.py` from cron at midnight every night:

    crontab -e
    0 0 * * * python3 /opt/emoncms/modules/givenergy_emoncms/agile_scheduler.py

## Check logs 

`sudo systemctl status givenergy_emoncms.service` 

`journalctl -u givenergy_emoncms.service --since today`

`tail /var/log/emoncms/givenergy.log`



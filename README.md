## System Overview
* Raspberry Pi based access control system
* Supports keypad and RFID over Wiegand protocol
* Relay output and LCD display

### Getting the list of members and fobs
* `members.csv` is a list of active users
* This is populated by `pull_members.sh`
* This is a local file which can be referred to even when internet is out
* Run this every 5 minutes via cron

### Access script
`scripts/access.sh` gets the API keys from `config.sh` and then runs `access.py`
# D-chat
A (mostly) Decentralised chat app made with WebRTC Technologies such as aiortc in python.

Installation:
* install dependencies : `pip3 install asyncio aiortc aiohttp blessed`
* clone repo (or just `rtc.py`)

Usage:
* By default, the application will use `https://rtc.zyugyzarc.repl.co/` as a signaling server. this can be overriden with the `RTC_SERVER` environment variable.
* if you are the first person to join a group, run the file with the `--create` flag : `python3 rtc.py [Username] --create`
* to join a group that already exists, the create flag can be ommited : `python3 rtc.py [Username]`
* you can also use the `/invite` command to allow another user to join the group.
* you can leave using `/leave`

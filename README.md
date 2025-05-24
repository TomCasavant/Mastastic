# Mastastic

1. pip install -r requirements.txt
2. Plug in meshtastic device
3. Modify client.py w/ the meshtastic channel ID (at the top of client.py) you want to send messages through (Connnect to device via phone, check channel number)
4. `python client.py`
5. Send `!ping` to the channel to make sure it's working. You will get 'Pong!' as a response if it is.
6. Send `!login <instance>`, bot will send you OAuth URL, authenticate on your phone, send OAUth code in channel
7. Send `!post <text>` to send your first message

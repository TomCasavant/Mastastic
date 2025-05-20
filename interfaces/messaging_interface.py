"""
Interface wrappers to simplify sending large messages
"""

import meshtastic.serial_interface

class SerialMessagingInterface(meshtastic.serial_interface.SerialInterface):
    def __init__(self):
        super().__init__()

    def sendText(self, text, channelIndex=0):
        # TODO: Actually calculate how many bytes are in text (Emojis can be 4?)
        # TODO: Actually thinking about this now, we should modify __init__ to take a specific number of chars
        for i in range(0, len(text), 220):
            chunk = text[i:i + 220]
            super().sendText(chunk, channelIndex=channelIndex)
            print(f"[Mesh] Sent: {chunk}")


# TODO: Implement other interfaces, or can we simplify this process?

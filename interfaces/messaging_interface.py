"""
Interface wrappers to simplify sending large messages
"""

import meshtastic.serial_interface
from meshtastic.protobuf import mesh_pb2

DATA_PAYLOAD_LEN = mesh_pb2.Constants.DATA_PAYLOAD_LEN

class MessageSplitMixin:
    def __init__(self, max_bytes=DATA_PAYLOAD_LEN, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_bytes = max_bytes

    def sendText(self, text, channelIndex=0):
        # TODO: Actually calculate how many bytes are in text (Emojis can be 4?)
        for i in range(0, len(text), self.max_bytes):
            chunk = text[i:i + self.max_bytes]
            super().sendText(chunk, channelIndex=channelIndex)
            print(f"[Mesh] Sent: {chunk}")


class SerialMessagingInterface(MessageSplitMixin, meshtastic.serial_interface.SerialInterface):
    def __init__(self, max_bytes=DATA_PAYLOAD_LEN):
        super().__init__(max_bytes=max_bytes)


# TODO: Bluetooth interface,

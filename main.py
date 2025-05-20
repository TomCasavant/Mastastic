import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from mastodon import Mastodon, StreamListener
import threading
import time
from lxml.html import fromstring

command_registry = {}

def register(command_name, help_message='', example=''):
    def decorator(func):
        command_registry[command_name] = { 'function': func, 'help': help_message, example: example }
        return func
    return decorator

def onReceive(packet, interface):
    channel = packet['channel']
    if (channel != 2 and channel != "2"):
        print("Wrong channel")
    text = packet['decoded']['text']
    print(f"{packet['decoded']['text']}")
    interface.sendText(f"Received: {text}", channelIndex=2)
    mastodon = Mastodon(access_token='meshtastic_usercred.secret')
    mastodon.toot(text)

def onConnection(interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
    # defaults to broadcast, specify a destination ID if you wish
    print("Connected")
    interface.sendText("hello mesh", channelIndex=2)

class NotificationListener(StreamListener):
    def __init__(self, interface):
        self.interface = interface
    
    def on_notification(self, notification):
        print(f"[Mastodon] Notification: {notification.type} {notification} {notification.account}")
    
        text_notification = f"{notification.account.acct} {notification.type}d your status"
        if notification['type'] == 'mention':
            tree = fromstring(notification.status.content)
            text = tree.text_content()
            text_notification += f": {text}"
        try:
            self.interface.sendText(text_notification, channelIndex=2)
        except Exception as e:
            print(e)


@register('login', help='Authenticate with a Mastodon server. Required argument: mastodon instance', example='!login tomkahe.com')
def login(instance):
    print(f"Logging into {instance}...")
    # Logic for logging into a Mastodon server

        
'''Mastodon.create_app('meshtastic', api_base_url='https://tomkahe.com', to_file='meshtastic_clientcred.secret')'''

#mastodon = Mastodon(client_id = 'meshtastic_clientcred.secret',)
#print(mastodon.auth_request_url())

# open the URL in the browser and paste the code you get
#mastodon.log_in(
#    code=input("Enter the OAuth authorization code: "),
#    to_file="meshtastic_usercred.secret"
#)

def run_mastodon_stream(interface):
    mastodon = Mastodon(access_token='meshtastic_usercred.secret')
    listener = NotificationListener(interface)
    mastodon.stream_user(listener)

print("Subscribing")
pub.subscribe(onReceive, "meshtastic.receive.text")
pub.subscribe(onConnection, "meshtastic.connection.established")
print("creating interface")
interface = meshtastic.serial_interface.SerialInterface()

# Start Mastodon listener in a thread, pass the interface
mastodon_thread = threading.Thread(target=run_mastodon_stream, args=(interface,), daemon=True)
mastodon_thread.start()

print(interface.getLongName())
input("Press Enter to exit...\n")

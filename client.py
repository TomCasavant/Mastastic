import threading
import os

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from mastodon import Mastodon, StreamListener
from lxml.html import fromstring
from meshbot.command_registry import CommandRegistry
from interfaces.messaging_interface import SerialMessagingInterface

class MastodonClient:
    """Handles Mastodon API interactions."""
    def __init__(self):
        self.mastodon = None
        self.authenticate()

    def authenticate(self):
        try:
            if os.path.exists('meshtastic_usercred.secret'):
                self.mastodon = Mastodon(access_token='meshtastic_usercred.secret')
            elif os.path.exists('meshtastic_clientcred.secret'):
                self.mastodon = Mastodon(client_id='meshtastic_clientcred.secret')
            else:
                print("No credentials found.")
        except Exception as e:
            print(f"Error during authentication: {e}")

    def login(self, instance):
        try:
            # TODO: We shouldn't need to create the app every time we login?
            Mastodon.create_app('meshtastic', api_base_url=f'https://{instance}', to_file='meshtastic_clientcred.secret')
            self.mastodon = Mastodon(client_id='meshtastic_clientcred.secret')
            auth_url = self.mastodon.auth_request_url()
            print(f"Auth URL: {auth_url}")
            return auth_url
        except Exception as e:
            print(f"Error during login: {e}")

    def post_status(self, status):
        try:
            if self.mastodon:
                # TODO: Replace w/ the mastodon post method so we have finer control over visibility?
                self.mastodon.toot(status)
                print("Posted to Mastodon: ", status)
            else:
                print("Not logged in.")
        except Exception as e:
            print(f"Error posting status: {e}")

class NotificationListener(StreamListener):
    """Listen to Mastodon notifications."""
    def __init__(self, interface):
        self.interface = interface

    def clean_text(self, text):
        # Remove HTML tags and decode HTML entities
        tree = fromstring(text)
        text_content = tree.text_content()
        return text_content

    def build_notification(self, notification):
        text_notification = f"{notification.account.acct}"
        match notification.type:
            case 'mention':
                text = self.clean_text(notification.status.content)
                text_notification += f" mentioned you: {text}"
            case 'favourite':
                text_notification += " liked your status"
            case 'reblog':
                text_notification += " boosted your status"
            case 'follow':
                text_notification += " followed you"
            case 'status':
                text = self.clean_text(notification.status.content)
                text_notification += f" posted: {text}"
        return text_notification

    def on_notification(self, notification):
        print(f"[Mastodon] Notification: {notification.type} from {notification.account.acct}")
        text_notification = self.build_notification(notification)
        try:
            self.interface.sendText(text_notification, channelIndex=2)
        except Exception as e:
            print(f"Error sending notification to mesh: {e}")

class MeshtasticBot:
    def __init__(self):
        self.registry = CommandRegistry()
        self.mastodon_client = MastodonClient()
        self.awaiting_oauth = False
        self.setup_commands()
        self.interface = self.start_interface()
        self.run_mastodon_stream()

    def run_mastodon_stream(self):
        mastodon = self.mastodon_client.mastodon
        if mastodon:
            listener = NotificationListener(self.interface)
            try:
                threading.Thread(target=mastodon.stream_user, args=(listener,), daemon=True).start()
                print("Mastodon stream listener started in a separate thread.")
            except Exception as e:
                print(f"Error in Mastodon stream: {e}")

    def start_interface(self):
        try:
            interface = SerialMessagingInterface()
            pub.subscribe(self.on_receive, "meshtastic.receive.text")
            pub.subscribe(self.on_connection, "meshtastic.connection.established")
            return interface
        except Exception as e:
            print(f"Error starting interface: {e}")
            return None

    def on_receive(self, packet, interface):
        text = packet['decoded'].get('text', '')
        if self.awaiting_oauth:
            self.mastodon_client.mastodon.log_in(code=text, to_file='meshtastic_usercred.secret')
            self.awaiting_oauth = False
            self.interface.sendText("Login successful!", channelIndex=2)
            self.run_mastodon_stream()
            return
        elif text.startswith("!"):
            parts = text[1:].split(" ", 1)
            command_name = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            self.registry.execute(command_name, *args)

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        print("Connected to Meshtastic device")
        interface.sendText("Connected to Mesh!", channelIndex=2)

    def setup_commands(self):
    
        @self.registry.register('help', help_message='List available commands', example='!help')
        def help_command(*args):
            # If command provided show help for that command
            if args:
                command_name = args[0]
                command = self.registry.commands.get(command_name)
                if command:
                    help_text = f"Command: {command_name}\n"
                    help_text += f"Help: {command['help']}\n"
                    help_text += f"Example: {command['example']}"
                    self.interface.sendText(help_text, channelIndex=2)
                    return
                else:
                    self.interface.sendText(f"Command '{command_name}' not found.", channelIndex=2)
            command_list = "Available commands: " + ", ".join(self.registry.commands.keys())
            self.interface.sendText(command_list, channelIndex=2)

        @self.registry.register('post', help_message='Post to Mastodon', example='!post Hello World')
        def post_command(*args):
            message = ' '.join(args)
            self.mastodon_client.post_status(message)

        @self.registry.register('login', help_message='Login to a Mastodon instance', example='!login tomkahe.com')
        def login_command(*args):
            if len(args) != 1:
                self.interface.sendText("Usage: !login <instance>", channelIndex=2)
                return
            instance = args[0]
            auth_url = self.mastodon_client.login(instance)
            self.interface.sendText(f"{auth_url}", channelIndex=2)
            # Auth_URL might be too long for the mesh sometimes, not sure if there's any better way of handling that considering we only have 230 chars
            self.interface.sendText(f"Enter your OAuth code:", channelIndex=2)
            # TODO: Not sure if this is the best way to handle this? i.e. is there/should we wait for a response here instead of using a variable state?
            self.awaiting_oauth = True

        @self.registry.register('ping', example='!ping')
        def ping_command(*args):
            self.interface.sendText("pong", channelIndex=2)


if __name__ == "__main__":
    bot = MeshtasticBot()
    input("Press Enter to exit...")

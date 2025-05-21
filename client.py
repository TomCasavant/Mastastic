import threading
import os

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from mastodon import Mastodon, StreamListener
from lxml.html import fromstring
from meshbot.mesh_bot import MeshBot
from interfaces.messaging_interface import SerialMessagingInterface

MESHTASTIC_CHANNEL = 2  # TODO: Move to config file


class MastodonClient:
    """Handles Mastodon API interactions."""

    def __init__(self):
        self.mastodon = None
        self.authenticate()

    def authenticate(self):
        try:
            if os.path.exists("meshtastic_usercred.secret"):
                self.mastodon = Mastodon(access_token="meshtastic_usercred.secret")
            elif os.path.exists("meshtastic_clientcred.secret"):
                self.mastodon = Mastodon(client_id="meshtastic_clientcred.secret")
            else:
                print("No credentials found.")
        except Exception as e:
            print(f"Error during authentication: {e}")

    def login(self, instance):
        try:
            # TODO: We shouldn't need to create the app every time we login?
            Mastodon.create_app(
                "meshtastic",
                api_base_url=f"https://{instance}",
                to_file="meshtastic_clientcred.secret",
            )
            self.mastodon = Mastodon(client_id="meshtastic_clientcred.secret")
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

    def __init__(self, bot):
        self.bot = bot

    def clean_text(self, text):
        # Remove HTML tags and decode HTML entities
        tree = fromstring(text)
        text_content = tree.text_content()
        return text_content

    def build_notification(self, notification):
        text_notification = f"{notification.account.acct}"
        match notification.type:
            case "mention":
                text = self.clean_text(notification.status.content)
                text_notification += f" mentioned you: {text}"
            case "favourite":
                text_notification += " liked your status"
            case "reblog":
                text_notification += " boosted your status"
            case "follow":
                text_notification += " followed you"
            case "status":
                text = self.clean_text(notification.status.content)
                text_notification += f" posted: {text}"
        return text_notification

    def on_notification(self, notification):
        print(
            f"[Mastodon] Notification: {notification.type} from {notification.account.acct}"
        )
        text_notification = self.build_notification(notification)
        try:
            self.bot.send_text(text_notification, channelIndex=MESHTASTIC_CHANNEL)
        except Exception as e:
            print(f"Error sending notification to mesh: {e}")


class MastodonClientBot(MeshBot):
    def __init__(self, interface=None):
        self.mastodon_client = MastodonClient()
        super().__init__(interface=None, default_channel=MESHTASTIC_CHANNEL)
        self.run_mastodon_stream()

    def run_mastodon_stream(self):
        mastodon = self.mastodon_client.mastodon
        if mastodon:
            listener = NotificationListener(self)
            try:
                threading.Thread(
                    target=mastodon.stream_user, args=(listener,), daemon=True
                ).start()
                print("Mastodon stream listener started in a separate thread.")
            except Exception as e:
                print(f"Error in Mastodon stream: {e}")

    def handle_oauth_code(self, text):
        try:
            self.mastodon_client.mastodon.log_in(
                code=text, to_file="meshtastic_usercred.secret"
            )
            self.send_text("Login successful.", channelIndex=MESHTASTIC_CHANNEL)
            self.run_mastodon_stream()
        except Exception as e:
            self.send_text(f"OAuth failed: {e}", channelIndex=MESHTASTIC_CHANNEL)

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        print("Connected to Meshtastic device")
        self.send_text("Connected to Mesh!", channelIndex=MESHTASTIC_CHANNEL)

    def register_custom_commands(self):

        @self.registry.register(
            "post", help_message="Post to Mastodon", example="!post Hello World"
        )
        def post_command(*args):
            message = " ".join(args)
            self.mastodon_client.post_status(message)

        @self.registry.register(
            "login",
            help_message="Login to a Mastodon instance",
            example="!login tomkahe.com",
        )
        def login_command(*args):
            if len(args) != 1:
                self.interface.sendText(
                    "Usage: !login <instance>", channelIndex=MESHTASTIC_CHANNEL
                )
                return
            instance = args[0]
            auth_url = self.mastodon_client.login(instance)
            self.send_text(f"{auth_url}", channelIndex=MESHTASTIC_CHANNEL)
            # Auth_URL might be too long for the mesh sometimes, not sure if there's any better way of handling that considering we only have 230 chars
            self.send_text(f"Enter your OAuth code:", channelIndex=MESHTASTIC_CHANNEL)
            self.wait_for_next_message(self.handle_oauth_code)

        @self.registry.register("ping", example="!ping")
        def ping_command(*args):
            self.send_text("pong", channelIndex=MESHTASTIC_CHANNEL)


if __name__ == "__main__":
    bot = MastodonClientBot()
    input("Press Enter to exit...")

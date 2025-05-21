from meshbot.command_registry import CommandRegistry
from pubsub import pub
from interfaces.messaging_interface import SerialMessagingInterface


class MeshBot:
    def __init__(self, interface=None, default_channel=0):
        self.default_channel = default_channel
        # TODO: RIght now bots only reply on the default channel (unless overriden by child class), we should set this up to reply on the channel the command came in on
        self.registry = CommandRegistry()
        self.awaiting_callback = None
        # TODO: I setup interface this way so it's easy to test multiple bots but use the same radio. I have not tested this yet. Maybe we need some sort of botmanager class?
        self.interface = interface if interface else self.start_interface()
        self.setup_commands()

    def send_text(self, text, channelIndex=None):
        if self.interface:
            channelIndex = channelIndex or self.default_channel
            self.interface.sendText(text, channelIndex=channelIndex)

    def setup_commands(self):
        @self.registry.register(
            "help", help_message="List available commands", example="!help"
        )
        def help_command(*args):
            # If command provided show help for that command
            if args:
                command_name = args[0]
                command = self.registry.commands.get(command_name)
                if command:
                    help_text = f"Command: {command_name}\n"
                    help_text += f"Help: {command['help']}\n"
                    help_text += f"Example: {command['example']}"
                    self.send_text(help_text, channelIndex=self.default_channel)
                    return
                else:
                    self.send_text(
                        f"Command '{command_name}' not found.",
                        channelIndex=self.default_channel,
                    )
            command_list = "Available commands: " + ", ".join(
                self.registry.commands.keys()
            )
            self.send_text(command_list, channelIndex=self.default_channel)

        self.register_custom_commands()

    def start_interface(self):
        try:
            interface = (
                SerialMessagingInterface()
            )  # TODO: Allow bot to specify if we want SerialMessaging or BLE interface, although technically allowed now that we can pass in an interface in constructor
            pub.subscribe(self.on_receive, "meshtastic.receive.text")
            pub.subscribe(self.on_connection, "meshtastic.connection.established")
            # TODO: Look into other potential subscriptions a bot could utilize (i.e. sending a message when user information is retceived?)
            return interface
        except Exception as e:
            print(f"Error starting interface {e}")
            return None

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        print("Meshtastic connection established.")

    def on_receive(self, packet, interface):
        text = packet["decoded"].get("text", "")
        self.handle_message(text, packet)

    def handle_message(self, text, packet=None):
        if self.awaiting_callback:
            callback = self.awaiting_callback
            self.awaiting_callback = None
            callback(text)
        elif text.startswith("!"):
            parts = text[1:].split(" ", 1)
            command_name = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            self.registry.execute(command_name, *args)
            self.on_command_executed(text, packet)
        else:
            self.on_unhandled_message(text, packet)

        self.on_processed_message(text, packet)

    # Hooks for child classes
    def on_command_executed(self, text, packet):
        """When a message is received and a command is executed"""
        pass

    def on_unhandled_message(self, text, packet):
        """When a message is received but no command is executed"""
        pass

    def on_processed_message(self, text, packet):
        """When a message is received"""
        pass

    def register_custom_commands(self):
        """Override in child to add custom commands."""
        pass

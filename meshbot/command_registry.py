class CommandRegistry:
    """Registry for storing and executing commands."""

    def __init__(self):
        self.commands = {}

    def register(self, command_name, help_message="", example=""):
        def decorator(func):
            self.commands[command_name] = {
                "function": func,
                "help": help_message,
                "example": example,
            }
            return func

        return decorator

    def execute(self, command_name, *args):
        command = self.commands.get(command_name)
        if command:
            try:
                command["function"](*args)
            except Exception as e:
                print(f"Error executing '{command_name}': {e}")
        else:
            print(f"Command '{command_name}' not found.")

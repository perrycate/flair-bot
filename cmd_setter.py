
from discord.ext import commands
from datetime import datetime
from datetime import timedelta

PREFIX = _p = '!'
SUMMONING_KEY = '~'
SAVE_COMMAND = f'{_p}save '
RANDOM_COMMAND = f'{_p}random-add '
ADD_ALL_COMMAND = f'{_p}random-addall '
LIST_COMMAND = f'{_p}list'
DELETE_COMMAND = f'{_p}delete '
HELP_COMMAND = f'{_p}help'

# The maximum number of characters that a message can be before discord rejects
# the request.
#
# Most of the time we don't even check this, and just raise an exception (which
# is then ignored) if discord rejects the message for being too long. This is
# here for the special cases when we actually give a shit and want to make sure
# the message is actually sent.
MESSAGE_SIZE_LIMIT = 2000


class CommandSetter(commands.Cog):
    def __init__(self, user, storage, admin_channel):
        self._user = user
        self._db = storage
        self._admin_channel = admin_channel

    # TODO Now that I better understand discord.py, I desperately need to break these out into smaller commands.
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from ourself, otherwise we'll infinite loop.
        if message.author == self._user:
            return

        if message.content.startswith(SUMMONING_KEY):
            # Command is the first word, not including the summoning key
            command = message.content.split()[0][len(SUMMONING_KEY):].lower()
            content = self._db.get(command)
            if content != '':
                await message.channel.send(content)
            return

        # Admin-only commands below this point.
        if message.channel.name != self._admin_channel:
            return

        if message.content.startswith(DELETE_COMMAND):
            strs = message.content.split()
            if len(strs) != 2:
                await message.channel.send(f"Sorry, bud. I need the format '{DELETE_COMMAND} <command>'.")
                return
            command = strs[1].lower()
            self._db.delete(command)
            await message.channel.send(f"Got it! Will no longer respond to '{SUMMONING_KEY}{command}'.")
            print(f"{datetime.now()}: {message.author.name} deleted '{command}'")
            return

        if message.content.startswith(SAVE_COMMAND):
            strs = message.content.split(maxsplit=2)
            if len(strs) < 3:
                await message.channel.send(f"Sorry, I need the format '{SAVE_COMMAND} <keyword> <response content>'.")
                return

            # If something is a random command (has multiple responses), don't
            # automatically overwrite it.
            command = strs[1].lower()
            if self._db.count(command) > 1:
                await message.channel.send(
                    "Sorry, {0}{1} is already a command with multiple responses. "
                    "If you're sure you want to overwrite it, delete it first with {2} {1})".format(
                        SUMMONING_KEY, command, DELETE_COMMAND))
                return

            command = strs[1].lower()
            content = strs[2]
            self._db.delete(command)
            self._db.save(message.author.name, command, content)
            await message.channel.send(f"Got it! Will respond to '{SUMMONING_KEY}{command}' with '{content}'")
            print(
                f"{datetime.now()}: {message.author.name} set '{command}' to '{content}'")
            return

        if message.content.startswith(ADD_ALL_COMMAND):
            strs = message.content.split()
            if len(strs) < 3:
                await message.channel.send(f"Sorry, I need the format '{RANDOM_COMMAND} <keyword> <response> <response> <response>...'.")
                return
            command = strs[1].lower()
            content_words = strs[2:]
            for w in content_words:
                self._db.save(message.author.name, command, w)

            c = self._db.count(command)
            await message.channel.send(f"Got it! Will sometimes respond to '{SUMMONING_KEY}{command}' with one of those {len(content_words)} responses. ({c} total.)")
            print(
                f"{datetime.now()}: {message.author.name} added '{content_words}' to random command '{command}'")
            return

        if message.content.startswith(RANDOM_COMMAND):
            strs = message.content.split(maxsplit=2)
            if len(strs) < 3:
                await message.channel.send(f"Sorry, I need the format '{RANDOM_COMMAND} <keyword> <response content>'.")
                return
            command = strs[1].lower()
            content = strs[2]
            self._db.save(message.author.name, command, content)
            c = self._db.count(command)
            await message.channel.send(f"Got it! Will sometimes respond to '{SUMMONING_KEY}{command}' with '{content}'. (one of {c} possible responses).")
            print(
                f"{datetime.now()}: {message.author.name} added '{content}' to random command '{command}'")
            return

        if message.content.startswith(LIST_COMMAND):
            lines = []
            for command in self._db.list_commands():
                trigger, user, elapsed_seconds = command
                elapsed = timedelta(seconds=round(elapsed_seconds))

                lines.append(
                    f"**{SUMMONING_KEY}{trigger}**: last updated by {user} {elapsed.days} days and {elapsed.seconds//(60**2)} hours ago")

            # Discord limits the number of characters that can be in a message.
            # Split up if necessary.
            line_queue = []
            total_chars = 0
            for line in lines:
                length = len(line)

                # If this line would exceed the size limit, clear the queue
                # by sending all the previous unsent lines.
                if total_chars + length > MESSAGE_SIZE_LIMIT:
                    await message.channel.send('\n'.join(line_queue))
                    line_queue = []
                    total_chars = 0
                line_queue.append(line)
                total_chars += length+1  # +1 is for the \n
            await message.channel.send('\n'.join(line_queue))

        if message.content.startswith(HELP_COMMAND):
            await message.channel.send(
                f"""
Save a command: {SAVE_COMMAND} <keyword> <response content>
Save a random command: {RANDOM_COMMAND} <keyword> <response content> ({ADD_ALL_COMMAND} to add each word as a separate response)
Use a command: {SUMMONING_KEY}<keyword>
Delete a command: {DELETE_COMMAND} <keyword>
List all commands: {LIST_COMMAND}
Save a flair setting: {PREFIX}set-flair <message ID> <emoji> <@role>
""")

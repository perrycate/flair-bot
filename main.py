#!/usr/bin/env python3
import discord
import os
import sys
from datetime import datetime
from datetime import timedelta
from util import Storage

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'
ADMIN_CHANNEL_ENV_VAR = 'DISCORD_ADMIN_CHANNEL'

DEFAULT_DB_NAME = 'newton_storage.db'
DEFAULT_ADMIN_CHANNEL = 'newtons-study'

SUMMONING_KEY = '~'
SAVE_COMMAND = '!save '
RANDOM_COMMAND = '!random-add '
ADD_ALL_COMMAND = '!random-addall '
LIST_COMMAND = '!list'
DELETE_COMMAND = '!delete '
HELP_COMMAND = '!help'

# The maximum number of characters that a message can be before discord rejects
# the request.
#
# Most of the time we don't even check this, and just raise an exception (which
# is then ignored) if discord rejects the message for being too long. This is
# here for the special cases when we actually give a shit and want to make sure
# the message is actually sent.
MESSAGE_SIZE_LIMIT = 2000


class Bot(discord.Client):

    def __init__(self, storage, admin_channel_name):
        super().__init__()
        self._db = storage
        self._admin_channel = admin_channel_name

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message):
        # Ignore messages from ourself, otherwise we'll infinite loop.
        if message.author == self.user:
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
            strs = message.content.split()
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
            content = ' '.join(strs[2:])
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
            strs = message.content.split()
            if len(strs) < 3:
                await message.channel.send(f"Sorry, I need the format '{RANDOM_COMMAND} <keyword> <response content>'.")
                return
            command = strs[1].lower()
            content = ' '.join(strs[2:])
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
                    f"{SUMMONING_KEY}{trigger}: last updated by {user} {elapsed.days} days and {elapsed.seconds//(60**2)} hours ago")

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
""")


def _main():
    # Set admin channel, or notify what the default is.
    admin_channel = DEFAULT_ADMIN_CHANNEL
    if ADMIN_CHANNEL_ENV_VAR not in os.environ:
        print(
            f"Using the default admin channel ({admin_channel}). To change it, run again with the prefix '{ADMIN_CHANNEL_ENV_VAR}=<channel name>'")
    else:
        admin_channel = os.environ[ADMIN_CHANNEL_ENV_VAR]

    print(
        f"Admin channel is '{admin_channel}'. Will only accept !save and !delete commands if they appear there.")

    # Create bot instance.
    db = Storage(DEFAULT_DB_NAME)
    newton = Bot(db, admin_channel)

    # Check for auth token.
    if TOKEN_ENV_VAR not in os.environ:
        sys.exit("{0} not found in system environment. Try running again with the prefix '{0}=<insert discord bot token here>'".format(
            TOKEN_ENV_VAR))
    auth = os.environ[TOKEN_ENV_VAR]

    # Log in and begin reading and responding to messages.
    # Nothing else will run below this line.
    newton.run(auth)


if __name__ == '__main__':
    _main()

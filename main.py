#!/usr/bin/env python3
import discord
import os
import sys
from datetime import datetime

from util import Storage

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'
ADMIN_CHANNEL_ENV_VAR = 'DISCORD_ADMIN_CHANNEL'

DEFAULT_DB_NAME = 'newton_storage.db'
DEFAULT_ADMIN_CHANNEL = 'newtons-study'

SUMMONING_KEY = '~'
SAVE_COMMAND = '!save'
RANDOM_COMMAND = '!random'
DELETE_COMMAND = '!delete'
HELP_COMMAND = '!help'


class Bot(discord.Client):

    def __init__(self, storage, admin_channel_name):
        super().__init__()
        self._db = storage
        self._admin_channel = admin_channel_name

    async def on_ready(self):
        print("Logged in as {}".format(self.user))

    async def on_message(self, message):
        # Ignore messages from ourself, otherwise we'll infinite loop.
        if message.author == self.user:
            return

        if message.content.startswith(SUMMONING_KEY):
            # Command is the first word, not including the summoning key
            command = message.content.split(
                ' ')[0][len(SUMMONING_KEY):].lower()
            content = self._db.get(command)
            if content != '':
                await message.channel.send(content)
            return

        # Admin-only commands below this point.
        if message.channel.name != self._admin_channel:
            return

        if message.content.startswith(DELETE_COMMAND):
            strs = message.content.split(' ')
            if len(strs) != 2:
                await message.channel.send("Sorry, bud. I need the format '{} <command>'.".format(DELETE_COMMAND))
                return
            command = strs[1].lower()
            self._db.delete(command)
            await message.channel.send("Got it! Will no longer respond to '{}{}'.".format(SUMMONING_KEY, command))
            print("{}: {} deleted '{}'".format(
                datetime.now(), message.author.name, command))
            return

        if message.content.startswith(SAVE_COMMAND):
            strs = message.content.split(' ')
            if len(strs) < 3:
                await message.channel.send("Sorry, I need the format '{} <keyword> <response content>'.".format(SAVE_COMMAND))
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
            await message.channel.send("Got it! Will respond to '{}{}' with '{}'".format(SUMMONING_KEY, command, content))
            print("{}: {} set '{}' to '{}'".format(
                datetime.now(), message.author.name, command, content))
            return

        if message.content.startswith(RANDOM_COMMAND):
            strs = message.content.split(' ')
            if len(strs) < 3:
                await message.channel.send("Sorry, I need the format '{} <keyword> <response content>'.".format(RANDOM_COMMAND))
                return
            command = strs[1].lower()
            content = ' '.join(strs[2:])
            self._db.save(message.author.name, command, content)
            c = self._db.count(command)
            await message.channel.send("Got it! Will sometimes respond to '{}{}' with '{}'. (one of {} possible responses).".format(SUMMONING_KEY, command, content, c))
            print("{}: {} added '{}' to random command '{}'".format(
                datetime.now(), message.author.name, content, command))
            return

        if message.content.startswith(HELP_COMMAND):
            await message.channel.send(
                """
Save a command: {} <keyword> <response content>
Use a command: {}<keyword>
Delete a command: {} <keyword>
""".format(SAVE_COMMAND, SUMMONING_KEY, DELETE_COMMAND))


def _main():
    # Set admin channel, or notify what the default is.
    admin_channel = DEFAULT_ADMIN_CHANNEL
    if ADMIN_CHANNEL_ENV_VAR not in os.environ:
        print("Using the default admin channel ({}). To change it, run again with the prefix '{}=<channel name>'".format(
            admin_channel, ADMIN_CHANNEL_ENV_VAR))
    else:
        admin_channel = os.environ[ADMIN_CHANNEL_ENV_VAR]

    print("Admin channel is '{}'. Will only accept !save and !delete commands if they appear there.".format(admin_channel))

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

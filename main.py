#!/usr/bin/env python3
import os
import sys

from discord.ext import commands

from storage import CmdStore, FlairStore
import flairs
import cmd_setter

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'
ADMIN_CHANNEL_ENV_VAR = 'DISCORD_ADMIN_CHANNEL'
LOG_CHANNEL_ENV_VAR = 'DISCORD_LOG_CHANNEL'

# Keeping the DBs separate makes it less likely that a bug causes me to nuke both tables.
COMMAND_DB_NAME = 'newton_storage.db'
FLAIR_DB_NAME = 'newton_storage_flairs.db'

# The channel where admin commands (!save, !delete, etc) can be run.
DEFAULT_ADMIN_CHANNEL = 'newtons-study'
# The channel where newton will log any actions taken as the result of reactions.
# (Role add, role delete. etc.)
DEFAULT_LOG_CHANNEL = 'newtons-reactions-log'


class Bot(commands.Bot):
    def __init__(self, cmd_store, flair_store, admin_channel_name, log_channel_name):
        super().__init__(command_prefix=cmd_setter.PREFIX)
        # TODO because the bot isn't connected yet, self.user is still none. Fix.
        self.add_cog(cmd_setter.CommandSetter(
            self.user, cmd_store, admin_channel_name))
        self.add_cog(flairs.Flairs(flair_store, self,
                                   admin_channel_name, log_channel_name))

    async def on_ready(self):
        print(f"Logged in as {self.user}")


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

    log_channel = DEFAULT_LOG_CHANNEL
    if LOG_CHANNEL_ENV_VAR not in os.environ:
        print(
            f"Using the default log channel ({log_channel}). To change it, run again with the prefix '{LOG_CHANNEL_ENV_VAR}=<channel name>'")
    else:
        log_channel = os.environ[LOG_CHANNEL_ENV_VAR]

    # Create bot instance.
    cmd_db = CmdStore(COMMAND_DB_NAME)
    flair_db = FlairStore(FLAIR_DB_NAME)
    newton = Bot(cmd_db, flair_db, admin_channel, log_channel)

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

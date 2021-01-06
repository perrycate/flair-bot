#!/usr/bin/env python3
import discord
import os
import sys

from discord.ext import commands

from datetime import datetime
from datetime import timedelta
from storage import CmdStore, FlairStore

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'
ADMIN_CHANNEL_ENV_VAR = 'DISCORD_ADMIN_CHANNEL'

COMMAND_DB_NAME = 'newton_storage.db'
# Keeping the DBs separate makes it less likely that a bug causes me to nuke both tables.
FLAIR_DB_NAME = 'newton_storage_flairs.db'
DEFAULT_ADMIN_CHANNEL = 'newtons-study'

COMMAND_PREFIX = _p = '!'
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
""")


class Flairs(commands.Cog):

    def __init__(self, flair_store, bot):
        self._db = flair_store
        self._bot = bot

    @commands.command(name="debug-flair")
    async def debug_flair(self, ctx, reaction):
        print()
        print(reaction)
        print(type(reaction))
        print(self._emoji_id_from_str(reaction))

    @commands.command(name="debug-message")
    async def debug_message(self, ctx, message_id):
        print()
        print(message_id)
        print(type(message_id))
        g = ctx.guild
        print(g)
        m = await ctx.fetch_message(message_id)
        print(m)

    @commands.command(name="set-flair")
    async def set_flair(self, ctx, message_id, reaction):
        channel = ctx.message.channel

        # TODO Make sure the message actually exists
        # It's not documented, but ctx.fetch_message only fetches a message
        # from the channel this message originated from.
        # I am yet to find a way to retrieve a message without knowing the
        # channel it originated from, soo... We could just try every channel,
        # but f*ck that.

        # Try to verify that the provided emoji is valid.
        # We can't prove that it isn't valid, but we can log a warning if we can't
        # prove that it is.
        reaction_id = self._emoji_id_from_str(reaction)
        confirmed_custom_emoji = False
        try:
            # If the emoji was a built-in emoji, it's ID will not be convertable to an int.
            confirmed_custom_emoji = (
                ctx.bot.get_emoji(int(reaction_id)) is not None)
        except Exception as e:
            print(
                f"Failed to verify an emoji (ID {reaction_id}). This is probably fine: {e}")
            pass
        if not confirmed_custom_emoji:
            await channel.send(
                f"Heads up: The given emoji '{reaction}' isn't registering as a custom emoji. "
                "That's fine if it's a built-in emoji, otherwise something went wrong.")

        # Extract the mentioned role's ID
        if len(ctx.message.role_mentions) != 1:
            await channel.send("Sorry, I need exactly one role @mentioned.")
            return
        role = ctx.message.role_mentions[0]

        # Now that we've verified as much as we can, save it into our database.
        self._db.save(ctx.message.author.name,
                      message_id, reaction_id, role.id)
        await channel.send(f"Got it! Will add the '{role.name}' role to anyone that reacts {reaction} to message {message_id}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        reaction_id = self._get_emoji_id(payload.emoji)
        role_ids = self._db.get(payload.message_id, reaction_id)
        for rID in role_ids:
            guild = self._bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rID))
            await payload.member.add_roles(role, reason=f"Reacted with {payload.emoji} to message {payload.message_id}.")
            print(f"Added {role} to {payload.member}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        reaction_id = self._get_emoji_id(payload.emoji)
        role_ids = self._db.get(payload.message_id, reaction_id)
        for rID in role_ids:
            guild = self._bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rID))
            user = await guild.fetch_member(int(payload.user_id))
            await user.remove_roles(role, reason=f"Reacted with {payload.emoji} to message {payload.message_id}.")
            print(f"Removed {role} from {user}")

    def _get_emoji_id(self, emoji: discord.PartialEmoji) -> str:
        """
        Returns a useable string ID for the given emoji object.

        This is necessary because discord emojis have different semantics if
        they are a built-in emoji vs a custom one. Custom ones have an ID, but
        the name can be easily changed and is thus unreliable. Standard emojis
        have a name that is stable (in theory), but their ID is None.

        To discord's credit, I haven't looked up if this is a discord issue, or
        a bug in discord.py.
        """
        if emoji.id is None:
            return emoji.name
        return emoji.id

    def _emoji_id_from_str(self, emoji: str) -> str:
        """
        Returns the useable string ID for an emoji in string form. 

        Discord represents emojis completely differently in string format if
        they are a custom emoji vs a standard unicode emoji. Standard emojis
        are just raw unicode. Custom emojis seem to be of the following format:
        <:name:id> (or <a:name:id> if they're animated).

        This function should return a useable ID for the given string that
        matches whatever _get_emoji_id() would return for the object equivalent.
        Note that because standard emojis are raw unicode, we don't have a
        means (that I know of) of discerning between a standard emoji and a
        regular string, so if whotever we get doesn't match the custom format,
        we return the whole thing and hope for the best.
        """
        # Try treating the string as the custom emoji format.
        split_emoji = emoji.strip('>').split(':')
        if len(split_emoji) == 3:
            # String seems to match the custom emoji format. Return what we hope is
            # the ID.
            return split_emoji[2]

        # Whatever we were passed doesn't seem to be in the custom emoji
        # format. Just return the whole thing.
        return emoji


class Bot(commands.Bot):
    def __init__(self, cmd_store, flair_store, admin_channel_name):
        super().__init__(command_prefix=COMMAND_PREFIX)
        self.add_cog(CommandSetter(self.user, cmd_store, admin_channel_name))
        self.add_cog(Flairs(flair_store, self))

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

    # Create bot instance.
    cmd_db = CmdStore(COMMAND_DB_NAME)
    flair_db = FlairStore(FLAIR_DB_NAME)
    newton = Bot(cmd_db, flair_db, admin_channel)

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

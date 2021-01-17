
import discord

from discord.ext import commands
from datetime import datetime


class Flairs(commands.Cog):

    def __init__(self, flair_store, bot, admin_channel, log_channel):
        self._db = flair_store
        self._bot = bot
        self._log_channel_name = log_channel
        self._admin_channel_name = admin_channel
        self._log_channels_by_guild_id = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Register our log channels.
        # We can't do this in __init__ because we may not be logged in then.
        for g in self._bot.guilds:
            log_channel = None
            for c in g.channels:
                if c.name == self._log_channel_name:
                    log_channel = c
            if log_channel is None:
                print(
                    f"No channel with name {self._log_channel_name} in guild {g.name}. "
                    "Flairs added or removed there will only be logged to stdout.")
                continue
            self._log_channels_by_guild_id[g.id] = log_channel

    # Ignore any commands that aren't from the admin channel.
    # Does not apply to listeners.
    def bot_check(self, ctx):
        return ctx.message.channel.name == self._admin_channel_name

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
        await self._log(ctx.guild.id,
                        f"{datetime.now()}: {ctx.message.author.name} set the '{role.name}' role to anyone that reacts {reaction}' to message '{message_id}'")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        reaction_id = self._get_emoji_id(payload.emoji)
        role_ids = self._db.get(payload.message_id, reaction_id)
        for rID in role_ids:
            guild = self._bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rID))
            await payload.member.add_roles(role, reason=f"Reacted with {payload.emoji} to message {payload.message_id}.")
            await self._log(payload.guild_id, f"Added {role} to {payload.member}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        reaction_id = self._get_emoji_id(payload.emoji)
        role_ids = self._db.get(payload.message_id, reaction_id)
        for rID in role_ids:
            guild = self._bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rID))
            user = await guild.fetch_member(int(payload.user_id))
            await user.remove_roles(role, reason=f"Reacted with {payload.emoji} to message {payload.message_id}.")
            await self._log(payload.guild_id, f"Removed {role} from {user}")

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

    async def _log(self, guild_id, message):
        print(message)
        if guild_id not in self._log_channels_by_guild_id:
            return
        c = self._log_channels_by_guild_id[guild_id]
        await c.send(message)

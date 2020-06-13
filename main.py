#!/usr/bin/env python3
import discord
import os
import sys 

from util import Storage

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'
ADMIN_CHANNEL_ENV_VAR = 'DISCORD_ADMIN_CHANNEL'

SUMMONING_KEY = '~'
SAVE_COMMAND = '!save'
DELETE_COMMAND = '!delete'
HELP_COMMAND = '!help'

discord = discord.Client()
db = Storage()

# The channel to listen for save and delete commands for.
admin_channel = 'newtons-study'

@discord.event
async def on_ready():
    print("Logged in as {0.user}".format(discord))

@discord.event
async def on_message(message):
    # Ignore messages from self, otherwise we'll infinite loop.
    if message.author == discord.user:
        return

    if message.content.startswith(SUMMONING_KEY):
        # Command is the first word, not including the summoning key
        command = message.content.split(' ')[0][len(SUMMONING_KEY):].lower()
        content = db.get(command)
        if content != '':
            await message.channel.send(content)
        return

    # Admin-only commands below this point.
    if message.channel.name != admin_channel:
        return

    if message.content.startswith(DELETE_COMMAND):
        strs = message.content.split(' ')
        if len(strs) != 2:
            await message.channel.send("Sorry, bud. I need the format '{} <command>'.".format(DELETE_COMMAND))
            return
        command = strs[1].lower()
        db.delete(command)
        await message.channel.send("Got it! Will no longer respond to '{}{}'.".format(SUMMONING_KEY, command))
        return

    if message.content.startswith(SAVE_COMMAND):
        strs = message.content.split(' ')
        if len(strs) < 3:
            await message.channel.send("Sorry, bud. I need the format '{} <keyword> <response content>'.".format(SAVE_COMMAND))
            return
        command = strs[1].lower()
        content = ' '.join(strs[2:])
        db.save(message.author.name, command, content)
        await message.channel.send("Got it! Will respond to '{}{}' with '{}'".format(SUMMONING_KEY, command, content))
        return
   
    if message.content.startswith(HELP_COMMAND):
        await message.channel.send(
"""
Save a command: {} <keyword> <response content>
Use a command: {}<keyword>
Delete a command: {} <keyword>
""".format(SAVE_COMMAND, SUMMONING_KEY, DELETE_COMMAND))

   
def _main():
    global admin_channel

    # Set admin channel, or notify what the default is.
    if ADMIN_CHANNEL_ENV_VAR not in os.environ:
        print("Using the default admin channel. To change it, run again with the prefix '{}=<channel name>'".format(admin_channel, ADMIN_CHANNEL_ENV_VAR))
    else:
        admin_channel = os.environ[ADMIN_CHANNEL_ENV_VAR]

    print("Admin channel is '{}'. Will only accept !save and !delete commands if they appear there.".format(admin_channel))

    # Log in to Discord.
    if TOKEN_ENV_VAR not in os.environ:
        sys.exit("{0} not found in system environment. Try running again with the prefix '{0}=<insert discord bot token here>'".format(TOKEN_ENV_VAR))
    auth = os.environ[TOKEN_ENV_VAR]
    # This call blocks indefinitely. Nothing will run below this line.
    discord.run(auth)

_main()

#!/usr/bin/env python3
import discord
import os
import sys 

from util import Storage

TOKEN_ENV_VAR_NAME = 'NEWTON_BOT_TOKEN'

discord = discord.Client()
db = Storage()

@discord.event
async def on_ready():
    print("Logged in as {0.user}".format(discord))

@discord.event
async def on_message(message):
    # Ignore messages from self, otherwise we'll infinite loop.
    if message.author == discord.user:
        return

    if message.content.startswith('!record'):
        pass
    
    if message.content.startswith('?'):
        pass
   
def _err(str):
    sys.exit(str)
            
def _main():
    # Log in to Discord.
    if TOKEN_ENV_VAR_NAME not in os.environ:
        _err("{0} not found in system environment. Try running again, prefixing '{0}=<insert discord bot token here>'".format(TOKEN_ENV_VAR_NAME))
    auth = os.environ[TOKEN_ENV_VAR_NAME]
    discord.run(auth)


_main()

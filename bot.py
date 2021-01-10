import os
import sys, traceback
import logging
from dotenv import load_dotenv
load_dotenv() #Load .env file, contains bot secret

import discord
from discord.ext import commands

client = commands.Bot(command_prefix=commands.when_mentioned_or(".m "), help_command=None)

initial_extensions = [
                        'cogs.basic',
                        'cogs.request',
                        'cogs.reaction',
                        'cogs.dev'
                        #Add cog filenames here
                    ] 

@client.event
async def on_ready():
    
    print("Logged in")

    if __name__ == '__main__':
        for extension in initial_extensions:
            client.load_extension(extension)
    
    presence = discord.Activity(type=discord.ActivityType.watching, name="XANILLA ❤️😍")
    await client.change_presence(activity=presence)
    
    if ("restart" in sys.argv):
        respChanel = client.get_channel(int(sys.argv[2]))
        await respChanel.send("Restarted :white_check_mark:")

logging.basicConfig(level=logging.INFO)
client.run(os.getenv("BOT_TOKEN"), reconnect=True)

# Invite: 
# https://discord.com/oauth2/authorize?client_id=797227268228644874&scope=bot&permissions=1342565456
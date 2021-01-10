import discord
from discord.ext import commands

import os
import sys

class DevCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.message.delete()
        python = sys.executable
        args = [
            'bot.py',
            'restart',
            str(ctx.channel.id)
        ]
        os.execl(python, python, *args)

def setup(client):
    client.add_cog(DevCog(client))
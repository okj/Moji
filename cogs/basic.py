import discord
from discord.ext import tasks, commands
from tinydb import TinyDB, where
from tinydb.operations import set,delete

class BasicCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.guildsettings = TinyDB('database/guildsettings.json')
    
    @commands.check
    async def globally_block_dms(ctx):
        return ctx.guild is not None
    
    async def is_emoji_manager(ctx):
        return ctx.author.guild_permissions.manage_emojis
    
    @commands.command()
    @commands.check(is_emoji_manager)
    async def quickstart(self, ctx):
        # TODO: prevent duplication, do error handling etc.

        # Create Moji category channel
        new_category = await ctx.guild.create_category("moji")
        await new_category.set_permissions(self.client.user, read_messages=True)
        await new_category.set_permissions(ctx.guild.default_role, read_messages=False)
        await new_category.edit(position=0)

        for role in ctx.guild.roles:
            if (role.permissions.manage_emojis):
                await new_category.set_permissions(role, read_messages=True)
        
        # Create channels
        requestQueue = await new_category.create_text_channel("request-queue",permissions_synced=True)

        self.guildsettings.upsert({
            'guild': ctx.guild.id,
            'category': new_category.id,
            'request_queue': requestQueue.id
        }, where('guild') == ctx.guild.id)

    @commands.command()
    async def invite(self, ctx):
        await ctx.channel.send("https://discord.com/oauth2/authorize?client_id=797227268228644874&scope=bot&permissions=1342565456", delete_after=15.0)
        await ctx.message.delete(delay=15.0)

    @commands.command(aliases=['discord'])
    async def support(self, ctx):
        await ctx.channel.send("https://discord.com/invite/VeDjBR4", delete_after=15.0)
        await ctx.message.delete(delay=15.0)
    
    @commands.command(aliases=['code'])
    async def repo(self, ctx):
        await ctx.channel.send("", delete_after=15.0)
        await ctx.message.delete(delay=15.0)

def setup(client):
    client.add_cog(BasicCog(client))
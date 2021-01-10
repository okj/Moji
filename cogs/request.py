import discord
from discord.ext import tasks, commands
import time
from urllib.parse import urlparse
import re
import requests

from tinydb import TinyDB, where

class RequestCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.SIZE_LIMIT_KB = 256

        # Reaction Emojis
        self.approve_emoji = self.client.get_emoji(797574635239637032)
        self.edit_emoji = self.client.get_emoji(797574634722951200)
        self.deny_emoji = self.client.get_emoji(797574634970284082)

        # Database
        self.guildsettings = TinyDB('database/guildsettings.json')
        self.pendingemojis = TinyDB('database/pendingemojis.json')

    # Get emoji from message string
    def get_emoji(self, message):
        if (message.startswith('<a')):
            emoji = re.findall('<a:.+?:\d+>', message)
        else: emoji = re.findall('<:.+?:\d+>', message)

        if (len(emoji) >= 1):
            return emoji[0]
        return None
    
    # Determines if message is an emoji
    def is_emoji(self, message):
        if (self.get_emoji(message) != None):
            return True
        return False
    
    # Gets emoji name and url from string containing emoji
    def string_to_emoji_data(self, emoji_string):
        string_split = emoji_string.split(":")

        # Construct url
        emoji_url = "https://cdn.discordapp.com/emojis/" + string_split[2].replace(">","")
        if (string_split[0] == '<a'):
            emoji_url += '.gif'
        else: emoji_url += '.png'

        emoji_name = string_split[1]
        return emoji_url, emoji_name
    
    # Creates a request embed
    def get_request_embed(self, author, data, name):
        
        request_embed = discord.Embed(colour=15844367)
        request_embed.add_field(name="Requested by",value=author.mention,inline=False)

        if (name is None): name == ""
        request_embed.add_field(name="Emoji Name",value=name,inline=True)

        if (data.endswith(".gif")): 
            request_embed.add_field(name="Animated",value="True",inline=True)
        else: request_embed.add_field(name="Animated",value="False",inline=True)

        request_embed.set_image(url=data)

        return request_embed
    
    # Determines if supported url
    def valid_url(self, url):
        supported = [
            'cdn.discordapp.com',
            'media.discordapp.net'
        ]

        for link in supported:
            if (urlparse(url).netloc == link):
                return True
        return False
    
    # Submit requested emoji to queue
    async def request_submit(self, ctx, url, name):
        # TODO: Currently user *must* use basic.quickstart first
        request_queue_id = self.guildsettings.get(where('guild') == ctx.guild.id)['request_queue']

        request_queue = ctx.guild.get_channel(request_queue_id)
        request_embed = self.get_request_embed(ctx.author,url,name)
        
        emoji_entry = self.pendingemojis.insert({
            'guild': ctx.guild.id,
            'channel_requested': ctx.channel.id,
            'requested_by': ctx.author.id,
            'data': url,
            'name': name,
            'submitted_epoch': int(time.time())
        })
        request_embed.set_footer(text="ID: " + str(emoji_entry))
        request_msg = await request_queue.send(embed=request_embed)
        
        await request_msg.add_reaction(self.approve_emoji)
        await request_msg.add_reaction(self.edit_emoji)
        await request_msg.add_reaction(self.deny_emoji)

    # Request an emote for the server, pass it on for verification
    # Takes an optional suggested name and . . . . . . 
    @commands.command(aliases=["r", "req"])
    async def request(self, ctx, *data):

        name = None
        attachments = ctx.message.attachments
        
        # If true; will eventually check for requirements such as size and file type
        sanitize = True

        await ctx.message.delete()

        # If contains a suggested name and a link
        if (len(data) >= 2):
            name = data[0]
            data = data[1]
        # Only contains a suggested name or a link
        elif(len(data) == 1):
            data = data[0]
        # No data no attachment, just chuck this out the user is being silly
        elif (len(attachments) != 1):
            await ctx.channel.send(f"{ctx.author.mention} you gave me literally nothing.. not sure what you expected..", delete_after=15.0)
            return
        
        # If there is an attachment
        if (len(attachments) == 1):
            # If there isn't something in data, keep name = None
            if (name is None and len(data) >= 1): name = data
            data = attachments[0].proxy_url
        
        # Check if data is an emoji
        elif (self.is_emoji(data)):

            # Get emoji data
            emoji_data = self.string_to_emoji_data(data)
            data = emoji_data[0]
            if (name is None): name = emoji_data[1]
            sanitize = False # No need to sanitize if already a Discord emoji
        
        #print(f'\nData: {data}\nName: {name}')

        # Data is not an emoji we need to check some stuff
        if (sanitize):
            if (self.valid_url(data)):
                if (name is None): 
                    name = data.split(".")[-2].split("/")[-1]

                # check type
                if (data.endswith(".gif") or data.endswith(".png") or data.endswith(".jpg")):
                    # check size (resize)
                    try:
                        sizeKB = int(requests.head(data).headers['Content-Length'])/1024
                    except:
                        print("proxy url failed, attempting main url")
                        data = ctx.message.attachments[0].url
                        sizeKB = int(requests.head(data).headers['Content-Length'])/1024

                    if (sizeKB > self.SIZE_LIMIT_KB):
                        await ctx.channel.send(f"{ctx.author.mention} Your requested emote is too big! (Must be less than `{str(self.SIZE_LIMIT_KB)}kb`, currently `{str(sizeKB)}kb`)", delete_after=20.0)
                        return
                else:
                    await ctx.channel.send(f"{ctx.author.mention} invalid file type", delete_after=20.0)
                    return
            else:
                is_link = re.findall(r'(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', data)
                if (is_link):
                    await ctx.channel.send(f"{ctx.author.mention} that URL is not supported right now. If you believe this is a mistake, message rob <:seal:693625692277178479>", delete_after=20.0)
                else:
                    await ctx.channel.send(f"{ctx.author.mention} please provide an emoji, attachment, or valid URL", delete_after=20.0)
                return

        await self.request_submit(ctx,data,name)
        await ctx.channel.send(f"{ctx.author.mention} your emoji has been submitted for approval!", delete_after=20.0)

def setup(client):
    client.add_cog(RequestCog(client))
import discord
from discord.ext import commands
import requests
import aiohttp
import asyncio

from tinydb import TinyDB, where

class ReactionCog(commands.Cog):
    def __init__(self, client):
        self.client = client

        # Reaction Emojis
        self.approve_emoji = self.client.get_emoji(797574635239637032)
        self.edit_emoji = self.client.get_emoji(797574634722951200)
        self.denied_emoji = self.client.get_emoji(797574634970284082)

        # Database
        self.pendingemojis = TinyDB('database/pendingemojis.json')

    # Gets ID from a Moji embed
    async def embed_to_id(self, message):
        if (message.author.id != self.client.user.id):
            print(f'Attempting to get data from message sent by {message.author.id}')
            return None

        embed = message.embeds[0]
        return int(embed.footer.text.replace("ID: ",""))
    
    # Return Guild, and Message from payload
    async def payload_to_discord(self, payload):
        guild = self.client.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        return guild,message

    # Delete entry from pending emojis using document id
    def delete_entry(self, eid):
        self.pendingemojis.remove(doc_ids=[eid])

    # Update embed to denied and delete entry
    async def deny_emoji(self, payload):
        # Get Discord classes from payload
        payload_data = await self.payload_to_discord(payload)
        message = payload_data[1]

        # Get embed message data
        emoji_entry_id = await self.embed_to_id(message)
        self.delete_entry(emoji_entry_id)
        
        # Update embed
        new_embed = message.embeds[0]
        new_embed.colour = 12597547
        new_embed.add_field(name="Denied by",value=payload.member.mention,inline=False)
        new_embed.set_image(url=discord.Embed.Empty)

        await message.edit(embed=new_embed)
        await message.clear_reactions()

    # Update embed to approved, upload emoji, delete entry
    async def new_emoji(self, payload):
        # Get Discord classes from payload
        payload_data = await self.payload_to_discord(payload)
        guild = payload_data[0]
        message = payload_data[1]

        # Get embed message data
        emoji_entry_id = await self.embed_to_id(message)
        
        emoji = self.pendingemojis.get(doc_id=emoji_entry_id)

        # Download file to bytes
        headers= {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0'
        }

        # Alternatively use Discord.Asset -> https://discordpy.readthedocs.io/en/latest/api.html#discord.Asset
        # However, this current method allows for non-discord cdn links
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=emoji['data']) as response:
                raw_bytes = await response.read()

        # Upload emoji
        try:
            created_emoji = await guild.create_custom_emoji(name=emoji['name'],image=raw_bytes)
        except:
            await message.channel.send(f'Error uploading pending emoji with ID `{emoji_entry_id}`, edit the name and try again.', delete_after=30.0)
            return

        # Let the user know they were approved
        channel = guild.get_channel(emoji['channel_requested'])
        try:
            await channel.send(f'{self.approve_emoji} {message.embeds[0].fields[0].value} your emote {created_emoji} was approved!')
        except:
            print(f'No access to channel_requested in guild {guild.id}')
        
        # Update embed
        new_embed = message.embeds[0]
        new_embed.colour = 3066993
        new_embed.set_field_at(1,name="Emoji Name", value=created_emoji.name)
        new_embed.add_field(name="Approved by",value=payload.member.mention,inline=False)

        await message.edit(embed=new_embed)
        await message.clear_reactions()
        self.delete_entry(emoji_entry_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):

        if (payload.member.guild_permissions.manage_emojis and not payload.member.bot): # For some reason couldn't do this in a commands.check function
            
            if (payload.emoji == self.approve_emoji):
                await self.new_emoji(payload)

            elif (payload.emoji == self.denied_emoji):
                await self.deny_emoji(payload)

            elif (payload.emoji == self.edit_emoji):
                # Get request-queue message reacted to
                payload_data = await self.payload_to_discord(payload)
                message = payload_data[1]

                await message.remove_reaction(self.edit_emoji, payload.member)

                # Get emoji
                emoji_entry_id = await self.embed_to_id(message)
                emoji = self.pendingemojis.get(doc_id=emoji_entry_id)
                name = emoji['name']

                timeout = 60.0

                edit_msg = await message.channel.send(f'**Editing name for pending emoji** `{name}` ({emoji_entry_id})\nGive me a new name :pray:', delete_after=timeout)
                
                # Make sure response is from user who reacted
                def check(msg):
                    return msg.author.id == payload.member.id
                
                try:
                    msg = await self.client.wait_for('message', timeout=timeout, check=check)
                except asyncio.TimeoutError:
                    await message.channel.send(f'Took too long to respond lol', delete_after=15.0)
                else:
                    # Update record
                    self.pendingemojis.update({
                        'name': msg.content
                    }, doc_ids=[emoji_entry_id])

                    # Submit emoji
                    await self.new_emoji(payload)

                    try:
                        await edit_msg.delete()
                    except:
                        pass

                    await message.channel.send(f'Approved with new emoji name `{msg.content}`', delete_after=15.0)
                    await msg.delete()

def setup(client):
    client.add_cog(ReactionCog(client))
import asyncio
from cgi import test
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import discord
from discord.app_commands import Choice
from discord.ext import commands
from discord import app_commands
import os
from pyston import PystonClient, File
from ClassLibrary import *
import pathlib
from ClassLibrary2 import RequestUser
import mymodels as mm
import peewee as pw


class EmbedModal(discord.ui.Modal, title="Embed Creation"):
    embed_title = discord.ui.TextInput(label="Title")
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title=self.embed_title,
            description=self.description,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


class DebuggingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Testing command
    @app_commands.guilds(856915776345866240, 977351545966432306)
    @app_commands.command()
    async def itest(self, interaction: discord.Interaction):
        for user in mm.Users.select().objects():
            print(user)
            user_in_discord = interaction.client.get_user(user.id)
            print(user.name, user_in_discord.name)
            user.name = user_in_discord.name
            user.save()

        
    @commands.is_owner()
    @commands.command()
    async def use(self, ctx, item):
        inventory = Inventory(ctx)
        usable_items = [golden_ticket, robber_token]
        for x in usable_items:
            if item == x.name:
                if await inventory.get(item):
                    await x.use(ctx)
                    await inventory.remove_item(x.name, 1)
                    await ctx.send("Item used!")
                    return
            else:
                await ctx.send("You don't own this item!")

    # Sends the path of the bot. Mainly to check for more than one instance, not sure if this works yet
    @commands.is_owner()
    @commands.command(name='Ping')
    async def ping(self, ctx):
        path = pathlib.Path('main.py').parent.resolve()
        await ctx.send(f"`{os.path.abspath(__file__)}`")
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')
        sync = await self.bot.tree.sync(guild=discord.Object(id=856915776345866240))


    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f'Kicked {member.mention}.')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f'Banned {member.mention}.')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member):
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user

            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.send(f'User {user.mention} has been unbanned.')
                return

        print(banned_users)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount):
        await ctx.channel.purge(limit=int(amount) + 1)

    # A command for evaluating python code in discord
    @commands.command()
    async def eval(self, ctx, *, args):
        client = PystonClient()
        if str(args.startswith('`')):
            args = str(args.strip('`'))
        else:
            await ctx.send("Please format your code with ``` at the beginning and end.")
        output = await client.execute("python", [File(args)])
        embed = discord.Embed(
            title=f"Evaluation for: {ctx.author.name}",
            description=f"```{args}\n\nResults in:\n{output}```",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    # A command for sending embeds
    @app_commands.command(name="embed", description="Create an embed.")
    @app_commands.guilds(856915776345866240, 977351545966432306)
    async def embed(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())

    @app_commands.command(name="check", description="Check to see if you're on mobile or desktop!")
    @app_commands.guilds(856915776345866240, 977351545966432306)
    async def check(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)
        if member.is_on_mobile():
            await interaction.response.send_message("I'm a mobile user!")
            return
        await interaction.response.send_message("I'm not a mobile user...")

    # A command for sending embeds with images in them
    @commands.is_owner()
    @commands.command()
    async def embedimage(self, ctx):
        # Ask for title of embed and image of embed. Set those to the contents of the embed
        question1 = await ctx.send("What would you like the title of the embed to be.")
        title = await self.bot.wait_for(event="message")
        question2 = await ctx.send("Please send the attachment for the image.")
        file = await self.bot.wait_for('message')
        if file.attachments is None:
            # If there is no image attached, tell them to attach an image.
            await ctx.reply("Please rerun the command and an image.")
            return
        else:
            # Create the embed, set the image to be the url of the first image in attachments.
            embed = discord.Embed(
                title=title.content,
                color=discord.Color.green()
            )
            embed.set_image(url=file.attachments[0].url)
            # delete all of the previously asked questions and commands.
            await question1.delete()
            await question2.delete()
            await title.delete()
            await file.delete()
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DebuggingCommands(bot))

import asyncio
from datetime import datetime

import random
from random import randint
import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents, case_insensitive=True, strip_after_prefix=True)

with open('./config.json', 'r') as f:
    data = json.load(f)


def owner_perms_check(ctx):
    authorized = [326903703422500866, 730955069201317999]
    return ctx.message.author.id in authorized


@commands.is_owner()
@bot.command(hidden=True)
async def cogcheck(ctx):
    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await bot.load_extension(f"cogs.{cog[:-3]}")
            except commands.ExtensionAlreadyLoaded:
                await ctx.send(f"{cog} is currently loaded.")
            except commands.ExtensionNotFound:
                await ctx.send(f"{cog} could not be located.")


@commands.is_owner()
@bot.command(hidden=True)
async def sync(ctx):
    synced_commands = []
    treesync = await bot.tree.sync(guild=discord.Object(id=856915776345866240))  # Main guild sync
    for command in treesync:
        synced_commands.append(command.name)
    await ctx.send("synced!\n" + str(synced_commands))


@commands.check(owner_perms_check)
@bot.command(hidden=True, aliases=['rl'])
async def reload(ctx):
    cogs = []
    options = {}
    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            if cog.startswith('__init__'):
                pass
            else:
                cogs.append(cog)

    for x in cogs:
        options[x] = discord.SelectOption(label=x, value=x)
    select_options = []
    for x in options.values():
        select_options.append(x)

    class CogSelect(discord.ui.View):
        def __init__(self, *, timeout=180):
            super().__init__(timeout=timeout)

        @discord.ui.select(placeholder="Cog to reload", options=select_options)
        async def selection(self, interaction: discord.Interaction, select: discord.ui.Select):
            if interaction.user != ctx.author:
                return
            await bot.reload_extension(f"cogs.{select.values[0][:-3]}")
            last_cog_name = select.values[0][:-3]
            await interaction.response.edit_message(
                content=f"{select.values[0][:-3]} has successfully been reloaded.",
                view=None)
            await asyncio.sleep(0.6)
            await ctx.message.delete()
            await select_message.delete()

    select_message = await ctx.send("Which cog would you like to reload?", view=CogSelect())


@commands.is_owner()
@bot.command(hidden=True)
async def unload(ctx, cog):
    try:
        await bot.unload_extension(f"cogs.{cog}")
        await ctx.send(f"{cog} has successfully been unloaded.")
    except commands.ExtensionNotFound:
        await ctx.send(f"{cog} could not be located.")
    except commands.ExtensionNotLoaded:
        await ctx.send(f"{cog} is already unloaded.")


@commands.is_owner()
@bot.command(hidden=True)
async def load(ctx, cog):
    try:
        await bot.load_extension(f"cogs.{cog}")
        await ctx.send(f"{cog} has been successfully loaded.")
    except commands.ExtensionAlreadyLoaded:
        await ctx.send(f"{cog} is already loaded.")
    except commands.ExtensionNotFound:
        await ctx.send(f"{cog} could not be located.")


# @tasks.loop(minutes=randint(30, 60))
# async def drop_task():
#     guild = bot.get_guild(856915776345866240)
#     channels = [858549045613035541, 959271607241683044, 961471869725343834,
#                 961045401803317299, 962171274073899038, 962171351794327562]
#     channel = guild.get_channel(random.choice(channels))
#     drop_amount = randint(10000, 25000)
#     drop = Drop(bot, drop_amount)
#     await drop.prep_claim(channel)
#     random_drop_time = randint(60, 120)
#     drop_task.change_interval(minutes=random_drop_time)


@tasks.loop(minutes=30)
async def farm_task():

    plots1 = bot.dbfarms.find({"$or": [{"plot1": "coconut seeds"},
                                       {"plot2": "coconut seeds"},
                                       {"plot3": "coconut seeds"}]})
    plots2 = bot.dbfarms.find({"$or": [{"plot1": "cacao seeds"},
                                       {"plot2": "cacao seeds"},
                                       {"plot3": "cacao seeds"}]})
    plots3 = bot.dbfarms.find({"$or": [{"plot1": "almond seeds"},
                                       {"plot2": "almond seeds"},
                                       {"plot3": "almond seeds"}]})
    users_coconut = await plots1.to_list(length=None)
    users_cacao = await plots2.to_list(length=None)
    users_almond = await plots3.to_list(length=None)
    lucky_farmers = []
    coconut_odds = range(0, 3)
    cacao_odds = range(0, 1)
    almond_odds = range(0, 10)
    for users in users_coconut:
        plots = [users['plot1'], users['plot2'], users['plot3']]
        plot_names = ['plot1', 'plot2', 'plot3']
        for count, x in enumerate(plots):
            if x == "coconut seeds":
                roll = randint(0, 100)
                if roll in coconut_odds:
                    await bot.dbfarms.update_one({"_id": users['_id']}, {"$set": {plot_names[count]: "coconut"}})
                    user = bot.get_user(int(users["_id"]))
                    lucky_farmers.append(user.name)
    for users in users_cacao:
        plots = [users['plot1'], users['plot2'], users['plot3']]
        plot_names = ['plot1', 'plot2', 'plot3']
        for count, x in enumerate(plots):
            if x == "cacao seeds":
                roll = randint(0, 100)
                if roll in cacao_odds:
                    await bot.dbfarms.update_one({"_id": users['_id']}, {"$set": {plot_names[count]: "cacao"}})
                    user = bot.get_user(int(users['_id']))
                    lucky_farmers.append(user.name)
    for users in users_almond:
        plots = [users['plot1'], users['plot2'], users['plot3']]
        plot_names = ['plot1', 'plot2', 'plot3']
        for count, x in enumerate(plots):
            if x == "almond seeds":
                roll = randint(0, 100)
                if roll in almond_odds:
                    await bot.dbfarms.update_one({"_id": users['_id']}, {"$set": {plot_names[count]: "almonds"}})
                    user = bot.get_user(int(users["_id"]))
                    lucky_farmers.append(user.name)
    channel = bot.get_channel(966990507689533490)
    rain_events = ["The rains pour down onto the fields...", "The sun provides ample growth today!",
                   "The winds pass and bring an air of good harvest.",
                   "There's no better time of day to harvest than now!", "It's harvest o'clock somewhere...",
                   "Does the rain ever get tired of providing for these crops?", "Big rain storm approaching!"]
    if len(lucky_farmers) != 0:
        await channel.send(f"*{random.choice(rain_events)}*\nThe lucky farmers are: **{', '.join(lucky_farmers)}**")


@bot.event
async def on_ready():
    print("Bot is ready.")
    activity = discord.Game("-help")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    def seconds_until():  # Delay drops until half hour
        minutes = 30
        current_time = datetime.now()
        time_until = minutes - current_time.minute
        if time_until == 0:
            return 0
        elif time_until < 0:
            minutes = 60
            time_until = minutes - current_time.minute
        return (time_until * 60) - current_time.second

    now = datetime.now()
    print(f"-- BOT RAN --\nRan at: {now}\nDelaying tasks by: {seconds_until()} seconds")
    await asyncio.sleep(seconds_until())
    print("Running drop and farming tasks.")
    # drop_task.start()
    farm_task.start()


async def main():
    async def load_extensions():  # Function for loading cogs upon bot.run
        for filename in os.listdir('././cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')

    async with bot:
        await load_extensions()
        discord.utils.setup_logging()
        await bot.start(data["token"])


asyncio.run(main())

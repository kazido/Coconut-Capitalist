import discord
import time

from discord import utils
from typing import Literal

from cococap import instance
from cococap.item_models import Ranks, Master, Pets
from cococap.constants import DiscordGuilds
from cococap.models import UserCollection
from cococap.utils.utils import timestamp_to_digital

from logging import getLogger

log = getLogger(__name__)
log.setLevel(20)


class User:
    def __init__(self, uid: int) -> None:
        log.info("Initializing user object with user id: " + str(uid))
        self.uid = uid
        self.discord_info = self.get_discord_info()
        self.document: UserCollection

    def __str__(self) -> str:
        """Returns the user's name in discord"""
        return self.discord_info.name

    async def save(self):
        """Save the user document after any changes"""
        await self.document.save()

    async def load(self):
        """Loads the object with information from MongoDB"""
        self.document = await UserCollection.find_one(UserCollection.discord_id == self.uid)
        if self.document is None:
            self.document = UserCollection(name=self.discord_info.name, discord_id=self.uid)
            await self.document.insert()

    def get_discord_info(self) -> discord.Member:
        """Gets a user's discord info"""
        # If I ever expand the bot to other guilds, this needs to change
        guild: discord.Guild = instance.get_guild(DiscordGuilds.PRIMARY_GUILD.value)
        discord_user: discord.Member = guild.get_member(self.uid)
        if discord_user is None:
            raise Exception(f"No discord member with ID {self.uid}.")
        return discord_user

    async def get_user_rank(self) -> Ranks:
        """Retrieve the corresponding rank of a user based on their roles in a Discord guild."""
        unranked_id = 959850049188298772
        guild = instance.get_guild(DiscordGuilds.PRIMARY_GUILD.value)
        for rank in Ranks.select():
            discord_role = utils.get(guild.roles, id=rank.rank_id)
            # Check to see if the user has any matching role in discord
            if discord_role in self.discord_info.roles:
                return rank
        # If we don't find any rank, give them unranked
        unranked = guild.get_role(unranked_id)
        await self.discord_info.add_roles(unranked)
        return Ranks.get_by_id(unranked_id)

    def is_busy(self) -> bool:
        in_game = self.get_field("in_game")
        if in_game["in_game"]:
            embed = discord.Embed(
                title="You are busy elsewhere!",
                description=f"You are currently doing something else here: {in_game['channel']}!",
                color=discord.Color.red(),
            )
            return embed
        return False

    # UPDATE METHODS ------------------------------------
    async def inc_purse(self, amount: int):
        self.document.purse += amount
        await self.save()

    async def inc_bank(self, amount: int):
        self.document.bank += amount
        await self.save()

    async def inc_tokens(self, *, tokens: int):
        self.document.tokens += tokens
        await self.save()

    async def inc_xp(self, *, skill: str, xp: int, interaction: discord.Interaction):
        current_xp = getattr(self.document, skill)["xp"]
        current_level = self.xp_to_level(current_xp)
        pet, pet_data = self.get_active_pet()
        rewarded_xp = xp
        # if skill in pet_data.skill:
        #     rewarded_xp = xp + ((pet_data.max_level / 10) * pet["level"])
        level_to_be = self.xp_to_level(current_xp + rewarded_xp)
        if level_to_be > current_level:
            # If the user will level up, give them rewards
            bit_reward = level_to_be * 10000
            await self.inc_purse(amount=bit_reward)
            await self.inc_tokens(tokens=1)

            # Send an embed congratulating them
            embed = discord.Embed(
                title=f"{skill.capitalize()} level up! {current_level} -> {level_to_be}",
                description=f"Congratulations {interaction.user.mention}!",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Rewards",
                value=f":money_with_wings: +**{level_to_be*10000:,}** bits\n:coin: +**1** token",
            )
            embed.set_thumbnail(url=interaction.user.avatar.url)
            await interaction.channel.send(embed=embed)

        getattr(self.document, skill)["xp"] += rewarded_xp
        await self.save()
        return pet_data

    async def update_game(self, *, in_game: bool, interaction: discord.Interaction):
        if in_game:
            self.document.in_game["channel"] = interaction.channel.mention
        else:
            self.document.in_game["channel"] = ""
        self.document.in_game["in_game"] = in_game
        await self.save()

    # ITEM METHODS -----------------------------------
    async def create_item(self, item_id: str, quantity: int = 1):
        """Inserts an item into the database with specified owner and quantity"""

        inventory: dict = self.get_field("items")

        # Ensure that the item is an actual item first
        if not Master.get_or_none(item_id=item_id):
            message = f"'{item_id}' is not a valid item id."
            log.warn(message)
            return False, message
        if quantity < 1:
            message = f"Tried to create {quantity} {item_id}. Less than 1."
            log.warn(message)
            return False, message
        # Retrieve or create the item in the database
        if item_id not in inventory.keys():
            inventory[item_id] = {"quantity": quantity}
            message = f"{quantity} new {item_id} created with owner: {self}."
            log.info(message)
            await self.save()
            return True, message
        else:
            # If an item was found, add to it's quantity
            inventory[item_id]["quantity"] += quantity
            message = f"Added {quantity} {item_id} to: {self}"
            log.info(message)
            await self.save()
            return True, message

    async def delete_item(self, item_id: str, quantity: int = None):
        inventory: dict = self.get_field("items")
        # Ensure that the item is an actual item first
        if not Master.get_or_none(item_id=item_id):
            message = f"Tried to delete: {item_id}. Error: not a valid item id."
            log.warn(message)
            return False, message
        if quantity < 1:
            message = f"Tried to delete: {quantity} {item_id}. Error: less than 1."
            log.warn(message)
            return False, message
        if item_id in inventory.keys():
            # Try to decrement quantity of existing item
            if quantity and (inventory[item_id]["quantity"] - quantity > 0):
                inventory[item_id]["quantity"] -= quantity
                message = f"Deleted {quantity} {item_id} from {self}."
                log.info(message)
                await self.save()
                return True, message
            else:
                inventory.pop(item_id)
                message = f"Deleted all {item_id} from {self}."
                log.info(message)
                await self.save()
                return True, message
        else:
            # If item doesn't exist, do nothing
            message = f"Tried to delete {quantity} {item_id} from {self}. Does not exist."
            log.warn(message)
            return False, message

    async def trade_item(self, new_owner: int, item_id: str, quantity: int = None):
        user_2 = User(uid=new_owner)
        await user_2.load()

        inventory: dict = self.get_field("items")

        # Ensure that the item is an actual item first
        if not Master.get_or_none(item_id=item_id):
            message = f"Tried to trade: {item_id}. Error: not a valid item id."
            log.warn(message)
            return False, message
        if item_id in inventory.keys():
            # Transfer the ownership of the item if it exists
            item = inventory[item_id]
            if quantity:
                if quantity > item["quantity"]:
                    message = f"Tried to trade {quantity} {item_id}. Error: more than owned."
                    log.warn(message)
                    return False, message
                # Inserts same item into tradee's inventory
                await user_2.create_item(item_id, quantity)
                # Removes items from trader's inventory
                await self.delete_item(item_id, quantity)
                message = f"Traded {quantity} {item_id} from {self} to {user_2}."
                log.info(message)
                return True, message
            else:
                # Inserts same item into tradee's inventory
                await user_2.create_item(item_id, inventory[item_id]["quantity"])
                # Removes items from trader's inventory
                await self.delete_item(item_id)
                message = f"Traded all {item_id} from {self} to {user_2}."
                log.info(message)
                return True, message
        # If item doesn't exist, do nothing
        message = f"Tried to trade {item_id} from {self} to {user_2}. Item does not exist."
        log.warn(message)
        return False, message

    # GET METHODS ------------------------------------
    def get_field(self, field: str):
        if not hasattr(self.document, field):
            return "Object does not have field {field}."
        return getattr(self.document, field)

    def get_active_pet(self):
        pets = self.document.pets
        if "active" not in pets.keys():
            return None, None
        return pets["active"], Pets.get_by_id(pets["active"]["pet_id"])

    # XP METHODS ------------------------------------
    @staticmethod
    def level_to_xp(level):
        xp = ((level - 1) / 0.07) ** 2
        return int(xp)

    @staticmethod
    def xp_to_level(xp):
        level = 0.07 * (xp ** (1 / 2))
        return int(level + 1)

    @staticmethod
    def xp_for_next_level(xp):
        # Get current level and xp needed for current level
        level = User.xp_to_level(xp)
        level_xp = User.level_to_xp(level)
        # Get the next level and xp needed for next level
        next_level = level + 1
        next_level_xp = User.level_to_xp(next_level)
        # Get the overflow of xp above current level
        overflow_xp_at_level = xp - level_xp
        xp_between_levels = next_level_xp - level_xp
        return int(overflow_xp_at_level), int(xp_between_levels)

    @staticmethod
    def create_xp_bar(xp) -> str:
        overflow_xp, xp_needed = User.xp_for_next_level(xp)
        ratio = overflow_xp / xp_needed
        xp_bar = "<:xp_bar_left:1203894026265428021>"
        xp_bar_size = 10
        for _ in range(int(ratio * xp_bar_size)):
            xp_bar += "<:xp_bar_big:1203894024243777546>"
        for _ in range(xp_bar_size - int(ratio * xp_bar_size)):
            xp_bar += "<:xp_bar_small:1203894025137037443>"
        xp_bar += f"<:xp_bar_right:1203894027418599505>"
        return xp_bar

    # COOLDOWN METHODS ------------------------------------
    COMMAND_TYPES = Literal["daily", "work", "weekly"]

    async def set_cooldown(self, command_type: COMMAND_TYPES):
        now = time.time()
        self.document.cooldowns[command_type] = now
        await self.save()

    def check_cooldown(self, command_type: COMMAND_TYPES):
        """Checks to see if a command is currently on cooldown. Returns boolean result and cooldown, if any"""
        last_used = self.document.cooldowns[command_type]
        cooldowns = {"work": 6, "daily": 21, "weekly": 167}
        cooldown_hours = cooldowns[command_type]

        now = time.time()
        seconds_since_last_used = now - last_used
        hours_since_last_used = seconds_since_last_used / 3600

        if hours_since_last_used < cooldown_hours:
            # Cooldown has not yet finished
            off_cooldown = last_used + float(cooldown_hours * 3600)
            seconds_remaining = off_cooldown - now

            cooldown = timestamp_to_digital(seconds_remaining)

            return False, cooldown  # The check has been failed
        else:
            return True, None  # The check has been passed

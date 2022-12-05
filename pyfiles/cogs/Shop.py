from cogs.ErrorHandler import registered
from classLibrary import RequestUser, Inventory
from classLibrary import tools, consumables
from utils import SwitchButton
from discord.ext import commands
from discord import app_commands
import discord
import myModels as mm


class ShopCog(commands.Cog, name='Shop'):
    """Purchase helpful items on your way to the top!"""

    def __init__(self, bot):
        self.bot = bot

    @registered()
    @app_commands.guilds(977351545966432306, 856915776345866240)
    @app_commands.command(name="shop", description="Buy helpful items!")
    async def shop(self, interaction: discord.Interaction):
        user = RequestUser(interaction.user.id, interaction=interaction)  # User information
        inventory = Inventory(interaction)
        
        def add_button(view, parent_dict, item_ref_id):
            user_balance = user.instance.money
            label = parent_dict[item_ref_id]['item_name'].capitalize()
            if item_ref_id.startswith('TOOL_') and inventory.get(item_ref_id):
                style = discord.ButtonStyle.grey
                disabled = True
            elif user_balance >= parent_dict[item_ref_id]['price']:
                style = discord.ButtonStyle.green
                disabled = False
            else:
                style = discord.ButtonStyle.grey
                disabled = True
                
            new_button = PurchaseItemButton(item_ref_id, parent_dict, label=label, button_disabled=disabled, button_style=style)
            view.add_item(new_button)

        # Class for subclassing buttons for purchasing items
        class PurchaseItemButton(discord.ui.Button):
            def __init__(self, item_ref_id, parent_dict, label, button_disabled, button_style):
                if item_ref_id.startswith('TOOL_'):
                    item_exists = mm.Items.get_or_none(owner_id=interaction.user.id, reference_id=item_ref_id)
                    if item_exists:
                        self.button_label = 'Out of Stock'
                        self.button_emoji = '🚫'
                    else:
                        self.button_label = parent_dict[item_ref_id]['item_name']
                        self.button_emoji = None
                elif item_ref_id.startswith(('CROP', 'SEED')):
                    self.button_label = parent_dict[item_ref_id]['item_name']
                    self.button_emoji = parent_dict[parent_dict[item_ref_id]['grows_into']]['emoji']
                self.item_ref_id = item_ref_id
                self.parent_dict = parent_dict
                if label:
                    self.button_label = label
                else:
                    self.button_label = self.parent_dict[self.item_ref_id]['item_name']
                super().__init__(label=self.button_label,
                                 style=button_style, disabled=button_disabled)

            async def callback(self, purchase_interaction: discord.Interaction):
                if purchase_interaction.user != interaction.user:
                    return
                await purchase_interaction.response.send_message("This isn't finished yet.", ephemeral=True)
            
                # Add the item to the players inventory, subtract the price of the item from their balance, display purchased embed
                # item_price = self.parent_dict[self.item_ref_id]['price']
                # await user.update_balance(-item_price)

        # View that contains the Tools Shop
        class ToolShopView(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)
                self.view_embed = discord.Embed(title="Shop for Tools!",
                                                 description="Buy some tools that will allow you to dig, mine, or fish!\n*They're worth it, I promise.*",
                                                 color=discord.Color.blue())
                for tool in tools:
                    self.view_embed.add_field(name=tools[tool]['item_name'].capitalize(), value=f"{tools[tool]['price']:,}")
                    add_button(self, tools, tool)
                self.add_item(GoBackButton())

            async def on_timeout(self) -> None:
                await ShopSelectView.on_timeout(self=self)
                
        # View that contains the Seeds Shop
        class SeedShopView(discord.ui.View):
            def __init__(self, *, timeout=20):
                super().__init__(timeout=timeout)
                self.view_embed = discord.Embed(title="Shop for Seeds!",
                                                 description="Buy some seeds to plant.\n*Grown crops can be used to sell for profit or feed to pets.*",
                                                 color=discord.Color.brand_green())
                for key, value in consumables.items():
                    if key.startswith('SEED'):
                        self.view_embed.add_field(
                            name=f"{value['item_name'].capitalize()} {consumables[value['grows_into']]['emoji']}", value=f"{value['price']:,}")
                        add_button(self, consumables, key)
                self.add_item(GoBackButton())
            
            async def on_timeout(self) -> None:
                await ShopSelectView.on_timeout(self=self)

        # View that contains the main Shop page where the user selects the SubShop
        class ShopSelectView(discord.ui.View):
            def __init__(self, *, timeout=20):
                super().__init__(timeout=timeout)
                sub_shops = {
                    "tools": {
                        "view": ToolShopView(),
                        "label": "\u200b",
                        "emoji": '⚒️'
                    },
                    "seeds": {
                        "view": SeedShopView(),
                        "label": "\u200b",
                        "emoji": '🌱'
                    }
                }
                
                self.view_embed = discord.Embed(
                    title="Shop Select",
                    description="Choose which section you would like to shop from!",
                    color=discord.Color.teal()
                )
                for shop in sub_shops.values():
                    self.add_item(SwitchButton(interaction, shop['view'], shop['label'], shop['emoji']))
                self.add_item(CloseButton())
                
            async def on_timeout(self) -> None:
                shop_closed_embed = discord.Embed(
                    title="Shop Closed",
                    description=f"Thanks for your business, {interaction.user.mention}!\nCome again!",
                    color=discord.Color.gold()
                )
                self.view.stop()
                await interaction.edit_original_response(embed=shop_closed_embed, view=None)
                
        # Button to go back to the initial Shop Select page
        class GoBackButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label='\u200b', emoji='🔙', style=discord.ButtonStyle.blurple, row=2)

            async def callback(self, go_back_interaction):
                if interaction.user != go_back_interaction.user:
                    return
                new_view = ShopSelectView()
                self.view.stop()
                await go_back_interaction.response.edit_message(embed=new_view.view_embed, view=new_view)

        # Button to close the module
        class CloseButton(discord.ui.Button):
            def __init__(self, row=1):
                super().__init__(label="Leave", style=discord.ButtonStyle.red, row=row)

            async def callback(self, close_interaction: discord.Interaction):
                if close_interaction.user != interaction.user:
                    return
                await ShopSelectView.on_timeout(self)

        view = ShopSelectView()
        menu_message = await interaction.response.send_message(embed=view.view_embed, view=view)


async def setup(bot):
    await bot.add_cog(ShopCog(bot))

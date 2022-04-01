from discord.ext import commands
from discord import app_commands
from utils.modals import TransactionModal

async def setup(bot):
    await bot.load_cog(Institute)


class Institute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="subscribe")
    async def subscribe_(self, interaction):
        await interaction.response.send_modal(TransactionModal)

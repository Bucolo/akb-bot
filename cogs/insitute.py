from discord.ext import commands
from discord import app_commands
from utils.modals import SubscribeModal, RegisterModal


async def setup(bot):
    await bot.add_cog(Institute(bot))


class Institute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="subscribe")
    async def subscribe_(self, interaction):
        await interaction.response.send_modal(SubscribeModal())

    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.command(name="register")
    async def register_(self, interaction):
        await interaction.response.send_modal(RegisterModal())

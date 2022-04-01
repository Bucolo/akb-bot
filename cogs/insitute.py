import discord
from discord.ext import commands
from discord import app_commands


class Institute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="subscribe")
    async def subscribe_(self):
        
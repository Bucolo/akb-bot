import datetime
import pytz
import asyncio

import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.modals import SubscribeModal, RegisterModal


async def setup(bot):
    await bot.add_cog(Institute(bot))


class Institute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.first = True

    async def cog_load(self) -> None:
        self.check_expiration_date.start()

    @app_commands.command(name="subscribe", description="Cette commande te permet de procéder à ton inscription.")
    @app_commands.guilds(957989755184881764)
    async def subspicribe_(self, interaction):
        await interaction.response.send_modal(SubscribeModal())

    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.command(name="register", description="Cette commande permet d'ajouter un nouveau numéro de "
                                                       "transaction dans la base de donnée.")
    async def register_(self, interaction):
        await interaction.response.send_modal(RegisterModal())

    @tasks.loop(minutes=30)
    async def check_expiration_date(self):
        if self.first:
            self.first = False
            return
        data = await self.bot.pool.fetch("SELECT transaction,user_id,expire_at FROM subscribe")
        expired_transactions = []
        for r in data:
            if r["user_id"] is not None and r["expire_at"] is not None and r["expire_at"] <= datetime.datetime.utcnow().replace(tzinfo=pytz.UTC):
                member = self.bot.server_object.get_member(int(r["user_id"]))
                if member:
                    try:
                        await member.remove_roles(self.bot.server_premium_role, reason="Éxpiration de l'abonnement")
                    except discord.HTTPException:
                        pass
                expired_transactions.append((r["transaction"], r["user_id"]))
        print(len(expired_transactions))
        await self.bot.pool.executemany("DELETE FROM subscribe WHERE transaction=$1 AND user_id=$2",
                                        expired_transactions)

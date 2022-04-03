import datetime
import pytz
from typing import Union, Literal

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
    async def subscribe_(self, interaction):
        await interaction.response.send_modal(SubscribeModal())

    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.command(name="register", description="Cette commande permet d'ajouter un nouveau numéro de "
                                                       "transaction dans la base de donnée.")
    async def register_(self, interaction):
        await interaction.response.send_modal(RegisterModal())

    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.command(name="terminate",
                          description="Permet l'annulation d'abonnement(s) par utilisateur ou par numéro de transaction.")
    @app_commands.rename(user='utilisateur')
    @app_commands.describe(
        operation="Si l'abonnement doit verifier les 2 informations (AND)(par défaut) ou seulement une des 2 (OR)")
    async def terminate(self,
                        interaction,
                        transaction: str = None,
                        user: Union[discord.Member, discord.User] = None,
                        operation: Literal['OR', 'AND'] = 'AND'
                        ):
        if not user and not transaction:
            return await interaction.response.send_message("Au moins un des deux argument est nécessaire")
        filters = dict(transaction=transaction, user_id=user.id)
        query_list = []
        query_args = []
        c = 1
        for key, val in filters.items():
            if val is not None:
                query_list.append(f'{key}=${c}')
                query_args.append(val)
                c += 1
        query = f' {operation} '.join(query_list)
        query_args = tuple(query_args)
        info = await interaction.client.pool.fetch(
            f"DELETE subscribe FROM subscribe LEFT JOIN registered_user ON subscribe.user_id=registered_user.id WHERE {query} RETURNING  *",
            *query_args)
        if not info:
            return await interaction.response.send_message("Aucun abonnement n'a eté supprimer", ephemeral=True)
        string = "\n".join([f"""{', '.join('`' + [i["name"] + '`', '`' + i["transaction"] + '`'])}""" for i in info])
        await interaction.response.send_message(f"J'ai supprimer les abonnements suivant : {string}", ephemeral=True)

    @tasks.loop(minutes=30)
    async def check_expiration_date(self):
        if self.first:
            self.first = False
            return
        data = await self.bot.pool.fetch("SELECT transaction,user_id,expire_at FROM subscribe")
        expired_transactions = []
        for r in data:
            if r["user_id"] is not None and r["expire_at"] is not None and r[
                "expire_at"] <= datetime.datetime.utcnow().replace(tzinfo=pytz.UTC):
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

import math
import humanize

import discord
from discord import app_commands

from utils import exceptions


class CustomCommandTree(app_commands.CommandTree):
    async def on_error(
            self,
            interaction,
            command,
            error,
    ) -> None:
        """Handles command exceptions and logs unhandled ones to the support guild."""

        embed = discord.Embed(colour=interaction.client.colour)
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        if isinstance(error, app_commands.errors.CommandNotFound):
            embed.title = "🛑 Commande Introuvable"
            embed.description = "Desolé, cette commande n'existe plus."
            await interaction.client.send_interaction_error_message(interaction, embed=embed)
        elif isinstance(error, app_commands.CheckFailure):
            if isinstance(error, app_commands.BotMissingPermissions):
                missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
                perms_formatted = "**, **".join(missing[:-2] + ["** et **".join(missing[-2:])])
                _message = f"J'ai besoin des permissions **{perms_formatted}** pour procéder à cette commande."
                embed.title = "❌ Il Me Manque Des Permissions"
                embed.description = _message
                await interaction.client.send_interaction_error_message(interaction, embed=embed)

            elif isinstance(error, app_commands.CommandOnCooldown):
                _message = f"Cette commande est en cooldown, Merci de réessayer dans {humanize.time.precisedelta(math.ceil(error.retry_after))}. "
                embed.title = "🛑 Commande En Cooldown"
                embed.description = _message
                await interaction.client.send_interaction_error_message(interaction, embed=embed)

            elif isinstance(error, app_commands.MissingPermissions):
                missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
                perms_formatted = "**, **".join(missing[:-2] + ["** et **".join(missing[-2:])])
                _message = f"Tu as besoin des permissions **{perms_formatted}** pour utiliser cette commande."
                embed.title = "🛑 Il Te Manques Des Permissions"
                embed.description = _message
                await interaction.client.send_interaction_error_message(interaction, embed=embed)

            elif isinstance(error, app_commands.MissingRole):
                missing = error.missing_role
                _message = f"Tu as besoin du role **{missing}** pour utiliser cette commande."
                embed.title = "🛑 Il Te Manque Un Role"
                embed.description = _message
                await interaction.client.send_interaction_error_message(interaction, embed=embed)

            elif isinstance(error, app_commands.NoPrivateMessage):
                return

            elif isinstance(error, exceptions.NotOwner):
                _message = f"Désolé **{interaction.user}**, Mais cette commande est réservée a mon développeur."
                embed.title = "🛑 Seulement Pour Mon Developpeur"
                embed.description = _message
                await interaction.client.send_interaction_error_message(interaction, embed=embed)

            elif isinstance(error, exceptions.UserBlacklisted):
                embed.title = "🛑 Blacklisté"
                embed.description = str(error)
                await interaction.client.send_interaction_error_message(interaction, embed=embed)
            else:
                embed.title = "🛑 Interdit",
                embed.description = "L'un de nous deux ne peux pas faire cette action"
                await interaction.client.send_interaction_error_message(interaction, embed=embed)
        elif isinstance(error, app_commands.TransformerError):
            embed.title = "🛑 Mauvais Argument"
            embed.description = str(error)
            await interaction.client.send_interaction_error_message(interaction, embed=embed)
        else:
            await interaction.client.send_unexpected_error(interaction, command, error)

    async def interaction_check(self, interaction) -> bool:
        for check in interaction.client.default_checks:
            if await check(interaction) is False:
                return False
        return True

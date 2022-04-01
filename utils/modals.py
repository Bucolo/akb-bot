import discord
import asyncpg
import datetime


class BaseModal(discord.ui.Modal):
    async def on_error(self, error: Exception, interaction) -> None:
        await interaction.client.tree.on_error(interaction, interaction.command, error)


class TransactionModal(BaseModal):
    transaction_id = discord.ui.TextInput(
        label="Numéro De Transaction",
        min_length=5,
        max_length=50,
        placeholder="32435275Z397962A (vous pouvez le trouver dans les detail de la transaction sur PayPal)",
    )

    def __init__(self, **kwargs):
        super().__init__(title="Formulaire d'abonnement", **kwargs)

    async def on_submit(self, interaction) -> None:
        cleaned_transaction_id = self.transaction_id.value.replace(" ", "")
        if not discord.utils.get(interaction.client.server_object.members, id=interaction.user.id):
            return await interaction.response.send_message(
                f"Vous n'êtes pas dans le serveur, merci de rejoindre {self.server_invite} avant de vous inscrire.")
        await interaction.client.pool.execute(
            "INSERT INTO Registered_user(id,name) VALUES($1,$2) ON CONFLICT(id) DO UPDATE SET name=$2",
            interaction.user.id, str(interaction.user.name))
        try:
            await interaction.client.pool.execute(
                "INSERT INTO subscribe (transaction,user_id,approved,registered_at) VALUES($1,$2,$3,$4)",
                cleaned_transaction_id, interaction.user.id, False, datetime.datetime.utcnow())
            return await interaction.response.send_message(
                "Votre numéro de transaction n'a pas encore été ajouté dans la base de donnée, votre inscription est "
                "donc pour l'instant en attente. je vous contacterai quand elle aura eté validé.",
                ephemeral=True)
        except asyncpg.exceptions.UniqueViolationError:
            results = await interaction.client.pool.fetchrow(
                "SELECT * FROM subscribe WHERE transaction=$1", cleaned_transaction_id)
            if int(results["user_id"]) != interaction.user.id:
                await interaction.response.send_message("Un abonement a deja été enregistré avec ce numéro de "
                                                        "transaction, votre demande a donc été annulé.", ephemeral=True)
            else:
                if results["claimed_at"] is None:
                    claimed_at = datetime.datetime.utcnow()
                    new_expire_at = claimed_at + (results['expire_at'] - results['registered_at'])
                    await interaction.client.pool.execute("UPDATE subscribe SET user_id=$1,expire_at=$2,claimed_at=$3",
                                                          interaction.user.id, new_expire_at, claimed_at)
                else:
                    new_expire_at = results["expire_at"]
                await interaction.client.server_object.get_member(interaction.user.id).add_roles(
                    interaction.client.server_premium_role, reason="Abonnement automatique")
                message_ = f"Votre abonement a bien été enregistré et est valable jusqu'au " \
                           + \
                           discord.utils.format_dt(new_expire_at) + "."
                await interaction.response.send_message(message_)

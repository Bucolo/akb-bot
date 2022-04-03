import discord
import asyncpg
import datetime
import dateparser

NOT_APPROVED = "Votre numéro de transaction n'a pas encore été ajouté dans la base de donnée, votre inscription est " \
               "donc pour l'instant en attente. Le bot vous contactera quand elle aura eté validée (merci de ne pas " \
               "quitter le serveur). "


class BaseModal(discord.ui.Modal):
    async def on_error(self, error: Exception, interaction) -> None:
        await interaction.client.tree.on_error(interaction, interaction.command, error)


class SubscribeModal(BaseModal):
    transaction_id = discord.ui.TextInput(
        label="Numéro De Transaction",
        min_length=5,
        max_length=50,
        placeholder="Accessible depuis les détails de la transaction sur PayPal",
    )

    def __init__(self, **kwargs):
        super().__init__(title="Formulaire d'abonnement", **kwargs)

    async def on_submit(self, interaction) -> None:
        cleaned_transaction_id = self.transaction_id.value.replace(" ", "")
        await interaction.client.pool.execute(
            "INSERT INTO Registered_user(id,name) VALUES($1,$2) ON CONFLICT(id) DO UPDATE SET name=$2",
            interaction.user.id, str(interaction.user.name))
        try:
            await interaction.client.pool.execute(
                "INSERT INTO subscribe (transaction,user_id,approved,registered_at) VALUES($1,$2,$3,$4)",
                cleaned_transaction_id, interaction.user.id, False, datetime.datetime.utcnow())
            return await interaction.response.send_message(NOT_APPROVED,
                                                           ephemeral=True)
        except asyncpg.exceptions.UniqueViolationError:
            results = await interaction.client.pool.fetchrow(
                "SELECT * FROM subscribe WHERE transaction=$1", cleaned_transaction_id)
            if results["user_id"] is not None and int(results["user_id"]) != interaction.user.id:
                await interaction.response.send_message("Un abonnement a deja été enregistré avec ce numéro de "
                                                        "transaction, votre demande a donc été annulée.", ephemeral=True)
            else:
                if not results["approved"] or results["expire_at"] is None:
                    return await interaction.response.send_message(NOT_APPROVED, ephemeral=True)
                if results["claimed_at"] is None:
                    claimed_at = datetime.datetime.utcnow()
                    new_expire_at = claimed_at + (results['expire_at'] - results['registered_at'])
                    await interaction.client.pool.execute("UPDATE subscribe SET user_id=$1,expire_at=$2,claimed_at=$3",
                                                          interaction.user.id, new_expire_at, claimed_at)
                else:
                    new_expire_at = results["expire_at"]
                await interaction.user.add_roles(
                    interaction.client.server_premium_role, reason="Abonnement automatique")
                message_ = f"Votre abonnement a bien été enregistré et est valable jusqu'au " \
                           + \
                           discord.utils.format_dt(new_expire_at) + "."
                await interaction.response.send_message(message_, ephemeral=True)


class RegisterModal(BaseModal):
    transaction_id = discord.ui.TextInput(
        label="Numéro De Transaction",
        min_length=5,
        max_length=50,
        placeholder="32435275Z397962A",
    )
    expire_at = discord.ui.TextInput(
        label="Durée de l'abonnement ou date d'éxpiration",
        min_length=1,
        max_length=50,
        placeholder="'1 semaine' ou '10 avril 2022'",
    )

    def __init__(self, **kwargs):
        super().__init__(title="Enregistrement d'une nouvelle transaction", **kwargs)

    async def on_submit(self, interaction) -> None:
        cleaned_transaction_id = self.transaction_id.value.replace(" ", "")
        expire_at = dateparser.parse(
            self.expire_at.value,
            settings={'TO_TIMEZONE': 'UTC', 'TIMEZONE': 'Europe/Paris', 'RETURN_AS_TIMEZONE_AWARE': True,
                      'PREFER_DATES_FROM': 'future'},
        )
        if expire_at is None:
            return await interaction.response.send_message("Je n'ai pas pu comprendre la date d'éxpiration, merci de "
                                                           "réessayer avec une autre valeur")
        user_id = await interaction.client.pool.fetchval(
            "INSERT INTO subscribe(transaction,approved,expire_at,registered_at) VALUES ($1,$2,$3,$4) ON CONFLICT(transaction) DO UPDATE SET approved=$2,expire_at=$3,claimed_at=$4 RETURNING user_id",
            cleaned_transaction_id, True, expire_at, datetime.datetime.utcnow())
        if user_id:
            member = discord.utils.get(interaction.client.server_object.members, id=user_id)
            if not member:
                await interaction.client.pool.execute("UPDATE subscribe SET user_id=$1,claimed_at=$1", None)
            else:
                await member.add_roles(interaction.client.server_premium_role, reason="Abonnement automatique")
                await interaction.client.send_safe_dm(member,
                                                      f"Votre abonnement a été approuvé, vous pouvez donc bénéficier de celui-ci jusqu'au {discord.utils.format_dt(expire_at)}.")
        await interaction.response.send_message("L'abonnement a été enregistré avec succès !", ephemeral=True)

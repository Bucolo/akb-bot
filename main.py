import asyncio
import io
import os
import logging
import contextlib
import traceback

import aiohttp
import certifi
import ssl

import asyncpg
import discord

from discord.ext import commands

from utils.exceptions import UserBlacklisted
from private.config import (TOKEN, DEFAULT_PREFIXES, OWNER_IDS, DB_CONF)
from utils.tree import CustomCommandTree

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(asctime)-15s] %(message)s")

# Some very fancy characters hehe
err = '\033[41m\033[30m❌\033[0m'
oop = '\033[43m\033[37m⚠\033[0m'
ok = '\033[42m\033[30m✔\033[0m'

# Jishaku flags
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'


class AkbBot(commands.Bot):
    def __init__(self):
        # These are all attributes that will be set later in the `on_ready_once` method.
        self.pool = None
        self.invite: str = None
        self.session: aiohttp.ClientSession = None
        # All extensions that are not located in the 'cogs' directory.
        self.initial_extensions = ['jishaku']
        # Disabling the typing intents as we won't be using them.
        intents = discord.Intents.all()
        intents.typing = False  # noqa
        intents.dm_typing = False  # noqa
        super().__init__(
            tree_cls=CustomCommandTree,
            command_prefix=commands.when_mentioned_or(*DEFAULT_PREFIXES),
            strip_after_prefix=True,
            intents=intents
        )
        self.help_command = None
        self.server_invite = 'https://discord.gg/vEPEYTztgT'
        self.server_object = None
        self.server_premium_role = None
        self.owner_ids = OWNER_IDS
        self.colour = self.color = discord.Colour(value=0xA37FFF)
        self.default_checks = {self.check_blacklisted}

    @staticmethod
    async def check_blacklisted(interaction):
        if not hasattr(interaction.client, "pool"):
            return True
        result = await interaction.client.is_blacklisted(interaction.user)
        if result:
            raise UserBlacklisted(interaction.user, reason=result)
        return True

    async def is_blacklisted(self, user):
        return await self.pool.fetchval("SELECT reason FROM registered_user WHERE id=$1 AND is_blacklisted", user.id)

    async def before_ready_once(self) -> None:
        self.pool = await self.establish_database_connection()
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        self.loop.create_task(self.on_ready_once())

    async def on_ready_once(self):
        await self.wait_until_ready()
        self.server_object = self.get_guild(957989755184881764)
        self.server_premium_role = self.server_object.get_role(957993239816839208)
        self.invite = discord.utils.oauth_url(self.user.id,
                                              permissions=discord.Permissions(173211516614),
                                              redirect_uri=self.server_invite,
                                              scopes=["bot", "applications.commands"])
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="/subscribe"
            )
        )

    @staticmethod
    async def establish_database_connection() -> asyncpg.Pool:
        credentials = {
            "user": DB_CONF.user,
            "password": DB_CONF.password,
            "database": DB_CONF.db,
            "host": DB_CONF.host,
            "port": DB_CONF.port
        }

        try:
            return await asyncpg.create_pool(**credentials)

        except Exception as e:
            logging.error("Could not create database pool", exc_info=e)

        finally:
            logging.info(f'{ok} Database connection created.')

    async def on_ready(self):
        logging.info(f"\033[42m\033[35m Logged in as {self.user}! \033[0m")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """ Logs uncaught exceptions and sends them to the error log channel in the support guild. """
        traceback_string = traceback.format_exc()
        for line in traceback_string.split('\n'):
            logging.info(line)

        await self.wait_until_ready()
        error_channel = self.get_channel(959467834667319316)
        to_send = f"```yaml\nAn error occurred in an {event_method} event``````py" \
                  f"\n{traceback_string}\n```"

        if len(to_send) < 2000:
            try:
                await error_channel.send(to_send)

            except (discord.Forbidden, discord.HTTPException):
                await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                         file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))
        else:
            await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                     file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))

    @staticmethod
    async def send_interaction_error_message(interaction, *args, **kwargs):
        if interaction.response.is_done():
            await interaction.followup.send(*args, **kwargs)

        else:
            await interaction.response.send_message(*args, **kwargs)

    @staticmethod
    async def send_unexpected_error(interaction, command, error, **kwargs):
        with contextlib.suppress(discord.HTTPException):
            _message = f"Désolé, une erreur s'est produite, Mon developpeur en a été informé."
            embed = discord.Embed(title="❌ Erreur", colour=interaction.client.colour, description=_message)
            embed.add_field(name="Traceback :", value=f"```py\n{type(error).__name__} : {error}```")
            await interaction.client.send_interaction_error_message(interaction, embed=embed, **kwargs)

        error_channel = interaction.client.get_channel(959467834667319316)
        traceback_string = "".join(traceback.format_exception(etype=None, value=error, tb=error.__traceback__))

        if interaction.guild:
            command_data = (
                f"by: {interaction.user} ({interaction.user.id})"
                f"\ncommand: {command}"
                f"\nguild_id: {interaction.guild.id} - channel_id: {interaction.channel.id}"
                f"\nowner: {interaction.guild.owner.name} ({interaction.guild.owner.id})"
                f"\nbot admin: {'✅' if interaction.guild.me.guild_permissions.administrator else '❌'} "
                f"- role pos: {interaction.guild.me.top_role.position}"
            )
        else:
            command_data = (
                f"command: {command}"
                f"\nCommand executed in DMs"
            )

        to_send = (
            f"```yaml\n{command_data}``````py"
            f"\nCommand {command} raised the following error:"
            f"\n{traceback_string}\n```"
        )

        try:
            if len(to_send) < 2000:
                await error_channel.send(to_send)
            else:
                file = discord.File(
                    io.StringIO(traceback_string), filename="traceback.py"
                )
                await error_channel.send(
                    f"```yaml\n{command_data}``````py Command {command} raised the following error:\n```",
                    file=file,
                )
        finally:
            for line in traceback_string.split("\n"):
                logging.info(line)

    async def load_cogs(self):
        """
        Loads all the extensions in the ./cogs directory.
        """
        extensions = [f"cogs.{f[:-3]}" for f in os.listdir("./cogs") if f.endswith(".py")  # 'Cogs' folder
                      ] + self.initial_extensions  # Initial extensions like jishaku or others that may be elsewhere
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logging.info(f"{ok} Loaded extension {ext}")

            except Exception as e:
                if isinstance(e, commands.ExtensionNotFound):
                    logging.error(f"{oop} Extension {ext} was not found {oop}", exc_info=False)

                elif isinstance(e, commands.NoEntryPointError):
                    logging.error(f"{err} Extension {ext} has no setup function {err}", exc_info=False)

                else:
                    logging.error(f"{err}{err} Failed to load extension {ext} {err}{err}", exc_info=e)


if __name__ == "__main__":
    async def main():
        bot = AkbBot()
        async with bot:
            await bot.before_ready_once()
            await bot.load_cogs()
            await bot.start(TOKEN)

    asyncio.run(main())

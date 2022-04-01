from discord import app_commands


class UserBlacklisted(app_commands.CheckFailure):
    def __init__(self, user, message=None, reason="No reason provided"):
        self.user = user
        self.reason = reason
        self.message = message or f"Désolé **{user}**, tu ne peux plus utiliser le bot jusqu'a nouvel ordre, " \
                                  f"médite sur tes actions pendant ce temps :)"
        super().__init__(self.message)


class NotOwner(app_commands.CheckFailure):
    pass

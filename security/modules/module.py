from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip


class Module:
    name: str
    emoji: str
    description: str
    default_config: typing.Dict[str, typing.Any]
    configurable_by_trusted_admins: bool = True

    def __init__(self, cog: commands.Cog) -> None:
        self.cog: commands.Cog = cog

    @classmethod
    def key_name(self) -> str:
        return self.name.lower().replace(" ", "_")

    def config_value(self, guild: discord.Guild) -> typing.Any:
        return getattr(self.cog.config.guild(guild).modules, self.key_name())

    async def load(self) -> None:
        raise NotImplementedError()

    async def unload(self) -> None:
        raise NotImplementedError()

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎", "❌"], str, str]:
        raise NotImplementedError()

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        raise NotImplementedError()

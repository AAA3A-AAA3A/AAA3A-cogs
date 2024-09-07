from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from .views import RumbleNotifierView

# Credits:
# General repo credits.

_: Translator = Translator("RumbleNotifier", __file__)

class RoleConverter(commands.RoleConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = await super().convert(ctx, argument)
        if role >= ctx.author.top_role and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.BadArgument(_("You can't set a role higher than your own."))
        return role


@cog_i18n(_)
class RumbleNotifier(Cog):
    """Ping a role when a rumble starts, and let members suscribe or unsuscribe from the notifications!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            channels=[],
            role=None,
            suscribing=False,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "enabled": {
                "converter": bool,
                "description": "Enable or disable the cog.",
            },
            "channels": {
                "converter": commands.Greedy[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]],
                "description": "The channels/categories where the cog will detect rumbles.",
            },
            "role": {
                "converter": RoleConverter,
                "description": "The role that will be pinged when a rumble starts.",
            },
            "suscribing": {
                "converter": bool,
                "description": "Enable or disable the suscribing system.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.setrumblenotifier,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        view: RumbleNotifierView = RumbleNotifierView(self)
        self.bot.add_view(view)
        self.views[None] = view

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if isinstance(message.channel, discord.Thread):
            return
        if not (
            message.author.bot
            and message.author.id == 693167035068317736
        ):
            return
        config = await self.config.guild(message.guild).all()
        if (
            await self.bot.cog_disabled_in_guild(cog=self, guild=message.guild)
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or not message.channel.permissions_for(message.guild.me).send_messages
            or not config["enabled"]
            or not (channels_ids := config["channels"])
            or (message.channel.id not in channels_ids and message.channel.category_id not in channels_ids)
            or (role_id := config["role"]) is None
            or (role := message.guild.get_role(role_id)) is None
        ):
            return
        await asyncio.sleep(2)
        message = await message.channel.fetch_message(message.id)
        if not (
            message.embeds
            and (
                message.embeds[0].title is not None
                and "Rumble Royale" in message.embeds[0].title
            )
            and (
                message.embeds[0].description is not None
                and "Click the emoji below to join" in message.embeds[0].description
            )
        ):
            return
        suscribing = (
            await self.config.guild(message.guild).suscribing()
            and message.guild.me.guild_permissions.manage_roles
            and role.is_assignable()
            and role < message.guild.me.top_role
        )
        embed: discord.Embed = discord.Embed(
            title=_("⚔️ New Rumble battle! ⚔️"),
            description=_("I've notified the {length} members of the {role} role.").format(length=len(role.members), role=role.mention),
            color=discord.Color.gold(),
        )
        if suscribing:
            embed.add_field(
                name="\u200b",
                value=_("Want to be notified in the future? Use the buttons below!"),
                inline=False,
            )
        embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
        await message.channel.send(
            content=role.mention,
            embed=embed,
            view=self.views[None] if suscribing else None,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(aliases=["setrn"])
    async def setrumblenotifier(self, ctx: commands.Context) -> None:
        """Settings for the RumbleNotifier cog."""
        pass

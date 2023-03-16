from .AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .AAA3A_utils.settings import CustomMessageConverter

# Credits:
# General repo credits.

_ = Translator("ClearChannel", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class ClearChannel(Cog):
    """A cog to transfer all messages channel in a other channel!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 837018163805
            force_registration=True,
        )
        self.clearchannel_guild = {
            "channel_delete": True,
            "first_message": True,
            "author_dm": False,
            "custom_message": {},
        }
        self.config.register_guild(**self.clearchannel_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "delete_channel": {
                "path": ["channel_delete"],
                "converter": bool,
                "description": "If this option is disabled, the bot will not delete the original channel: it will duplicate it as normal, but move it to the end of the server's channel list.",
            },
            "first_message": {
                "path": ["first_message"],
                "converter": bool,
                "description": "If this option is enabled, the bot will send a message to the emptied channel to inform that it has been emptied.",
            },
            "dm_author": {
                "path": ["author_dm"],
                "converter": bool,
                "description": "If this option is enabled, the bot will try to send a dm to the author of the order to confirm that everything went well.",
            },
            "custom_message": {
                "path": ["custom_message"],
                "converter": CustomMessageConverter,
                "description": "Specify a custom message to be sent from the link of another message or a json (https://discohook.org/ for example).\n\nUse `{name}` or `{icon_url}` for the user.",
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
            commands_group=self.configuration,
        )

    async def cog_load(self):
        await self.settings.add_commands()

    @commands.guild_only()
    @commands.guildowner()
    @commands.bot_has_permissions(manage_channels=True)
    @hybrid_command(name="clearchannel")
    async def cleanup_channel(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete ALL messages from the current channel by duplicating it and then deleting it.
        For security reasons, only the server owner and the bot owner can use the command. Use the "permissions" tool for more options.
        """
        config = await self.config.guild(ctx.guild).all()
        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - ClearChannel")
            embed.description = _(
                "Do you really want to delete ALL messages from channel {old_channel.mention} ({old_channel.id})?"
            ).format(old_channel=old_channel)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return

        reason = _("Clear Channel requested by {ctx.author} ({ctx.author.id}).").format(ctx=ctx)
        new_channel = await old_channel.clone(reason=reason)
        if config["channel_delete"]:
            await old_channel.delete(reason=reason)
        else:
            await old_channel.edit(
                name=_("🗑️-Deleted-{old_channel.name}").format(old_channel=old_channel),
                position=len(ctx.guild.channels),
                reason=reason,
            )
        await new_channel.edit(
            position=channel_position,
            reason=reason,
        )
        self.log.info(
            f"{ctx.author} ({ctx.author.id}) deleted ALL messages in channel {old_channel.name} ({old_channel.id})."
        ),
        if config["first_message"]:
            if not config["custom_message"]:
                embed: discord.Embed = discord.Embed()
                embed.title = _("ClearChannel")
                embed.description = _("ALL the messages in this channel have been deleted...")
                embed.color = 0xF00020
                embed.set_author(
                    name=ctx.author.display_name if self.cogsutils.is_dpy2 else ctx.author.name,
                    url=ctx.author.display_avatar
                    if self.cogsutils.is_dpy2
                    else ctx.author.avatar_url,
                    icon_url=ctx.author.display_avatar
                    if self.cogsutils.is_dpy2
                    else ctx.author.avatar_url,
                )
                await new_channel.send(embed=embed)
            else:
                env = {
                    "user_name": ctx.author.display_name
                    if self.cogsutils.is_dpy2
                    else ctx.author.name,
                    "icon_url": ctx.author.display_avatar
                    if self.cogsutils.is_dpy2
                    else ctx.author.avatar_url,
                }
                await CustomMessageConverter(**config["custom_message"]).send_message(
                    ctx, channel=new_channel, env=env
                )
        if config["author_dm"]:
            await ctx.author.send(
                _(
                    "All messages in channel #{old_channel.name} ({old_channel.id}) have been deleted! You can find the new channel, with the same permissions: #{new_channel.name} ({new_channel.id})."
                ).format(old_channel=old_channel, new_channel=new_channel)
            )

    @commands.guild_only()
    @commands.guildowner()
    @hybrid_group(name="setclearchannel", aliases=["clearchannelset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure ClearChannel for your server."""
        pass

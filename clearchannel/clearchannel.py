from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from AAA3A_utils.settings import CustomMessageConverter

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_ = Translator("ClearChannel", __file__)


@cog_i18n(_)
class ClearChannel(DashboardIntegration, Cog):
    """A cog to delete ALL messages of a channel!

    ⚠ The channel will be cloned, and then **deleted**.
    """

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 837018163805
            force_registration=True,
        )
        self.config.register_guild(
            channel_delete=True,
            first_message=True,
            author_dm=False,
            custom_message={},
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "channel_delete": {
                "converter": bool,
                "description": "If this option is disabled, the bot will not delete the original channel: it will duplicate it as normal, but move it to the end of the server's channel list.",
            },
            "first_message": {
                "converter": bool,
                "description": "If this option is enabled, the bot will send a message to the emptied channel to inform that it has been emptied.",
            },
            "dm_author": {
                "converter": bool,
                "description": "If this option is enabled, the bot will try to send a dm to the author of the order to confirm that everything went well.",
            },
            "custom_message": {
                "converter": CustomMessageConverter,
                "description": "Specify a custom message to be sent from the link of another message or a json (https://discohook.org/ for example).\n\nUse the variables `{user_name}`, `{user_avatar_url}`, `{user_mention}`, `{user_id}`, `{channel_name}`, `{channel_mention}` and `{channel_id}`.",
            },
            "prompt_message": {
                "converter": CustomMessageConverter,
                "description": "Specify a custom message to be sent to confirm the clearing of the channel.\n\nUse the variables `{user_name}`, `{user_avatar_url}`, `{channel_name}`, `{channel_mention}` and `{channel_id}`.",
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

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    @commands.guild_only()
    @commands.guildowner()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.hybrid_command(name="clearchannel")
    async def cleanup_channel(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete ALL messages from the current channel by duplicating it and then deleting it.

        For security reasons, only the server owner and the bot owner can use the command. Use the "permissions" cog for more options.
        ⚠ The channel will be cloned, and then **deleted**.
        """
        config = await self.config.guild(ctx.guild).all()
        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation and not ctx.assume_yes:
            if not config["prompt_message"]:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - ClearChannel")
                embed.description = _(
                    "Do you really want to delete ALL messages from channel {old_channel.mention} ({old_channel.id})?\n⚠ The channel will be cloned, and then **deleted**."
                ).format(old_channel=old_channel)
                embed.color = 0xF00020
                if not await CogsUtils.ConfirmationAsk(
                    ctx, content=f"{ctx.author.mention}", embed=embed
                ):
                    await CogsUtils.delete_message(ctx.message)
                    return
            else:
                env = {
                    "user_name": ctx.author.display_name,
                    "user_avatar_url": ctx.author.display_avatar.url,
                    "user_mention": ctx.author.mention,
                    "user_id": ctx.author.id,
                    "channel_name": old_channel.name,
                    "channel_mention": old_channel.mention,
                    "channel_id": old_channel.id,
                }
                _kwargs = {}
                class FakeChannel:
                    async def send(self, **kwargs):
                        _kwargs.update(kwargs)
                await CustomMessageConverter(**config["prompt_message"]).send_message(
                    ctx, channel=FakeChannel(), env=env
                )
                if not await CogsUtils.ConfirmationAsk(
                    ctx, **_kwargs
                ):
                    await CogsUtils.delete_message(ctx.message)
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
        self.logger.info(
            f"{ctx.author} ({ctx.author.id}) deleted ALL messages in channel {old_channel.name} ({old_channel.id})."
        ),
        if config["first_message"]:
            if not config["custom_message"]:
                embed: discord.Embed = discord.Embed()
                embed.title = _("ClearChannel")
                embed.description = _("ALL the messages in this channel have been deleted...")
                embed.color = 0xF00020
                embed.set_author(
                    name=ctx.author.display_name,
                    url=ctx.author.display_avatar,
                    icon_url=ctx.author.display_avatar,
                )
                await new_channel.send(embed=embed)
            else:
                env = {
                    "user_name": ctx.author.display_name,
                    "user_avatar_url": ctx.author.display_avatar.url,
                    "user_mention": ctx.author.mention,
                    "user_id": ctx.author.id,
                    "channel_name": new_channel.name,
                    "channel_mention": new_channel.mention,
                    "channel_id": new_channel.id,
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
    @commands.hybrid_group(name="setclearchannel", aliases=["clearchannelset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure ClearChannel for your server."""
        pass

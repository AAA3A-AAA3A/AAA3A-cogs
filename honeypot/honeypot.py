from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config, modlog  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import os

from redbot.core.utils.chat_formatting import box

# Credits:
# General repo credits.
# Thanks to Matt for the cog idea!

_: Translator = Translator("Honeypot", __file__)


@cog_i18n(_)
class Honeypot(Cog):
    """Create a channel at the top of the server to attract self bots/scammers and notify/mute/kick/ban them immediately!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            action=None,
            logs_channel=None,
            ping_role=None,
            honeypot_channel=None,
            mute_role=None,
            ban_delete_message_days=3,
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Toggle the cog.",
            },
            "action": {
                "converter": typing.Literal["mute", "kick", "ban"],
                "description": "The action to take when a self bot/scammer is detected.",
            },
            "logs_channel": {
                "converter": typing.Union[
                    discord.TextChannel, discord.VoiceChannel, discord.Thread
                ],
                "description": "The channel to send the logs to.",
            },
            "ping_role": {
                "converter": discord.Role,
                "description": "The role to ping when a self bot/scammer is detected.",
            },
            "mute_role": {
                "converter": discord.Role,
                "description": "The mute role to assign to the self bots/scammers, if the action is `mute`.",
            },
            "ban_delete_message_days": {
                "converter": commands.Range[int, 0, 7],
                "description": "The number of days of messages to delete when banning a self bot/scammer.",
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
            commands_group=self.sethoneypot,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if message.author.bot:
            return
        config = await self.config.guild(message.guild).all()
        if (
            not config["enabled"]
            or (honeypot_channel_id := config["honeypot_channel"]) is None
            or (logs_channel_id := config["logs_channel"]) is None
            or (logs_channel := message.guild.get_channel(logs_channel_id)) is None
        ):
            return
        if message.channel.id != honeypot_channel_id:
            return
        if (
            message.author.id in self.bot.owner_ids
            or await self.bot.is_mod(message.author)
            or await self.bot.is_admin(message.author)
            or message.author.guild_permissions.manage_guild
            or message.author.top_role >= message.guild.me.top_role
        ):
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        action = config["action"]
        embed: discord.Embed = discord.Embed(
            title=_("Honeypot — Self Bot/Scammer Detected!"),
            description=f">>> {message.content}",
            color=discord.Color.red(),
            timestamp=message.created_at,
        )
        embed.set_author(
            name=f"{message.author.display_name} ({message.author.id})",
            icon_url=message.author.display_avatar,
        )
        embed.set_thumbnail(url=message.author.display_avatar)
        failed = None
        if action is not None:
            reason = "Self bot/scammer detected (message in the HoneyPot channel)."
            try:
                if action == "mute":
                    if (mute_role_id := config["mute_role"]) is not None and (
                        mute_role := message.guild.get_role(mute_role_id)
                    ) is not None:
                        await message.author.add_roles(
                            mute_role, reason=reason
                        )
                    else:
                        failed = _(
                            "**Failed:** The mute role is not set or doesn't exist anymore."
                        )
                elif action == "kick":
                    await message.author.kick(reason=reason)
                elif action == "ban":
                    await message.author.ban(
                        reason=reason,
                        delete_message_days=config["ban_delete_message_days"],
                    )
            except discord.HTTPException as e:
                failed = _(
                    "**Failed:** An error occurred while trying to take action against the member:\n"
                ) + box(str(e), lang="py")
            else:
                await modlog.create_case(
                    self.bot,
                    message.guild,
                    message.created_at,
                    action_type=action,
                    user=message.author,
                    moderator=message.guild.me,
                    reason=reason,
                )
            embed.add_field(
                name=_("Action:"),
                value=(
                    (
                        _("The member has been muted.")
                        if action == "mute"
                        else (
                            _("The member has been kicked.")
                            if action == "kick"
                            else _("The member has been banned.")
                        )
                    )
                    if failed is None
                    else failed
                ),
                inline=False,
            )
        embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
        await logs_channel.send(
            content=(
                ping_role.mention
                if (ping_role_id := config["ping_role"]) is not None
                and (ping_role := message.guild.get_role(ping_role_id)) is not None
                else None
            ),
            embed=embed,
        )

    @commands.guild_only()
    @commands.guildowner()
    @commands.hybrid_group()
    async def sethoneypot(self, ctx: commands.Context) -> None:
        """Set the honeypot settings. Only the server owner can use this command for security reasons."""
        pass

    @commands.bot_has_guild_permissions(manage_channels=True)
    @sethoneypot.command(aliases=["makechannel"])
    async def createchannel(self, ctx: commands.Context) -> None:
        """Create the honeypot channel."""
        if (
            honeypot_channel_id := await self.config.guild(ctx.guild).honeypot_channel()
        ) is not None and (
            honeypot_channel := ctx.guild.get_channel(honeypot_channel_id)
        ) is not None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The honeypot channel already exists: {honeypot_channel.mention} ({honeypot_channel.id})."
                ).format(honeypot_channel=honeypot_channel)
            )
        honeypot_channel = await ctx.guild.create_text_channel(
            name="honeypot",
            position=0,
            overwrites={
                ctx.guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    manage_channels=True,
                ),
                ctx.guild.default_role: discord.PermissionOverwrite(
                    view_channel=True, read_messages=True, send_messages=True
                ),
            },
            reason=f"Honeypot channel creation requested by {ctx.author.display_name} ({ctx.author.id}).",
        )
        embed = discord.Embed(
            title=_("⚠️ DO NOT POST HERE! ⚠️"),
            description=_(
                "An action will be immediately taken against you if you send a message in this channel."
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name=_("What not to do?"),
            value=_("Do not send any messages in this channel."),
            inline=False,
        )
        embed.add_field(
            name=_("What WILL happen?"),
            value=_("An action will be taken against you."),
            inline=False,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.set_image(url="attachment://do_not_post_here.png")
        await honeypot_channel.send(
            content=_("## ⚠️ WARNING ⚠️"),
            embed=embed,
            files=[discord.File(os.path.join(os.path.dirname(__file__), "do_not_post_here.png"))],
        )
        await self.config.guild(ctx.guild).honeypot_channel.set(honeypot_channel.id)
        await ctx.send(
            _(
                "The honeypot channel has been set to {honeypot_channel.mention} ({honeypot_channel.id}). You can now start attracting self bots/scammers!\n"
                "Please make sure to enable the cog and set the logs channel, the action to take, the role to ping (and the mute role) if you haven't already."
            ).format(honeypot_channel=honeypot_channel)
        )

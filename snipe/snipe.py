from AAA3A_utils import Cog, Menu, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from collections import defaultdict, deque
from copy import deepcopy

# Credits:
# General repo credits.
# Thanks to Epic for the original code (https://github.com/npc203/npc-cogs/tree/dpy2/snipe)!

_ = Translator("Snipe", __file__)


class SnipedMessage:
    def __init__(self, message: discord.Message, after: typing.Optional[discord.Message] = None) -> None:
        self.type: typing.Literal["deleted", "edited"] = "deleted" if after is None else "edited"

        self.id: int = message.id
        self.jump_url: str = message.jump_url
        self.author: discord.Member = message.author
        self.channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]] = message.channel

        self.created_at: datetime.datetime = message.created_at
        self.deleted_at: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

        if (
            hasattr(message, "reference")
            and message.reference is not None
            and isinstance((reference := message.reference.resolved), discord.Message)
        ):
            self.reference: discord.Message = reference
        else:
            self.reference = None
        self.content: str = message.content
        if self.type == "edited":
            self.new_content: str = after.content
        self.embeds: typing.List[discord.Embed] = message.embeds.copy()
        self.attachments: typing.List[discord.Attachment] = message.attachments.copy()
        self.stickers: typing.List[discord.Sticker] = message.stickers.copy()

        self.mentions: typing.List[discord.Member] = message.mentions.copy()
        self.role_mentions: typing.List[discord.Role] = message.role_mentions.copy()
        self.member_mentions: typing.List[typing.Union[discord.Member, discord.User]] = [mention for mention in message.mentions if isinstance(mention, (discord.Member, discord.User))]

    def to_embed(self, embed_color: discord.Color = discord.Color.green()) -> discord.Embed:
        embed: discord.Embed = None
        image = None

        if self.embeds:
            e = self.embeds[0]
            if e.type == "rich":
                e.timestamp = self.deleted_at
                embed = discord.Embed.from_dict(deepcopy(e.to_dict()))
            if e.type in ("image", "article"):
                image = e.url
        if embed is None:
            embed = discord.Embed(
                description=f">>> {self.content}" if self.content.strip() else None,
                timestamp=self.deleted_at,
                color=embed_color,
            )
        if self.type == "deleted":
            embed.title = _("Deleted Message (Sent at {created_timestamp})").format(created_timestamp=f"<t:{int(self.created_at.timestamp())}:F>")
        else:
            embed.title = _("Edited Message (Sent at {created_timestamp})").format(created_timestamp=f"<t:{int(self.created_at.timestamp())}:F>")
        embed.set_author(
            name=f"{self.author.display_name} ({self.author.id})",
            icon_url=self.author.display_avatar,
            url=self.jump_url,
        )
        embed.set_footer(text=f"#{self.channel.name}", icon_url=self.channel.guild.icon)
        embed.add_field(name=_("Channel:"), value=self.channel.mention, inline=True)
        embed.add_field(name=_("Deleted at:") if self.type == "deleted" else _("Edited at:"), value=f"<t:{int(self.deleted_at.timestamp())}:F>", inline=True)

        # if self.attachments:
        #     image = self.attachments[0].proxy_url
        #     embed.add_field(name=_("Attachments:"), value="\n".join(f"[{attachment.filename}]({attachment.url})" for attachment in self.attachments), inline=False)

        # sourcery skip: merge-nested-ifs
        if image is None:
            if self.stickers:
                for sticker in self.stickers:
                    if sticker.url:
                        image = str(sticker.url)
                        embed.add_field(name=_("Stickers:"), value=f"[{sticker.name}]({image})", inline=False)
                        break
        # else:
        #     embed.set_image(url=image)

        if self.type == "edited":
            embed.add_field(
                name=_("New Content:"),
                value=f"[{self.new_content.strip()[:1000] if self.new_content.strip() else _('Click to view attachments.')}]({self.jump_url})",
                inline=False,
            )

        if self.reference is not None:
            jump_url = self.reference.jump_url
            embed.add_field(
                name=_("Replying to:"),
                value=f"[{self.reference.content.strip()[:1000] if self.reference.content.strip() else _('Click to view attachments.')}]({jump_url})",
                inline=False,
            )

        return embed


@cog_i18n(_)
class Snipe(Cog):
    """Bulk sniping deleted and edited messages, for moderation purpose!"""

    def __init__(self, bot: Red):
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["epic guy", "AAA3A"]

        self.deleted_messages: typing.Dict[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread], typing.List[SnipedMessage]] = defaultdict(lambda: deque(maxlen=100))
        self.edited_messages: typing.Dict[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread], typing.List[SnipedMessage]] = defaultdict(lambda: deque(maxlen=100))
        self.no_track: typing.Set[int] = set()

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 969369062738
            force_registration=True,
        )
        self.snipe_guild: typing.Dict[str, bool] = {
            "ignored": False,
            "ignored_channels": [],
        }
        self.config.register_guild(**self.snipe_guild)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Any]
        ] = {
            "ignored": {
                "converter": bool,
                "description": "Set if the deleted and edited messages in this guild will be ignored.",
            },
            "ignored_channels": {
                "converter": commands.Greedy[discord.abc.GuildChannel],
                "description": "Set the channels in which deleted and edited messages will be ignored.",
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
            commands_group=self.setsnipe,
        )

    async def cog_load(self) -> None:
        await self.settings.add_commands()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ):
            return
        if message.guild is None or message.id in self.no_track:
            return
        if message.webhook_id is not None or message.author == message.guild.me:
            return
        config = await self.config.guild(message.guild).all()
        if config["ignored"] or getattr(message.channel, "parent", message.channel).id in config["ignored_channels"]:
            return
        if message.embeds and message.embeds[0].title is not None and message.embeds[0].title.startswith(("Deleted Message", "Edited Message")):
            return
        elif not message.embeds and message.components and ("Deleted Messages" in message.content or "Edited Messages" in message.content):
            return
        self.deleted_messages[message.channel].append(SnipedMessage(message=message))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=after.guild
        ):
            return
        if after.guild is None or after.id in self.no_track:
            return
        if after.webhook_id is not None or after.author == after.guild.me:
            return
        config = await self.config.guild(after.guild).all()
        if config["ignored"] or getattr(after.channel, "parent", after.channel).id in config["ignored_channels"]:
            return
        if after.embeds and after.embeds[0].title is not None and after.embeds[0].title.startswith(("Deleted Message", "Edited Message")):
            return
        elif not after.embeds and after.components and ("Deleted Messages" in after.content or "Edited Messages" in after.content):
            return
        self.edited_messages[after.channel].append(SnipedMessage(message=before, after=after))

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.hybrid_group(invoke_without_command=True)
    async def snipe(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], index: int = 0) -> None:
        """Bulk snipe deleted messages."""
        await self.snipe_index(ctx, channel=channel, index=index)

    @snipe.command(name="index")
    async def snipe_index(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], index: int = 0) -> None:
        """Snipe a deleted message."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        try:
            embed = self.deleted_messages[channel][-index].to_embed(embed_color=await ctx.embed_color())
        except IndexError:
            raise commands.UserFeedbackCheckFailure(_("No deleted message at this index in this channel."))
        await Menu(pages=[embed]).start(ctx)

    @snipe.command(name="bulk")
    async def snipe_bulk(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe deleted messages."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
        ]
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="member", aliases=["user"])
    async def snipe_member(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], *, member: typing.Union[discord.Member, discord.User]) -> None:
        """Bulk snipe deleted messages for the specified member."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
            if deleted_message.author == member
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded for this member in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="embeds")
    async def snipe_embeds(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe deleted messages with embeds."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
            if deleted_message.embeds
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with embeds recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="mentions")
    async def snipe_mentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe deleted messages with roles/users mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
            if deleted_message.mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="rolesmentions")
    async def snipe_rolesmentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe deleted messages with roles mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
            if deleted_message.role_mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with roles mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="membersmentions", aliases=["usersmentions"])
    async def snipe_membersmentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe deleted messages with members mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        embeds = [
            deleted_message.to_embed(embed_color=await ctx.embed_color())
            for deleted_message in self.deleted_messages[channel]
            if deleted_message.member_mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with members mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @snipe.command(name="list")
    async def snipe_list(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], *, member: typing.Union[discord.Member, discord.User] = None) -> None:
        """List deleted messages."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded in this channel."))
        content = "\n".join(
            [
                f"[{deleted_message.created_at.strftime('%A %d-%m-%Y %H:%M:%S')}] {deleted_message.author.display_name} ({deleted_message.author.id}): {deleted_message.content}"
                for deleted_message in
                sorted(
                    [
                        deleted_message
                        for deleted_message in self.deleted_messages[channel]
                        if member is None or deleted_message.author == member
                    ],
                    key=lambda message: message.created_at,
                )
            ]
        )
        if not content:
            raise commands.UserFeedbackCheckFailure(_("No deleted message recorded for this member in this channel."))
        await Menu(pages=content, prefix="-------------------- Deleted Messages --------------------", page_start=-1, lang="py").start(ctx)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.hybrid_group(invoke_without_command=True)
    async def esnipe(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], index: int = 0) -> None:
        """Bulk snipe edited messages."""
        await self.esnipe_index(ctx, channel=channel, index=index)

    @esnipe.command(name="index")
    async def esnipe_index(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], index: int = 0) -> None:
        """Snipe an edited message."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        try:
            embed = self.edited_messages[channel][-index].to_embed(embed_color=await ctx.embed_color())
        except IndexError:
            raise commands.UserFeedbackCheckFailure(_("No edited message at this index in this channel."))
        await Menu(pages=[embed]).start(ctx)

    @esnipe.command(name="bulk")
    async def esnipe_bulk(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe edited messages."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.deleted_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
        ]
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @esnipe.command(name="member", aliases=["user"])
    async def esnipe_member(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], *, member: typing.Union[discord.Member, discord.User]) -> None:
        """Bulk snipe edited messages for the specified member."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
            if edited_message.author == member
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded for this member in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @esnipe.command(name="embeds")
    async def esnipe_embeds(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe edited messages with embeds."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
            if edited_message.embeds
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with embeds recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @esnipe.command(name="mentions")
    async def esnipe_mentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe edited messages with roles/users mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
            if edited_message.mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)
        
    @esnipe.command(name="rolesmentions")
    async def esnipe_rolesmentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe edited messages with roles mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
            if edited_message.role_mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with roles mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=len(embeds) - 1).start(ctx)

    @esnipe.command(name="membersmentions", aliases=["usersmentions"])
    async def esnipe_membersmentions(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]) -> None:
        """Bulk snipe edited messages with members mentions."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        embeds = [
            edited_message.to_embed(embed_color=await ctx.embed_color())
            for edited_message in self.edited_messages[channel]
            if edited_message.member_mentions
        ]
        if not embeds:
            raise commands.UserFeedbackCheckFailure(_("No deleted message with members mentions recorded in this channel."))
        await Menu(pages=embeds, page_start=-1).start(ctx)

    @esnipe.command(name="list")
    async def esnipe_list(self, ctx: commands.Context, channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]], *, member: typing.Union[discord.Member, discord.User] = None) -> None:
        """List edited messages."""
        if channel is None:
            channel = ctx.channel
        ctx.message.channel = channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You are not allowed to execute this command in this channel."))
        if getattr(channel, "parent", channel).id in await self.config.guild(ctx.guild).ignored_channels():
            raise commands.UserFeedbackCheckFailure(_("This channel is in the ignored list."))
        if not self.edited_messages[channel]:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded in this channel."))
        content = "\n".join(
            [
                f"[{edited_message.created_at.strftime('%A %d-%m-%Y %H:%M:%S')}] {edited_message.author.display_name} ({edited_message.author.id}): {edited_message.content}"
                for edited_message in
                sorted(
                    [
                        edited_message
                        for edited_message in self.edited_messages[channel]
                        if member is None or edited_message.author == member
                    ],
                    key=lambda message: message.created_at,
                )
            ]
        )
        if not content:
            raise commands.UserFeedbackCheckFailure(_("No edited message recorded for this member in this channel."))
        await Menu(pages=content, prefix="-------------------- Edited Messages --------------------", page_start=-1, lang="py").start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setsnipe(self, ctx: commands.Context) -> None:
        """Commands to configure Snipe."""
        pass

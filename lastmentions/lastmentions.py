from AAA3A_utils import Cog, Menu, Settings, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import io

import plotly.graph_objects as go
from PIL import Image, ImageDraw
from redbot.core.utils.chat_formatting import pagify

# Credits:
# General repo credits.
# Thanks to evanroby for the idea and the initial implementation!

_: Translator = Translator("LastMentions", __file__)


class MemberOrChannelConverter(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> typing.Union[
        discord.Member,
        discord.TextChannel,
        discord.VoiceChannel,
        discord.Thread,
        discord.CategoryChannel,
        discord.ForumChannel,
    ]:
        for converter in (
            commands.MemberConverter,
            commands.TextChannelConverter,
            commands.VoiceChannelConverter,
            commands.ThreadConverter,
            commands.CategoryChannelConverter,
            commands.ForumChannelConverter,
        ):
            try:
                return await converter().convert(ctx, argument)
            except commands.BadArgument:
                continue
        raise commands.BadArgument(_("Please provide a valid member or channel."))


@cog_i18n(_)
class LastMentions(Cog):
    """Check the last mentions you received easily and get your or server statistics!"""

    __authors__: typing.List[str] = ["AAA3A", "evanroby"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=True,
            max_mentions_per_member=10,
            retention_days=3,
            track_replies=True,
            ignore_bots=True,
            max_mentions_per_5_minutes=3,
        )
        self.config.register_member(
            ignored=False,
            last_mentions=[],
            all_mention_timestamps=[],
            ignored_members=[],
            ignored_channels=[],
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Toggle the cog in the server.",
            },
            "max_mentions_per_member": {
                "converter": commands.Range[int, 1, 50],
                "description": "Maximum number of mentions to store per member.",
            },
            "retention_days": {
                "converter": commands.Range[int, 1, 14],
                "description": "Number of days to keep the mentions.",
            },
            "track_replies": {
                "converter": bool,
                "description": "Track replies to mentions.",
            },
            "ignore_bots": {
                "converter": bool,
                "description": "Ignore mentions from bots.",
            },
            "max_mentions_per_5_minutes": {
                "converter": commands.Range[int, 1, 10],
                "description": "Maximum number of mentions allowed per member in a 5-minute window before ignoring further mentions in that period.",
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
            commands_group=self.setlastmentions,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.loops.append(
            Loop(
                cog=self,
                name="Cleanup Last Mentions",
                function=self.cleanup_last_mentions,
                hours=1,
            )
        )

    async def cleanup_last_mentions(self) -> None:
        """Cleanup old mentions based on retention days."""
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild_id in members_data:
                retention_days = await self.config.guild_from_id(int(guild_id)).retention_days()
                retention_timestamp = int(
                    (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(days=retention_days)
                    ).timestamp()
                )
                for member_data in members_data[guild_id].values():
                    if not (last_mentions := member_data.get("last_mentions", [])):
                        continue
                    member_data["last_mentions"] = [
                        last_mention
                        for last_mention in last_mentions
                        if last_mention["timestamp"] >= retention_timestamp
                    ]

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not message.raw_mentions:
            return
        config = await self.config.guild(message.guild).all()
        if not config["enabled"] or await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if message.author.bot and config["ignore_bots"]:
            return
        for mention in message.mentions:
            if not isinstance(mention, discord.Member):
                continue
            if mention == message.author or mention.bot:
                continue
            if mention.id not in message.raw_mentions and not config["track_replies"]:
                continue
            if (
                not (channel_permissions := message.channel.permissions_for(mention)).view_channel
                or not channel_permissions.read_message_history
            ):
                continue
            member_data = await self.config.member(mention).all()
            if member_data["ignored"]:
                continue
            if message.author.id in member_data["ignored_members"]:
                continue
            if message.channel.id in member_data["ignored_channels"]:
                continue
            if (
                message.channel.category is not None
                and message.channel.category.id in member_data["ignored_channels"]
            ):
                continue
            if (
                isinstance(message.channel, discord.Thread)
                and message.channel.parent.id in member_data["ignored_channels"]
            ):
                continue
            message_timestamp = int(message.created_at.timestamp())
            if (
                len(
                    [
                        timestamp
                        for timestamp in member_data["all_mention_timestamps"]
                        if timestamp >= message_timestamp - 300
                    ]
                )
                >= config["max_mentions_per_5_minutes"]
            ):
                continue
            last_mentions = member_data["last_mentions"]
            if len(last_mentions) >= config["max_mentions_per_member"]:
                last_mentions = member_data["last_mentions"] = last_mentions[
                    -config["max_mentions_per_member"] + 1 :
                ]
            last_mentions.append(
                {
                    "timestamp": message_timestamp,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                    "message_id": message.id,
                    "content": message.content,
                    "attachments": len(message.attachments),
                    "reply_to": message.reference.message_id if message.reference else None,
                }
            )
            member_data["all_mention_timestamps"].append(message_timestamp)
            await self.config.member(mention).set(member_data)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Handle message deletion to remove mentions."""
        if message.guild is None:
            return
        if not await self.config.guild(
            message.guild
        ).enabled() or await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if message.author.bot and await self.config.guild(message.guild).ignore_bots():
            return
        for mention in message.mentions:
            if not isinstance(mention, discord.Member):
                continue
            member_data = await self.config.member(mention).all()
            if member_data["ignored"]:
                continue
            last_mentions = [
                last_mention
                for last_mention in member_data["last_mentions"]
                if last_mention["message_id"] != message.id
            ]
            await self.config.member(mention).last_mentions.set(last_mentions)

    @commands.guild_only()
    @commands.hybrid_group(aliases=["lm"], invoke_without_command=True)
    async def lastmentions(self, ctx: commands.Context) -> None:
        """Check the last mentions you received easily and get your or server statistics."""
        if ctx.invoked_subcommand is None:
            await self.show(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @lastmentions.command()
    async def show(self, ctx: commands.Context) -> None:
        """Show the last mentions you received."""
        if not (last_mentions := await self.config.member(ctx.author).last_mentions()):
            raise commands.UserFeedbackCheckFailure(_("You have no last mentions recorded."))
        embed: discord.Embed = discord.Embed(
            title=_("🔔 Last Mentions"),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        description = "\n\n".join(
            _("- {emoji} {timestamp} {author} ➡️ {message_jump_url}:\n> {content}").format(
                emoji="📢" if last_mention["reply_to"] is None else "💬",
                timestamp=discord.utils.format_dt(created_at, style="R"),
                author=(
                    f"{author.mention} (`{author}`)"
                    if (author := ctx.guild.get_member(last_mention["author_id"]))
                    else f"`{last_mention['author_id']}`"
                ),
                channel=channel,
                message_jump_url=channel.get_partial_message(last_mention["message_id"]).jump_url,
                content=(
                    last_mention["content"]
                    if len(last_mention["content"]) <= 1000
                    else last_mention["content"][:997] + "..."
                ).replace("\n", " ")
                + (
                    (
                        "\n"
                        if last_mention["content"]
                        else ""
                        + _("+ {attachments} attachments").format(
                            attachments=last_mention["attachments"]
                        )
                    )
                    if last_mention["attachments"] > 0
                    else ""
                ),
            )
            for last_mention in reversed(last_mentions)
            if (channel := ctx.guild.get_channel(last_mention["channel_id"])) is not None
            and (
                created_at := datetime.datetime.fromtimestamp(
                    last_mention["timestamp"], tz=datetime.timezone.utc
                )
            )
        )
        embeds = []
        for page in pagify(description, page_length=2000, delims=("\n\n")):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(embeds).start(ctx)

    @lastmentions.command()
    async def ignore(
        self,
        ctx: commands.Context,
        *,
        member_or_channel: MemberOrChannelConverter,
    ) -> None:
        """Ignore a member or channel for Last Mentions."""
        if isinstance(member_or_channel, discord.Member):
            ignored_members = await self.config.member(ctx.author).ignored_members()
            if member_or_channel.id in ignored_members:
                raise commands.UserFeedbackCheckFailure(_("You are already ignoring this member."))
            ignored_members.append(member_or_channel.id)
            await self.config.member(ctx.author).ignored_members.set(ignored_members)
        else:
            ignored_channels = await self.config.member(ctx.author).ignored_channels()
            if member_or_channel.id in ignored_channels:
                raise commands.UserFeedbackCheckFailure(
                    _("You are already ignoring this channel.")
                )
            ignored_channels.append(member_or_channel.id)
            await self.config.member(ctx.author).ignored_channels.set(ignored_channels)
        await self.config.member(ctx.author).last_mentions.set(
            [
                last_mention
                for last_mention in await self.config.member(ctx.author).last_mentions()
                if (
                    isinstance(member_or_channel, discord.Member)
                    and last_mention["author_id"] != member_or_channel.id
                )
                or (
                    not isinstance(member_or_channel, discord.Member)
                    and last_mention["channel_id"] != member_or_channel.id
                )
            ]
        )

    @lastmentions.command()
    async def unignore(
        self,
        ctx: commands.Context,
        *,
        member_or_channel: MemberOrChannelConverter,
    ) -> None:
        """Unignore a member or channel for Last Mentions."""
        if isinstance(member_or_channel, discord.Member):
            ignored_members = await self.config.member(ctx.author).ignored_members()
            if member_or_channel.id not in ignored_members:
                raise commands.UserFeedbackCheckFailure(_("You are not ignoring this member."))
            ignored_members.remove(member_or_channel.id)
            await self.config.member(ctx.author).ignored_members.set(ignored_members)
        else:
            ignored_channels = await self.config.member(ctx.author).ignored_channels()
            if member_or_channel.id not in ignored_channels:
                raise commands.UserFeedbackCheckFailure(_("You are not ignoring this channel."))
            ignored_channels.remove(member_or_channel.id)
            await self.config.member(ctx.author).ignored_channels.set(ignored_channels)

    @lastmentions.command()
    async def ignoreme(self, ctx: commands.Context) -> None:
        """Mark yourself as ignored for Last Mentions and clear your data."""
        ignored = await self.config.member(ctx.author).ignored()
        if not ignored:
            await self.config.member(ctx.author).ignored.set(True)
            await self.config.member(ctx.author).clear()
        else:
            await self.config.member(ctx.author).ignored.set(False)

    @lastmentions.command()
    async def stats(self, ctx: commands.Context) -> None:
        """Show your statistics for Last Mentions."""
        if not await self.config.guild(ctx.guild).enabled():
            raise commands.UserFeedbackCheckFailure(
                _("Last Mentions is not enabled in this server.")
            )
        if not (
            all_mention_timestamps := await self.config.member(ctx.author).all_mention_timestamps()
        ):
            raise commands.UserFeedbackCheckFailure(_("You have no mentions recorded."))
        embed: discord.Embed = discord.Embed(
            title=_("📊 Last Mentions Statistics"),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar,
        )
        embed.description = _(
            "You have received a total of **{total_mentions} mentions** since the feature was enabled."
        ).format(total_mentions=len(all_mention_timestamps))
        embed.set_image(url="attachment://image.png")
        file = await asyncio.to_thread(
            self.generate_graphic,
            all_mention_timestamps,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await Menu(pages=[{"embed": embed, "file": file}]).start(ctx)

    @lastmentions.command()
    async def serverstats(self, ctx: commands.Context) -> None:
        """Show the server statistics for Last Mentions."""
        if not await self.config.guild(ctx.guild).enabled():
            raise commands.UserFeedbackCheckFailure(
                _("Last Mentions is not enabled in this server.")
            )
        members_data = {
            member_id: member_data
            for member_id, member_data in (await self.config.all_members(ctx.guild)).items()
            if not member_data.get("ignored", False)
            and member_data.get("all_mention_timestamps", [])
        }
        total_mentions = sum(
            len(member_data["all_mention_timestamps"]) for member_data in members_data.values()
        )
        members_with_mentions = len(members_data)
        embed: discord.Embed = discord.Embed(
            title=_("📊 Server Last Mentions Statistics"),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(url=ctx.guild.icon)
        embed.description = _(
            "- **Mentions recorded:** {total_mentions}\n"
            "- **Members with mentions:** {members_with_mentions}\n"
            "- **Average mentions per member:** {average_mentions_per_member:.2f}\n"
        ).format(
            total_mentions=total_mentions,
            members_with_mentions=members_with_mentions,
            average_mentions_per_member=(
                total_mentions / members_with_mentions if members_with_mentions else 0
            ),
        )
        embed.add_field(
            name=_("Top 5 Mentioned Members:"),
            value="\n".join(
                _("{i}. {mention}: {count} mention{s}").format(
                    i=i,
                    mention=f"<@{member_id}>",
                    count=(count := len(member_data["all_mention_timestamps"])),
                    s="" if count == 1 else "s",
                )
                for i, (member_id, member_data) in enumerate(
                    sorted(
                        members_data.items(),
                        key=lambda item: len(item[1]["all_mention_timestamps"]),
                        reverse=True,
                    )[:5],
                    start=1,
                )
            ),
        )
        embed.set_image(url="attachment://image.png")
        all_mention_timestamps = []
        for member_data in members_data.values():
            if not member_data.get("ignored", False):
                all_mention_timestamps.extend(member_data.get("all_mention_timestamps", []))
        file = await asyncio.to_thread(
            self.generate_graphic,
            all_mention_timestamps,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await Menu(pages=[{"embed": embed, "file": file}]).start(ctx)

    def generate_graphic(
        self,
        all_mention_timestamps: typing.List[int],
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        img: Image.Image = Image.new("RGBA", (1500, 800), (0, 0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=15, fill=(32, 34, 37))
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            font_color="white",  # White characters font.
            font_size=30,  # Characters font size.
            yaxis2={"overlaying": "y", "side": "right"},
        )
        x = list(range(-7, 1))
        y = []
        for i in x:
            start = int(
                (
                    datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=-i + 1)
                ).timestamp()
            )
            end = int(
                (
                    datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=-i)
                ).timestamp()
            )
            y.append(
                len(
                    [timestamp for timestamp in all_mention_timestamps if start <= timestamp < end]
                )
            )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                line_color="rgb(0,255,0)",
                name=_("Mentions"),
                showlegend=False,
                line={"width": 14},
                fill="tozeroy",
                fillcolor="rgba(0,255,0,0.2)",
            )
        )
        fig.update_xaxes(type="category", tickvals=x)
        fig.update_yaxes(showgrid=True)
        graphic_bytes: bytes = fig.to_image(
            format="png",
            width=img.size[0],
            height=img.size[1],
            scale=1,
        )
        image = Image.open(io.BytesIO(graphic_bytes))
        img.paste(image, (0, 0, img.size[0], img.size[1]), mask=image.split()[3])
        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="image.png")

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setlastmentions(self, ctx: commands.Context) -> None:
        """Configure the Last Mentions settings."""
        pass

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all user chosen prefixes in all Config guilds."""
        if requester not in ("discord_deleted_user", "owner", "user", "user_strict"):
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    del members_data[guild][str(user_id)]
                if members_data[guild] == {}:
                    del members_data[guild]

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data:
                if str(user_id) in members_data[guild]:
                    data[Config.MEMBER][guild] = {str(user_id): members_data[guild][str(user_id)]}
        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

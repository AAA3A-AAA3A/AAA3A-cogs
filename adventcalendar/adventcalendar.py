from AAA3A_utils import Cog, Settings, CogsUtils, Loop, Menu  # isort:skip
from redbot.core import commands, Config, bank  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import functools
import io
import random
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import plotly.graph_objects as go
from redbot.core.data_manager import bundled_data_path

from .view import SetRewardsView

# Credits:
# General repo credits.

_: Translator = Translator("AdventCalendar", __file__)


@cog_i18n(_)
class AdventCalendar(Cog):
    """Set up an Advent Calendar for your members, with custom rewards or messages each day! Work in december only..."""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            whitelist_roles=[],
            blacklist_roles=[],
            rewards={str(day) if day is not None else "null": [] for day in list(range(1, 25)) + [None]},
            custom_rewards_logs_channel=None,
            custom_rewards_ping_role=None,
            priority_multiplier_roles=[],
            include_opener_mention=False,
        )
        self.config.register_member(
            opened_days=[],
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Whether the Advent Calendar is enabled in this server.",
            },
            "whitelist_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that can access the Advent Calendar.",
            },
            "blacklist_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that cannot access the Advent Calendar.",
            },
            "custom_rewards_logs_channel": {
                "converter": typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
                "description": "The channel where custom rewards logs will be sent.",
            },
            "custom_rewards_ping_role": {
                "converter": discord.Role,
                "description": "The role that will be pinged when custom rewards are given.",
            },
            "priority_multiplier_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that will have their rewards priority multiplied (set individually for each reward).",
            },
            "include_opener_mention": {
                "converter": bool,
                "description": "Whether to include the opener's mention in all messages.",
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
            commands_group=self.setadventcalendar,
        )

        self.bold_font_path: Path = bundled_data_path(self) / "arial_bold.ttf"
        self.merry_christmas_flake_font_path: Path = bundled_data_path(self) / "MerryChristmasFlake.ttf"
        self.merry_christmas_star_font_path: Path = bundled_data_path(self) / "MerryChristmasStar.ttf"
        self.bold_font: typing.Dict[int, ImageFont.ImageFont] = {
            size: ImageFont.truetype(str(self.bold_font_path), size=size)
            for size in {80, 100}
        }
        self.merry_christmas_flake_font: typing.Dict[int, ImageFont.ImageFont] = {
            size: ImageFont.truetype(str(self.merry_christmas_flake_font_path), size=size)
            for size in {200, 325}
        }
        self.merry_christmas_star_font: typing.Dict[int, ImageFont.ImageFont] = {
            size: ImageFont.truetype(str(self.merry_christmas_star_font_path), size=size)
            for size in {200, 325}
        }
        self.christmas_tree_path: Path = bundled_data_path(self) / "christmas_tree.png"
        self.christmas_tree: Image.Image = Image.open(self.christmas_tree_path)
        self.x_path: Path = bundled_data_path(self) / "x.png"
        self.x: Image.Image = Image.open(self.x_path)

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.loops.append(
            Loop(
                cog=self,
                name="Cleanup Last Year's Opened Days",
                function=self.cleanup_last_year_opened_days,
                days=1,
            )
        )

    async def cog_unload(self) -> None:
        self.christmas_tree.close()
        await super().cog_unload()

    def align_text_center(
        self,
        draw: ImageDraw.Draw,
        xy: typing.Tuple[int, int, int, int],
        text: str,
        fill: typing.Optional[typing.Tuple[int, int, int, typing.Optional[int]]],
        font: ImageFont.ImageFont,
    ) -> typing.Tuple[int, int]:
        x1, y1, x2, y2 = xy
        text_size = font.getbbox(text)
        x = int((x2 - x1 - text_size[2]) / 2)
        x = max(x, 0)
        y = int((y2 - y1 - text_size[3]) / 2)
        y = max(y, 0)
        if font in self.bold_font.values():
            y -= 5
        draw.text((x1 + x, y1 + y), text=text, fill=fill, font=font)
        return text_size

    def _generate_advent_calendar(
        self,
        today_day: int,
        opened_days: typing.List[int],
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        img: Image.Image = Image.new("RGBA", (2465, 1280), (0, 0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            (0, 0, img.width, img.height),
            radius=50,
            fill=(43, 45, 49),
        )
        align_text_center = functools.partial(self.align_text_center, draw)

        christmas_tree = self.christmas_tree.resize((350, 350))
        img.paste(christmas_tree, (0, 0, 350, 350), mask=christmas_tree.split()[3])
        align_text_center(
            (300, 0, 1680, 400),
            text=_("*Advent0Calendar*"),
            fill=(255, 255, 255),
            font=self.merry_christmas_flake_font[325],
        )

        open_emojis = []
        for __ in range(len(opened_days) // 10):
            open_emojis.extend(list(range(10)))
        open_emojis.extend(random.sample(list(range(10)), k=len(opened_days) % 10))
        random.shuffle(open_emojis)

        def box_day(
            day: int,
            x: int, y: int,
            size: int,
            color: typing.Tuple[typing.Tuple[int, int, int], typing.Tuple[int, int, int]],
        ) -> None:
            draw.polygon(
                (
                    (x + 15, y - 15),
                    (x + size + 15, y + 15),
                    (x + size - 15, y + size + 15),
                    (x - 15, y + size - 15),
                ),
                fill=color[0],
            )
            draw.polygon(
                (
                    (x - 15, y + 15),
                    (x + size - 15, y - 15),
                    (x + size + 15, y + size - 15),
                    (x + 15, y + size + 15),
                ),
                fill=color[1],
            )
            draw.rectangle(
                (x, y, x + size, y + size),
                fill=(43, 45, 49),  # (0, 0, 0, 0),
            )
            # draw.rectangle(
            #     (x + 30, y + 30, x + size - 30, y + size - 30),
            #     fill=(0, 0, 0),
            # )
            if day in opened_days:
                align_text_center(
                    (x + 4, y, x + size, y + size - 40),
                    text=str(open_emojis.pop()),
                    fill=(255, 255, 255),
                    font=self.merry_christmas_flake_font[200],
                )
            elif today_day <= day:
                draw.rectangle(
                    (x + 20, y + 20, x + size - 20, y + size - 20),
                    fill=color[0],
                )
                align_text_center(
                    (x, y, x + size, y + size // 1.1),
                    text=str(day),
                    fill=(255, 255, 255),
                    font=self.bold_font[80],
                )
            else:
                x_img = self.x.resize((size - 80, size - 80))
                img.paste(x_img, (x + 40, y + 40, x + size - 40, y + size - 40), mask=x_img.split()[3])

        colors = [
            (  # yellow
                (255, 170, 50),
                (255, 200, 80),
            ),
            (  # green
                (60, 110, 35),
                (90, 135, 60),
            ),
            (  # red
                (220, 45, 45),
                (240, 80, 80),
            ),
        ]
        box_day(24, 2185, 90, size=230, color=colors[0])
        days = list(range(1, 24))
        for i in range(3):
            for j in range(8 if i != 2 else 7):
                day = random.choice(days)
                days.remove(day)
                size = 230
                box_day(
                    day,
                    50 + j*(size+75), 395 + i*(size+75),
                    size=size,
                    color=colors[(i+j)%3],
                )

        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="advent_calendar.png")

    async def generate_advent_calendar(
        self,
        today_day: typing.Optional[int] = None,
        opened_days: typing.List[int] = [],
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        if today_day is None:
            today_day = datetime.date.today().day
        return await asyncio.to_thread(
            self._generate_advent_calendar,
            today_day=today_day,
            opened_days=opened_days,
            to_file=to_file,
        )

    def _generate_merry_christmas(self, to_file: bool = True) -> typing.Union[Image.Image, discord.File]:
        img: Image.Image = Image.new("RGBA", (1900, 450), (0, 0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        # draw.rounded_rectangle(
        #     (0, 0, img.width, img.height),
        #     radius=50,
        #     fill=(43, 45, 49),
        # )
        align_text_center = functools.partial(self.align_text_center, draw)
        align_text_center(
            xy=(0, 0, img.width, img.height),
            text=_("Merry4Christmas!"),
            fill=(255, 215, 0),  # gold
            # fill=(255, 255, 255),
            font=self.merry_christmas_star_font[325],
        )

        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="merry_christmas.png")

    async def generate_merry_christmas(self, to_file: bool = True) -> typing.Union[Image.Image, discord.File]:
        return await asyncio.to_thread(
            self._generate_merry_christmas,
            to_file=to_file,
        )

    async def get_reward(self, member: discord.Member, day: typing.Optional[int]) -> typing.Tuple[typing.Optional[typing.Dict[str, typing.Union[str, int]]], typing.Optional[typing.Dict[typing.Literal["embed", "file"], typing.Union[discord.Embed, discord.File]]]]:
        day_rewards = [
            reward
            for reward in await self.config.guild(member.guild).rewards.get_raw(str(day) if day is not None else "null")
            if not (
                (
                    reward["type"] == "role"
                    and (
                        (role := member.guild.get_role(reward["role_id"])) is None 
                        or role in member.roles
                    )
                )
                or (
                    reward["type"] == "temp_role"
                    and (
                        (TempRoles := self.bot.get_cog("TempRoles")) is None
                        or (role := member.guild.get_role(reward["role_id"])) is None
                        or role in member.roles
                    )
                )
                or (
                    reward["type"] == "bank_credits"
                    and await bank.is_global()
                )
                or (
                    reward["type"] == "levelup_xp"
                    and (
                        (LevelUp := self.bot.get_cog("LevelUp")) is None
                        or not hasattr(LevelUp, "add_xp")
                    )
                )
                or (
                    reward["type"] == "custom"
                    and (
                        (custom_rewards_logs_channel_id := await self.config.guild(member.guild).custom_rewards_logs_channel()) is None
                        or (custom_rewards_logs_channel := member.guild.get_channel(custom_rewards_logs_channel_id)) is None
                    )
                )
            )
        ]
        if not day_rewards:
            return None, None
        reward = random.sample(
            day_rewards, k=1,
            counts=[
                (
                    reward["priority"] * reward["priority_multiplier"]
                    if (
                        reward["priority_multiplier"] is not None
                        and any(
                            member.get_role(role_id) is not None
                            for role_id in await self.config.guild(member.guild).priority_multiplier_roles()
                        )
                    ) else reward["priority"]
                )
                for reward in day_rewards
            ],
        )[0]
        if reward["type"] is None:
            return None, None
        elif reward["type"] == "role":
            try:
                await member.add_roles(role, reason=f"🎄 Advent Calendar {f'reward for day {day}' if day is not None else 'final reward'}.")
            except discord.HTTPException:
                return None, None
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 You've received a **new role**! 🎁"),
                    description=_("You've received the {role} role!").format(role=role.mention),
                    color=discord.Color.green(),
                ),
            }
        elif reward["type"] == "temp_role":
            duration = datetime.timedelta(seconds=reward["duration"])
            try:
                end_time: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc) + duration
            except OverflowError:
                return None, None
            end_time = end_time.replace(second=0 if end_time.second < 30 else 30)
            try:
                await member.add_roles(role, reason=f"🎄 Advent Calendar {f'reward for day {day}' if day is not None else 'final reward'} (temporary).")
            except discord.HTTPException:
                return None, None
            member_temp_roles = await TempRoles.config.member(member).temp_roles()
            member_temp_roles[str(role.id)] = int(end_time.replace(microsecond=0).timestamp())
            await TempRoles.config.member(member).temp_roles.set(member_temp_roles)
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 You've received a **temporary role**! 🎁"),
                    description=_("You've received the {role} role **for {duration_string}**!").format(role=role.mention, duration_string=CogsUtils.get_interval_string(duration)),
                    color=discord.Color.green(),
                ),
            }
        elif reward["type"] == "bank_credits":
            await bank.deposit_credits(member, reward["amount"])
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 You've received **{amount} credits**! 🎁").format(amount=reward["amount"]),
                    color=discord.Color.green(),
                ),
            }
        elif reward["type"] == "levelup_xp":
            await LevelUp.add_xp(member, xp=reward["amount"])
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 You've received **{amount} XP**! 🎁").format(amount=reward["amount"]),
                    color=discord.Color.green(),
                ).set_image(url="attachment://profile.webp"),
                "file": file if isinstance((file := await LevelUp.get_user_profile_cached(member)), discord.File) else None,
            }
        elif reward["type"] == "custom":
            embed = discord.Embed(
                title=_("Advent Calendar — {member.display_name} received a **custom reward**").format(member=member) + (f" for **day {day}**!" if day is not None else " as **final reward**!"),
                color=discord.Color.green(),
                timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar)
            embed.add_field(name=_("Member:"), value=f"{member.mention} ({member.id})")
            embed.add_field(name=_("Reward label:"), value=reward["label"])
            embed.set_footer(text=member.guild.name, icon_url=member.guild.icon)
            await custom_rewards_logs_channel.send(
                content=(
                    custom_rewards_ping_role.mention
                    if (
                        (custom_rewards_ping_role_id := await self.config.guild(member.guild).custom_rewards_ping_role()) is not None
                        and (custom_rewards_ping_role := member.guild.get_role(custom_rewards_ping_role_id)) is not None
                    )
                    else None
                ),
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True),
            )
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 You will receive **{label}**! 🎁").format(label=reward["label"]),
                    description=_("Please wait for a staff member to give you your reward."),
                    color=discord.Color.green(),
                ),
            }
        elif reward["type"] == "message":
            return reward, {
                "embed": discord.Embed(
                    title=_("🎁 Here's a **message** for you! 🎁"),
                    description=f">>> {reward['message']}",
                    color=discord.Color.green(),
                ),
            }

    async def cleanup_last_year_opened_days(self) -> None:
        today = datetime.date.today()
        if today.month == 12:
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            members_data.clear()

    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.hybrid_command(aliases=["advent"])
    async def adventcalendar(self, ctx: commands.Context) -> None:
        """Open your Advent Calendar box for the day!"""
        today = datetime.date.today()
        if today.month != 12:
            first_december = today.replace(month=12, day=1)
            raise commands.UserFeedbackCheckFailure(
                _("The Advent Calendar is only available in December. **Come back in {interval_string}!** 🎄").format(
                    interval_string=CogsUtils.get_interval_string(first_december - today),
                )
            )
        config = await self.config.guild(ctx.guild).all()
        if not config["enabled"]:
            raise commands.UserFeedbackCheckFailure(_("The Advent Calendar is not enabled in this server."))
        if (
            config["whitelist_roles"]
            and not any(role.id in config["whitelist_roles"] for role in ctx.author.roles)
        ):
            raise commands.UserFeedbackCheckFailure(_("You don't have the required roles to access the Advent Calendar."))
        if any(role.id in config["blacklist_roles"] for role in ctx.author.roles):
            raise commands.UserFeedbackCheckFailure(_("You're not allowed to access the Advent Calendar."))

        content, embeds, files = None, [], []
        today_day = today.day
        opened_days = await self.config.member(ctx.author).opened_days()
        if today_day <= 24:
            if today_day not in opened_days:
                reward, kwargs = await self.get_reward(ctx.author, today_day)
                if reward is not None:
                    content = _("🎄 Here's your surprise for **day {today_day}** of the Advent Calendar! 🎄").format(today_day=today_day)
                    if kwargs is not None:
                        embeds.append(kwargs["embed"])
                        if (file := kwargs.get("file")) is not None:
                            files.append(file)
                else:
                    content = _("🎄 You didn't get anything today, **come back tomorrow!** 🎄")
                opened_days.append(today_day)
                await self.config.member(ctx.author).opened_days.set(opened_days)
            else:
                content = _(
                    "You've already opened your box for the day, **come back <t:{timestamp}:R>!** 😉 Here's your current Advent Calendar!"
                ).format(timestamp=int(datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time(0, 0, 0)).timestamp()))
        elif today_day == 25:
            embeds.append(
                discord.Embed(
                    color=await ctx.embed_color(),
                ).set_image(url="attachment://merry_christmas.png")
            )
            files.append(await self.generate_merry_christmas())
            if len(opened_days) == 24 and None not in opened_days:
                content = _("🎄 You've opened all the boxes! 🎄")
                reward, kwargs = await self.get_reward(ctx.author, None)
                if reward is not None:
                    content += _(" Here's your **final surprise**!")
                    if kwargs is not None:
                        embeds.append(kwargs["embed"])
                        if (file := kwargs.get("file")) is not None:
                            files.append(file)
                opened_days.append(None)
                await self.config.member(ctx.author).opened_days.set(opened_days)

        embeds.append(
            discord.Embed(
                color=await ctx.embed_color(),
            ).set_image(url="attachment://advent_calendar.png").set_footer(
                text=ctx.guild.name, icon_url=ctx.guild.icon,
            )
        )
        files.append(await self.generate_advent_calendar(today_day=today_day, opened_days=opened_days))
        await ctx.send(
            (
                content
                if not await self.config.guild(ctx.guild).include_opener_mention()
                else f"{ctx.author.mention} {content or ''}"
            ),
            embeds=embeds,
            files=files,
            reference=ctx.message.to_reference(fail_if_not_exists=False),
        )

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(aliases=["setac"])
    async def setadventcalendar(self, ctx: commands.Context) -> None:
        """Set up the Advent Calendar for your server."""
        pass

    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @setadventcalendar.command()
    async def rewards(self, ctx: commands.Context) -> None:
        """Set up the rewards for each day of the Advent Calendar."""
        await SetRewardsView(self).start(ctx)

    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @setadventcalendar.command()
    async def madvent(self, ctx: commands.Context, *, member: discord.Member = commands.Author) -> None:
        """Get the Advent Calendar for a member."""
        today = datetime.date.today()
        if not today.month == 12:
            raise commands.UserFeedbackCheckFailure(_("The Advent Calendar is only available in December."))
        opened_days = await self.config.member(member).opened_days()
        embed: discord.Embed = discord.Embed(
            title=_("Advent Calendar"),
            color=await ctx.embed_color(),
        )
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar,
        )
        embed.set_image(url="attachment://advent_calendar.png")
        await Menu(
            pages=[
                {
                    "embed": embed,
                    "file": await self.generate_advent_calendar(today_day=today.day, opened_days=opened_days),
                },
            ],
        ).start(ctx)

    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @setadventcalendar.command()
    async def mstats(self, ctx: commands.Context, *, member: discord.Member = commands.Author) -> None:
        """Get the stats of the Advent Calendar for a member."""
        today = datetime.date.today()
        if not today.month == 12:
            raise commands.UserFeedbackCheckFailure(_("The Advent Calendar is only available in December."))
        opened_days = await self.config.member(member).opened_days()
        embed = discord.Embed(
            title=_("Advent Calendar Stats"),
            color=discord.Color.green() if len(opened_days) == today.day else (discord.Color.orange() if opened_days else discord.Color.red()),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar,
        )
        embed.add_field(
            name=_("Opened Days:"),
            value="".join(
                "✅" if (day if day != 25 else None) in opened_days else "❌"
                for day in range(1, min(today.day, 25) + 1)
            ),
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        await Menu(pages=[embed]).start(ctx)

    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @setadventcalendar.command()
    async def stats(self, ctx: commands.Context) -> None:
        """Get the stats of the Advent Calendar for the server."""
        today = datetime.date.today()
        if not today.month == 12:
            raise commands.UserFeedbackCheckFailure(_("The Advent Calendar is only available in December."))
        members_data = await self.config.all_members(ctx.guild)
        opened_days = {
            member_id: data["opened_days"]
            for member_id, data in members_data.items()
        }
        total_boxes_opened = sum(len(data) for data in opened_days.values())
        members_all_boxes_opened = sum(len(data) == max(today.day, 25) for data in opened_days.values())
        boxes_opened: Counter = Counter(
            day
            for data in opened_days.values()
            for day in data
        )
        embed = discord.Embed(
            title=_("Advent Calendar Stats"),
            color=discord.Color.green() if members_all_boxes_opened else (discord.Color.orange() if total_boxes_opened else discord.Color.red()),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.add_field(
            name=_("Total Boxes Opened:"),
            value=_(
                "{total_boxes_opened} Boxe{s}"
            ).format(
                total_boxes_opened=total_boxes_opened,
                s="s" if total_boxes_opened != 1 else "",
            ),
            inline=True,
        )
        embed.add_field(
            name=_("Members with All Boxes Opened:"),
            value=_(
                "{members_all_boxes_opened} Member{s}"
            ).format(
                members_all_boxes_opened=members_all_boxes_opened,
                s="s" if members_all_boxes_opened != 1 else "",
            ),
            inline=True,
        )
        if today.day <= 25:
            embed.add_field(
                name=_("Today Boxes Opened:"),
                value=_(
                    "{today_boxes_opened} Boxe{s}"
                ).format(
                    today_boxes_opened=boxes_opened[today.day if today.day != 25 else None],
                    s="s" if boxes_opened[today.day] != 1 else "",
                ),
                inline=False,
            )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )

        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            font_color="white",  # White characters font.
            font_size=30,  # Characters font size.
            yaxis2={"overlaying": "y", "side": "right"},
        )
        x = list(range(1, min(today.day, 25) + 1))
        y = [
            boxes_opened[day]
            for day in x
        ]
        self.logger.critical(f"{x=}, {y=}")
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                line_color="rgb(0,255,0)",
                name=_("Opened Boxes"),
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
            width=1920,
            height=1080,
            scale=1,
        )
        buffer = io.BytesIO()
        buffer.write(graphic_bytes)
        buffer.seek(0)
        graphic = discord.File(buffer, filename="graphic.png")
        embed.set_image(url="attachment://graphic.png")

        await Menu(pages=[{"embed": embed, "file": graphic}]).start(ctx)

from AAA3A_utils import Cog, Loop, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import io
from copy import deepcopy

from PIL import Image, ImageDraw
import plotly.graph_objects as go

# Credits:
# General repo credits.

_ = Translator("PresenceChart", __file__)


@cog_i18n(_)
class PresenceChart(Cog):
    """A cog to make a chart with the different Discord statuses (presence) of a Discord user, in the previous x days (last 100 days maximum)!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.presencechart_global: typing.Dict[str, typing.List[int]] = {
            "ignored_users": [],
        }
        self.presencechart_user: typing.Dict[str, typing.List[typing.Tuple[typing.Literal["online", "dnd", "idle", "offline"], int]]] = {
            "presence_data": [],
        }
        self.config.register_global(**self.presencechart_global)
        self.config.register_user(**self.presencechart_user)

        self.presence_map: typing.Dict[typing.Literal["online", "dnd", "idle", "offline"], typing.Literal["Online", "Do Not Dirstub", "Idle", "Offline"]] = {
            "online": "Online",
            "dnd": "Do Not Disturb",
            "idle": "Idle",
            "offline": "Offline",
        }
        self.presence_data_cache: typing.Dict[int, typing.Tuple[int, typing.Tuple[discord.Status, discord.Status]]] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        self.loops.append(
            Loop(
                cog=self,
                name="Save PresenceChart Data",
                function=self.save_to_config,
                minutes=1,
            )
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all GuildStats data for user, members, roles, channels, categories, guilds; if the user ID matches."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        await self.save_to_config()  # To clean up the cache too.

        # Users.
        await self.config.user_from_id(user_id).clear()

        # Global.
        global_data = await self.config.all()
        if user_id in global_data["ignored_users"]:
            global_data["ignored_users"].remove(user_id)
        await self.config.set(global_data)

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        await self.save_to_config()  # To clean up the cache too.
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        # Users.
        user_data = await self.config.user_from_id(user_id).all()
        data[Config.USER] = {str(user_id): user_data}

        # Global.
        global_data = await self.config.all()
        if user_id in global_data["ignored_users"]:
            data[Config.GLOBAL]["ignored_users"] = [user_id]

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    async def generate_chart(self, user: typing.Union[discord.Member, discord.User], presence_timers: typing.Dict[typing.Literal["online", "idle", "do_not_disturb", "offline"], int], to_file: bool = True) -> typing.Union[Image.Image, discord.File]:
        img: Image.Image = Image.new("RGBA", (1600, 1000), (0, 0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, img.width, img.height), radius=50, fill=(32, 34, 37))

        fig = go.Figure()
        fig.update_layout(
            title_text=f"{user.display_name}'s Presence",
            title_x=0.5,
            title_xanchor="center",
            title_y=0.96,
            title_yanchor="middle",
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            font_color="white",  # White characters font.
            font_size=50,  # Characters font size.
            yaxis2={"overlaying": "y", "side": "right"},
        )
        # fig.add_layout_image(
        #     x=2.5,
        #     y=1.5,
        #     xanchor="center",
        #     yanchor="middle",
        #     sizex=2.5,
        #     sizey=2.5,
        #     xref="x",
        #     yref="y",
        #     opacity=1.0,
        #     layer="above",
        #     source=Image.open(io.BytesIO(await user.display_avatar.read())),
        # )
        fig.update_yaxes(showgrid=False)

        x_and_y = {self.presence_map[x]: presence_timers.get(x, 0) for x in self.presence_map}  #  + " " * (len("Do Not Disturb") - len(self.presence_map[x])) /  if x in presence_timers
        colors_map = {"Online": "#43b581", "Do Not Disturb": "#f04747", "Idle": "#fba31c", "Offline": "#747f8d"}
        colors = [colors_map[x] for x in x_and_y]  # .rstrip(" ")
        fig.add_trace(
            go.Pie(
                labels=list(x_and_y.keys()),
                values=list(x_and_y.values()),
                hole=0.8,
                textfont_size=50,
                textposition="inside",
                textfont={"color": "rgb(255,255,255)"},
                marker={"line": {"color": "rgb(0,0,0)", "width": 0}, "colors": colors},
                direction="clockwise",
            )
        )

        graphic_bytes: bytes = fig.to_image(
            format="png",
            width=img.width,
            height=img.height - 30,  # The title of the graphic...
            scale=1,
        )
        image = Image.open(io.BytesIO(graphic_bytes))
        img.paste(image, (0, 30, img.width, img.height), mask=image.split()[3])
        avatar_bytes: bytes = await user.display_avatar.read()
        image = Image.open(io.BytesIO(avatar_bytes))
        image = image.resize((400, 400))
        mask = Image.new("L", image.size, 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle(
            (0, 0, image.width, image.height),
            radius=40,
            fill=255,
        )
        img.paste(image, (img.width // 2 - 200 - 182, img.height // 2 - 200 + 25, img.width // 2 + 200 - 182, img.height // 2 + 200 + 25), mask=mask)
        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="image.png")

    async def save_to_config(self) -> None:
        all_presence_data = self.presence_data_cache.copy()
        self.presence_data_cache = {}
        for user_id, (time, data) in all_presence_data.items():
            presence_data = await self.config.user_from_id(user_id).presence_data()
            presence_data.append([time, data[1]])
            await self.config.user_from_id(user_id).presence_data.set(presence_data)
        # Run Cleanup
        await self.cleanup()

    async def cleanup(self) -> None:
        # Users.
        user_group = self.config._get_base_group(self.config.USER)
        async with user_group.all() as users_data:
            _users_data = deepcopy(users_data)
            for user_id in _users_data:
                if "presence_data" in _users_data[user_id]:
                    deleted_count = 0
                    for i, data in enumerate(_users_data[user_id]["presence_data"]):
                        changed_at = data[0]
                        if changed_at < int((datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=100)).timestamp()):
                            del users_data[user_id]["presence_data"][i - deleted_count]
                            deleted_count += 1
                    if not users_data[user_id]["presence_data"]:
                        del users_data[user_id]

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        """Handles a member updating their presence."""
        if not await self.bot.allowed_by_whitelist_blacklist(who=after):
            return
        ignored_users = await self.config.ignored_users()
        if after.id in ignored_users:
            return

        status = after.raw_status if after.raw_status in self.presence_map else "online"
        old_status = before.raw_status if before.raw_status in self.presence_map else "online"
        if status == old_status:
            return
        if after._user.id in self.presence_data_cache and self.presence_data_cache[after._user.id][1] == (old_status, status):  # Discord dispatches this event for every guild the user is in.
            return
        time = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        self.presence_data_cache[after._user.id] = (time, (old_status, status))

    @commands.bot_has_permissions(attach_files=True)
    @commands.hybrid_command(aliases=["statuschart", "statuseschart"])
    async def presencechart(self, ctx: commands.Context, days_number: typing.Optional[commands.Range[int, 1, 100]] = 30, *, member: discord.Member = commands.Author) -> None:
        """Make a chart with the different Discord statuses (presence) of a Discord user, in the previous x days (last 100 days maximum)."""
        ignored_users = await self.config.ignored_users()
        if member.id in ignored_users:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This user is in the ignored users list (`{prefix}presencechartignoreme`)."
                ).format(prefix=ctx.prefix)
            )
        presence_data = await self.config.user(member._user).presence_data()
        presence_timers: typing.Dict[typing.Literal["online", "dnd", "idle", "offline"], int] = {}
        if len(presence_data) <= 1:  # In this case, `member.raw_status` should be the same than in Config.
            presence_timers[member.raw_status if member.raw_status in self.presence_map else "online"] = 100
        else:
            time_delta = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_number)
            for i, data in enumerate(presence_data):
                changed_at, status = data[0], data[1]
                if days_number is not None:
                    time_delta = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_number)
                    time_delta_timestamp = int(time_delta.timestamp())  # Convert datetime to timestamp
                    if changed_at < time_delta_timestamp:
                        continue
                if i != 0:
                    if status not in presence_timers:
                        presence_timers[status] = 0
                    presence_timers[status] += (changed_at - presence_data[i - 1][0])
        file: discord.File = await self.generate_chart(user=member, presence_timers=presence_timers, to_file=True)
        await Menu(pages=[{"file": file}]).start(ctx)

    @commands.command()
    async def presencechartignoreme(self, ctx: commands.Context) -> None:
        """Asking PresenceChart to ignore your statuses (presence)."""
        user = ctx.author
        ignored_users: typing.List[int] = await self.config.ignored_users()
        if user.id not in ignored_users:
            ignored_users.append(user.id)
            await self.red_delete_data_for_user(requester="user", user_id=user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(
                _(
                    "You will no longer be seen by this cog and the data I held on you have been deleted."
                )
            )
        else:
            ignored_users.remove(user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(_("You'll be seen again by this cog."))

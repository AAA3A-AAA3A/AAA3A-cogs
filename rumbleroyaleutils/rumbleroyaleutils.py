from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import re

from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.menus import start_adding_reactions

from .types import PlayerApparition, RumbleRoyale
from .view import AmIAliveView

# Credits:
# General repo credits.

_: Translator = Translator("RumbleRoyaleUtils", __file__)

RUMBLE_BOT_ID: int = 693167035068317736


def clean_embed_description(description: str) -> str:
    return re.sub(r":.*?:", "", re.sub(r"<a?:.+?:\d+>", "", description)).replace(" | ", "")


def clean_name(name: str) -> str:
    return name.split(" ")[0].replace("\\", "")


@cog_i18n(_)
class RumbleRoyaleUtils(Cog):
    """Allow Rumble Royale players to check easely if they are alive or not and ping the host when a Rumble Royale ends!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            am_i_alive=False,
            ping_players_on_death=False,
            ping_host_on_end=False,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "am_i_alive": {
                "converter": bool,
                "description": "Enable or disable the am I alive feature.",
            },
            "ping_players_on_death": {
                "converter": bool,
                "description": "Enable or disable the ping players on death feature.",
            },
            "ping_host_on_end": {
                "converter": bool,
                "description": "Enable or disable the ping host on end feature.",
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
            commands_group=self.setrumbleroyaleutils,
        )

        self.rumbles: typing.Dict[discord.abc.GuildChannel, RumbleRoyale] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.guild is None or await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ):
            return
        if not message.author.bot or message.author.id != RUMBLE_BOT_ID:
            return
        if message.application_id is not None:
            await asyncio.sleep(2)
            message = await message.channel.fetch_message(message.id)
        if not message.embeds:
            return
        embed = message.embeds[0]
        if embed.title is None:
            return
        config = await self.config.guild(message.guild).all()
        if "Rumble Royale hosted by " in embed.title:
            self.rumbles[message.channel] = RumbleRoyale(
                first_message=message,
                host=discord.utils.get(message.guild.members, name=embed.title.split(" ")[-1]),
            )
        elif (rumble := self.rumbles.get(message.channel)) is not None:
            if "Started a new Rumble Royale session" in embed.title:
                rumble.first_message = await message.channel.fetch_message(rumble.first_message.id)
                rumble.players = {
                    member: []
                    async for member in next(
                        (
                            reaction
                            for reaction in rumble.first_message.reactions
                            if isinstance(reaction.emoji, discord.PartialEmoji)
                            # and reaction.emoji.id in (1371131643569635348, 1374771017569800233, 1387054688477642782)
                        )
                    ).users()
                    if not member.bot
                }
                # if config["am_i_alive"]:
                #     await message.reply(
                #         embed=discord.Embed(
                #             title=_("Quick Tip"),
                #             description=_(
                #                 "You can check if you are dead or not by sending `Am I dead?`/`Dead` in this channel."
                #             ),
                #             color=await self.bot.get_embed_color(message.channel),
                #         ),
                #     )

            elif rumble.is_started:
                if "Round " in embed.title:
                    round_number = int(
                        embed.title.replace("*", "").replace("_", "").strip().split(" ")[1]
                    )
                    if config["am_i_alive"]:
                        view: AmIAliveView = AmIAliveView(self)
                        view._message = await message.reply(
                            _("Click on the button below to see if you are alive or dead!"),
                            view=view,
                        )
                        self.views[view._message] = view
                        rumble.views.append(view)
                    embed.description = clean_embed_description(embed.description)
                    events = embed.description.split("\n\n")[0].split("\n")
                    round_victims = []
                    for event in events:
                        try:
                            victim_name = clean_name(event.split("~~**")[1].split("**~~")[0])
                        except IndexError:
                            victim_name = None
                        try:
                            killer_name = clean_name(event.replace("~~**", "....").split("**")[1])
                        except IndexError:
                            killer_name = None
                        killer = (
                            discord.utils.get(rumble.players, name=killer_name)
                            if killer_name is not None
                            else None
                        )
                        if victim_name is not None:
                            victim = discord.utils.get(rumble.players, name=victim_name)
                        else:
                            alive = True
                            for event in rumble.players[killer]:
                                alive = event.type != "death"
                            if not alive:
                                rumble.players[killer].append(
                                    PlayerApparition(
                                        round_number=round_number,
                                        type="revive",
                                        cause=event,
                                        message=message,
                                    )
                                )
                            else:
                                rumble.players[killer].append(
                                    PlayerApparition(
                                        round_number=round_number,
                                        type="apparition",
                                        cause=event,
                                        message=message,
                                    )
                                )
                            continue
                        if killer is not None:
                            rumble.players[killer].append(
                                PlayerApparition(
                                    round_number=round_number,
                                    type="kill",
                                    cause=event,
                                    message=message,
                                    other=victim,
                                )
                            )
                        rumble.players[victim].append(
                            PlayerApparition(
                                round_number=round_number,
                                type="death",
                                cause=event,
                                message=message,
                                other=killer,
                            )
                        )
                        round_victims.append(victim)
                    if config["ping_players_on_death"] and round_victims:
                        await message.channel.send(
                            (
                                _("{victims} are dead!")
                                if len(round_victims) > 1
                                else _("{victims} is dead!")
                            ).format(
                                victims=humanize_list(
                                    [victim.mention for victim in round_victims]
                                ),
                            )
                        )

                elif "WINNER!" in embed.title:
                    if config["ping_host_on_end"]:
                        await message.channel.send(
                            _("{host.mention} The Rumble Royale has ended!").format(
                                host=rumble.host,
                            )
                        )
                    start_adding_reactions(message, ("✅",))
                    del self.rumbles[message.channel]
                    for view in rumble.views:
                        await view.on_timeout()

    # @commands.Cog.listener(name="on_message_without_command")
    # async def on_message_without_command_2(self, message: discord.Message) -> None:
    #     if message.webhook_id is not None:
    #         return
    #     if message.guild is None:
    #         return
    #     if await self.bot.cog_disabled_in_guild(
    #         cog=self, guild=message.guild
    #     ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
    #         return
    #     if message.author.bot:
    #         return
    #     if (rumble := self.rumbles.get(message.channel)) is None:
    #         return
    #     if not rumble.is_started:
    #         return
    #     if message.content.lower().rstrip("?") in ["am i dead", "dead"]:
    #         if not await self.config.guild(message.guild).am_i_alive():
    #             return
    #         if ...:
    #             start_adding_reactions(message, ("💀",))
    #         elif ...:
    #             start_adding_reactions(message, ("❌",))
    #         else:
    #             start_adding_reactions(message, ("💥",))
    #             await message.reply(
    #                 embed=discord.Embed(
    #                     title=_("You are not in the game!"),
    #                     color=await self.bot.get_embed_color(message.channel),
    #                 ),
    #                 delete_after=3,
    #             )

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setrumbleroyaleutils(self, ctx: commands.Context) -> None:
        """Settings for the RumbleRoyaleUtils cog."""
        pass

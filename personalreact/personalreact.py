from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from copy import deepcopy

from .converter import Emoji
from .dashboard_integration import DashboardIntegration
from .views import PersonalReactView, SettingsView

# Credits:
# General repo credits.

_: Translator = Translator("PersonalReact", __file__)


@cog_i18n(_)
class PersonalReact(DashboardIntegration, Cog):
    """Make the bot react to messages with your mention, reply or your custom trigger, based on roles perks!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            max_reactions_per_member=5,
            min_custom_trigger_length=3,
            blacklisted_channels=[],
            always_allow_custom_trigger=False,
            base_roles_requirements={},
            custom_trigger_roles_requirements={},
        )
        self.config.register_member(
            enabled=False,
            reactions=[],
            replies=False,
            custom_trigger=None,
            ignore_myself=True,
            ignore_bots=True,
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "max_reactions_per_member": {
                "converter": commands.Range[int, 1, 8],
                "description": "The maximum number of reactions a member can set for them.",
            },
            "min_custom_trigger_length": {
                "converter": commands.Range[int, 3, 8],
                "description": "The minimum length of a custom trigger.",
            },
            "blacklisted_channels": {
                "converter": typing.Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.Thread],
                "description": "The channels where the bot won't react.",
            },
            "always_allow_custom_trigger": {
                "converter": bool,
                "description": "Whether to always allow the custom trigger feature.",
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
            commands_group=self.setpersonalreact,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all PersonalReact data for a user."""
        if requester not in ("discord_deleted_user", "owner", "user", "user_strict"):
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data.copy():
                if str(user_id) in members_data[guild]:
                    del members_data[guild][str(user_id)]
                if not members_data[guild]:
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

    async def get_reactions(self, member: discord.Member, _type: typing.Literal["base", "custom_trigger"]) -> typing.Tuple[typing.List[typing.Union[str, discord.Emoji]], int, int, bool, typing.Dict[discord.Role, int]]:
        reactions = await self.config.member(member).reactions()
        max_reactions_per_member = await self.config.guild(member.guild).max_reactions_per_member()
        if _type == "base":
            _roles_requirements = await self.config.guild(member.guild).base_roles_requirements()
        else:
            _roles_requirements = await self.config.guild(member.guild).custom_trigger_roles_requirements()
        roles_requirements = {}
        for role_id, amount in sorted(_roles_requirements.items(), key=lambda x: x[1]):
            if (role := member.guild.get_role(int(role_id))) is not None:
                if role in roles_requirements:
                    continue
                roles_requirements[role] = amount
        total_amount = sum(roles_requirements.values())
        is_staff = member.id in self.bot.owner_ids or await self.bot.is_admin(member) or member.guild.get_member(member.id).guild_permissions.administrator
        if is_staff:
            total_amount = max_reactions_per_member
        if (always_allow_custom_trigger := await self.config.guild(member.guild).always_allow_custom_trigger()) and _type == "custom_trigger":
            total_amount += (await self.get_reactions(member, "base"))[1]
        reactions = [
            reaction
            for r in reactions
            if (reaction := (r if isinstance(r, str) else self.bot.get_emoji(r))) is not None
        ]
        return reactions[:total_amount], total_amount, max_reactions_per_member, is_staff, always_allow_custom_trigger, roles_requirements
        

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.webhook_id is not None:
            return
        if message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if (
            await self.bot.cog_disabled_in_guild(cog=self, guild=message.guild)
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
        ):
            return
        blacklisted_channels = await self.config.guild(message.guild).blacklisted_channels()
        if message.channel.id in await self.config.guild(message.guild).blacklisted_channels() or message.channel.category_id in blacklisted_channels:
            return
        member = None
        members_data = await self.config.all_members(guild=message.guild)
        for m_id, data in members_data.items():
            _type = "base"
            if (
                data.get("enabled", False)
                and (
                    message.author.id != int(m_id)
                    or not data.get("ignore_myself", False)
                )
                and (
                    not message.author.bot
                    or not data.get("ignore_bots", True)
                )
                and (
                    (
                        discord.utils.get(message.mentions, id=m_id) is not None
                        and m_id in message.raw_mentions
                    )
                    or (
                        data.get("replies", False)
                        and m_id in message.raw_mentions
                    )
                    or (
                        (custom_trigger := data.get("custom_trigger")) is not None
                        and custom_trigger.lower() in message.content.lower().split(" ")
                        and (_type := "custom_trigger")
                    )
                )
                and (m := message.guild.get_member(int(m_id))) is not None
                and await self.bot.allowed_by_whitelist_blacklist(who=m)
            ):
                if not (reactions := (await self.get_reactions(m, _type))[0]):
                    continue
                if member is not None:
                    return
                member = m
        if member is None:
            return
        for reaction in reactions:
            try:
                await message.add_reaction(reaction)
            except discord.NotFound:
                reactions = members_data[str(member.id)]["reactions"]
                reactions.remove(getattr(reaction, "id", reaction))
                if reactions:
                    await self.config.member(member).reactions.set(reactions)
                else:
                    await self.config.member(member).reactions.clear()
                    await self.config.member(member).enabled.set(False)
            except discord.HTTPException:
                pass

    @commands.guild_only()
    @commands.hybrid_group(aliases=["pr"])
    async def personalreact(self, ctx: commands.Context) -> None:
        """Make the bot react to messages with your mention, reply or your custom trigger!"""
        pass

    @personalreact.command()
    async def view(self, ctx: commands.Context) -> None:
        """View your PersonalReact settings."""
        await PersonalReactView(cog=self).start(ctx)

    @personalreact.command()
    async def enable(self, ctx: commands.Context) -> None:
        """Enable PersonalReact for you."""
        if (await self.get_reactions(ctx.author, "base"))[1] == 0 and (await self.get_reactions(ctx.author, "custom_trigger"))[1] == 0:
            raise commands.UserFeedbackCheckFailure(_("You aren't elligible for using PersonalReact."))
        if not await self.config.member(ctx.author).reactions():
            raise commands.UserFeedbackCheckFailure(_("You don't have any reaction set."))
        await self.config.member(ctx.author).enabled.set(True)

    @personalreact.command()
    async def disable(self, ctx: commands.Context) -> None:
        """Disable PersonalReact for you."""
        await self.config.member(ctx.author).enabled.set(False)

    @personalreact.command()
    async def replies(self, ctx: commands.Context, toggle: bool) -> None:
        """Allow the bot to react on the messages which ping you in replies."""
        await self.config.member(ctx.author).replies.set(toggle)

    @personalreact.command()
    async def customtrigger(self, ctx: commands.Context, custom_trigger: str) -> None:
        """Set a custom trigger."""
        if (await self.get_reactions(ctx.author, "custom_trigger"))[1] == 0:
            raise commands.UserFeedbackCheckFailure(_("You aren't elligible for using the custom trigger feature."))
        if len(custom_trigger) < (min_custom_trigger_length := await self.config.guild(ctx.guild).min_custom_trigger_length()):
            raise commands.UserFeedbackCheckFailure(_("The custom trigger must be at least {min_custom_trigger_length} characters long.").format(min_custom_trigger_length=min_custom_trigger_length))
        if " " in custom_trigger:
            raise commands.UserFeedbackCheckFailure(_("The custom trigger can't have spaces."))
        await self.config.member(ctx.author).custom_trigger.set(custom_trigger)

    @personalreact.command(aliases=["reacts"])
    async def reactions(self, ctx: commands.Context, reactions: commands.Greedy[Emoji]) -> None:
        """Set your reactions."""
        if (await self.get_reactions(ctx.author, "base"))[1] == 0 and (await self.get_reactions(ctx.author, "custom_trigger"))[1] == 0:
            raise commands.UserFeedbackCheckFailure(_("You aren't elligible for using PersonalReact."))
        if not reactions:
            await self.config.member(ctx.author).reactions.clear()
            await self.config.member(ctx.author).enabled.set(False)
            return
        if len(reactions) > (max_reactions_per_member := (await self.config.guild(ctx.guild).max_reactions_per_member())):
            raise commands.UserFeedbackCheckFailure(_("You can't have more than {max_reactions_per_member} reactions.").format(max_reactions_per_member=max_reactions_per_member))
        await self.config.member(ctx.author).reactions.set([getattr(reaction, "id", reaction) for reaction in reactions])

    @personalreact.command(aliases=["addreacts"])
    async def addreactions(self, ctx: commands.Context, reactions: commands.Greedy[Emoji]) -> None:
        """Add reaction(s)."""
        if (await self.get_reactions(ctx.author, "base"))[1] == 0 and (await self.get_reactions(ctx.author, "custom_trigger"))[1] == 0:
            raise commands.UserFeedbackCheckFailure(_("You aren't elligible for using PersonalReact."))
        if not reactions:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one reaction."))
        _reactions = await self.config.member(ctx.author).reactions()
        _reactions.extend([getattr(reaction, "id", reaction) for reaction in reactions])
        if len(_reactions) > (max_reactions_per_member := (await self.config.guild(ctx.guild).max_reactions_per_member())):
            raise commands.UserFeedbackCheckFailure(_("You can't have more than {max_reactions_per_member} reactions.").format(max_reactions_per_member=max_reactions_per_member))
        await self.config.member(ctx.author).reactions.set(_reactions)

    @personalreact.command(aliases=["removereacts"])
    async def removereactions(self, ctx: commands.Context, reactions: commands.Greedy[Emoji]) -> None:
        """Remove reaction(s)."""
        if not reactions:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one reaction."))
        _reactions = await self.config.member(ctx.author).reactions()
        for reaction in reactions:
            _reactions.remove(reaction)
        await self.config.member(ctx.author).reactions.set(_reactions)

    @personalreact.command()
    async def ignoremyself(self, ctx: commands.Context, toggle: bool) -> None:
        """Ignore yourself."""
        await self.config.member(ctx.author).ignore_myself.set(toggle)

    @personalreact.command()
    async def ignorebots(self, ctx: commands.Context, toggle: bool) -> None:
        """Ignore bots."""
        await self.config.member(ctx.author).ignore_bots.set(toggle)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(aliases=["setpr"])
    async def setpersonalreact(self, ctx: commands.Context) -> None:
        """Set PersonalReact settings."""
        pass

    @commands.bot_has_permissions(embed_links=True)
    @setpersonalreact.command(aliases=["view"])
    async def roles(self, ctx: commands.Context) -> None:
        """Set the roles requirements."""
        await SettingsView(cog=self).start(ctx)

    @setpersonalreact.command(aliases=["addbaserolerequirement", "addbaserolesreq", "addbaserolereq"])
    async def addbaserolesrequirements(
        self,
        ctx: commands.Context,
        roles: commands.Greedy[discord.Role],
        amount: commands.Range[int, 1, 8],
    ) -> None:
        """Add base roles requirements."""
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one role."))
        base_roles_requirements = await self.config.guild(ctx.guild).base_roles_requirements()
        for role in roles:
            base_roles_requirements[str(role.id)] = amount
        if len(base_roles_requirements) > 25:
            raise commands.UserFeedbackCheckFailure(_("You can't have more than 25 base roles requirements."))
        await self.config.guild(ctx.guild).base_roles_requirements.set(base_roles_requirements)

    @setpersonalreact.command(aliases=["removebaserolerequirement", "removebaserolesreq", "removebaserolereq"])
    async def removebaserolesrequirements(
        self,
        ctx: commands.Context,
        roles: commands.Greedy[discord.Role],
    ) -> None:
        """Remove base roles requirements."""
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one role."))
        base_roles_requirements = await self.config.guild(ctx.guild).base_roles_requirements()
        for role in roles:
            if str(role.id) in base_roles_requirements:
                del base_roles_requirements[str(role.id)]
        await self.config.guild(ctx.guild).base_roles_requirements.set(base_roles_requirements)

    @setpersonalreact.command(aliases=["addctrolerequirement", "addctrolesreq", "addctrolereq"])
    async def addctrolesrequirements(
        self,
        ctx: commands.Context,
        roles: commands.Greedy[discord.Role],
        amount: commands.Range[int, 1, 8],
    ) -> None:
        """Add custom trigger roles requirements."""
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one role."))
        custom_trigger_roles_requirements = await self.config.guild(ctx.guild).custom_trigger_roles_requirements()
        for role in roles:
            custom_trigger_roles_requirements[str(role.id)] = amount
        if len(custom_trigger_roles_requirements) > 25:
            raise commands.UserFeedbackCheckFailure(_("You can't have more than 25 custom trigger roles requirements."))
        await self.config.guild(ctx.guild).custom_trigger_roles_requirements.set(custom_trigger_roles_requirements)

    @setpersonalreact.command(aliases=["removectrolerequirement", "removectrolesreq", "removectrolereq"])
    async def removectrolesrequirements(
        self,
        ctx: commands.Context,
        roles: commands.Greedy[discord.Role],
    ) -> None:
        """Remove custom trigger roles requirements."""
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You need to provide at least one role."))
        custom_trigger_roles_requirements = await self.config.guild(ctx.guild).custom_trigger_roles_requirements()
        for role in roles:
            if str(role.id) in custom_trigger_roles_requirements:
                del custom_trigger_roles_requirements[str(role.id)]
        await self.config.guild(ctx.guild).custom_trigger_roles_requirements.set(custom_trigger_roles_requirements)

    @setpersonalreact.command()
    async def clearmember(self, ctx: commands.Context, *, member: discord.Member) -> None:
        await self.config.member(member).clear()

    @setpersonalreact.command(hidden=True)
    async def purge(self, ctx: commands.Context, confirmation: bool = False) -> None:
        if not confirmation:
            raise commands.UserInputError()
        await self.config.guild(ctx.guild).clear()
        await self.config.clear_all_members(guild=ctx.guild)

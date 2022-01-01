import asyncio
import discord
from discord.ext.commands import BadArgument
import typing
from redbot.core import Config, commands
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.commands.converter import parse_timedelta
from copy import copy
from dislash import InteractionClient, Option, OptionType, message_command, slash_command, user_command
from .utils import utils, Timeout_or_Cancel
from .settings import settings

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to Laggrons-dumb's WarnSystem cog (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/warnsystem) for giving me some ideas and code for subcommands for a main command!
# Thanks to @Aikaterna on the Redbot support server for help on displaying the main command help menu and other commands!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class SimpleSanction(settings, commands.Cog):
    """A cog to sanction a user!"""

    def __init__(self, bot):
        self.bot = bot
        test = settings.test
        inter_client = InteractionClient(bot)
        self.data: Config = Config.get_conf(
            self,
            identifier=793615829052,
            force_registration=True,
        )
        self.sanction_guild = {
            "color": 0xf00020,
            "thumbnail": "https://i.imgur.com/Bl62rGd.png",
            "show_author": True,
            "action_confirmation": True,
            "finish_message": True,
            "warn_system_use": True,
            "buttons_use": True,
            "reason_required": True,
            "delete_embed": True,
            "delete_message": True,
            "timeout": 180,
        }

        self.data.register_guild(**self.sanction_guild)

    def check_timedelta(string):
        try:
            delta = parse_timedelta(string)
        except BadArgument:
            raise BadArgument()
        else:
            if delta is not None:
                return string
            else:
                raise BadArgument()

    @user_command(name="Sanction user")
    async def sanctionusermenu(self, inter):
        try:
            message = await inter.channel.send("Sanction.")
            p = await inter.bot.get_valid_prefixes()
            p = p[0]
            msg = copy(message)
            msg.author = inter.author
            msg.channel = inter.channel
            msg.content = f"{p}sanction {inter.user.id}"
            self.bot.dispatch("message", msg)
            self.bot.process_commands(msg)
            await inter.respond(f"You have chosen to sanction {inter.user.mention} ({inter.user.id}) in {inter.channel.mention}.", ephemeral=True)
        except Exception:
            await inter.respond("An error has occurred in your interaction. Please try to use the real command instead of this contextual menu.", ephemeral=True)

    @message_command(name="Sanction author")
    async def sanctionmessagemenu(self, inter):
        try:
            message = await inter.channel.send("Sanction.")
            p = await inter.bot.get_valid_prefixes()
            p = p[0]
            msg = copy(message) 
            msg.author = inter.author
            msg.channel = inter.channel
            msg.content = f"{p}sanction {inter.message.author.id}"
            self.bot.dispatch("message", msg)
            self.bot.process_commands(msg)
            await inter.respond(f"You have chosen to sanction {inter.message.author.mention} ({inter.message.author.id}) in {inter.channel.mention}.", ephemeral=True)
        except Exception:
            await inter.respond("An error has occurred in your interaction. Please try to use the real command instead of this contextual menu.", ephemeral=True)

    @slash_command(name="sanction", description="Sanction user", options=[Option("user", "Enter the user.", OptionType.USER, required=True), Option("confirmation", "test", OptionType.BOOLEAN, required=False), Option("show_author", "test", OptionType.BOOLEAN, required=False), Option("finish_message", "test", OptionType.BOOLEAN, required=False), Option("fake_action", "test", OptionType.BOOLEAN, required=False), Option("args", "Enter the arguments of the command.", OptionType.STRING, required=False)])
    async def sanctionslash(self, inter, user, confirmation: typing.Optional[bool]="", show_author: typing.Optional[bool]="", finish_message: typing.Optional[bool]="", fake_action: typing.Optional[bool]="", args: typing.Optional[str]=""):
        try:
            message = await inter.channel.send("Sanction.")
            p = await inter.bot.get_valid_prefixes()
            p = p[0]
            msg = copy(message)
            msg.author = inter.author
            msg.channel = inter.channel
            if not confirmation == "": confirmation = f" {confirmation}"
            if not show_author == "": show_author = f" {show_author}"
            if not finish_message == "": finish_message = f" {finish_message}"
            if not fake_action == "": fake_action = f" {fake_action}"
            if not args == "": args = f" {args}"
            msg.content = f"{p}sanction {user.id}{confirmation}{show_author}{finish_message}{fake_action}{args}"
            self.bot.dispatch("message", msg)
            self.bot.process_commands(msg)
            await inter.respond(f"You have chosen to sanction {user.mention} ({user.id}) in {inter.channel.mention}.", ephemeral=True)
        except Exception:
            await inter.respond("An error has occurred in this interaction. Please try to use the real command instead of this contextual menu.", ephemeral=True)

    @commands.group(invoke_without_command=True, name="sanction", aliases=["punishuser"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    @commands.guild_only()
    @commands.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    async def _sanction(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
        Sanction a user quickly and easily.

        All arguments are optional and will be requested during the course of the action if necessary.
        For "Confirmation", "Show_author" and "finish_message", a `true` or `false` is expected.
        In this order, you must put the arguments and it is mandatory to specify the ones before if you want to specify one after.

        ``user``: Server member.			    Who is the user concerned?
        ``confirmation``: True or False.		Do you want the bot to ask for confirmation from you before the action? (Default is the recorded value)
        ``show_author``: True or False.			Do you want the bot to show in its embeds who is the author of the command/sanction? (Default is the recorded value)
        ``finish_message``: True or False.		Do you want the bot to show an embed just before the action summarising the action and giving the sanctioned user and the reason? (Default is the recorded value)
        ``fake_action``: True or False.		    Do you want the command to do everything as usual, but (unintentionally) forget to execute the action?
        ``duration``: Duration. (5d, 8h, 1m...)	If you choose a TempBan, TempMute or TempMuteChanne, this value will be used for the duration of that action.
        ``reason``: Text.				        The reason for this action. (`not` to not specify one, unless the reason has been made falcutative in the parameters)

        Short version: [p]sanction
        Long version:  [p]sanction 10 @user true true true true true true 3d Spam.
        """
        await self.call_sanction(ctx, 0, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="01", aliases=["1","userinfo","info"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_1(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :information_source: Show info on a user.

        Examples:
        - `[p]sanction 1 @user`: UserInfo for no reason
        - `[p]sanction 1 @user What are these roles?`: Ban for the reason "What are these roles?"
        - `[p]sanction 1 012345678987654321`: UserInfo with the ID provided.
        """
        await self.call_sanction(ctx, 1, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="02", aliases=["2","warn"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_2(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :warning: Set a simple warning on a user.

        Examples:
        - `[p]sanction 2 @user not`: Warn for no reason
        - `[p]sanction 2 @user Insults`: Warn for the reason "Insults"
        - `[p]sanction 2 012345678987654321 Advertising`: Warn the user with the ID provided.
        """
        await self.call_sanction(ctx, 2, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="03", aliases=["3","ban"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_3(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :hammer: Ban the member from the server.

        It won't delete messages by default.

        Examples:
        - `[p]sanction 3 @user not`: Ban for no reason
        - `[p]sanction 3 @user Insults`: Ban for the reason "Insults"
        - `[p]sanction 3 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(ctx, 3, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="04", aliases=["4","softban"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_4(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :repeat_one: Softban the member from the server.

        This means that the user will be banned and immediately unbanned, so it will purge their messages in all channels.

        Examples:
        - `[p]sanction 4 @user not`: SoftBan for no reason
        - `[p]sanction 4 @user Insults`: SoftBan for the reason "Insults"
        - `[p]sanction 4 012345678987654321 Advertising`: SoftBan the user with the ID provided.
        """
        await self.call_sanction(ctx, 4, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="05", aliases=["5","tempban"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_5(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :dash: Tempban the member from the server.

        It won't delete messages by default.

        If you want to perform a temporary ban, provide the time before the reason.

        Examples:
        - `[p]sanction 5 @user not`: Ban for no reason
        - `[p]sanction 5 @user 7d Insults`: 7 days ban for the reason "Insults"
        - `[p]sanction 5 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(ctx, 5, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="06", aliases=["6","kick"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_6(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :boot: Kick the member from the server.

        Examples:
        - `[p]sanction 6 @user not`: Kick for no reason
        - `[p]sanction 6 @user Insults`: Kick for the reason "Insults"
        - `[p]sanction 6 012345678987654321 Advertising`: Kick the user with the ID provided.
        """
        await self.call_sanction(ctx, 6, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="07", aliases=["7","mute"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_6(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :mute: Mute the user in all channels, including voice channels.

        Examples:
        - `[p]sanction 7 @user not`: Infinite mute for no reason
        - `[p]sanction 7 @user Spam`:Infinite  mute for the reason "Spam"
        - `[p]sanction 7 @user Advertising`: Infinite mute for the reason "Advertising"
        """
        await self.call_sanction(ctx, 7, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="08", aliases=["8","mutechannel"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_8(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :punch: Mute the user in this channel.

        Examples:
        - `[p]sanction 8 @user not`: Infinite mute for no reason
        - `[p]sanction 8 @user Spam`: Infinite mute for the reason "Spam"
        - `[p]sanction 8 @user Advertising`: Infinite mute for the reason "Advertising"
        """
        await self.call_sanction(ctx, 8, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="09", aliases=["9","tempmute"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")
    async def sanction_9(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :hourglass_flowing_sand: TempMute the user in all channels, including voice channels.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 9 @user 30m not`: 30 minutes mute for no reason
        - `[p]sanction 9 @user 5h Spam`: 5 hours mute for the reason "Spam"
        - `[p]sanction 9 @user 3d Advertising`: 3 days mute for the reason "Advertising"
        """
        await self.call_sanction(ctx, 9, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    @_sanction.command(name="10", aliases=["tempmutechannel"], usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]")

    async def sanction_10(self, ctx, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, *, reason: str = None):
        """
         - :hourglass: TempMute the user in this channel.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 10 @user 30m not`: 30 minutes mute for no reason
        - `[p]sanction 10 @user 5h Spam`: 5 hours mute for the reason "Spam"
        - `[p]sanction 10 @user 3d Advertising`: 3 days mute for the reason "Advertising"
        """
        await self.call_sanction(ctx, 10, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

    @commands.guild_only()
    async def call_sanction(self, ctx, action: typing.Optional[int]=None, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, reason: str = None):
        """Sanction a user quickly and easily.
        """
        config = await self.data.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        actual_show_author = config["show_author"]
        actual_action_confirmation = config["action_confirmation"]
        actual_finish_message = config["finish_message"]
        actual_warn_system_use = config["warn_system_use"]
        actual_buttons_use = config["buttons_use"]
        actual_reason_required = config["reason_required"]
        actual_delete_embed = config["delete_embed"]
        actual_delete_message = config["delete_message"]
        actual_timeout = config["timeout"]
        if ctx.bot.get_cog("WarnSystem"):
            if actual_warn_system_use:
                warn_system_exist = True
            else:
                warn_system_exist = False
        else:
            warn_system_exist = False
        if action == 0:
            action = None
        if confirmation is None:
            confirmation = actual_action_confirmation
        if show_author is None:
            show_author = actual_show_author
        if finish_message is None:
            finish_message = actual_finish_message
        if delete_embed is None:
            delete_embed = actual_delete_embed
        if delete_message is None:
            delete_message = actual_delete_message
        if reason is not None:
            if reason.lower() == "not":
                reason = "not"
        if delete_message and ctx.author == ctx.message.author:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        if user is None:
            embed: discord.Embed = discord.Embed()
            embed.title = "Sanctioning a member"
            embed.description = "Which member do you want to sanction? (Set `cancel` to cancel.)"
            embed.color = actual_color
            message = await ctx.send(embed=embed)
            try:
                pred = MessagePredicate.valid_member(ctx)
                msg = await self.bot.wait_for(
                    "message",
                    timeout=actual_timeout,
                    check=pred,
                )
                if msg.content.lower() == "cancel":
                    await message.delete()
                    await msg.delete()
                    return
                await message.delete()
                await msg.delete()
                user = pred.result
            except asyncio.TimeoutError:
                await ctx.send("Timed out, please try again.")
                return

        if action is None:
            embed: discord.Embed = discord.Embed()
            embed.title = "Sanctioning a member"
            embed.description = f"This tool allows you to easily sanction a server member.\nUser mention: {user.mention} - User ID: {user.id}"
            embed.set_thumbnail(url=actual_thumbnail)
            embed.color = actual_color
            embed.set_author(name=user, url=user.avatar_url, icon_url=user.avatar_url)
            if show_author:
                embed.set_footer(text=ctx.author, icon_url=ctx.author.avatar_url)
            embed.add_field(
                inline=False,
                name="Possible actions:",
                value=f":information_source: UserInfo - :warning: Warn - :hammer: Ban - :repeat_one: SoftBan - :dash: TempBan\n:boot: Kick - :mute: Mute - :punch: MuteChannel - :hourglass_flowing_sand: TempMute\n:hourglass: TempMuteChannel - :x: Cancel")
            if reason == "not":
                 embed.add_field(
                    inline=False,
                    name="Reason:",
                    value=f"The reason was not given and will not be asked later.")
            else:
                if not reason is None:
                    embed.add_field(
                        inline=False,
                        name="Reason:",
                        value=f"{reason}")
            if not duration is None:
                embed.add_field(
                    inline=False,
                    name="Duration:",
                    value=f"{parse_timedelta(duration)}")
            reactions, buttons_one, buttons_two, buttons_three = await utils.emojis()
            if actual_buttons_use:
                message = await ctx.send(embed=embed, components=[buttons_one, buttons_two, buttons_three])
            else:
                message = await ctx.send(embed=embed)
                start_adding_reactions(message, reactions)
            # "\N{information_source}", "\N{warning}", "\N{hammer}", "\N{repeat_one}", "\N{dash}", "\N{boot}", "\N{mute}", "\N{hourglass_flowing_sand}", "\N{punch}", "\N{x}"
            end_reaction = False

        if action is not None:
            await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)

        if action is None and not actual_buttons_use:
            def check(reaction, abc_author):
                return abc_author == ctx.author or abc_author.id in ctx.bot.owner_ids and str(reaction.emoji) in reactions
                # This makes sure nobody except the command sender can interact with the "menu"
            while True:
                try:
                    reaction, abc_author = await ctx.bot.wait_for("reaction_add", timeout=actual_timeout, check=check)
                    # waiting for a reaction to be added - times out after x seconds, 30 in this
                    if str(reaction.emoji) == "ℹ️":
                        end_reaction = True
                        action = 1
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "⚠️":
                        end_reaction = True
                        action = 2
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "🔨":
                        end_reaction = True
                        action = 3
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "🔂":
                        end_reaction = True
                        action = 4
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "💨":
                        end_reaction = True
                        action = 5
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "👢":
                        end_reaction = True
                        action = 6
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "🔇":
                        end_reaction = True
                        action = 7
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "👊":
                        end_reaction = True
                        action = 8
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "⏳":
                        end_reaction = True
                        action = 9
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "⌛":
                        end_reaction = True
                        action = 10
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    elif str(reaction.emoji) == "❌":
                        end_reaction = True
                        action = 11
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                        break
                    else:
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    if not end_reaction:
                        if delete_embed:
                            try:
                                await message.delete()
                            except Exception:
                                pass
                        await ctx.send("Timed out, please try again.")
                        return

        if action is None and actual_buttons_use:
            def check(reaction, abc_author):
                return abc_author == ctx.author or abc_author.id in ctx.bot.owner_ids
                # This makes sure nobody except the command sender can interact with the "menu"
            on_click = message.create_click_listener(timeout=actual_timeout)
            @on_click.not_from_user(ctx.author, cancel_others=True, reset_timeout=False)
            async def on_wrong_user(inter):
                # This function is called in case a button was clicked not by the author
                # cancel_others=True prevents all on_click-functions under this function from working
                # regardless of their checks
                # reset_timeout=False makes the timer keep going after this function is called
                await inter.reply("You are not the author of this command.", ephemeral=True)
            @on_click.matching_id("userinfo_button")
            async def on_userinfo_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 1
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("warn_button")
            async def on_warn_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 2
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("ban_button")
            async def on_ban_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 3
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("softban_button")
            async def on_softban_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 4
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("tempban_button")
            async def on_tempban_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 5
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("kick_button")
            async def on_kick_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 6
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("mute_button")
            async def on_mute_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 7
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("mutechannel_button")
            async def on_mutechannel_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 8
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("tempmute_button")
            async def on_tempmute_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 9
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("tempmutechannel_button")
            async def on_tempmutechannel_button(inter):
                end_reaction = True
                if fake_action:
                    await inter.reply("You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case.", ephemeral=True)
                action = 10
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.matching_id("close_button")
            async def on_test_button(inter):
                end_reaction = True
                action = 11
                try:
                    await message.delete()
                except Exception:
                    pass
                await self.call_actions(ctx, action, user, confirmation, show_author, finish_message, fake_action, delete_embed, delete_message, duration, reason)
                return
            @on_click.timeout
            async def on_timeout():
                if not end_reaction:
                    if delete_embed:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                    await ctx.send("Timed out, please try again.")
                    return

    async def call_actions(self, ctx, action: typing.Optional[int]=None, user: typing.Optional[discord.Member]=None, confirmation: typing.Optional[bool]=None, show_author: typing.Optional[bool]=None, finish_message: typing.Optional[bool]=None, fake_action: typing.Optional[bool]=False, delete_embed: typing.Optional[bool]=None, delete_message: typing.Optional[bool]=None, duration: typing.Optional[check_timedelta]=None, reason: str = None):
        config = await self.data.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        actual_warn_system_use = config["warn_system_use"]
        actual_reason_required = config["reason_required"]
        actual_timeout = config["timeout"]
        if ctx.bot.get_cog("WarnSystem"):
            if actual_warn_system_use:
                warn_system_exist = True
            else:
                warn_system_exist = False
        else:
            warn_system_exist = False

        if action == 1:
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :information_source: UserInfo", f"Here is the information about the user {user.name}!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not ctx.bot.get_cog("Mod"):
                    await ctx.send(f"The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`.")
                msg = copy(ctx.message)
                msg.author = ctx.author
                msg.channel = ctx.channel
                msg.content = f"{ctx.prefix}userinfo {user.id}"
                ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 2:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :warning: Warn", f"Why do you want warn {user}? (Set `cancel` to cancel or `not` for none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :warning: Warn", f"Do you really want to warn {user}?", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :warning: Warn", f"The user {user} has been received a warning!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Warnings"):
                        await ctx.send(f"The cog Warnings is not loaded. To load it, do `{ctx.prefix}load warnings`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn {user.id} The reason was not given."
                    else:
                        msg.content = f"{ctx.prefix}warn {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 1 {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}warn 1 {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 3:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :hammer: Ban", f"Why do you want to ban {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :hammer: Ban", f"Do you really want to ban {user}?", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :hammer: Ban", f"The user {user} has been banned!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(f"The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}ban {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}ban {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 5 {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}warn 5 {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 4:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :repeat_one: SoftBan", f"Why do you want to softban {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :repeat_one: SoftBan", f"Do you really want to softban {user}?", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :repeat_one: SoftBan", f"The user {user} has been softbanned!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(f"The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}softban {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}softban {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 4 {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}warn 4 {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 5:
            try:
                duration = await utils.duration_ask(ctx, duration, "Sanctioning a member - :dash: TempBan", f"How long do you want to tempban {user}? (Set `cancel` to cancel)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :dash: TempBan", f"Why do you want to tempban {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :dash: TempBan", f"Do you really want to tempban {user}?", actual_color, user, reason, duration, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :dash: TempBan", f"The user {user} has been tempban!", actual_thumbnail, actual_color, user, show_author, duration, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(f"The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}tempban {user.id} {duration}"
                    else:
                        msg.content = f"{ctx.prefix}tempban {user.id} {duration} {reason}"
                    await ctx.send(f"{ctx.prefix}tempban {user.id} {duration} {reason}")
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 5 {user.id} {duration}"
                    else:
                        msg.content = f"{ctx.prefix}warn 5 {user.id} {duration} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 6:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :boot: Kick", f"Why do you want to kick {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :boot: Kick", f"Why do you want to kick {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :boot: Kick", f"The user {user} has been kicked!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(f"The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}kick {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}kick {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 3 {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}warn 3 {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 7:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :mute: Mute", f"Why do you want to mute {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :mute: Mute", f"Do you really want to mute {user}?", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :mute: Mute", f"The user {user} has been muted!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mutes"):
                        await ctx.send(f"The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}mute {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}mute {user.id}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 2 {user.id}"
                    else:
                        msg.content = f"{ctx.prefix}warn 2 {user.id} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 8:
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :punch: MuteChannel", f"Why do you want to mute {user} in {ctx.channel.mention}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :punch: MuteChannel", f"Do you really want to mute {user} in {ctx.channel.mention}?", actual_color, user, reason, None, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :punch: MuteChannel", f"The user {user} has been muted in #{ctx.channel.name}!", actual_thumbnail, actual_color, user, show_author, None, reason)
            if not fake_action:
                if not ctx.bot.get_cog("Mutes"):
                    await ctx.send(f"The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`.")
                msg = copy(ctx.message)
                msg.author = ctx.author
                msg.channel = ctx.channel
                if reason == "not":
                    msg.content = f"{ctx.prefix}mutechannel {user.id}"
                else:
                    msg.content = f"{ctx.prefix}mutechannel {user.id}"
                ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 9:
            try:
                duration = await utils.duration_ask(ctx, duration, "Sanctioning a member - :hourglass_flowing_sand: TempMute", f"How long do you want to tempmute {user}? (Set `cancel` to cancel)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :hourglass_flowing_sand: TempMute", f"Why do you want to tempmute {user}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :hourglass_flowing_sand: TempMute", f"Do you really want to tempmute {user}?", actual_color, user, reason, duration, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :hourglass_flowing_sand: TempMute", f"The user {user} has been tempmuted!", actual_thumbnail, actual_color, user, show_author, duration, reason)
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mutes"):
                        await ctx.send(f"The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`. You can also install/load the WarnSystem cog.")
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}mute {user.id} {duration}"
                    else:
                        msg.content = f"{ctx.prefix}mute {user.id} {duration} {reason}"
                    ctx.bot.dispatch("message", msg)
                else:
                    msg = copy(ctx.message)
                    msg.author = ctx.author
                    msg.channel = ctx.channel
                    if reason == "not":
                        msg.content = f"{ctx.prefix}warn 2 {user.id} {duration}"
                    else:
                        msg.content = f"{ctx.prefix}warn 2 {user.id} {duration} {reason}"
                    ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 10:
            try:
                duration = await utils.duration_ask(ctx, duration, "Sanctioning a member - :hourglass: TempMuteChannel", f"How long do you want to tempmute {user} in {ctx.channel.mention}? (Set `cancel` to cancel)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                reason = await utils.reason_ask(ctx, reason, actual_reason_required, "Sanctioning a member - :hourglass: TempMuteChannel", f"Why do you want to tempmute {user} in {ctx.channel.mention}? (Set `cancel` to cancel or `not` to none)", actual_color, user, actual_timeout)
            except Timeout_or_Cancel:
                return
            try:
                confirmation = await utils.confirmation_ask(ctx, confirmation, "Sanctioning a member - :hourglass: TempMuteChannel", f"Do you really want to tempmute {user} in {ctx.channel.mention}?", actual_color, user, reason, duration, actual_timeout)
            except Timeout_or_Cancel:
                return
            message = await utils.finish_message(ctx, finish_message, "Sanctioning a member - :hourglass: TempMuteChannel", f"The user {user} has been tempmuted in #{ctx.channel.name}!", actual_thumbnail, actual_color, user, show_author, duration, reason)
            if not fake_action:
                if not ctx.bot.get_cog("Mutes"):
                    await ctx.send(f"The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`.")
                msg = copy(ctx.message)
                msg.author = ctx.author
                msg.channel = ctx.channel
                if reason == "not":
                    msg.content = f"{ctx.prefix}mutechannel {user.id} {duration}"
                else:
                    msg.content = f"{ctx.prefix}mutechannel {user.id} {duration} {reason}"
                ctx.bot.dispatch("message", msg)
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return
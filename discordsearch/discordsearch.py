from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import argparse
import asyncio
import datetime
import functools
import multiprocessing
import re
from time import monotonic

import dateparser
from redbot.core.utils.chat_formatting import bold, box, underline
from redbot.core.utils.common_filters import URL_RE

# Credits:
# General repo credits.
# Thanks to Trusty for the secure way to manage user Regexes (https://github.com/TrustyJAID/Trusty-cogs/blob/master/retrigger/triggerhandler.py#L542-L606)!

_: Translator = Translator("DiscordSearch", __file__)


class StrConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return argument


@cog_i18n(_)
class DiscordSearch(Cog):
    """A cog to edit roles!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.re_pool: multiprocessing.Pool = multiprocessing.Pool()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.cooldown(rate=3, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(name="discordsearch", aliases=["dsearch"])
    async def discordsearch(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        args: commands.Greedy[StrConverter],
    ) -> None:
        """Search for a message on Discord in a channel.

        Warning: The bot uses the api for each search.
        Arguments:
        `--author @user1 --author user2#1234 --author 0123456789`
        `--mention @user1 --mention user2#1234 --mention 0123456789`
        `--before now`
        `--after "25/12/2000 00h00"`
        `--pinned true`
        `--content "AAA3A-cogs"`
        `--regex "\\[p\\]"`
        `--contain link --contain embed --contain file`
        `--limit 100` (It's the limit of the number of messages taken into account in the search, not the number of results.)
        """
        if not args:
            raise commands.UserInputError()
        try:
            args = await SearchArgs().convert(ctx, args)
        except commands.BadArgument as e:
            await ctx.send(e)
            return
        authors = args.authors
        mentions = args.mentions
        before = args.before
        after = args.after
        pinned = args.pinned
        content = args.content
        regex = args.regex
        contains = args.contains
        limit = args.limit
        if channel is None:
            channel = ctx.channel
        if all(
            setting is None
            for setting in (
                authors,
                mentions,
                before,
                after,
                pinned,
                content,
                regex,
                contains,
                limit,
            )
        ):
            raise commands.UserFeedbackCheckFailure(_("You must provide at least one parameter."))
        args_str = [
            underline("--- Settings of search ---"),
            bold("Authors:")
            + " "
            + (
                ", ".join([author.mention for author in authors])
                if authors is not None
                else "None"
            ),
            bold("Mentions:")
            + " "
            + (
                ", ".join([mention.mention for mention in mentions])
                if mentions is not None
                else "None"
            ),
            bold("Before:") + " " + f"{before}",
            bold("After:") + " " + f"{after}",
            bold("Pinned:") + " " + f"{pinned}",
            bold("Content:") + " " + (f"`{content}`" if content is not None else "None"),
            bold("Regex:") + " " + f"{regex}",
            bold("Contains:")
            + " "
            + (", ".join(list(contains)) if contains is not None else "None"),
            bold("Limit:") + " " + f"{limit}",
        ]
        start = monotonic()
        messages: typing.List[discord.Message] = []
        async for message in channel.history(
            limit=limit, oldest_first=False, before=before, after=after
        ):
            if message.id == ctx.message.id:
                continue
            if authors is not None and message.author not in authors:
                continue
            if mentions is not None and not any(
                True for mention in message.mentions if mention in mentions
            ):
                continue
            if pinned is not None and message.pinned != pinned:
                continue
            if (
                content is not None
                and content.lower() not in message.content.lower()
                and all(
                    content.lower() not in str(embed.to_dict()).lower() for embed in message.embeds
                )
            ):
                continue
            if regex is not None and message.content is not None:
                # Thanks Trusty for this.
                try:
                    trigger_timeout = 1
                    process = self.re_pool.apply_async(regex.findall, (message.content,))
                    task = functools.partial(process.get, timeout=trigger_timeout)
                    loop = asyncio.get_running_loop()
                    new_task = loop.run_in_executor(None, task)
                    search = await asyncio.wait_for(new_task, timeout=trigger_timeout + 5)
                except (multiprocessing.TimeoutError, asyncio.TimeoutError):
                    raise commands.UserFeedbackCheckFailure(
                        _("Your regex process took too long. Removing from memory.")
                    )
                except ValueError:
                    continue
                except Exception as e:
                    raise commands.UserFeedbackCheckFailure(
                        _("There is an error in your regex.\n{e}").format(e=box(str(e), lang="py"))
                    )
                else:
                    if not search:
                        continue
            if contains is not None:
                if "link" in contains:
                    regex = URL_RE.findall(message.content.lower())
                    if regex == []:
                        continue
                if "embed" in contains and len(message.embeds) == 0:
                    continue
                if "file" in contains and len(message.attachments) == 0:
                    continue
            messages.append(message)
        embeds = []
        not_found = len(messages) == 0
        args_str = "\n".join(args_str)
        if not not_found:
            for i, message in enumerate(messages, start=1):
                embed: discord.Embed = discord.Embed()
                embed.title = f"Search in #{channel.name} ({channel.id})"
                embed.description = args_str
                embed.url = message.jump_url
                embed.set_author(name=f"{message.author.display_name} ({message.author.id})")
                embed.add_field(
                    name=f"Message ({message.id}) content:",
                    value=(
                        message.content
                        if len(message.content) < 1025
                        else (message.content[:1020] + "\n...")
                    )
                    if message.content
                    else "None",
                    inline=False,
                )
                embed.add_field(
                    name="Embed(s):",
                    value=_("Look at the original message.")
                    if len(message.embeds) > 0
                    else "None",
                    inline=False,
                )
                embed.timestamp = message.created_at
                embed.set_thumbnail(
                    url="https://us.123rf.com/450wm/sommersby/sommersby1610/sommersby161000062/66918773-recherche-ic%C3%B4ne-plate-recherche-ic%C3%B4ne-conception-recherche-ic%C3%B4ne-web-vecteur-loupe.jpg"
                )
                embed.set_footer(
                    text=f"Page {i}/{len(messages)}",
                    icon_url="https://us.123rf.com/450wm/sommersby/sommersby1610/sommersby161000062/66918773-recherche-ic%C3%B4ne-plate-recherche-ic%C3%B4ne-conception-recherche-ic%C3%B4ne-web-vecteur-loupe.jpg",
                )
                embeds.append(embed)
        else:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Search in #{channel.name} ({channel.id})").format(channel=channel)
            embed.add_field(name="Result:", value=_("Sorry, I could not find any results."))
            embed.timestamp = datetime.datetime.now()
            embed.set_thumbnail(
                url="https://us.123rf.com/450wm/sommersby/sommersby1610/sommersby161000062/66918773-recherche-ic%C3%B4ne-plate-recherche-ic%C3%B4ne-conception-recherche-ic%C3%B4ne-web-vecteur-loupe.jpg"
            )
            embed.set_footer(
                text="Page 1/1",
                icon_url="https://us.123rf.com/450wm/sommersby/sommersby1610/sommersby161000062/66918773-recherche-ic%C3%B4ne-plate-recherche-ic%C3%B4ne-conception-recherche-ic%C3%B4ne-web-vecteur-loupe.jpg",
            )
            embeds.append(embed)
        end = monotonic()
        total = round(end - start, 1)
        for embed in embeds:
            embed.title = _("Search in #{channel.name} ({channel.id}) in {total}s").format(
                channel=channel, total=total
            )
        await Menu(pages=embeds).start(ctx)


class DateConverter(commands.Converter):
    """Date converter which uses dateparser.parse()."""

    async def convert(self, ctx: commands.Context, argument: str) -> datetime.datetime:
        parsed = dateparser.parse(argument)
        if parsed is None:
            raise commands.BadArgument(_("Unrecognized date/time."))
        return parsed


# class SearchArgs(commands.FlagConverter, case_insensitive=False, prefix="--", delimiter=" "):
#     authors: commands.Greedy[discord.Member]
#     mentions: commands.Greedy[discord.Member]
#     before: DateConverter
#     after: DateConverter
#     pinned: bool
#     content: str
#     regex: str
#     contains: commands.Greedy[str]
#     limit: int


class NoExitParser(argparse.ArgumentParser):
    def error(self, message) -> None:
        raise commands.BadArgument(message)


class SearchArgs:
    def parse_arguments(self, arguments: str) -> argparse.Namespace:
        parser = NoExitParser(description="Selection args for DiscordSearch.", add_help=False)
        parser.add_argument("--author", dest="authors", nargs="+")
        parser.add_argument("--mention", dest="mentions", nargs="+")
        parser.add_argument("--before", dest="before")
        parser.add_argument("--after", dest="after")
        parser.add_argument("--pinned", dest="pinned")
        parser.add_argument("--content", dest="content", nargs="*")
        parser.add_argument("--regex", dest="regex", nargs="*")
        parser.add_argument("--contain", dest="contains", nargs="+")
        parser.add_argument("--limit", dest="limit")

        return parser.parse_args(arguments)

    async def convert(self, ctx: commands.Context, arguments) -> typing.Any:
        self.ctx = ctx
        args = self.parse_arguments(arguments)
        if args.authors is not None:
            self.authors = []
            for author in args.authors:
                author = await commands.MemberConverter().convert(ctx, author)
                if author is None:
                    raise commands.BadArgument("`--author` must be a member.")
                self.authors.append(author)
        else:
            self.authors = None
        if args.mentions is not None:
            self.mentions = []
            for mention in args.mentions:
                mention = await commands.MemberConverter().convert(ctx, mention)
                if mention is None:
                    raise commands.BadArgument("`--mention` must be a member.")
                self.mentions.append(mention)
        else:
            self.mentions = None
        self.before = (
            await DateConverter().convert(ctx, args.before)
            if args.before is not None
            else args.before
        )
        self.after = (
            await DateConverter().convert(ctx, args.after)
            if args.after is not None
            else args.after
        )
        if args.pinned is not None:
            args.pinned = str(args.pinned)
            if args.pinned.lower() in ("true", "y", "yes"):
                self.pinned = True
            elif args.pinned.lower() in ("false", "n", "no"):
                self.pinned = False
            else:
                raise commands.BadArgument("`--pinned` must be a bool.")
        else:
            self.pinned = args.pinned
        self.content = "".join(args.content) if args.content is not None else args.content
        if args.regex is not None:
            try:
                self.regex = re.compile("".join(args.regex))
            except Exception as e:
                raise commands.BadArgument(f"`{args.regex}` is not a valid regex pattern.\n{e}")
        else:
            self.regex = None
        if args.contains is not None:
            self.contains = []
            for contain in args.contains:
                if contain.lower() not in ("link", "embed", "file"):
                    raise commands.BadArgument("`--contain` must be `link`, `embed` or `file`.")
                self.contains.append(contain.lower())
        else:
            self.contains = None
        if args.limit is not None:
            try:
                self.limit = int(args.limit)
            except ValueError:
                raise commands.BadArgument("`--limit` must be a int.")
            else:
                self.limit = int(args.limit)
        else:
            self.limit = None
        return self

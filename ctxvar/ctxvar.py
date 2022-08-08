from .AAA3A_utils.cogsutils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
from copy import copy

from redbot.core.utils.chat_formatting import box

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("CtxVar", __file__)

@cog_i18n(_)
class CtxVar(commands.Cog):
    """A cog to list and display the contents of all sub-functions of `ctx`!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.command()
    async def ctxvar(self, ctx: commands.Context, message: typing.Optional[discord.Message]=None, args: typing.Optional[str]=""):
        if message is not None:
            instance = await ctx.bot.get_context(message)
        else:
            instance = ctx
        if not args == "":
            if not hasattr(instance, f"{args}"):
                await ctx.send(_("The argument you specified is not a subclass of the instance.").format(**locals()))
                return
            args = f".{args}"
        instance_name = "ctx"
        full_instance_name = f"{instance_name}{args}"
        if len(f"**{full_instance_name}**") > 256:
            return None
        embed: discord.Embed = discord.Embed()
        embed.title = f"**{full_instance_name}**"
        embed.description = _("Here are all the variables and their associated values that can be used in this class.").format(**locals())
        embed.color = 0x01d758
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/2048px-Python-logo-notext.svg.png")
        one_l = []
        for x in eval(f"dir(instance{args})"):
            try:
                if not eval(f"hasattr(instance{args}.{x}, '__call__')") and "__" not in x:
                    one_l.append(x)
            except Exception:
                pass
        lists = []
        while True:
            l = one_l[0:20]
            one_l = one_l[20:]
            lists.append(l)
            if one_l == []:
                break
        embeds = []
        for l in lists:
            e = copy(embed)
            for x in l:
                if not len(f"{x}") > 256:
                    try:
                        e.add_field(
                            inline=True,
                            name=f"{x}",
                            value=box(str(eval(f"instance{args}.{x}"))[:100]))
                    except Exception:
                        pass
            embeds.append(e)

        page = 0
        for embed in embeds:
            page += 1
            l = len(embeds)
            embed.set_footer(text=_("Page {page}/{l}").format(**locals()))

        await Menu(pages=embeds, delete_after_timeout=True).start(ctx)
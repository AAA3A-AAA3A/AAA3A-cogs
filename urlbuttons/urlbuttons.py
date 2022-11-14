from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons  # isort:skip
else:
    from dislash import ActionRow  # isort:skip

from redbot.core import Config

from .converters import Emoji, EmojiUrlConverter

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

# Credits:
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel!
# Thanks to Kuro for the emoji converter!(https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("UrlButtons", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class UrlButtons(commands.Cog):
    """A cog to have url-buttons!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 974269742704
            force_registration=True,
        )
        self.url_buttons_guild = {
            "url_buttons": {},
        }
        self.config.register_guild(**self.url_buttons_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()
        self.purge.very_hidden = True

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        config = await self.config.guild(message.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).url_buttons.set(config)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_messages=True)
    @hybrid_group()
    async def urlbuttons(self, ctx: commands.Context):
        """Group of commands for use UrlButtons."""
        pass

    @urlbuttons.command()
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        url: str,
        emoji: Emoji,
        *,
        text_button: typing.Optional[str] = None,
    ):
        """Add a url-button to a message."""
        if not message.author == ctx.guild.me:
            await ctx.send(
                _("I have to be the author of the message for the url-button to work.").format(
                    **locals()
                )
            )
            return
        if getattr(ctx, "interaction", None) is None:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send(
                    _(
                        "The emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    ).format(**locals())
                )
                return
        if not url.startswith("http"):
            await ctx.send(_("Url must start with `https` or `http`.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) >= 25:
            await ctx.send(
                _("I can't do more than 25 url-buttons for one message.").format(**locals())
            )
            return
        if hasattr(emoji, "id"):
            config[f"{message.channel.id}-{message.id}"][f"{emoji.id}"] = {
                "url": url,
                "text_button": text_button,
            }
        else:
            config[f"{message.channel.id}-{message.id}"][f"{emoji}"] = {
                "url": url,
                "text_button": text_button,
            }
        if self.cogsutils.is_dpy2:
            await message.edit(
                view=Buttons(timeout=None, buttons=self.get_buttons(config, message))
            )
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        url_buttons: commands.Greedy[EmojiUrlConverter],
    ):
        """Add a url-button to a message.

        ```[p]urlbuttons bulk <message> :red_circle:|<https://github.com/Cog-Creators/Red-DiscordBot> :smiley:|<https://github.com/Cog-Creators/Red-SmileyBot> :green_circle:|<https://github.com/Cog-Creators/Green-DiscordBot>```
        """
        if not message.author == ctx.guild.me:
            await ctx.send(
                _("I have to be the author of the message for the url-button to work.").format(
                    **locals()
                )
            )
            return
        if len(url_buttons) == 0:
            await ctx.send(_("You have not specified any valid url-button.").format(**locals()))
            return
        if getattr(ctx, "interaction", None) is None:
            try:
                for emoji, url in url_buttons:
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send(
                    _(
                        "A emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    ).format(**locals())
                )
                return
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(url_buttons) >= 25:
            await ctx.send(
                _("I can't do more than 25 url-buttons for one message.").format(**locals())
            )
            return
        for emoji, url in url_buttons:
            if hasattr(emoji, "id"):
                config[f"{message.channel.id}-{message.id}"][f"{emoji.id}"] = {
                    "url": url,
                    "text_button": None,
                }
            else:
                config[f"{message.channel.id}-{message.id}"][f"{emoji}"] = {
                    "url": url,
                    "text_button": None,
                }
        if self.cogsutils.is_dpy2:
            await message.edit(
                view=Buttons(timeout=None, buttons=self.get_buttons(config, message))
            )
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, button: Emoji):
        """Remove a url-button to a message."""
        if not message.author == ctx.guild.me:
            await ctx.send(
                _("I have to be the author of the message for the role-button to work.").format(
                    **locals()
                )
            )
            return
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            await ctx.send(_("No url-button is configured for this message.").format(**locals()))
            return
        if f"{getattr(button, 'id', button)}" not in config[f"{message.channel.id}-{message.id}"]:
            await ctx.send(
                _("I wasn't watching for this button on this message.").format(**locals())
            )
            return
        if hasattr(button, "id"):
            del config[f"{message.channel.id}-{message.id}"][f"{button.id}"]
        else:
            del config[f"{message.channel.id}-{message.id}"][f"{button}"]
        if not config[f"{message.channel.id}-{message.id}"] == {}:
            if self.cogsutils.is_dpy2:
                await message.edit(
                    view=Buttons(timeout=None, buttons=self.get_buttons(config, message))
                )
            else:
                await message.edit(components=self.get_buttons(config, message))
        else:
            del config[f"{message.channel.id}-{message.id}"]
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=None)
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message):
        """Clear all url-buttons to a message."""
        if not message.author == ctx.guild.me:
            await ctx.send(
                _("I have to be the author of the message for the url-button to work.").format(
                    **locals()
                )
            )
            return
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            await ctx.send(_("No role-button is configured for this message.").format(**locals()))
            return
        try:
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=[])
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context):
        """Clear all url-buttons to a **guild**."""
        await self.config.guild(ctx.guild).url_buttons.clear()

    def get_buttons(self, config: typing.Dict, message: discord.Message):
        all_buttons = []
        if self.cogsutils.is_dpy2:
            for button in config[f"{message.channel.id}-{message.id}"]:
                try:
                    int(button)
                except ValueError:
                    b = button
                else:
                    b = str(self.bot.get_emoji(int(button)))
                all_buttons.append(
                    {
                        "style": 5,
                        "label": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                            "text_button"
                        ],
                        "emoji": f"{b}",
                        "url": config[f"{message.channel.id}-{message.id}"][f"{button}"]["url"],
                    }
                )
        else:
            lists = []
            one_l = [button for button in config[f"{message.channel.id}-{message.id}"]]
            while True:
                l = one_l[0:4]
                one_l = one_l[4:]
                lists.append(l)
                if one_l == []:
                    break
            for l in lists:
                buttons = {"type": 1, "components": []}
                for button in l:
                    try:
                        int(button)
                    except ValueError:
                        buttons["components"].append(
                            {
                                "type": 2,
                                "style": 5,
                                "label": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                                    "text_button"
                                ],
                                "emoji": {"name": f"{button}"},
                                "url": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                                    "url"
                                ],
                            }
                        )
                    else:
                        buttons["components"].append(
                            {
                                "type": 2,
                                "style": 5,
                                "label": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                                    "text_button"
                                ],
                                "emoji": {"name": f"{button}", "id": int(button)},
                                "url": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                                    "url"
                                ],
                            }
                        )
            all_buttons.append(ActionRow.from_dict(buttons))
        return all_buttons

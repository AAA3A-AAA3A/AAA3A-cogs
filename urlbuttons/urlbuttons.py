from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .converters import Emoji, EmojiUrlConverter

# Credits:
# General repo credits.# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("UrlButtons", __file__)


@cog_i18n(_)
class UrlButtons(Cog):
    """A cog to have url-buttons!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 974269742704
            force_registration=True,
        )
        self.url_buttons_guild: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]
        ] = {
            "url_buttons": {},
        }
        self.config.register_guild(**self.url_buttons_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).url_buttons.set(config)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_messages=True)
    @commands.hybrid_group()
    async def urlbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use UrlButtons."""
        pass

    @urlbuttons.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
        url: str,
        *,
        text_button: typing.Optional[str] = None,
    ) -> None:
        """Add a url-button for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the url-button to work.")
            )
        if ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        if not url.startswith("http"):
            raise commands.UserFeedbackCheckFailure(_("Url must start with `https` or `http`."))
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) >= 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 url-buttons for one message.")
            )
        config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
            "url": url,
            "text_button": text_button,
        }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        url_buttons: commands.Greedy[EmojiUrlConverter],
    ) -> None:
        """Add a url-button for a message.

        ```[p]urlbuttons bulk <message> :red_circle:|<https://github.com/Cog-Creators/Red-DiscordBot> :smiley:|<https://github.com/Cog-Creators/Red-SmileyBot> :green_circle:|<https://github.com/Cog-Creators/Green-DiscordBot>```
        """
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the url-button to work.")
            )
        if len(url_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid url-button.")
            )
        if ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                for emoji, url in url_buttons:
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(url_buttons) >= 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 url-buttons for one message.")
            )
        for emoji, url in url_buttons:
            config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
                "url": url,
                "text_button": None,
            }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command(aliases=["-"])
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a url-button for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No url-button is configured for this message.")
            )
        if f"{getattr(emoji, 'id', emoji)}" not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all url-buttons for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the url-button to work.")
            )
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).url_buttons.set(config)

    @urlbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all url-buttons for a guild."""
        await self.config.guild(ctx.guild).url_buttons.clear()

    def get_buttons(self, config: typing.Dict, message: discord.Message) -> discord.ui.View:
        view = discord.ui.View()
        for button in config[f"{message.channel.id}-{message.id}"]:
            try:
                int(button)
            except ValueError:
                b = button
            else:
                b = str(self.bot.get_emoji(int(button)))
            view.add_item(
                discord.ui.Button(
                    emoji=b,
                    label=config[f"{message.channel.id}-{message.id}"][f"{button}"]["text_button"],
                    url=config[f"{message.channel.id}-{message.id}"][f"{button}"]["url"],
                )
            )
        return view

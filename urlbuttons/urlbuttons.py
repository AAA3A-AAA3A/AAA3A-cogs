from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

from .converters import Emoji, EmojiUrlConverter, UrlConverter

# Credits:
# General repo credits.# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_: Translator = Translator("UrlButtons", __file__)


class MyMessageConverter(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument=argument)
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I have to be the author of the message. You can use EmbedUtils by AAA3A to send one."
                )
            )
        return message


@cog_i18n(_)
class UrlButtons(Cog):
    """A cog to have url-buttons!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 974269742704
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.config.register_global(CONFIG_SCHEMA=None)
        self.config.register_guild(url_buttons={})

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            for guild_id in await self.config.all_guilds():
                url_buttons = await self.config.guild_from_id(guild_id).url_buttons()
                for message in url_buttons:
                    message_data = url_buttons[message].copy()
                    for emoji in message_data:
                        data = url_buttons[message].pop(emoji)
                        data["emoji"] = emoji
                        config_identifier = CogsUtils.generate_key(
                            length=5, existing_keys=url_buttons[message]
                        )
                        url_buttons[message][config_identifier] = data
                await self.config.guild_from_id(guild_id).url_buttons.set(url_buttons)
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.logger.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

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
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group()
    async def urlbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use UrlButtons."""
        pass

    @urlbuttons.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        url: UrlConverter,
        emoji: typing.Optional[Emoji],
        *,
        text_button: typing.Optional[commands.Range[str, 1, 100]] = None,
    ) -> None:
        """Add a url-button for a message."""
        channel_permissions = message.channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        if not url.startswith("http"):
            raise commands.UserFeedbackCheckFailure(_("Url must start with `https` or `http`."))
        if emoji is None and text_button is None:
            raise commands.UserFeedbackCheckFailure(
                _("You have to specify at least an emoji or a label.")
            )
        if emoji is not None and ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) >= 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 url-buttons for one message.")
            )
        config_identifier = CogsUtils.generate_key(
            length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
        )
        config[f"{message.channel.id}-{message.id}"][config_identifier] = {
            "url": url,
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "text_button": text_button,
        }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        await self.config.guild(ctx.guild).url_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @urlbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        url_buttons: commands.Greedy[EmojiUrlConverter],
    ) -> None:
        """Add a url-button for a message.

        ```[p]urlbuttons bulk <message> :red_circle:|<https://github.com/Cog-Creators/Red-DiscordBot> :smiley:|<https://github.com/Cog-Creators/Red-SmileyBot> :green_circle:|<https://github.com/Cog-Creators/Green-DiscordBot>```
        """
        if len(url_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid url-button.")
            )
        if ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                for emoji, url in url_buttons:
                    if emoji is None:
                        continue
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(url_buttons) >= 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 url-buttons for one message.")
            )
        for emoji, url in url_buttons:
            config_identifier = CogsUtils.generate_key(
                length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
            )
            config[f"{message.channel.id}-{message.id}"][config_identifier] = {
                "url": url,
                "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
                "text_button": None,
            }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        await self.config.guild(ctx.guild).url_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @urlbuttons.command(aliases=["-"])
    async def remove(
        self, ctx: commands.Context, message: MyMessageConverter, config_identifier: str
    ) -> None:
        """Remove a url-button for a message.

        Use `[p]urlbuttons list <message>` to find the config identifier.
        """
        config = await self.config.guild(ctx.guild).url_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No url-button is configured for this message.")
            )
        if config_identifier not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][config_identifier]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
        await self.config.guild(ctx.guild).url_buttons.set(config)
        if f"{message.channel.id}-{message.id}" in config:
            await self.list.callback(self, ctx, message=message)
        else:
            await ctx.send(_("Url-buttons cleared for this message."))

    @urlbuttons.command()
    async def clear(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Clear all url-buttons for a message."""
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
        await ctx.send(_("Url-buttons cleared for this message."))

    @commands.bot_has_permissions(embed_links=True)
    @urlbuttons.command()
    async def list(self, ctx: commands.Context, message: MyMessageConverter = None) -> None:
        """List all url-buttons of this server or display the settings for a specific one."""
        url_buttons = await self.config.guild(ctx.guild).url_buttons()
        for url_button in url_buttons:
            url_buttons[url_button]["message"] = url_button
        if message is None:
            _url_buttons = list(url_buttons.values()).copy()
        elif f"{message.channel.id}-{message.id}" not in url_buttons:
            raise commands.UserFeedbackCheckFailure(
                _("No url-button is configured for this message.")
            )
        else:
            _url_buttons = url_buttons.copy()
            _url_buttons = [url_buttons[f"{message.channel.id}-{message.id}"]]
        if not _url_buttons:
            raise commands.UserFeedbackCheckFailure(_("No url-buttons in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("URL Buttons"),
            description=_("There is {len_url_buttons} url buttons in this server.").format(
                len_url_buttons=len(url_buttons)
            ),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embeds = []
        for li in discord.utils.as_chunks(_url_buttons, max_size=5):
            e = embed.copy()
            for url_button in li:
                value = _("Message Jump Link: {message_jump_link}\n").format(
                    message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{url_button['message'].replace('-', '/')}"
                )
                value += "\n".join(
                    [
                        f"• `{config_identifier}` - Emoji {(ctx.bot.get_emoji(int(data['emoji'])) if data['emoji'].isdigit() else data['emoji']) if data['emoji'] is not None else '`None`'} - Label `{data['text_button']}` - URL `{data['url']}`"
                        for config_identifier, data in url_button.items()
                        if config_identifier != "message"
                    ]
                )
                for page in pagify(value, page_length=1024):
                    e.add_field(
                        name="\u200B",
                        value=page,
                        inline=False,
                    )
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @urlbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all url-buttons for a guild."""
        await self.config.guild(ctx.guild).url_buttons.clear()
        await ctx.send(_("All url-buttons purged."))

    def get_buttons(
        self, config: typing.Dict, message: typing.Union[discord.Message, str]
    ) -> discord.ui.View:
        message = (
            f"{message.channel.id}-{message.id}"
            if isinstance(message, discord.Message)
            else message
        )
        view = discord.ui.View()
        for config_identifier in config[message]:
            if config[message][config_identifier]["emoji"] is not None:
                try:
                    int(config[message][config_identifier]["emoji"])
                except ValueError:
                    b = config[message][config_identifier]["emoji"]
                else:
                    b = str(self.bot.get_emoji(int(config[message][config_identifier]["emoji"])))
            else:
                b = None
            view.add_item(
                discord.ui.Button(
                    emoji=b,
                    label=config[message][config_identifier]["text_button"],
                    url=config[message][config_identifier]["url"],
                )
            )
        return view

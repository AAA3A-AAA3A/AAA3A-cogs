from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
from functools import partial

from redbot.core.utils.chat_formatting import pagify

from .converters import Emoji, EmojiLabelTextConverter

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("DropdownsTexts", __file__)


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
class DropdownsTexts(Cog):
    """A cog to have dropdowns-texts!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 985347935839
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 3
        self.dropdowns_texts_global: typing.Dict[str, typing.Optional[int]] = {
            "CONFIG_SCHEMA": None,
        }
        self.dropdowns_texts_guild = {
            "dropdowns_texts": {},
        }
        self.config.register_global(CONFIG_SCHEMA=None)
        self.config.register_guild(dropdowns_texts={})

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()
        asyncio.create_task(self.load_dropdowns())

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            for guild_id in await self.config.all_guilds():
                dropdowns_texts = await self.config.guild_from_id(guild_id).dropdowns_texts()
                for message in dropdowns_texts:
                    message_data = dropdowns_texts[message].copy()
                    for emoji in message_data:
                        data = dropdowns_texts[message].pop(emoji)
                        data["emoji"] = emoji
                        config_identifier = CogsUtils.generate_key(
                            length=5, existing_keys=dropdowns_texts[message]
                        )
                        dropdowns_texts[message][config_identifier] = data
                await self.config.guild_from_id(guild_id).dropdowns_texts.set(dropdowns_texts)
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == 2:
            for guild_id in await self.config.all_guilds():
                dropdowns_texts = await self.config.guild_from_id(guild_id).dropdowns_texts()
                for message in dropdowns_texts:
                    for custom_id in dropdowns_texts[message]:
                        if "text" in dropdowns_texts[message][custom_id]:
                            dropdowns_texts[message][custom_id]["data"] = {"content": dropdowns_texts[message][custom_id].pop("text")}
                await self.config.guild_from_id(guild_id).dropdowns_texts.set(dropdowns_texts)
            CONFIG_SCHEMA = 3
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.logger.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def load_dropdowns(self) -> None:
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["dropdowns_texts"]
            for message in config:
                channel = self.bot.get_channel(int((str(message).split("-"))[0]))
                if channel is None:
                    continue
                message_id = int((str(message).split("-"))[1])
                try:
                    view = self.get_dropdown(config=config, message=message)
                    self.bot.add_view(view, message_id=message_id)
                    self.views[discord.PartialMessage(channel=channel, id=message_id)] = view
                except Exception as e:
                    self.logger.error(
                        f"The Dropdown View could not be added correctly for the `{guild}-{message}` message.",
                        exc_info=e,
                    )

    async def on_dropdown_interaction(
        self, interaction: discord.Interaction, dropdown: discord.ui.Select
    ) -> None:
        if await self.bot.cog_disabled_in_guild(self, interaction.guild):
            return
        if not interaction.data["custom_id"].startswith("DropdownsTexts"):
            return
        selected_options = dropdown.values
        if len(selected_options) == 0:
            if not interaction.response.is_done():
                await interaction.response.defer()
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        config = await self.config.guild(interaction.guild).dropdowns_texts.all()
        if f"{interaction.channel.id}-{interaction.message.id}" not in config:
            await interaction.followup.send(_("This message is not in Config."), ephemeral=True)
            return
        config_identifier = selected_options[0]
        if config_identifier not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.followup.send(_("This option is not in Config."), ephemeral=True)
            return
        data = config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier]["data"]
        if interaction.channel.permissions_for(interaction.guild.me).embed_links:
            if "embed" in data:
                if "title" not in data["embed"]:
                    data["embed"]["title"] = config[f"{interaction.channel.id}-{interaction.message.id}"][
                        config_identifier
                    ]["label"]
                data["embed"] = discord.Embed.from_dict(data["embed"])
            await interaction.followup.send(**data, ephemeral=True)
        elif "embed" in data:
            await interaction.followup.send(data["embed"]["description"], ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).dropdowns_texts.set(config)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group()
    async def dropdownstexts(self, ctx: commands.Context) -> None:
        """Group of commands to use DropdownsTexts."""
        pass

    @dropdownstexts.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        emoji: typing.Optional[Emoji],
        label: commands.Range[str, 1, 100],
        *,
        text_or_message: commands.Range[str, 1, 2000],
    ) -> None:
        """Add a dropdown-text for a message."""
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
        if emoji is not None and ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 dropdown-texts for one message.")
            )
        config_identifier = CogsUtils.generate_key(
            length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
        )
        try:
            text_or_message = await commands.MessageConverter().convert(ctx, text_or_message)
        except commands.BadArgument:
            pass
        config[f"{message.channel.id}-{message.id}"][config_identifier] = {
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "label": label,
            "data": {"embed": {"description": text_or_message}} if isinstance(text_or_message, str) else {"content": text_or_message.content, "embed": text_or_message.embeds[0].to_dict()},
        }
        view = self.get_dropdown(config=config, message=message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)
        await self.list.callback(self, ctx, message=message)

    @dropdownstexts.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        dropdown_texts: commands.Greedy[EmojiLabelTextConverter],
    ) -> None:
        """Add dropdown-texts for a message."""
        if len(dropdown_texts) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid dropdown-text.")
            )
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
        if ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                for emoji, __, __ in dropdown_texts[:19]:
                    if emoji is None:
                        continue
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(dropdown_texts) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 dropdown-texts for one message.")
            )
        for emoji, label, text_or_message in dropdown_texts:
            config_identifier = CogsUtils.generate_key(
                length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
            )
            try:
                text_or_message = await commands.MessageConverter().convert(ctx, text_or_message)
            except commands.BadArgument:
                pass
            config[f"{message.channel.id}-{message.id}"][config_identifier] = {
                "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
                "label": label,
                "data": {"embed": {"description": text_or_message}} if isinstance(text_or_message, str) else {"content": text_or_message.content, "embed": text_or_message.embeds[0].to_dict()},
            }
        view = self.get_dropdown(config=config, message=message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)
        await self.list.callback(self, ctx, message=message)

    @dropdownstexts.command(aliases=["-"])
    async def remove(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        config_identifier: str,
    ) -> None:
        """Remove a dropdown-text for a message.

        Use `[p]dropdownstexts list <message>` to find the config identifier.
        """
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No dropdown-texts is configured for this message.")
            )
        if config_identifier not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this dropdown-text on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][config_identifier]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_dropdown(config=config, message=message)
            message = await message.edit(view=view)
            self.views[message] = view
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)
        if f"{message.channel.id}-{message.id}" in config:
            await self.list.callback(self, ctx, message=message)
        else:
            await ctx.send(_("Dropdowns-buttons cleared for this message."))

    @dropdownstexts.command()
    async def clear(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Clear a dropdown-texts for a message."""
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No dropdown-texts is configured for this message.")
            )
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)
        await ctx.send(_("Dropdown-texts cleared for this message."))

    @commands.bot_has_permissions(embed_links=True)
    @dropdownstexts.command()
    async def list(self, ctx: commands.Context, message: MyMessageConverter = None) -> None:
        """List all dropdowns-texts of this server or display the settings for a specific one."""
        dropdowns_texts = await self.config.guild(ctx.guild).dropdowns_texts()
        for dropdown_text in dropdowns_texts:
            dropdowns_texts[dropdown_text]["message"] = dropdown_text
        if message is None:
            _dropdowns_texts = list(dropdowns_texts.values()).copy()
        elif f"{message.channel.id}-{message.id}" not in dropdowns_texts:
            raise commands.UserFeedbackCheckFailure(
                _("No dropdown-text is configured for this message.")
            )
        else:
            _dropdowns_texts = dropdowns_texts.copy()
            _dropdowns_texts = [dropdowns_texts[f"{message.channel.id}-{message.id}"]]
        if not _dropdowns_texts:
            raise commands.UserFeedbackCheckFailure(_("No dropdowns-texts in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("Dropdowns Texts"),
            description=_("There is {len_dropdowns_texts} dropdowns texts in this server.").format(
                len_dropdowns_texts=len(dropdowns_texts)
            ),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embeds = []
        break_line, fake_backstick = "\n", "\u02CB"
        for li in discord.utils.as_chunks(_dropdowns_texts, max_size=5):
            e = embed.copy()
            for dropdown_text in li:
                value = _("Message Jump Link: {message_jump_link}\n").format(
                    message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{dropdown_text['message'].replace('-', '/')}"
                )
                value += "\n".join(
                    [
                        f"• `{config_identifier}` - Emoji {(ctx.bot.get_emoji(int(data['emoji'])) if data['emoji'].isdigit() else data['emoji']) if data['emoji'] is not None else '`None`'} - Label `{data['label']}`{' - Text `' + data['data']['embed']['description'].replace(break_line, ' ').replace('`', fake_backstick) + '`' if 'embed' in data['data'] else ''}"
                        for config_identifier, data in dropdown_text.items()
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

    @dropdownstexts.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all dropdowns-texts for a guild."""
        await self.config.guild(ctx.guild).dropdowns_texts.clear()
        await ctx.send(_("All dropdowns-texts purged."))

    def get_dropdown(
        self, config: typing.Dict, message: typing.Union[discord.Message, str]
    ) -> discord.ui.View:
        message = (
            f"{message.channel.id}-{message.id}"
            if isinstance(message, discord.Message)
            else message
        )
        options = []
        view = discord.ui.View(timeout=None)
        for config_identifier in config[message]:
            if config[message][config_identifier]["emoji"] is not None:
                try:
                    int(config[message][config_identifier]["emoji"])
                except ValueError:
                    e = config[message][config_identifier]["emoji"]
                else:
                    e = self.bot.get_emoji(int(config[message][config_identifier]["emoji"]))
            else:
                e = None
            options.append(
                discord.SelectOption(
                    label=config[message][config_identifier]["label"],
                    value=config_identifier,
                    emoji=e,
                )
            )
            # all_options.append({"label": config[message][option]["label"], "emoji": e})
        dropdown = discord.ui.Select(
            custom_id=f"DropdownsTexts_{message}",
            placeholder=_("Select an option."),
            min_values=0,
            max_values=1,
            options=options,
            disabled=False,
        )
        dropdown.callback = partial(self.on_dropdown_interaction, dropdown=dropdown)
        view.add_item(dropdown)
        return view

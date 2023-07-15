from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
from functools import partial

from .converters import Emoji, EmojiLabelTextConverter

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("DropdownsTexts", __file__)


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
        self.CONFIG_SCHEMA = 2
        self.dropdowns_texts_global: typing.Dict[str, typing.Optional[int]] = {
            "CONFIG_SCHEMA": None,
        }
        self.dropdowns_texts_guild = {
            "dropdowns_texts": {},
        }
        self.config.register_global(**self.dropdowns_texts_global)
        self.config.register_guild(**self.dropdowns_texts_guild)

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()
        asyncio.create_task(self.load_dropdowns())

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

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
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
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
                    self.log.error(
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
        if interaction.channel.permissions_for(interaction.guild.me).embed_links:
            embed: discord.Embed = discord.Embed()
            embed.title = config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier][
                "label"
            ]
            embed.description = config[f"{interaction.channel.id}-{interaction.message.id}"][
                config_identifier
            ]["text"]
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier]["text"],
                ephemeral=True,
            )

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
        message: discord.Message,
        emoji: typing.Optional[Emoji],
        label: commands.Range[str, 1, 100],
        *,
        text: commands.Range[str, 1, 1000],
    ) -> None:
        """Add a dropdown-text for a message."""
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
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
        config[f"{message.channel.id}-{message.id}"][config_identifier] = {
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "label": label,
            "text": text,
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
        message: discord.Message,
        dropdown_texts: commands.Greedy[EmojiLabelTextConverter],
    ) -> None:
        """Add dropdown-texts for a message."""
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
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
        for emoji, label, text in dropdown_texts:
            config_identifier = CogsUtils.generate_key(
                length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
            )
            config[f"{message.channel.id}-{message.id}"][config_identifier] = {
                "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
                "label": label,
                "text": text,
            }
        view = self.get_dropdown(config=config, message=message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)
        await self.list.callback(self, ctx, message=message)

    @dropdownstexts.command()
    async def remove(
        self,
        ctx: commands.Context,
        message: discord.Message,
        config_identifier: str,
    ) -> None:
        """Remove a dropdown-text for a message.

        Use `[p]dropdownstexts list <message>` to find the config identifier.
        """
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
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
        await self.list.callback(self, ctx, message=message)

    @dropdownstexts.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear a dropdown-texts for a message."""
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
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
    async def list(self, ctx: commands.Context, message: discord.Message = None) -> None:
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
        lists = []
        while _dropdowns_texts != []:
            li = _dropdowns_texts[:5]
            _dropdowns_texts = _dropdowns_texts[5:]
            lists.append(li)
        embeds = []
        for li in lists:
            embed: discord.Embed = discord.Embed(
                title=_("Dropdowns Texts"),
                description=_("There is {len_dropdowns_texts} dropdowns texts in this server.").format(
                    len_dropdowns_texts=len(dropdowns_texts)
                ),
                color=await ctx.embed_color(),
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            break_line = "\n"
            for dropdown_text in li:
                value = _("Message Jump Link: {message_jump_link}\n").format(message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{dropdown_text['message'].replace('-', '/')}")
                value += "\n".join([f"• `{config_identifier}` - Emoji {ctx.bot.get_emoji(int(data['emoji'])) if data['emoji'] is not None and data['emoji'].isdigit() else data['emoji']} - Label `{data['label']}` - Text `{data['text'].replace(break_line, ' ')}`" for config_identifier, data in dropdown_text.items() if config_identifier != "message"])
                embed.add_field(
                    name="\u200B", value=value, inline=False
                )
            embeds.append(embed)
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
            min_values=1,
            max_values=1,
            options=options,
            disabled=False,
        )
        dropdown.callback = partial(self.on_dropdown_interaction, dropdown=dropdown)
        view.add_item(dropdown)
        return view

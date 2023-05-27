from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

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
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 985347935839
            force_registration=True,
        )
        self.dropdowns_texts_guild = {
            "dropdowns_texts": {},
        }
        self.config.register_guild(**self.dropdowns_texts_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        await self.load_dropdowns()

    async def load_dropdowns(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["dropdowns_texts"]
            for dropdown_text in config:
                try:
                    view = self.get_dropdown(config=config, message=dropdown_text)
                    self.bot.add_view(view, message_id=int((str(dropdown_text).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Dropdown View could not be added correctly for the {guild}-{dropdown_text} message.",
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
            await interaction.followup.send(
                _("This message is not in Config."), ephemeral=True
            )
            return
        options = [
            option for option in dropdown.options if option.value == selected_options[0]
        ]
        emoji = options[0].emoji

        class FakeContext:
            def __init__(
                self,
                bot: Red,
                author: discord.Member,
                guild: discord.Guild,
                channel: discord.TextChannel,
            ):
                self.bot: Red = bot
                self.author: discord.Member = author
                self.guild: discord.Guild = guild
                self.channel: discord.TextChannel = channel

        fake_context = FakeContext(
            self.bot, interaction.user, interaction.guild, interaction.channel
        )
        emoji = await Emoji().convert(fake_context, str(emoji))
        emoji = f"{getattr(emoji, 'id', emoji)}"
        if f"{emoji}" not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.followup.send(_("This emoji is not in Config."), ephemeral=True)
            return
        if interaction.channel.permissions_for(interaction.guild.me).embed_links:
            embed: discord.Embed = discord.Embed()
            embed.title = config[f"{interaction.channel.id}-{interaction.message.id}"][
                f"{emoji}"
            ]["label"]
            embed.description = config[f"{interaction.channel.id}-{interaction.message.id}"][
                f"{emoji}"
            ]["text"]
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                config[f"{interaction.channel.id}-{interaction.message.id}"][f"{emoji}"][
                    "text"
                ],
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
    @commands.hybrid_group()
    async def dropdownstexts(self, ctx: commands.Context) -> None:
        """Group of commands to use DropdownsTexts."""
        pass

    @dropdownstexts.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
        label: str,
        *,
        text: str,
    ) -> None:
        """Add a dropdown-text for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        permissions = message.channel.permissions_for(ctx.guild.me)
        if (
            not permissions.add_reactions
            or not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.view_channel
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
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
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 dropdown-texts for one message.")
            )
        if hasattr(emoji, "id"):
            config[f"{message.channel.id}-{message.id}"][f"{emoji.id}"] = {
                "label": label,
                "text": text,
            }
        else:
            config[f"{message.channel.id}-{message.id}"][f"{emoji}"] = {
                "label": label,
                "text": text,
            }
        view = self.get_dropdown(config=config, message=message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)

    @dropdownstexts.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        dropdown_texts: commands.Greedy[EmojiLabelTextConverter],
    ) -> None:
        """Add dropdown-texts for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        permissions = message.channel.permissions_for(ctx.guild.me)
        if (
            not permissions.add_reactions
            or not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.view_channel
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        try:
            for emoji, label, text in dropdown_texts[:19]:
                await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                )
            )
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(dropdown_texts) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 dropdown-texts for one message.")
            )
        for emoji, label, text in dropdown_texts:
            if hasattr(emoji, "id"):
                config[f"{message.channel.id}-{message.id}"][f"{emoji.id}"] = {
                    "label": label,
                    "text": text,
                }
            else:
                config[f"{message.channel.id}-{message.id}"][f"{emoji}"] = {
                    "label": label,
                    "text": text,
                }
        view = self.get_dropdown(config=config, message=message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)

    @dropdownstexts.command()
    async def remove(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
    ) -> None:
        """Remove a dropdown-text for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        config = await self.config.guild(ctx.guild).dropdowns_texts.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No dropdown-texts is configured for this message.")
            )
        if f"{getattr(emoji, 'id', emoji)}" not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this dropdown-text on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_dropdown(config=config, message=message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).dropdowns_texts.set(config)

    @dropdownstexts.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear a dropdown-texts for a message."""
        if message.author != ctx.guild.me:
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

    @dropdownstexts.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all dropdowns-texts for a guild."""
        await self.config.guild(ctx.guild).dropdowns_texts.clear()

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
        for option in config[message]:
            try:
                int(option)
            except ValueError:
                e = option
            else:
                e = self.bot.get_emoji(int(option))
            options.append(
                discord.SelectOption(
                    label=config[message][option]["label"],
                    value=config[message][option]["label"],
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

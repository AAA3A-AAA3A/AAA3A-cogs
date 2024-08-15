from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .utils import Emoji, EmojiLabelDescriptionValueConverter

_: Translator = Translator("TicketTool", __file__)


class ProfileConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if len(argument) > 10:
            raise commands.BadArgument(_("This profile does not exist."))
        profiles = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).profiles()
        if argument.lower() not in profiles:
            raise commands.BadArgument(_("This profile does not exist."))
        return argument.lower()


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
class settings(Cog):
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group(name="settickettool", aliases=["tickettoolset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure TicketTool for your server."""
        pass

    @configuration.command(name="message")
    async def message(
        self,
        ctx: commands.Context,
        profile: ProfileConverter,
        channel: typing.Optional[discord.TextChannel],
        message: typing.Optional[MyMessageConverter],
        reason_options: commands.Greedy[EmojiLabelDescriptionValueConverter],
        emoji: typing.Optional[Emoji] = "🎟️",
        label: commands.Range[str, 1, 80] = None,
    ) -> None:
        """Send a message with a button to open a ticket or dropdown with possible reasons.

        Examples:
        - `[p]settickettool message <profile> #general "🐛|Report a bug|If you find a bug, report it here.|bug" "⚠️|Report a user|If you find a malicious user, report it here.|user"`
        - `[p]settickettool <profile> 1234567890-0987654321`
        """
        if channel is None:
            channel = message.channel if message is not None else ctx.channel
        channel_permissions = channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
            or not channel_permissions.send_messages
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions in this channel to view it and to send messages into."
                )
            )
        if reason_options == []:
            reason_options = None
        config = await self.get_config(ctx.guild, profile)
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = config["embed_button"]["title"]
        embed.description = config["embed_button"]["description"].replace(
            "{prefix}", f"{ctx.prefix}"
        )
        embed.set_image(url=config["embed_button"]["image"])
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        if reason_options is None:
            buttons_config = await self.config.guild(ctx.guild).buttons.all()
            view = self.get_buttons(
                buttons=[
                    {
                        "style": discord.ButtonStyle(2),
                        "label": label or _("Create Ticket"),
                        "emoji": f"{getattr(emoji, 'id', emoji)}",
                        "custom_id": "create_ticket_button",
                        "disabled": False,
                    }
                ],
            )
            if message is None:
                message = await channel.send(embed=embed, view=view)
            else:
                await message.edit(view=view)
            self.views[message] = view
            buttons_config[f"{message.channel.id}-{message.id}"] = {"profile": profile}
            await self.config.guild(ctx.guild).buttons.set(buttons_config)
        else:
            if len({value for __, __, __, value in reason_options}) != len(
                [value for __, __, __, value in reason_options]
            ):
                raise commands.UserFeedbackCheckFailure(
                    _("A different value must be provided for each dropdown option.")
                )
            if ctx.interaction is None and ctx.bot_permissions.add_reactions:
                try:
                    for emoji, label, description, value in reason_options[:19]:
                        await ctx.message.add_reaction(emoji)
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                        )
                    )
                    return
            dropdowns_config = await self.config.guild(ctx.guild).dropdowns.all()
            all_options = [
                {
                    "label": label,
                    "value": value.strip(),
                    "description": description,
                    "emoji": f"{getattr(emoji, 'id', emoji)}",
                    "default": False,
                }
                for emoji, label, description, value in reason_options
            ]
            view = self.get_dropdown(
                placeholder=config["embed_button"]["placeholder_dropdown"],
                options=all_options,
            )
            if message is None:
                message = await channel.send(embed=embed, view=view)
            else:
                message = await message.edit(view=view)
            self.views[message] = view
            dropdowns_config[f"{message.channel.id}-{message.id}"] = [
                {
                    "profile": profile,
                    "emoji": f"{getattr(emoji, 'id', emoji)}",
                    "label": label,
                    "description": description,
                    "value": value.strip(),
                }
                for emoji, label, description, value in reason_options
            ]
            await self.config.guild(ctx.guild).dropdowns.set(dropdowns_config)

    async def check_permissions_in_channel(
        self, permissions: typing.List[str], channel: discord.TextChannel
    ) -> typing.List[str]:
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    # @configuration.command(aliases=["buttonembed"])
    # async def embedbutton(
    #     self,
    #     ctx: commands.Context,
    #     profile: ProfileConverter,
    #     where: typing.Literal["title", "description", "image", "placeholderdropdown"],
    #     *,
    #     text: typing.Optional[str] = None,
    # ):
    #     """Set the settings for the button embed."""
    #     if text is None:
    #         if where == "title":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "title")
    #         elif where == "description":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "description")
    #         elif where == "image":
    #             await self.config.guild(ctx.guild).profiles.clear_raw(profile, "embed_button", "image")
    #         elif where == "placeholderdropdown":
    #             await self.config.guild(
    #                 ctx.guild
    #             ).profiles.clear_raw(profile, "embed_button", "placeholder_dropdown")

    #         return

    #     if where == "title":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "title", value=text)
    #     elif where == "description":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "description", value=text)
    #     elif where == "image":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "image", value=text)
    #     elif where == "placeholderdropdown":
    #         await self.config.guild(ctx.guild).profiles.set_raw(profile, "embed_button", "placeholder_dropdown", value=text)

from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from copy import deepcopy

from .converters import MESSAGE_LINK_REGEX, LinkToMessageConverter

# Credits:
# General repo credits.
# Thanks to Phen for the original code (https://github.com/phenom4n4n/phen-cogs/tree/master/linkquoter)!

_ = Translator("LinkQuoter", __file__)


class LinkQuoterView(discord.ui.View):
    def __init__(self, quoted_message: discord.Message) -> None:
        super().__init__(timeout=60)
        self.quoted_message: discord.Message = quoted_message
        self.add_item(discord.ui.Button(label="Jump to Message!", style=discord.ButtonStyle.link, url=self.quoted_message.jump_url))
        self._message: discord.Message = None

    async def on_timeout(self) -> None:
        self.remove_item(self.delete_message)
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger, custom_id="delete_message")
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await CogsUtils.delete_message(self._message)
        self.stop()


@cog_i18n(_)
class LinkQuoter(Cog):
    """Quote any Discord message from its link!"""

    def __init__(self, bot: Red):
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["PhenoM4n4n", "AAA3A"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 969369062738
            force_registration=True,
        )
        self.linkquoter_guild: typing.Dict[str, bool] = {
            "enabled": False,
            "webhooks": True,
            "cross_server": False,
            "delete_message": False,
            "whitelist_channels": [],
            "blacklist_channels": [],
        }
        self.config.register_guild(**self.linkquoter_guild)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Any]
        ] = {
            "enabled": {
                "converter": bool,
                "description": "Toggle automatic link-quoting.\n\nEnabling this will make [botname] attempt to quote any message link that is sent in this server.\n[botname] will ignore any message that has `no quote` in it.\nIf the user doesn't have permission to view the channel that they link, it will not quote.\n\nTo enable quoting from other servers, run `[p]linkquoteset global`.\n\nTo prevent spam, links can be automatically quoted 3 times every 10 seconds.",
                "aliases": ["auto"],
            },
            "webhooks": {
                "converter": bool,
                "description": "Toggle deleting of messages for automatic quoting.\n\nIf automatic quoting is enabled, then [botname] will also delete messages that contain links in them.",
                "aliases": ["webhook"],
            },
            "cross_server": {
                "converter": bool,
                "description": " Toggle cross-server quoting.\n\nTurning this setting on will allow this server to quote other servers, and other servers to quote this one.",
                "aliases": ["global"],
            },
            "delete_message": {
                "converter": bool,
                "description": "Toggle deleting of messages for automatic quoting.\n\nIf automatic quoting is enabled, then [botname] will also delete messages that contain links in them.",
                "aliases": ["delete"],
            },
            "whitelist_channels": {
                "converter": commands.Greedy[discord.abc.GuildChannel],
                "description": "Set the channels in which auto-quoting will be enabled.",
                "aliases": ["whitelist"],
            },
            "blacklist_channels": {
                "converter": commands.Greedy[discord.abc.GuildChannel],
                "description": "Set the channels in which auto-quoting will be disabled.",
                "aliases": ["blacklist"],
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.setlinkquoter,
        )

    async def cog_load(self) -> None:
        await self.settings.add_commands()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None or message.author.bot:
            return
        if message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me).embed_links:
            return
        config = await self.config.guild(message.guild).all()
        if not config["enabled"]:
            return
        if config["whitelist_channels"] and getattr(message.channel, "parent", message.channel).id not in config["whitelist_channels"]:
            return
        elif config["blacklist_channels"] and getattr(message.channel, "parent", message.channel).id in config["blacklist_channels"]:
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        if "no quote" in message.content.lower():
            return
        if len(MESSAGE_LINK_REGEX.findall(message.content)) > 1:  # If it's a list of several messages links, just display the first one is useless...
            return
        try:
            msg = await LinkToMessageConverter().convert(await self.bot.get_context(message), argument=message.content)
        except commands.BadArgument:
            return
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=message.author,
            channel=message.channel,
            command=f"linkquote {msg.id}",
            message=message,
        )
        if config["delete_message"]:
            await CogsUtils.delete_message(message)

    async def message_to_embed(
        self,
        message: discord.Message,
        *,
        invoke_guild: discord.Guild = None,
        author_field: bool = True,
        footer_field: bool = True,
        url_field: bool = True
    ) -> discord.Embed:
        embed: discord.Embed = None
        image = None

        if message.embeds:
            e = message.embeds[0]
            if e.type == "rich":
                if footer_field:
                    e.timestamp = message.created_at
                embed = discord.Embed.from_dict(deepcopy(e.to_dict()))
            if e.type in ("image", "article"):
                image = e.url

        if embed is None:
            embed = discord.Embed(
                description=f">>> {message.content}" if message.content.strip() else None,
                timestamp=message.created_at,
                color=message.author.color,
            )

        if author_field:
            embed.set_author(
                name=_("{author.display_name} said...").format(author=message.author),
                icon_url=message.author.display_avatar,
                url=message.jump_url,
            )

        if footer_field:
            if invoke_guild and message.guild != invoke_guild:
                embed.set_footer(
                    icon_url=message.guild.icon.url,
                    text=f"#{message.channel.name} | {message.guild}",
                )
            else:
                embed.set_footer(text=f"#{message.channel.name}")

        if message.attachments:
            image = message.attachments[0].proxy_url
            embed.add_field(name=_("Attachments:"), value="\n".join(f"[{attachment.filename}]({attachment.url})" for attachment in message.attachments), inline=False)

        if image is None:
            if message.stickers:
                for sticker in message.stickers:
                    if sticker.url:
                        image = str(sticker.url)
                        embed.add_field(name=_("Stickers:"), value=f"[{sticker.name}]({image})", inline=False)
                        break
        else:
            embed.set_image(url=image)

        if (
            hasattr(message, "reference")
            and message.reference is not None
            and isinstance((reference := message.reference.resolved), discord.Message)
        ):
            jump_url = reference.jump_url
            embed.add_field(
                name=_("Replying to:"),
                value=f"[{reference.content.strip()[:1000] if reference.content.strip() else _('Click to view attachments.')}]({jump_url})",
                inline=False,
            )

        if url_field:
            embed.url = message.jump_url
        # embed.add_field(
        #     name="Source:",
        #     value=f'[Jump to Message!]({message.jump_url} "Follow me to the original message!")',
        #     inline=False,
        # )

        return embed

    @commands.guild_only()
    @commands.cooldown(rate=3, per=10, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["linquoter", "lq"])
    async def linkquote(self, ctx: commands.Context, *, message: LinkToMessageConverter = None) -> None:
        if message is None:
            if not (
                hasattr(ctx.message, "reference")
                and ctx.message.reference is not None
                and isinstance((message := ctx.message.reference.resolved), discord.Message)
            ):
                raise commands.UserInputError()
        view = LinkQuoterView(quoted_message=message)
        if await self.config.guild(ctx.guild).webhooks() and ctx.bot_permissions.manage_webhooks:
            embed = await self.message_to_embed(
                message, invoke_guild=ctx.guild, author_field=False
            )
            try:
                hook: discord.Webhook = await CogsUtils.get_hook(bot=self.bot, channel=ctx.channel)
                view._message = await hook.send(
                    embed=embed,
                    view=view,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar,
                    wait=True,
                )
            except discord.HTTPException:
                pass
            else:
                return
        else:
            embed = await self.message_to_embed(
                message, invoke_guild=ctx.guild
            )
            view._message = await ctx.send(embed=embed, view=view)
        self.views[view._message] = view

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setlinkquoter(self, ctx: commands.Context) -> None:
        """Commands to configure LinkQuoter."""
        pass

    @commands.is_owner()
    @setlinkquoter.command(aliases=["migratefromlinkquoter"])
    async def migratefromphen(self, ctx: commands.Context) -> None:
        """Migrate config from LinkQuoter by Phen."""
        old_config: Config = Config.get_conf(
            "LinkQuoter", identifier=6234567898747434823, force_registration=True, cog_name="LinkQuoter"
        )
        new_guild_group = self.config._get_base_group(self.config.GUILD)
        old_guilds_data = await old_config.all_members()
        async with new_guild_group.all() as new_guilds_data:
            for guild_id in old_guilds_data:
                if "on" in old_guilds_data[guild_id]:
                    new_guilds_data[str(guild_id)]["enabled"] = old_guilds_data[guild_id]["on"]
                if "webhooks" in old_guilds_data[guild_id]:
                    new_guilds_data[str(guild_id)]["webhooks"] = old_guilds_data[guild_id]["webhooks"]
                if "cross_server" in old_guilds_data[guild_id]:
                    new_guilds_data[str(guild_id)]["cross_server"] = old_guilds_data[guild_id]["cross_server"]
                if "delete" in old_guilds_data[guild_id]:
                    new_guilds_data[str(guild_id)]["delete_message"] = old_guilds_data[guild_id]["delete_message"]
        await ctx.send(_("Data successfully migrated from LinkQuoter by Phen."))

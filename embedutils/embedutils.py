from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import aiohttp
import json

from redbot.core.utils.chat_formatting import text_to_file, pagify

from .converters import StringToEmbed, ListStringToEmbed, PastebinConverter, PastebinListConverter, MessageableConverter, MyMessageConverter, MessageableOrMessageConverter, StrConverter

# Credits:
# General repo credits.
# Thanks to Phen for the original code (https://github.com/phenom4n4n/phen-cogs/tree/master/embedutils)!
# Thanks to Max for hosting an embeds creator (https://embedutils.com/)!

_ = Translator("EmbedUtils", __file__)

YAML_CONVERTER = StringToEmbed(conversion_type="yaml", content=False)
YAML_CONTENT_CONVERTER = StringToEmbed(conversion_type="yaml")
YAML_LIST_CONVERTER = ListStringToEmbed(conversion_type="yaml")
JSON_CONVERTER = StringToEmbed(content=False)
JSON_CONTENT_CONVERTER = StringToEmbed()
JSON_LIST_CONVERTER = ListStringToEmbed()
PASTEBIN_CONVERTER = PastebinConverter(conversion_type="json", content=False)
PASTEBIN_CONTENT_CONVERTER = PastebinConverter(conversion_type="json")
PASTEBIN_LIST_CONVERTER = PastebinListConverter(conversion_type="json")


@cog_i18n(_)
class EmbedUtils(Cog):
    """Create, send, and store embeds!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["PhenoM4n4n", "AAA3A"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.embedutils_global: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "stored_embeds": {}
        }
        self.embedutils_guild: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "stored_embeds": {}
        }
        self.config.register_global(**self.embedutils_global)
        self.config.register_guild(**self.embedutils_guild)

        self._session: aiohttp.ClientSession = None

    async def cog_load(self) -> None:
        await super().cog_load()
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group(invoke_without_command=True, aliases=["embedutils"])
    async def embed(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter],
        color: typing.Optional[discord.Color],
        title: str,
        *,
        description: str,
    ) -> None:
        """Post a simple embed with a color, a title and a description.

        Put the title in quotes if it contains spaces.
        If you provide a message, it will be edited.
        """
        color = color or await ctx.embed_color()
        embed: discord.Embed = discord.Embed(color=color, title=title, description=description)
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(embed=embed)
            else:
                await channel_or_message.edit(embed=embed)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="json", aliases=["fromjson", "fromdata"])
    async def embed_json(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter] = None,
        *,
        data: JSON_LIST_CONVERTER = None,
    ):
        """Post embeds from valid JSON.

        This must be in the format expected by [**this Discord documentation**](https://discord.com/developers/docs/resources/channel#embed-object).
        Here's an example: [**this example**](https://gist.github.com/AAA3A-AAA3A/3c9772b34a8ebc09b3b10018185f4cd4).
        You can use an [**embeds creator**](https://embedutils.com/) to get a JSON payload.

        If you provide a message, it will be edited.
        You can use an attachment and the command `[p]embed yamlfile` will be invoked automatically.
        """
        if data is None:
            return await self.embed_fromfile(ctx, channel_or_message=channel_or_message)
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="yaml", aliases=["fromyaml"])
    async def embed_yaml(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter] = None,
        *,
        data: YAML_LIST_CONVERTER = None,
    ):
        """Post embeds from valid YAML.

        This must be in the format expected by [**this Discord documentation**](https://discord.com/developers/docs/resources/channel#embed-object).
        Here's an example: [**this example**](https://gist.github.com/AAA3A-AAA3A/3c9772b34a8ebc09b3b10018185f4cd4).

        If you provide a message, it will be edited.
        You can use an attachment and the command `[p]embed yamlfile` will be invoked automatically.
        """
        if data is None:
            return await self.embed_yamlfile(ctx, channel_or_message=channel_or_message)
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="fromfile", aliases=["jsonfile", "fromjsonfile", "fromdatafile"])
    async def embed_fromfile(self, ctx: commands.Context, channel_or_message: MessageableOrMessageConverter = None):
        """Post an embed from a valid JSON file (upload it).

        This must be in the format expected by [**this Discord documentation**](https://discord.com/developers/docs/resources/channel#embed-object).
        Here's an example: [**this example**](https://gist.github.com/AAA3A-AAA3A/3c9772b34a8ebc09b3b10018185f4cd4).
        You can use an [**embeds creator**](https://embedutils.com/) to get a JSON payload.

        If you provide a message, it will be edited.
        """
        if not ctx.message.attachments or ctx.message.attachments[
            0
        ].filename.split(".")[-1] not in ("json", "txt"):
            raise commands.UserInputError()
        try:
            argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
        except UnicodeDecodeError:
            raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
        data = await JSON_LIST_CONVERTER.convert(ctx, argument=argument)
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="yamlfile", aliases=["fromyamlfile"])
    async def embed_yamlfile(self, ctx: commands.Context, channel_or_message: MessageableOrMessageConverter = None):
        """Post an embed from a valid YAML file (upload it).

        If you provide a message, it will be edited.
        """
        if not ctx.message.attachments or ctx.message.attachments[
            0
        ].filename.split(".")[-1] not in ("yaml", "txt"):
            raise commands.UserInputError()
        try:
            argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
        except UnicodeDecodeError:
            raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
        data = await YAML_LIST_CONVERTER.convert(ctx, argument=argument)
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="pastebin", aliases=["frompastebin", "gist", "fromgist", "hastebin", "fromhastebin"])
    async def embed_pastebin(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter] = None,
        *,
        data: PASTEBIN_LIST_CONVERTER,
    ):
        """ Post embeds from a GitHub/Gist/Pastebin/Hastebin link containing valid JSON.

        This must be in the format expected by [**this Discord documentation**](https://discord.com/developers/docs/resources/channel#embed-object).
        Here's an example: [**this example**](https://gist.github.com/AAA3A-AAA3A/3c9772b34a8ebc09b3b10018185f4cd4).

        If you provide a message, it will be edited.
        """
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @embed.command(name="message", aliases=["frommessage", "frommsg"])
    async def embed_message(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter],
        message: discord.Message,
        index: typing.Optional[int] = None,
        include_content: typing.Optional[bool] = False,
    ):
        """Post embed(s) from an existing message.

        The message must have at least one embed.
        You can specify an index (starting by 0) if you want to send only one of the embeds.
        You can include the content of the message already sent.

        If you provide a message, it will be edited.
        """
        data = {}
        if not message.embeds:
            raise commands.UserInputError()
        if index is None:
            data["embeds"] = message.embeds.copy()
        else:
            try:
                data["embeds"] = [message.embeds[index]]
            except IndexError:
                raise commands.UserInputError
        if include_content:
            data["content"] = message.content
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(**data, allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True) if ctx.permissions.mention_everyone else discord.utils.MISSING)
            else:
                await channel_or_message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @commands.bot_has_permissions(attach_files=True)
    @embed.command(name="download")
    async def embed_download(
        self,
        ctx: commands.Context,
        message: discord.Message,
        index: typing.Optional[int] = None,
        include_content: typing.Optional[bool] = False,
    ):
        """Download a JSON file for a message's embed(s).

        The message must have at least one embed.
        You can specify an index (starting by 0) if you want to include only one of the embeds.
        You can include the content of the message already sent.
        """
        data = {}
        if not message.embeds:
            raise commands.UserInputError()
        if index is None:
            data["embeds"] = [embed.to_dict() for embed in message.embeds.copy()]
        else:
            try:
                data["embeds"] = [message.embeds[index].to_dict()]
            except IndexError:
                raise commands.UserInputError
        if include_content:
            data["content"] = message.content
        await ctx.send(file=text_to_file(text=json.dumps(data, indent=4), filename="embed.json"))

    @commands.mod_or_permissions(manage_messages=True)
    @embed.command(name="edit", usage="<message> <json|yaml|jsonfile|yamlfile|pastebin|message> [data]")
    async def embed_edit(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        conversion_type: typing.Literal["json", "fromjson", "fromdata", "yaml", "fromyaml", "fromfile", "jsonfile", "fromjsonfile", "fromdatafile", "yamlfile", "fromyamlfile", "gist", "pastebin", "hastebin", "message", "frommessage", "frommsg"],
        *,
        data: str = None,
    ):
        """Edit a message sent by [botname].

        It would be better to use the `message` parameter of all the other commands.
        """
        if conversion_type in ("json", "fromjson", "fromdata"):
            if data is None:
                raise commands.UserInputError()
            data = await JSON_LIST_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("yaml", "fromyaml"):
            if data is None:
                raise commands.UserInputError()
            data = await YAML_LIST_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("fromfile", "jsonfile", "fromjsonfile", "fromdatafile"):
            if not ctx.message.attachments or ctx.message.attachments[
                0
            ].filename.split(".")[-1] not in ("json", "txt"):
                raise commands.UserInputError()
            try:
                argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
            except UnicodeDecodeError:
                raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
            data = await JSON_LIST_CONVERTER.convert(ctx, argument=argument)
        elif conversion_type in ("yamlfile", "fromyamlfile"):
            if not ctx.message.attachments or ctx.message.attachments[
                0
            ].filename.split(".")[-1] not in ("yaml", "txt"):
                raise commands.UserInputError()
            try:
                argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
            except UnicodeDecodeError:
                raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
            data = await YAML_LIST_CONVERTER.convert(ctx, argument=argument)
        elif conversion_type in ("gist", "pastebin", "hastebin"):
            if data is None:
                raise commands.UserInputError()
            data = await PASTEBIN_LIST_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("message", "frommessage", "frommsg"):
            if data is None:
                raise commands.UserInputError()
            message = await commands.MessageConverter().convert(ctx, argument=data)
            if not message.embeds:
                raise commands.UserInputError()
            data = {"embeds": [embed.to_dict() for embed in message.embeds]}
        try:
            await message.edit(**data)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @commands.mod_or_permissions(manage_guild=True)
    @embed.command(name="store", aliases=["storeembed"], usage="[global_level=False] [locked=False] <name> <json|yaml|jsonfile|yamlfile|pastebin|message> [data]")
    async def embed_store(
        self,
        ctx: commands.Context,
        global_level: typing.Optional[bool],
        locked: typing.Optional[bool],
        name: str,
        conversion_type: typing.Literal["json", "fromjson", "fromdata", "yaml", "fromyaml", "fromfile", "jsonfile", "fromjsonfile", "fromdatafile", "yamlfile", "fromyamlfile", "gist", "pastebin", "hastebin", "message", "frommessage", "frommsg"],
        *,
        data: str = None,
    ):
        """Store an embed.

        Put the name in quotes if it is multiple words.
        The `locked` argument specifies whether the embed should be locked to mod and superior only (guild level) or bot owners only (global level).
        """
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        if locked is None:
            locked = False

        if conversion_type in ("json", "fromjson", "fromdata"):
            if data is None:
                raise commands.UserInputError()
            data = await JSON_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("yaml", "fromyaml"):
            if data is None:
                raise commands.UserInputError()
            data = await YAML_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("fromfile", "jsonfile", "fromjsonfile", "fromdatafile"):
            if not ctx.message.attachments or ctx.message.attachments[
                0
            ].filename.split(".")[-1] not in ("json", "txt"):
                raise commands.UserInputError()
            try:
                argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
            except UnicodeDecodeError:
                raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
            data = await JSON_CONVERTER.convert(ctx, argument=argument)
        elif conversion_type in ("yamlfile", "fromyamlfile"):
            if not ctx.message.attachments or ctx.message.attachments[
                0
            ].filename.split(".")[-1] not in ("yaml", "txt"):
                raise commands.UserInputError()
            try:
                argument = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
            except UnicodeDecodeError:
                raise commands.UserFeedbackCheckFailure(_("Unreadable attachment with `utf-8`."))
            data = await YAML_CONVERTER.convert(ctx, argument=argument)
        elif conversion_type in ("gist", "pastebin", "hastebin"):
            if data is None:
                raise commands.UserInputError()
            data = await PASTEBIN_CONVERTER.convert(ctx, argument=data)
        elif conversion_type in ("message", "frommessage", "frommsg"):
            if data is None:
                raise commands.UserInputError()
            message = await commands.MessageConverter().convert(ctx, argument=data)
            if not message.embeds:
                raise commands.UserInputError()
            data = {"embed": message.embeds[0].to_dict()}
        embed = data["embed"]
        try:
            await ctx.channel.send(embed=embed)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

        async with (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds() as stored_embeds:
            total_embeds = set(stored_embeds)
            total_embeds.add(name)
            # If the user provides a name that's already used as an embed, it won't increment the embed count, which is why total embeds is converted to a set to calculate length to prevent duplicate names.
            embed_limit = 100
            if not global_level and len(total_embeds) > embed_limit:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "This server has reached the embed limit of {embed_limit}. You must remove an embed with `{ctx.clean_prefix}embed unstore` before you can add a new one."
                    ).format(embed_limit=embed_limit, ctx=ctx)
                )
            stored_embeds[name] = {"author": ctx.author.id, "embed": embed.to_dict(), "locked": locked, "uses": 0}

    @commands.mod_or_permissions(manage_guild=True)
    @embed.command(name="unstore", aliases=["unstoreembed"], usage="[global_level=False] <name>")
    async def embed_unstore(
        self,
        ctx: commands.Context,
        global_level: typing.Optional[bool],
        name: str,
    ):
        """Remove a stored embed."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        async with (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds() as stored_embeds:
            if name not in stored_embeds:
                raise commands.UserFeedbackCheckFailure(_("This is not a stored embed at this level."))
            del stored_embeds[name]

    @commands.mod_or_permissions(manage_guild=True)
    @embed.command(name="list", aliases=["liststored", "liststoredembeds"], usage="[global_level=False]")
    async def embed_list(self, ctx: commands.Context, global_level: typing.Optional[bool]):
        """Get info about a stored embed."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        stored_embeds = await (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds()
        if not stored_embeds:
            raise commands.UserFeedbackCheckFailure(
                _("No stored embeds is configured at this level.")
            )
        description = "\n".join(f"- `{name}`" for name in stored_embeds)
        embed: discord.Embed = discord.Embed(
            title=(_("Global ") if global_level else "") + _("Stored Embeds"),
            color=await ctx.embed_color()
        )
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.display_avatar)
        embeds = []
        for page in pagify(description):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.mod_or_permissions(manage_guild=True)
    @embed.command(name="info", aliases=["infostored", "infostoredembed"], usage="[global_level=False] <name>")
    async def embed_info(self, ctx: commands.Context, global_level: typing.Optional[bool], name: str):
        """Get info about a stored embed."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        stored_embeds = await (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds()
        if name not in stored_embeds:
            raise commands.UserFeedbackCheckFailure(_("This is not a stored embed at this level."))
        stored_embed = stored_embeds[name]
        description = [
            f"• **Author:** <@{stored_embed['author']}> ({stored_embed['author']})",
            f"• **Uses:** {stored_embed['uses']}",
            f"• **Length:** {len(stored_embed['embed'])}",
            f"• **Locked:** {stored_embed['locked']}",
        ]
        embed: discord.Embed = discord.Embed(
            title=f"Info about `{name}`",
            description="\n".join(description),
            color=await ctx.embed_color()
        )
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.display_avatar)
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))

    @commands.mod_or_permissions(manage_guild=True)
    @embed.command(name="downloadstored", aliases=["downloadstoredembed"], usage="[global_level=False] <name>")
    async def embed_download_stored(self, ctx: commands.Context, global_level: typing.Optional[bool], name: str):
        """Download a JSON file for a stored embed."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        stored_embeds = await (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds()
        if name not in stored_embeds:
            raise commands.UserFeedbackCheckFailure(_("This is not a stored embed at this level."))
        stored_embed = stored_embeds[name]
        await ctx.send(file=text_to_file(text=json.dumps({"embed": stored_embed["embed"]}, indent=4), filename="embed.json"))

    @embed.command(name="poststored", aliases=["poststoredembed", "post"], usage="[channel_or_message=<CurrentChannel>] [global_level=False] <names>")
    async def embed_post_stored(
        self,
        ctx: commands.Context,
        channel_or_message: typing.Optional[MessageableOrMessageConverter],
        global_level: typing.Optional[bool],
        names: commands.Greedy[StrConverter]
    ):
        """Post stored embeds."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        async with (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds() as stored_embeds:
            embeds = []
            for name in names:
                if (
                    name not in stored_embeds
                    or (global_level and stored_embeds[name]["locked"] and ctx.author.id not in ctx.bot.owner_ids)
                    or (not global_level and stored_embeds[name]["locked"] and await ctx.bot.is_mod(ctx.author))
                ):
                    raise commands.UserFeedbackCheckFailure(_("`{name}` is not a stored embed at this level.").format(name=name))
                embeds.append(discord.Embed.from_dict(stored_embeds[name]["embed"]))
                stored_embeds[name]["uses"] += 1
        try:
            if not isinstance(channel_or_message, discord.Message):
                channel = channel_or_message or ctx.channel
                await channel.send(embeds=embeds)
            else:
                await channel_or_message.edit(embeds=embeds)
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @commands.mod_or_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @embed.command(name="postwebhook", aliases=["webhook"], usage="[channel_or_message=<CurrentChannel>] <username> <avatar_url> [global_level=False] <names>")
    async def embed_post_webhook(
        self,
        ctx: commands.Context,
        channel: typing.Optional[MessageableConverter],
        username: commands.Range[str, 1, 80],
        avatar_url: str,
        global_level: typing.Optional[bool],
        names: commands.Greedy[StrConverter]
    ):
        """Post stored embeds with a webhook."""
        if global_level is None:
            global_level = False
        elif global_level and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't manage global stored embeds."))
        async with (self.config if global_level else self.config.guild(ctx.guild)).stored_embeds() as stored_embeds:
            embeds = []
            for name in names:
                if (
                    name not in stored_embeds
                    or (global_level and stored_embeds[name]["locked"] and ctx.author.id not in ctx.bot.owner_ids)
                    or (not global_level and stored_embeds[name]["locked"] and await ctx.bot.is_mod(ctx.author))
                ):
                    raise commands.UserFeedbackCheckFailure(_("`{name}` is not a stored embed at this level.").format(name=name))
                embeds.append(discord.Embed.from_dict(stored_embeds[name]["embed"]))
                stored_embeds[name]["uses"] += 1
        try:
            channel = channel or ctx.channel
            hook: discord.Webhook = await CogsUtils.get_hook(bot=self.bot, channel=channel)
            await hook.send(
                embeds=embeds,
                username=username,
                avatar_url=avatar_url,
                wait=True,
            )
        except discord.HTTPException as error:
            return await StringToEmbed.embed_convert_error(ctx, _("Embed Send Error"), error)

    @commands.is_owner()
    @embed.command(aliases=["migratefromembedutils"])
    async def migratefromphen(self, ctx: commands.Context) -> None:
        """Migrate stored embeds from EmbedUtils by Phen."""
        old_config: Config = Config.get_conf(
            "EmbedUtils", identifier=43248937299564234735284, force_registration=True, cog_name="EmbedUtils"
        )
        old_global_data = await old_config.all()
        new_global_group = self.config._get_base_group(self.config.GLOBAL)
        async with new_global_group.all() as new_global_data:
            if "embeds" in old_global_data:
                if "stored_embeds" not in new_global_data:
                    new_global_data["stored_embeds"] = {}
                _stored_embeds = new_global_data["stored_embeds"]
                new_global_data["stored_embeds"] = {name: {"author": data["author"], "embed": data["embed"], "locked": data.get("locked", False), "uses": data["uses"]} for name, data in old_global_data["embeds"].items()}
                new_global_data["stored_embeds"].update(**_stored_embeds)
        new_guild_group = self.config._get_base_group(self.config.GUILD)
        old_guilds_data = await old_config.all_guilds()
        async with new_guild_group.all() as new_guilds_data:
            for guild_id in old_guilds_data:
                if "embeds" in old_guilds_data[guild_id]:
                    if str(guild_id) not in new_guilds_data:
                        new_guilds_data[str(guild_id)] = {}
                    if "stored_embeds" not in new_guilds_data[str(guild_id)]:
                        new_guilds_data[str(guild_id)]["stored_embeds"] = {}
                    _stored_embeds = new_guilds_data[str(guild_id)]["stored_embeds"]
                    new_guilds_data[str(guild_id)]["stored_embeds"] = {name: {"author": data["author"], "embed": data["embed"], "locked": data.get("locked", False), "uses": data["uses"]} for name, data in old_guilds_data[guild_id]["embeds"].items()}
                    new_guilds_data[str(guild_id)]["stored_embeds"].update(**_stored_embeds)
        await ctx.send(_("Data successfully migrated from EmbedUtils by Phen."))

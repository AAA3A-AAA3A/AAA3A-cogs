from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import gists

from .view import GistsHandlerView

# Credits:
# General repo credits.
# Thanks to WitherredAway for the cog's idea and a part of the code (https://github.com/WitherredAway/Yeet/blob/master/cogs/gist.py)!

_ = Translator("GistsHandler", __file__)


class GistConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        cog: GistsHandler = ctx.bot.get_cog("GistsHandler")
        try:
            gist_id = gists.Gist.gist_url_to_id(argument)
            gist_data: typing.Dict = await cog.gists_client.request(
                "GET", f"gists/{gist_id}", authorization=cog.gists_client.access_token is not None
            )
            gist = gists.Gist(gist_data, self)
        except gists.NotFound:
            raise commands.BadArgument(_("Gist not found."))
        return gist


@cog_i18n(_)
class GistsHandler(Cog):
    """A cog to create new Gists and edit/delete existing ones!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.gists_client: gists.Client = None

    async def cog_load(self) -> None:
        await super().cog_load()
        api_tokens = await self.bot.get_shared_api_tokens(service_name="github")
        self.gists_client = gists.Client()
        if (token := api_tokens.get("token")) is not None:
            try:
                await self.gists_client.authorize(token)
            except gists.AuthorizationFailure as e:
                self.logger.error("The GitHub token is invalid.", exc_info=e)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    @commands.Cog.listener()
    async def on_red_api_tokens_update(
        self, service_name: str, api_tokens: typing.Mapping[str, str]
    ) -> None:
        if service_name != "github":
            return
        if (token := api_tokens.get("token")) is None:
            return
        try:
            await self.gists_client.authorize(token)
        except gists.AuthorizationFailure as e:
            self.logger.error("The GitHub token is invalid.", exc_info=e)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["gisthandler"], usage="[gist_url_or_id] [file_name]")
    async def gist(
        self, ctx: commands.Context, gist: GistConverter = None, file_name: str = None
    ) -> None:
        """Create a new Gist and edit an existing one.

        You need to set up a GitHub token with `[p]set api github token,[TOKEN]` first.
        """
        if self.gists_client is None or self.gists_client.access_token is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You need to set up a GitHub token with `{ctx.prefix}set api github token,[TOKEN]` first!"
                ).format(ctx=ctx)
            )
        file = None if gist is None else discord.utils.get(gist.files, name=file_name)
        await GistsHandlerView(cog=self, gist=gist, file=file).start(ctx)

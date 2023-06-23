from AAA3A_utils import Cog  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import typing  # isort:skip

# from .editautomod import EditAutoMod
from .editguild import EditGuild
from .editrole import EditRole
from .edittextchannel import EditTextChannel
from .editthread import EditThread
from .editvoicechannel import EditVoiceChannel

# Credits:
# General repo credits.

_ = Translator("DiscordEdit", __file__)

BASES = [EditGuild, EditRole, EditTextChannel, EditThread, EditVoiceChannel]  # EditAutoMod


@cog_i18n(_)
class DiscordEdit(*BASES, Cog):
    """A cog to edit Discord default objects, like guilds, roles, text channels, voice channels, threads and AutoMod!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip

from .editguild import EditGuild
from .editrole import EditRole
from .edittextchannel import EditTextChannel
if CogsUtils().is_dpy2:
    from .editthread import EditThread
from .editvoicechannel import EditVoiceChannel

# Credits:
# General repo credits.

_ = Translator("DiscordEdit", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

if CogsUtils().is_dpy2:
    BASES = [EditGuild, EditRole, EditTextChannel, EditThread, EditVoiceChannel]
else:
    BASES = [EditGuild, EditRole, EditTextChannel, EditVoiceChannel]

@cog_i18n(_)
class DiscordEdit(*BASES, Cog):
    """A cog to edit Discord default objects!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

import typing  # isort:skip

from .anti_nuke import AntiNukeModule
from .join_gate import JoinGateModule
from .auto_mod import AutoModModule
from .logging import LoggingModule
from .reports import ReportsModule
from .lockdown import LockdownModule
from .module import Module
from .protected_roles import ProtectedRolesModule
from .unauthorized_text_channel_deletions import UnauthorizedTextChannelDeletionsModule

MODULES: typing.List[Module] = [
    JoinGateModule,
    AutoModModule,
    ReportsModule,
    LoggingModule,
    AntiNukeModule,
    ProtectedRolesModule,
    LockdownModule,
    UnauthorizedTextChannelDeletionsModule,
]

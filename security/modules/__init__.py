import typing  # isort:skip

from .anti_nuke import AntiNukeModule
from .auto_mod import AutoModModule
from .join_gate import JoinGateModule
from .lockdown import LockdownModule
from .logging import LoggingModule
from .module import Module
from .protected_roles import ProtectedRolesModule
from .reports import ReportsModule
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

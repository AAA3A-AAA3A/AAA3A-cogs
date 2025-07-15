import typing  # isort:skip

from .anti_impersonation import AntiImpersonationModule
from .anti_nuke import AntiNukeModule
from .auto_mod import AutoModModule
from .dank_pool_protection import DankPoolProtectionModule
from .join_gate import JoinGateModule
from .lockdown import LockdownModule
from .logging import LoggingModule
from .module import Module
from .protected_roles import ProtectedRolesModule
from .reports import ReportsModule
from .sentinel_relay import SentinelRelayModule
from .unauthorized_text_channel_deletions import UnauthorizedTextChannelDeletionsModule

MODULES: typing.List[Module] = [
    JoinGateModule,
    AutoModModule,
    ReportsModule,
    LoggingModule,
    AntiNukeModule,
    ProtectedRolesModule,
    DankPoolProtectionModule,
    AntiImpersonationModule,
    UnauthorizedTextChannelDeletionsModule,
    LockdownModule,
    SentinelRelayModule,
]

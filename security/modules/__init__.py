from .anti_impersonation import AntiImpersonationModule
from .anti_nuke import AntiNukeModule
from .anti_raid import AntiRaidModule
from .auto_mod import AutoModModule
from .dank_pool_protection import DankPoolProtectionModule
from .image_checking import ImageCheckingModule
from .join_gate import JoinGateModule
from .lockdown import LockdownModule
from .logging import LoggingModule
from .message_analysis import MessageAnalysisModule
from .module import Module
from .protected_roles import ProtectedRolesModule
from .reports import ReportsModule
from .sentinel_relay import SentinelRelayModule
from .unauthorized_text_channel_deletions import UnauthorizedTextChannelDeletionsModule
from .verification import VerificationModule

MODULES: list[Module] = [
    JoinGateModule,
    VerificationModule,
    AntiRaidModule,
    AutoModModule,
    ImageCheckingModule,
    MessageAnalysisModule,
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

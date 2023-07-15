import typing  # isort:skip


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ACTIONS_DICT: typing.Dict[str, typing.Dict[str, str]] = {
    "userinfo": {
        "label": "UserInfo",
        "emoji": "ℹ️",
        "cog_required": "Mod",
        "command": "userinfo {member.id}",
        "warn_system_command": None,
        "duration_ask_message": None,
        "reason_ask_message": None,
        "confirmation_ask_message": None,
        "finish_message": _("Here is my informations about {member.display_name} ({member.id})."),
    },
    "warn": {
        "label": "Warn",
        "emoji": "⚠️",
        "cog_required": "Warnings",
        "command": "warn {member.id} {reason}",
        "warn_system_command": "warn 1 {member.id} {reason}",
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to warn {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": None,
        "finish_message": _(
            "The member {member.display_name} ({member.id}) has received a warning."
        ),
    },
    "ban": {
        "label": "Ban",
        "emoji": "🔨",
        "cog_required": "Mod",
        "command": "ban {member.id} {reason}",
        "warn_system_command": "warn 5 {member.id} {reason}",
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to ban {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to ban {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _("The member {member.display_name} ({member.id}) has been banned."),
    },
    "softban": {
        "label": "SoftBan",
        "emoji": "🔂",
        "cog_required": "Mod",
        "command": "softban {member.id} {reason}",
        "warn_system_command": "warn 4 {member.id} {reason}",
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to softban {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to softban {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _("The member {member.display_name} ({member.id}) has been softbanned."),
    },
    "tempban": {
        "label": "TempBan",
        "emoji": "💨",
        "cog_required": "Mod",
        "command": "tempban {member.id} {duration} {reason}",
        "warn_system_command": "warn 5 {member.id} {duration} {reason}",
        "duration_ask_message": _(
            "How long do you want to tempban {member.display_name} ({member.id})? (Type `cancel` to cancel.)"
        ),
        "reason_ask_message": _(
            "Why do you want to tempban {member.display_name} ({member.id}) during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to tempban {member.display_name} ({member.id}) during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _(
            "The member {member.display_name} ({member.id}) has been tempbanned and will be unbanned in {duration}."
        ),
    },
    "kick": {
        "label": "Kick",
        "emoji": "👢",
        "cog_required": "Mod",
        "command": "kick {member.id} {reason}",
        "warn_system_command": "warn 3 {member.id} {reason}",
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to kick {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to kick {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _("The member {member.display_name} ({member.id}) has been kicked."),
    },
    "mute": {
        "label": "Mute",
        "emoji": "🔇",
        "cog_required": "Mutes",
        "command": "mute {member.id} {reason}",
        "warn_system_command": "warn 2 {member.id} {reason}",
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to mute {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to mute {member.display_name} ({member.id})? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _("The member {member.display_name} ({member.id}) has been muted."),
    },
    "mutechannel": {
        "label": "MuteChannel",
        "emoji": "👊",
        "cog_required": "Mutes",
        "command": "mutechannel {member.id} {reason}",
        "warn_system_command": None,
        "duration_ask_message": None,
        "reason_ask_message": _(
            "Why do you want to mute {member.display_name} ({member.id}) in {channel.mention}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to mute {member.display_name} ({member.id}) in {channel.mention}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _(
            "The member {member.display_name} ({member.id}) has been muted in {channel.mention}."
        ),
    },
    "tempmute": {
        "label": "TempMute",
        "emoji": "⏳",
        "cog_required": "Mutes",
        "command": "mute {member.id} {duration} {reason}",
        "warn_system_command": "warn 2 {member.id} {duration} {reason}",
        "duration_ask_message": _(
            "How long do you want to tempmute {member.display_name} ({member.id})? (Type `cancel` to cancel.)"
        ),
        "reason_ask_message": _(
            "Why do you want to tempmute {member.display_name} ({member.id}) during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to tempmute {member.display_name} ({member.id}) during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _(
            "The member {member.display_name} ({member.id}) has been tempmuted and will be unmuted in {duration}."
        ),
    },
    "tempmutechannel": {
        "label": "TempMuteChannel",
        "emoji": "⌛",
        "cog_required": "Mutes",
        "command": "mutechannel {member.id} {duration} {reason}",
        "warn_system_command": None,
        "duration_ask_message": _(
            "How long do you want to tempmute {member.display_name} ({member.id}) in {channel.mention}? (Type `cancel` to cancel.)"
        ),
        "reason_ask_message": _(
            "Why do you want to tempmute {member.display_name} ({member.id}) in {channel.mention} during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "confirmation_ask_message": _(
            "Do you really want to tempmute {member.display_name} ({member.id}) in {channel.mention} during {duration}? (Type `cancel` to cancel or `not` to none.)"
        ),
        "finish_message": _(
            "The member {member.display_name} ({member.id}) has been tempmuted in {channel.mention} and will be unmuted in {duration}."
        ),
    },
}

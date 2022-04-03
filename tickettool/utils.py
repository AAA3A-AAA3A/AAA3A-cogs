import discord  # isort:skip

def _(untranslated: str):
    return untranslated

class utils():
    def __init__(self, bot):
        self.bot = bot

    async def get_overwrites(self, ticket):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        overwrites = {
            ticket.owner: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
            ),
            ticket.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                manage_messages=True,
                manage_channels=True,
                manage_permissions=True,
            ),
            ticket.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
            )
        }
        if ticket.claim is not None:
            overwrites[ticket.claim] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
        if config["admin_role"] is not None:
            overwrites[config["admin_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                    manage_messages=True,
                )
            )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
        if config["view_role"] is not None:
            overwrites[config["view_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    add_reactions=False,
                )
            )
        return overwrites
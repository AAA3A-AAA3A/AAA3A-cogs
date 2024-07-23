from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

_ = Translator("ViewPermissions", __file__)


class PermissionsView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        guild: discord.Guild,
        roles: typing.List[discord.Role] = None,
        members: typing.List[discord.Member] = None,
        channel: typing.Optional[discord.abc.GuildChannel] = None,
        permissions: typing.List[str] = None,
        advanced: bool = False,
    ) -> None:
        roles = [] if roles is None else roles.copy()
        if members is None:
            members = []
        if permissions is None:
            permissions = []
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.guild: discord.Guild = guild
        self.roles: typing.Optional[typing.List[discord.Role]] = roles
        self.members: typing.Optional[typing.List[discord.Member]] = members
        for member in self.members:
            self.roles.extend(member.roles)
        self.roles = sorted(set(self.roles))
        self.channel: typing.Optional[discord.abc.GuildChannel] = channel
        self.permissions: typing.List[str] = permissions
        self.advanced: bool = advanced

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()
        self._current: int = 0
        self._pages: typing.List[discord.Embed] = []

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            roles=self.roles,
            members=self.members,
            channel=self.channel,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        # if self.permissions and self.channel is None:
        #     self.remove_item(self.channel_select)
        #     self.remove_item(self._server_permissions_button)
        #     self.remove_item(self._current_channel_permissions_button)
        self._current: int = 0
        self._message: discord.Message = await self.ctx.send(
            embed=self._pages[self._current], view=self
        )
        self.cog.views[self._message] = self
        await self._ready.wait()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    @discord.ui.select(
        cls=discord.ui.MentionableSelect,
        placeholder="Select mentionables.",
        min_values=0,
        max_values=None,
    )
    async def mentionables_select(
        self, interaction: discord.Interaction, select: discord.ui.MentionableSelect
    ):
        await interaction.response.defer()
        self.roles: typing.List[discord.Role] = [
            mentionable for mentionable in select.values if isinstance(mentionable, discord.Role)
        ]
        self.members: typing.List[discord.Member] = [
            mentionable for mentionable in select.values if isinstance(mentionable, discord.Member)
        ]
        for member in self.members:
            self.roles.extend(member.roles)
        self.roles = sorted(set(self.roles))
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            roles=self.roles,
            members=self.members,
            channel=self.channel,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        self._current: int = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, placeholder="Select channel.", min_values=0, max_values=1
    )
    async def channel_select(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        await interaction.response.defer()
        self.channel = await select.values[0].fetch() if select.values else None
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            channel=self.channel,
            roles=self.roles,
            members=self.members,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        self._current: int = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.button(emoji="◀️", custom_id="back_button", row=2)
    async def _back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self._current == 0:
            self._current = len(self._pages) - 1
        else:
            self._current -= 1
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page", row=2)
    async def close_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    @discord.ui.button(emoji="▶️", custom_id="next_button", row=2)
    async def _next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self._current < len(self._pages) - 1:
            self._current += 1
        else:
            self._current = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.button(emoji="🔄", custom_id="reload_button", row=2)
    async def _reload_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            roles=self.roles,
            members=self.members,
            channel=self.channel,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        self._current: int = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.button(
        label="Server Permissions", emoji="🌍", custom_id="server_permissions_button", row=3
    )
    async def _server_permissions_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.channel: typing.Optional[discord.abc.GuildChannel] = None
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            roles=self.roles,
            members=self.members,
            channel=self.channel,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        self._current: int = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

    @discord.ui.button(
        label="Current Channel Permissions",
        emoji="📪",
        custom_id="current_channel_permissions",
        row=3,
    )
    async def _current_channel_permissions_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.channel: typing.Optional[discord.abc.GuildChannel] = self.ctx.channel
        self._pages: typing.List[discord.Embed] = await self.cog.get_embeds(
            guild=self.guild,
            roles=self.roles,
            members=self.members,
            channel=self.channel,
            permissions=self.permissions,
            advanced=self.advanced,
            embed_color=await self.ctx.embed_color(),
        )
        self._current: int = 0
        self._message: discord.Message = await self._message.edit(embed=self._pages[self._current])

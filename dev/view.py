from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import io
import textwrap

from redbot.core.dev_commands import START_CODE_BLOCK_RE

_: Translator = Translator("Dev", __file__)


def cleanup_code(code: str) -> str:
    if code.startswith("```") and code.endswith("```"):
        code = START_CODE_BLOCK_RE.sub("", code)[:-3].rstrip("\n")
    else:
        code = code.strip("\n`")
    code = textwrap.dedent(code)
    with io.StringIO(code) as codeio:
        for line in codeio:
            line = line.strip()
            if line and not line.startswith("#"):
                break
        else:
            return "pass"
    return code


class ExecuteModal(discord.ui.Modal):
    def __init__(
        self,
        cog: commands.Cog,
        ctx: commands.Context,
        choice: typing.Literal["debug", "eval"] = "eval",
    ) -> None:
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = ctx
        self.choice: typing.Literal["debug", "eval"] = choice
        super().__init__(title=_("Execute") + " " + self.choice.title(), timeout=60 * 10)
        self.code: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Code to Execute"),
            style=discord.TextStyle.long,
            placeholder=_("Write your code here..."),
            required=True,
        )
        self.add_item(self.code)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        context = getattr(self.ctx, "original_context", self.ctx)
        context.interaction = interaction
        code = self.code.value
        source = cleanup_code(code)
        await self.cog.my_exec(
            context,
            type="debug",
            source=source,
            send_result=True,
        )


class ExecuteView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._message: discord.Message = await self.ctx.send(view=self)
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

    @discord.ui.button(label=_("Execute Debug"), custom_id="execute_debug")
    async def execute_debug(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            ExecuteModal(cog=self.cog, ctx=self.ctx, choice="debug")
        )

    @discord.ui.button(label=_("Execute Eval"), custom_id="execute_eval")
    async def execute_eval(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            ExecuteModal(cog=self.cog, ctx=self.ctx, choice="eval")
        )

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
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

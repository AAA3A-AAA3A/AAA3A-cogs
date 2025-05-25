from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import random

_: Translator = Translator("BotSaysGame", __file__)


WORDS: typing.List[str] = [
    "apple",
    "school",
    "home",
    "car",
    "computer",
    "dog",
    "cat",
    "house",
    "tree",
    "phone",
    "book",
    "table",
    "chair",
    "window",
    "door",
    "light",
    "fan",
    "television",
    "because",
]
REACTIONS: typing.List[str] = [
    "👍",
    "👎",
    "😂",
    "😢",
    "😡",
    "😍",
    "😱",
    "🤔",
    "🙄",
    "😴",
    "😜",
    "😎",
    "😇",
    "😈",
    "🤖",
    "👻",
]


def get_on_message_without_command_listener(test: "Test") -> typing.Callable:
    async def on_message_without_command(message: discord.Message) -> None:
        if (
            message.guild is not None
            and message.author in test.players
            and message.channel == test.ctx.channel
        ):
            await test.check(message.author, message.content.lower().strip())
    return on_message_without_command


class Test:
    def __init__(self, ctx: commands.Context, players: typing.List[discord.Member]) -> None:
        self.ctx: commands.Context = ctx
        self.players: discord.Member = players
        self.lowered_time: bool = False

        self.answer: typing.Optional[str] = None
        self.listener: typing.Optional[typing.Callable] = None
        self.success: typing.List[discord.Member] = []
        self.fail: typing.List[discord.Member] = []

    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        raise NotImplementedError()

    async def check(self, player: discord.Member, answer: typing.Optional[str]) -> None:
        if player in self.success or player in self.fail:
            return
        if answer is None or await self.answer_check(player, answer):
            self.success.append(player)
            return
        self.fail.append(player)

    async def answer_check(self, player: discord.Member, answer: str) -> None:
        return answer == self.answer

    async def get_eliminated_players(self) -> typing.List[discord.Member]:
        if self.listener is not None:
            self.ctx.bot.remove_listener(self.listener)
        return [player for player in self.players if player not in self.success]


class BaseView(discord.ui.View):
    def __init__(self, test: Test) -> None:
        super().__init__(timeout=20)
        self.test: Test = test
        self._message: discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user not in self.test.players:
            await interaction.response.send_message(
                _("You are not a player in this game or you are already eliminated during a previous round!"),
                ephemeral=True,
            )
            return False
        elif interaction.user in self.test.success:
            await interaction.response.send_message(
                _("You already succeeded in this round!"),
                ephemeral=True,
            )
            return False
        elif interaction.user in self.test.fail:
            await interaction.response.send_message(
                _("You are already eliminated!"),
                ephemeral=True,
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


class BaseModal(discord.ui.Modal):
    def __init__(self, test: Test) -> None:
        super().__init__(title="Bot Says Game")
        self.test: Test = test
        self.answer: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Your answer"),
            style=discord.TextStyle.short,
            required=True,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self.test.check(interaction.user, self.answer.value)


class ColorButtonTest(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        colors = ["green", "red", "blue", "dark"]
        self.answer = random.choice(colors)
        type = random.choice(["label", "style"])
        styles = [discord.ButtonStyle.success, discord.ButtonStyle.danger, discord.ButtonStyle.primary, discord.ButtonStyle.secondary]
        random.shuffle(colors)
        random.shuffle(styles)
        view: BaseView = BaseView(self)
        for label, style in zip(colors, styles):
            button: discord.ui.Button = discord.ui.Button(
                label=label.title(),
                style=style,
                custom_id=(
                    label
                    if type == "label" else
                    {
                        discord.ButtonStyle.success: "green",
                        discord.ButtonStyle.danger: "red",
                        discord.ButtonStyle.primary: "blue",
                        discord.ButtonStyle.secondary: "dark",
                    }[style]
                ),
            )
            async def callback(interaction: discord.Interaction) -> None:
                await interaction.response.defer()
                await self.check(interaction.user, interaction.data["custom_id"])
            button.callback = callback
            view.add_item(button)
        self.lowered_time = True
        return _("Press the {color} {type} button.").format(color=self.answer.title(), type=type), view, []


class SelectionTest(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        words = random.sample(WORDS, 5)
        self.answer = random.choice(words)
        view: BaseView = BaseView(self)
        select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Make a selection!"),
            options=[discord.SelectOption(label=word, value=word) for word in words],
        )
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            await self.check(interaction.user, interaction.data["values"][0])
        select.callback = callback
        view.add_item(select)
        self.lowered_time = True
        return _("Select {word} from the menu below.").format(word=self.answer), view, []


class WriteWordTest(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        self.answer = random.choice(WORDS)
        self.listener = get_on_message_without_command_listener(self)
        self.ctx.bot.add_listener(self.listener)
        return _("Write {word} here.").format(word=self.answer), None, []


class PingMemberTest(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        player = random.choice(self.players)
        self.answer = player.mention
        self.listener = get_on_message_without_command_listener(self)
        self.ctx.bot.add_listener(self.listener)
        return _("Ping __{player.name}__ here.").format(player=player), None, []


class QuickMath(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        self.answer = str(a - b)
        view: BaseView = BaseView(self)
        button: discord.ui.Button = discord.ui.Button(
            label=_("Submit!"),
            style=discord.ButtonStyle.secondary,
        )
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(BaseModal(self))
        button.callback = callback
        view.add_item(button)
        return _("Quick Math! {a} - {b} = ??").format(a=a, b=b), view, []


class ReactionTest(Test):
    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View]]:
        reactions = random.sample(REACTIONS, 5)
        self.answer = random.choice(reactions)
        async def on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None:
            if user in self.players and reaction.message.channel == self.ctx.channel:
                await self.check(user, reaction.emoji)
        self.listener = on_reaction_add
        self.ctx.bot.add_listener(self.listener)
        self.lowered_time = random.random() < 0.5
        return _("React to this message with {emoji}.").format(emoji=self.answer), None, (reactions if self.lowered_time else [])


class EnglishWordTest(Test):
    def __init__(self, ctx: commands.Context, players: typing.List[discord.Member]) -> None:
        super().__init__(ctx, players)
        self.previously_used_words: typing.List[str] = []
        self.used_words: typing.List[str] = []

    async def initialize(self) -> typing.Tuple[str, typing.Optional[discord.ui.View], typing.List[str]]:
        view: BaseView = BaseView(self)
        button: discord.ui.Button = discord.ui.Button(
            label=_("Submit!"),
            style=discord.ButtonStyle.secondary,
        )
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(BaseModal(self))
        button.callback = callback
        view.add_item(button)
        return _("Click the button then provide one ENGLISH word between five and ten letters in the box provided. You can only use each word once."), view, []

    async def answer_check(self, player: discord.Member, answer: str) -> None:
        if len(answer) < 5 or len(answer) > 10:
            return False
        if not answer.isalpha():
            return False
        if answer in self.previously_used_words:
            return False
        self.used_words.append(answer)
        return True


TESTS: typing.List[typing.Type[Test]] = [ColorButtonTest, SelectionTest, WriteWordTest, PingMemberTest, QuickMath, ReactionTest, EnglishWordTest]

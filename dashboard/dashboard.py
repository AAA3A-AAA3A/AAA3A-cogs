from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import argparse
import asyncio

# import importlib
# import sys
from fernet import Fernet

from .rpc import DashboardRPC

# Credits:
# General repo credits.
# Thank you very much to Neuro Assassin for the original code (https://github.com/NeuroAssassin/Toxic-Cogs/tree/master/dashboard)!

_ = Translator("Dashboard", __file__)


class StrConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return argument


class RedirectURIConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if not argument.startswith("http"):
            raise commands.BadArgument(_("This is not a valid URL."))
        if not argument.endswith("/callback"):
            raise commands.BadArgument(_("This is not a valid Dashboard redirect URI: it must end with `/callback`."))
        return argument


class ThirdPartyConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("Dashboard")
        if argument not in cog.rpc.third_parties_handler.third_parties:
            raise commands.BadArgument(_("This third party is not available."))
        return argument


@cog_i18n(_)
class Dashboard(Cog):
    """Interact with your bot through a web Dashboard!

    **Installation guide:** https://red-web-dashboard.readthedocs.io/en/latest
    ⚠️ This package is a fork of Neuro Assassin's work, and isn't endorsed by the Org at all.
    """

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["Neuro Assassin", "AAA3A"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.dashboard_global: typing.Dict[str, typing.Any] = {
            "CONFIG_SCHEMA": None,
            "all_in_one": False,
            "flask_flags": [],
            "webserver": {
                "core": {
                    "secret_key": None,
                    "jwt_secret_key": None,
                    "secret": None,
                    "redirect_uri": None,
                    "blacklisted_ips": [],
                },
                "ui": {
                    "meta": {
                        "title": None,
                        "icon": None,
                        "website_description": None,
                        "description": None,
                        "support_server": None,
                        "default_color": "success",
                        "default_background_theme": "white",
                        "default_sidenav_theme": "white",
                    },
                    "sidenav": [
                        {
                            "pos": 1,
                            "name": "builtin-home",
                            "icon": "ni ni-atom text-success",
                            "route": "base_blueprint.index",
                            "session": None,
                            "owner": False,
                            "locked": True,
                            "hidden": False,
                        },
                        {
                            "pos": 2,
                            "name": "builtin-commands",
                            "icon": "ni ni-bullet-list-67 text-danger",
                            "route": "base_blueprint.commands",
                            "session": None,
                            "owner": False,
                            "locked": False,
                            "hidden": False,
                        },
                        {
                            "pos": 3,
                            "name": "builtin-dashboard",
                            "icon": "ni ni-settings text-primary",
                            "route": "base_blueprint.dashboard",
                            "session": True,
                            "owner": False,
                            "locked": False,
                            "hidden": False,
                        },
                        {
                            "pos": 4,
                            "name": "builtin-third_parties",
                            "icon": "ni ni-diamond text-success",
                            "route": "third_parties_blueprint.third_parties",
                            "session": True,
                            "owner": False,
                            "locked": False,
                            "hidden": False,
                        },
                        {
                            "pos": 5,
                            "name": "builtin-admin",
                            "icon": "ni ni-badge text-danger",
                            "route": "base_blueprint.admin",
                            "session": True,
                            "owner": True,
                            "locked": True,
                            "hidden": False,
                        },
                        {
                            "pos": 6,
                            "name": "builtin-credits",
                            "icon": "ni ni-book-bookmark text-info",
                            "route": "base_blueprint.credits",
                            "session": None,
                            "owner": False,
                            "locked": True,
                            "hidden": False,
                        },
                        {
                            "pos": 7,
                            "name": "builtin-login",
                            "icon": "ni ni-key-25 text-success",
                            "route": "login_blueprint.login",
                            "session": False,
                            "owner": False,
                            "locked": True,
                            "hidden": False,
                        },
                        {
                            "pos": 8,
                            "name": "builtin-logout",
                            "icon": "ni ni-user-run text-warning",
                            "route": "login_blueprint.logout",
                            "session": True,
                            "owner": False,
                            "locked": True,
                            "hidden": False,
                        },
                    ],
                },
                "disabled_third_parties": [],
            },
        }
        self.config.register_global(**self.dashboard_global)

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "all_in_one": {
                "converter": bool,
                "description": "Run the Dashboard in the bot process, without having to open another window. You have to install Red-Dashboard in your bot venv with Pip and reload the cog.",
                "hidden": True, "no_slash": True,
            },
            "flask_flags": {
                "converter": commands.Greedy[StrConverter],
                "description": "The flags used to setting the webserver if `all_in_one` is enabled. They are the cli flags of `reddash` without `--rpc-port`.",
                "hidden": True, "no_slash": True,
            },
            "redirect_uri": {
                "converter": RedirectURIConverter,
                "description": "The redirect uri to use for the Discord Oauth.",
                "path": ["webserver", "core", "redirect_uri"],
                "aliases": ["redirect"],
            },
            "meta_title": {
                "converter": str,
                "description": "The website title to use.",
                "path": ["webserver", "ui", "meta", "title"],
            },
            "meta_icon": {
                "converter": str,
                "description": "The website icon to use.",
                "path": ["webserver", "ui", "meta", "icon"],
            },
            "meta_website_description": {
                "converter": str,
                "description": "The website short description to use.",
                "path": ["webserver", "ui", "meta", "website_description"],
            },
            "meta_description": {
                "converter": str,
                "description": "The website long description to use.",
                "path": ["webserver", "ui", "meta", "description"],
            },
            "support_server": {
                "converter": str,
                "description": "Set the support server url of your bot.",
                "path": ["webserver", "ui", "meta", "support_server"],
                "aliases": ["support"],
            },
            "default_color": {
                "converter": typing.Literal[
                    "success", "danger", "primary", "info", "warning", "dark"
                ],
                "description": "Set the default Color of the dashboard.",
                "path": ["webserver", "ui", "meta", "default_color"],
            },
            "default_background_theme": {
                "converter": typing.Literal["white", "dark"],
                "description": "Set the default Background theme of the dashboard.",
                "path": ["webserver", "ui", "meta", "default_background_theme"],
            },
            "default_sidenav_theme": {
                "converter": typing.Literal["white", "dark"],
                "description": "Set the default Sidenav theme of the dashboard.",
                "path": ["webserver", "ui", "meta", "default_sidenav_theme"],
            },
            "disabled_third_parties": {
                "converter": commands.Greedy[ThirdPartyConverter],
                "description": "The third parties to disable.",
                "path": ["webserver", "disabled_third_parties"],
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.setdashboard,
        )

        self.app: typing.Optional[typing.Any] = None
        self.rpc: DashboardRPC = DashboardRPC(bot=self.bot, cog=self)

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()
        await self.settings.add_commands()
        self.logger.info("Loading cog...")
        asyncio.create_task(self.create_app(flask_flags=await self.config.flask_flags()))

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            global_group = self.config._get_base_group(self.config.GLOBAL)
            async with global_group() as global_data:
                if "default_sidebar_theme" in global_data:
                    global_data["default_sidenav_theme"] = global_data.pop("default_sidebar_theme")
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.logger.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def cog_unload(self) -> None:
        self.logger.info("Unloading cog...")
        if self.app is not None and self.app.server_thread is not None:
            await asyncio.to_thread(self.app.server_thread.shutdown)
            await asyncio.to_thread(self.app.tasks_manager.stop_tasks)
        await super().cog_unload()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def create_app(self, flask_flags: str) -> None:
        await self.bot.wait_until_red_ready()
        if await self.config.webserver.core.secret_key() is None:
            await self.config.webserver.core.secret_key.set(Fernet.generate_key().decode())
        if await self.config.webserver.core.jwt_secret_key() is None:
            await self.config.webserver.core.jwt_secret_key.set(Fernet.generate_key().decode())
        if await self.config.all_in_one():
            try:
                # for module_name in ("flask", "reddash"):
                #     modules = sorted(
                #         [module for module in sys.modules if module.split(".")[0] == module_name], reverse=True
                #     )
                #     for module in modules:
                #         try:
                #             importlib.reload(sys.modules[module])
                #         except ModuleNotFoundError:
                #             pass
                from reddash import FlaskApp

                parser: argparse.ArgumentParser = argparse.ArgumentParser(exit_on_error=False)
                parser.add_argument("--host", dest="host", type=str, default="0.0.0.0")
                parser.add_argument("--port", dest="port", type=int, default=42356)
                # parser.add_argument("--rpc-port", dest="rpcport", type=int, default=6133)
                parser.add_argument(
                    "--interval", dest="interval", type=int, default=5, help=argparse.SUPPRESS
                )
                parser.add_argument(
                    "--development", dest="dev", action="store_true", help=argparse.SUPPRESS
                )
                # parser.add_argument("--instance", dest="instance", type=str, default=None)
                args = vars(parser.parse_args(args=flask_flags))
                self.app: FlaskApp = FlaskApp(cog=self, **args)
                await self.app.create_app()
            except Exception as e:
                self.logger.critical("Error when creating the Flask webserver app.", exc_info=e)

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command()
    async def dashboard(self, ctx: commands.Context) -> None:
        """Get the link to the Dashboard."""
        if (dashboard_url := getattr(ctx.bot, "dashboard_url", None)) is None:
            raise commands.UserFeedbackCheckFailure(_("Red-Dashboard is not installed. Check <https://red-web-dashboard.readthedocs.io>."))
        if not dashboard_url[1] and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't access the Dashboard."))
        embed: discord.Embed = discord.Embed(
            title=_("Red-Dashboard"),
            color=await ctx.embed_color(),
        )
        url = dashboard_url[0]
        if ctx.guild is not None and (ctx.author.id in ctx.bot.owner_ids or await self.bot.is_mod(ctx.author)):
            url += f"/dashboard/{ctx.guild.id}"
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.url = url
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.hybrid_group()
    async def setdashboard(self, ctx: commands.Context) -> None:
        """Configure Dashboard."""
        pass

    @setdashboard.command()
    async def secret(self, ctx: commands.Context, *, secret: str = None):
        """Set the client secret needed for Discord Oauth."""
        if secret is not None:
            await self.config.webserver.core.secret.set(secret)
            return

        class SecretModal(discord.ui.Modal):
            def __init__(_self) -> None:
                super().__init__(title="Discord OAuth Secret")
                _self.secret: discord.ui.TextInput = discord.ui.TextInput(
                    label=_("Discord Secret"),
                    style=discord.TextStyle.short,
                    custom_id="discord_secret",
                )
                _self.add_item(_self.secret)

            async def on_submit(_self, interaction: discord.Interaction) -> None:
                await self.config.webserver.core.secret.set(_self.secret.value)
                await interaction.response.send_message(_("Discord OAuth secret set."))

        class SecretView(discord.ui.View):
            def __init__(_self) -> None:
                super().__init__()
                _self._message: discord.Message = None

            async def on_timeout(_self) -> None:
                for child in _self.children:
                    child: discord.ui.Item
                    if hasattr(child, "disabled") and not (
                        isinstance(child, discord.ui.Button)
                        and child.style == discord.ButtonStyle.url
                    ):
                        child.disabled = True
                try:
                    await _self._message.edit(view=_self)
                except discord.HTTPException:
                    pass

            async def interaction_check(_self, interaction: discord.Interaction) -> bool:
                if interaction.user.id not in [ctx.author.id] + list(ctx.bot.owner_ids):
                    await interaction.response.send_message(
                        "You are not allowed to use this interaction.", ephemeral=True
                    )
                    return False
                return True

            @discord.ui.button(label=_("Set Discord OAuth Secret"))
            async def set_secret_button(
                _self, interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                await interaction.response.send_modal(SecretModal())

        view = SecretView()
        view._message = await ctx.send(
            _("Click on the button below to set a secret for Discord OAuth."), view=view
        )

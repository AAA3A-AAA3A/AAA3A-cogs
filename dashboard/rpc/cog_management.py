from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list, inline

from unittest.mock import patch

from .utils import rpc_check

_: Translator = Translator("Dashboard", __file__)


class FakeContext:
    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.contents: typing.List[str] = []

    async def send(self, message: str, **kwargs) -> None:
        self.contents.append(message)

    def get_notifications(self) -> typing.List[typing.Dict[str, str]]:
        content = "\n".join(self.contents)
        notifications = []
        for line in content.split("\n"):
            if not line:
                continue
            elif line.startswith((_("Successfully"), _("Pinned"), _("Enabled"), _("Disabled"))) or _("successfully") in line:
                notifications.append({"message": line, "category": "success"})
            elif (
                line.startswith((_("Failed"), _("Something went wrong")))
                or _("Couldn't") in line or _("could not be found") in line
                or "reached" in line or "exceeding" in line
            ):
                notifications.append({"message": line, "category": "danger"})
            elif line.lstrip().startswith(("-", "**", "`")):
                notifications[-1]["message"] += f"\n{line}"
            else:
                notifications.append({"message": line, "category": "info"})
        return notifications

    @property
    def assume_yes(self) -> bool:
        return True

    @property
    def prefix(self) -> str:
        return "[p]"

    @property
    def clean_prefix(self) -> str:
        return "[p]"

    @property
    def me(self) -> str:
        return self.bot.user

    def typing(self) -> typing.AsyncContextManager:
        return self

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


class DashboardRPC_CogManagement:
    def __init__(self, cog: commands.Cog) -> None:
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        # Cogs.
        self.bot.register_rpc_handler(self.get_cogs)
        self.bot.register_rpc_handler(self.set_cogs)
        # Downloader.
        self.bot.register_rpc_handler(self.get_repos)
        self.bot.register_rpc_handler(self.add_repo)
        self.bot.register_rpc_handler(self.update_repos)
        self.bot.register_rpc_handler(self.update_cogs)
        self.bot.register_rpc_handler(self.update_repo)
        self.bot.register_rpc_handler(self.update_cogs_from_repo)
        self.bot.register_rpc_handler(self.remove_repo)
        self.bot.register_rpc_handler(self.install_cog)
        self.bot.register_rpc_handler(self.update_cog)
        self.bot.register_rpc_handler(self.pin_or_unpin_cog)
        self.bot.register_rpc_handler(self.uninstall_cog)
        # Application commands.
        self.bot.register_rpc_handler(self.get_application_commands)
        self.bot.register_rpc_handler(self.sync_application_commands)
        self.bot.register_rpc_handler(self.set_application_commands)

    def unload(self) -> None:
        # Cogs.
        self.bot.unregister_rpc_handler(self.get_cogs)
        self.bot.unregister_rpc_handler(self.set_cogs)
        # Downloader.
        self.bot.unregister_rpc_handler(self.get_repos)
        self.bot.unregister_rpc_handler(self.add_repo)
        self.bot.unregister_rpc_handler(self.update_repos)
        self.bot.unregister_rpc_handler(self.update_cogs)
        self.bot.unregister_rpc_handler(self.update_repo)
        self.bot.unregister_rpc_handler(self.update_cogs_from_repo)
        self.bot.unregister_rpc_handler(self.remove_repo)
        self.bot.unregister_rpc_handler(self.install_cog)
        self.bot.unregister_rpc_handler(self.update_cog)
        self.bot.unregister_rpc_handler(self.pin_or_unpin_cog)
        self.bot.unregister_rpc_handler(self.uninstall_cog)
        # Application commands.
        self.bot.unregister_rpc_handler(self.get_application_commands)
        self.bot.unregister_rpc_handler(self.sync_application_commands)
        self.bot.unregister_rpc_handler(self.set_application_commands)

    @rpc_check()
    async def get_cogs(
        self, user_id: int
    ) -> typing.Dict[str, typing.Union[int, typing.Dict[str, bool]]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        all_cogs = await self.bot._cog_mgr.available_modules()
        loaded_cogs = self.bot.extensions.keys()
        return {
            "status": 0,
            "cogs": dict(
                sorted(
                    {cog: cog in loaded_cogs for cog in all_cogs}.items(),
                    key=lambda cog: (not cog[1], cog[0].lower()),
                )
            ),
        }

    @rpc_check()
    async def set_cogs(
        self, user_id: int, cogs: typing.Dict[str, bool]
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        all_cogs = set(await self.bot._cog_mgr.available_modules())
        loaded_cogs = set(self.bot.extensions.keys())
        status, notifications = 0, []

        if to_load := [
            cog
            for cog, loaded in cogs.items()
            if cog in all_cogs and loaded and cog not in loaded_cogs
        ]:
            outcomes = await self.bot.get_cog("Core")._load(to_load)
            if loaded := outcomes.get("loaded_packages"):
                notifications.append(
                    {
                        "message": _("Loaded: {packs}.").format(
                            packs=humanize_list([inline(package) for package in loaded]),
                        ),
                        "category": "success",
                    }
                )
            if failed := outcomes.get("failed_packages"):
                status = 1
                notifications.append(
                    {
                        "message": _("Failed to load: {packs}. Check logs for details.").format(
                            packs=humanize_list([inline(package) for package in failed]),
                        ),
                        "category": "danger",
                    }
                )
            if failed_with_reason := outcomes.get("failed_with_reason_packages"):
                status = 1
                reasons = "\n".join(
                    [
                        f"{inline(package)}: {reason}"
                        for package, reason in failed_with_reason.items()
                    ]
                )
                notifications.append(
                    {
                        "message": _("Failed with reasons:\n{reasons}").format(reasons=reasons),
                        "category": "danger",
                    }
                )

        if to_unload := [
            cog
            for cog, loaded in cogs.items()
            if cog in all_cogs and not loaded and cog in loaded_cogs
        ]:
            outcomes = await self.bot.get_cog("Core")._unload(to_unload)
            if unloaded := outcomes.get("unloaded_packages"):
                notifications.append(
                    {
                        "message": _("Unloaded: {packs}.").format(
                            packs=humanize_list([inline(package) for package in unloaded]),
                        ),
                        "category": "success",
                    }
                )

        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def get_repos(
        self, user_id: int, include_data: bool = True
    ) -> typing.Dict[str, typing.Union[int, typing.List[typing.Dict[str, str]]]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if not include_data:
            return {
                "status": 0,
                "repos": [
                    repo.name
                    for repo in Downloader._repo_manager.repos
                ],
            }
        return {
            "status": 0,
            "repos": [
                {
                    "name": repo.name,
                    "url": repo.url,
                    "branch": repo.branch,
                    "author": humanize_list(repo.author) if repo.author else "Unknown",
                    "description": repo.description,
                    "current_commit": await repo.current_commit(),
                    "available_cogs": dict(
                        sorted(
                            {
                                cog.name: {
                                    "installed": (
                                        installed := discord.utils.get(
                                            await Downloader.installed_cogs(),
                                            repo_name=repo.name,
                                            name=cog.name,
                                        )
                                    )
                                    is not None,
                                    "pinned": installed.pinned if installed is not None else False,
                                    "hidden": cog.hidden,
                                    "short_description": cog.short,
                                    "description": cog.description,
                                    "author": humanize_list(cog.author) if cog.author else None,
                                    "tags": humanize_list([inline(tag) for tag in cog.tags]),
                                    "requirements": humanize_list(
                                        [inline(req) for req in cog.requirements]
                                    ),
                                    "end_user_data_statement": cog.end_user_data_statement,
                                }
                                for cog in repo.available_cogs
                                if not cog.disabled
                            }.items(),
                            key=lambda cog: (
                                not cog[1]["installed"],
                                cog[1]["hidden"],
                                cog[0].lower(),
                            ),
                        )
                    ),
                }
                for repo in sorted(
                    Downloader._repo_manager.repos,
                    key=lambda repo: repo.name.lower(),
                )
            ],
        }

    @rpc_check()
    async def add_repo(
        self,
        user_id: int,
        name: str,
        repo_url: str,
        branch: typing.Optional[str] = None,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        fake_ctx = FakeContext(self.bot)
        await Downloader._repo_add(
            fake_ctx,
            name=name,
            repo_url=repo_url,
            branch=branch,
        )
        notifications = fake_ctx.get_notifications()
        status = int(any(notification["category"] == "danger" for notification in notifications))
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def update_repos(self, user_id: int) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        fake_ctx = FakeContext(self.bot)
        await Downloader._repo_update(fake_ctx)
        notifications = fake_ctx.get_notifications()
        status = int(any(notification["category"] == "danger" for notification in notifications))
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def update_cogs(self, user_id: int) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        fake_ctx = FakeContext(self.bot)
        await Downloader._cog_update_logic(
            fake_ctx,
        )
        notifications = fake_ctx.get_notifications()
        status = int(any(notification["category"] == "danger" for notification in notifications))
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def update_repo(
        self, user_id: int, name: str
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        repo = Downloader._repo_manager.get_repo(name)
        if repo is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await Downloader._repo_update(
                fake_ctx,
                repo,
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def update_cogs_from_repo(
        self, user_id: int, name: str
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if (repo := Downloader._repo_manager.get_repo(name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await Downloader._cog_update_logic(
                fake_ctx,
                repo=repo,
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def remove_repo(
        self, user_id: int, name: str
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if Downloader._repo_manager.get_repo(name) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        else:
            await Downloader._repo_manager.delete_repo(name)
            notifications = [
                {
                    "message": _("Repo {name} successfully removed.").format(name=inline(name)),
                    "category": "success",
                },
            ]
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def install_cog(
        self,
        user_id: int,
        repo_name: str,
        name: str,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if (repo := Downloader._repo_manager.get_repo(repo_name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await Downloader._cog_installrev(
                fake_ctx,
                repo=repo,
                rev=None,
                cog_names=[name],
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def update_cog(
        self,
        user_id: int,
        repo_name: str,
        name: str,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if (repo := Downloader._repo_manager.get_repo(repo_name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif (cog := discord.utils.get(await Downloader.installed_cogs(), name=name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The cog name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif cog.repo != repo:
            status, notifications = 1, [
                {
                    "message": _(
                        "The cog you provided isn't installed from the repo you provided."
                    ),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await Downloader._cog_update_logic(
                fake_ctx,
                cogs=[cog],
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def pin_or_unpin_cog(
        self,
        user_id: int,
        repo_name: str,
        name: str,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if (repo := Downloader._repo_manager.get_repo(repo_name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif (cog := discord.utils.get(await Downloader.installed_cogs(), name=name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The cog name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif cog.repo != repo:
            status, notifications = 1, [
                {
                    "message": _(
                        "The cog you provided isn't installed from the repo you provided."
                    ),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await (Downloader._cog_pin if not cog.pinned else Downloader._cog_unpin)(
                fake_ctx,
                cog,
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def uninstall_cog(
        self,
        user_id: int,
        repo_name: str,
        name: str,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        if (Downloader := self.bot.get_cog("Downloader")) is None:
            return {"status": 1}
        if (repo := Downloader._repo_manager.get_repo(repo_name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The repo name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif (cog := discord.utils.get(await Downloader.installed_cogs(), name=name)) is None:
            status, notifications = 1, [
                {
                    "message": _("The cog name you provided does not exist."),
                    "category": "danger",
                },
            ]
        elif cog.repo != repo:
            status, notifications = 1, [
                {
                    "message": _(
                        "The cog you provided isn't installed from the repo you provided."
                    ),
                    "category": "danger",
                },
            ]
        else:
            fake_ctx = FakeContext(self.bot)
            await Downloader._cog_uninstall(
                fake_ctx,
                cog,
            )
            notifications = fake_ctx.get_notifications()
            status = int(
                any(notification["category"] == "danger" for notification in notifications)
            )
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def get_application_commands(
        self, user_id: int,
    ) -> typing.Dict[str, typing.Union[int, typing.Dict[str, typing.List[typing.Dict[typing.Literal["type", "name"], str]]]]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        command = self.bot.get_command("slash list")
        callback = command.callback
        content = ""
        async def fake_menu(ctx, pages):
            nonlocal content
            content = "\n".join([page[8:-4] for page in pages])
        with patch.dict(callback.__globals__, {"menu": fake_menu}):
            await callback(command.cog, FakeContext(self.bot))
        return {
            "status": 0,
            "application_commands": {
                    module.split("\n")[0]: [
                    {
                        "type": element.split("|")[0][1:].strip(),
                        "name": element.split("|")[1].strip(),
                        "enabled": element[0] == "+",
                    }
                    for element in module.split("\n")[1:]
                ]
                for module in content.split("\n\n")
            },
        }

    @rpc_check()
    async def sync_application_commands(
        self, user_id: int,
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        try:
            commands = await self.bot.tree.sync()
        except Exception as e:
            status, notifications = 1, [
                {
                    "message": _("Failed to sync commands: {error}").format(error=str(e)),
                    "category": "danger",
                },
            ]
        else:
            status, notifications = 0, [
                {
                    "message": _("Synced {count} commands.").format(count=len(commands)),
                    "category": "success",
                },
            ]
        return {
            "status": status,
            "notifications": notifications,
        }

    @rpc_check()
    async def set_application_commands(
        self, user_id: int, commands: typing.Dict[str, typing.List[typing.Dict[str, str]]]
    ) -> typing.Dict[str, typing.Union[int, str]]:
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        application_commands = (await self.get_application_commands(user_id))["application_commands"]
        Core = self.bot.get_cog("Core")
        fake_ctx = FakeContext(self.bot)
        for module, elements in commands.items():
            if all(
                element["enabled"] for element in elements
            ) and any(not element["enabled"] for element in application_commands[module]):
                await Core.slash_enablecog(fake_ctx, module)
            elif all(
                not element["enabled"] for element in elements
            ) and any(element["enabled"] for element in application_commands[module]):
                await Core.slash_disablecog(fake_ctx, module)
            else:
                for element in elements:
                    if (
                        current_state := next(
                            (x for x in application_commands[module] if x["name"] == element["name"]), None
                        )
                    ) is None:
                        continue
                    if element["enabled"] and not current_state["enabled"]:
                        await Core.slash_enable(fake_ctx, element["name"], element["type"])
                    elif not element["enabled"] and current_state["enabled"]:
                        await Core.slash_disable(fake_ctx, element["name"], element["type"])
        notifications = fake_ctx.get_notifications()
        status = int(
            any(notification["category"] == "danger" for notification in notifications)
        )
        return {
            "status": status,
            "notifications": notifications,
        }

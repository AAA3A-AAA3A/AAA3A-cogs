from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import base64
import inspect
import types

from redbot.core.i18n import get_locale_from_guild, set_contextual_locale, set_regional_format
from werkzeug.datastructures import ImmutableMultiDict

from .form import INITIAL_INIT_FIELD, Field, get_form_class
from .pagination import Pagination
from .utils import rpc_check


def dashboard_page(
    name: typing.Optional[str] = None,
    description: typing.Optional[str] = None,
    methods: typing.Tuple[str] = ("GET",),
    context_ids: typing.List[str] = None,
    required_kwargs: typing.List[str] = None,
    optional_kwargs: typing.List[str] = None,
    is_owner: bool = False,
    hidden: typing.Optional[bool] = None,
):
    if context_ids is None:
        context_ids = []
    if required_kwargs is None:
        required_kwargs = []
    if optional_kwargs is None:
        optional_kwargs = []

    def decorator(func: typing.Callable):
        if name is not None:
            if not isinstance(name, str):
                raise TypeError("Name of a page must be a string.")
            discord.app_commands.commands.validate_name(name)
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Func must be a coroutine.")

        params = {
            "name": name,
            "description": description or func.__doc__,
            "methods": methods,
            "context_ids": context_ids,
            "required_kwargs": required_kwargs,
            "optional_kwargs": optional_kwargs,
            "is_owner": is_owner,
            "hidden": hidden,
        }
        for key, value in inspect.signature(func).parameters.items():
            if value.name == "self" or value.kind in (
                inspect._ParameterKind.POSITIONAL_ONLY,
                inspect._ParameterKind.VAR_KEYWORD,
            ):
                continue
            if value.default is not inspect._empty:
                params["optional_kwargs"].append(key)
                continue
            if (
                key in ("user_id", "guild_id", "member_id", "role_id", "channel_id")
                and key not in params["context_ids"]
            ):
                params["context_ids"].append(key)
            elif f"{key}_id" in ("user_id", "guild_id", "member_id", "role_id", "channel_id"):
                if f"{key}_id" not in params["context_ids"]:
                    params["context_ids"].append(f"{key}_id")
            elif key not in (
                "method",
                "request_url",
                "csrf_token",
                "wtf_csrf_secret_key",
                "extra_kwargs",
                "data",
                "lang_code",
                "Form",
                "DpyObjectConverter",
                "Pagination",
            ):
                params["required_kwargs"].append(key)

        # A guild must be chose for these kwargs.
        if "guild_id" not in params["context_ids"]:
            for key in ("member_id", "role_id", "channel_id"):
                if key in params["context_ids"]:
                    params["context_ids"].append("guild_id")
                    break

        # No method `GET`, no guild available and no owner check without user connection.
        if "user_id" not in params["context_ids"] and (
            "guild_id" in params["context_ids"] or is_owner
        ):
            params["context_ids"].append("user_id")
        if params["hidden"] is None:
            params["hidden"] = (
                "GET" not in methods
                or params["required_kwargs"]
                or any(x for x in params["context_ids"] if x not in ("user_id", "guild_id"))
            )

        func.__dashboard_params__ = params.copy()
        return func

    return decorator


class DashboardRPC_ThirdParties:
    def __init__(self, cog: commands.Cog) -> None:
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.third_parties: typing.Dict[
            str, typing.Dict[str, typing.Tuple[typing.Callable, typing.Dict[str, bool]]]
        ] = {}
        self.third_parties_cogs: typing.Dict[str, commands.Cog] = {}

        self.bot.register_rpc_handler(self.oauth_receive)
        self.bot.register_rpc_handler(self.get_third_parties)
        self.bot.register_rpc_handler(self.data_receive)
        self.bot.add_listener(self.on_cog_add)
        self.bot.add_listener(self.on_cog_remove)
        self.bot.dispatch("dashboard_cog_add", self.cog)

    def unload(self) -> None:
        self.bot.dispatch("dashboard_cog_remove", self.cog)
        self.bot.unregister_rpc_handler(self.oauth_receive)
        self.bot.unregister_rpc_handler(self.get_third_parties)
        self.bot.unregister_rpc_handler(self.data_receive)
        self.bot.remove_listener(self.on_cog_add)
        self.bot.remove_listener(self.on_cog_remove)

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog) -> None:
        ev = "on_dashboard_cog_add"
        funcs = [listener[1] for listener in cog.get_listeners() if listener[0] == ev]
        for func in funcs:
            self.bot._schedule_event(func, ev, self.cog)  # Like in `bot.dispatch`.

    @commands.Cog.listener()
    async def on_cog_remove(self, cog: commands.Cog) -> None:
        if cog not in self.third_parties_cogs.values():
            return
        self.remove_third_party(cog)

    def add_third_party(self, cog: commands.Cog, overwrite: bool = False) -> None:
        name = cog.qualified_name
        if name in self.third_parties and not overwrite:
            raise RuntimeError(f"`{name}` is already an existing third party.")
        _pages = {}
        for attr in dir(cog):
            try:
                if hasattr((func := getattr(cog, attr)), "__dashboard_decorator_params__"):
                    setattr(
                        cog,
                        attr,
                        types.MethodType(
                            dashboard_page(
                                *func.__dashboard_decorator_params__[0],
                                **func.__dashboard_decorator_params__[1],
                            )(func.__func__),
                            func.__self__,
                        ),
                    )
                if hasattr((func := getattr(cog, attr)), "__dashboard_params__"):
                    page = func.__dashboard_params__["name"]
                    if page in _pages:
                        raise RuntimeError(
                            f"The page {page} is already an existing page for this third party."
                        )
                    _pages[page] = (func, func.__dashboard_params__)
            except TypeError:
                continue
        if not _pages:
            raise RuntimeError("No page found.")
        self.third_parties[name] = _pages
        self.third_parties_cogs[name] = cog

    def remove_third_party(
        self, cog: commands.Cog
    ) -> typing.Dict[str, typing.Tuple[typing.Callable, typing.Dict[str, bool]]]:
        name = cog.qualified_name
        try:
            del self.third_parties_cogs[name]
        except KeyError:
            pass
        return self.third_parties.pop(name, None)

    @rpc_check()
    async def oauth_receive(
        self, user_id: int, payload: typing.Dict[str, str]
    ) -> typing.Dict[str, int]:
        self.bot.dispatch("oauth_receive", user_id, payload)
        return {"status": 0}

    @rpc_check()
    async def get_third_parties(
        self,
    ) -> typing.Dict[str, typing.Dict[str, typing.Tuple[typing.Callable, typing.Dict[str, bool]]]]:
        return {
            key: {k: v[1] for k, v in value.items()} for key, value in self.third_parties.items()
        }

    @rpc_check()
    async def data_receive(
        self,
        method: typing.Literal["HEAD", "GET", "OPTIONS", "POST", "PATCH", "DELETE"],
        name: str,
        page: str,
        request_url: str,
        csrf_token: typing.Tuple[str, str],
        wtf_csrf_secret_key: str,
        context_ids: typing.Optional[typing.Dict[str, int]] = None,
        required_kwargs: typing.Dict[str, typing.Any] = None,
        optional_kwargs: typing.Dict[str, typing.Any] = None,
        extra_kwargs: typing.Dict[str, typing.Any] = None,
        data: typing.Dict[typing.Literal["form", "json"], typing.Dict[str, typing.Any]] = None,
        lang_code: typing.Optional[str] = None,
    ) -> typing.Dict[str, typing.Any]:
        if context_ids is None:
            context_ids = {}
        if required_kwargs is None:
            required_kwargs = {}
        if optional_kwargs is None:
            optional_kwargs = {}
        if extra_kwargs is None:
            extra_kwargs = {}
        if data is None:
            data = {"form": {}, "json": {}}
        kwargs = {}
        if not name or name not in self.third_parties or name not in self.third_parties_cogs:
            return {
                "status": 1,
                "message": "Third party not found.",
                "error_code": 404,
                "error_message": "Looks like that third party doesn't exist... Strange...",
            }
        if self.bot.get_cog(self.third_parties_cogs[name].qualified_name) is None:
            return {
                "status": 1,
                "message": "Third party not loaded.",
                "error_code": 404,
                "error_message": "Looks like that third party doesn't exist... Strange...",
            }
        page = page.lower() if page is not None else page
        if page not in self.third_parties[name]:
            return {
                "status": 1,
                "message": "Page not found.",
                "error_code": 404,
                "error_message": "Looks like that page doesn't exist... Strange...",
            }
        if "user_id" in self.third_parties[name][page][1]["context_ids"]:
            if (user := self.bot.get_user(context_ids["user_id"])) is None:
                return {
                    "status": 1,
                    "message": "Forbidden access.",
                    "error_code": 404,
                    "error_message": "Looks like that I do not share any server with you...",
                }
            kwargs["user_id"] = context_ids["user_id"]
            kwargs["user"] = user
            if (
                self.third_parties[name][page][1]["is_owner"]
                and context_ids["user_id"] not in self.bot.owner_ids
            ):
                return {
                    "status": 1,
                    "message": "Forbidden access.",
                    "error_code": 403,
                    "error_message": "You must be the owner of the bot to access this page.",
                }
        if (
            "guild_id" in self.third_parties[name][page][1]["context_ids"]
            and "user_id" in self.third_parties[name][page][1]["context_ids"]
        ):
            if (guild := self.bot.get_guild(context_ids["guild_id"])) is None:
                return {
                    "status": 1,
                    "message": "Forbidden access.",
                    "error_code": 404,
                    "error_message": "Looks like that I'm not in this server...",
                }
            if (
                context_ids["user_id"] not in self.bot.owner_ids
                and guild.get_member(context_ids["user_id"]) is None
            ):
                return {
                    "status": 1,
                    "message": "Forbidden access.",
                    "error_code": 403,
                    "error_message": "Looks like that you're not in this server...",
                }
            kwargs["guild_id"] = context_ids["guild_id"]
            kwargs["guild"] = guild
            if "member_id" in self.third_parties[name][page][1]["context_ids"]:
                if (member := guild.get_member(context_ids["member_id"])) is None:
                    return {
                        "status": 1,
                        "message": "Forbidden access.",
                        "error_code": 403,
                        "error_message": "Looks like that this member is not found in this guild...",
                    }
                kwargs["member_id"] = context_ids["member_id"]
                kwargs["member"] = member
            if "role_id" in self.third_parties[name][page][1]["context_ids"]:
                if (role := guild.get_role(context_ids["role_id"])) is None:
                    return {
                        "status": 1,
                        "message": "Forbidden access.",
                        "error_code": 404,
                        "error_message": "Looks like that this role is not found in this guild...",
                    }
                kwargs["role_id"] = context_ids["role_id"]
                kwargs["role"] = role
            if "channel_id" in self.third_parties[name][page][1]["context_ids"]:
                if (channel := guild.get_channel(context_ids["channel_id"])) is None:
                    return {
                        "status": 1,
                        "message": "Forbidden access.",
                        "error_code": 404,
                        "error_message": "Looks like that this channel is not found in this guild...",
                    }
                kwargs["channel_id"] = context_ids["channel_id"]
                kwargs["channel"] = channel
        for key, value in required_kwargs.items():
            kwargs[key] = value
        for key, value in optional_kwargs.items():
            if key not in kwargs:
                kwargs[key] = value
        kwargs["method"] = method
        kwargs["request_url"] = request_url
        kwargs["csrf_token"] = tuple(csrf_token)
        kwargs["wtf_csrf_secret_key"] = base64.urlsafe_b64decode(wtf_csrf_secret_key)
        kwargs["extra_kwargs"] = extra_kwargs
        kwargs["data"] = {
            "form": ImmutableMultiDict(data["form"]),
            "json": ImmutableMultiDict(data["json"]),
        }
        kwargs["lang_code"] = lang_code or await get_locale_from_guild(
            self.bot, guild=kwargs.get("guild")
        )
        set_contextual_locale(kwargs["lang_code"])
        set_regional_format(kwargs["lang_code"])

        (
            kwargs["Form"],
            kwargs["DpyObjectConverter"],
            extra_notifications,
            kwargs["get_sorted_channels"],
            kwargs["get_sorted_roles"],
        ) = await get_form_class(self, third_party_cog=self.third_parties_cogs[name], **kwargs)
        kwargs["Pagination"] = Pagination

        result = await self.third_parties[name][page][0](**kwargs)
        if "web_content" in result and isinstance(result["web_content"], typing.Dict):
            for key, value in result["web_content"].items():
                if isinstance(value, kwargs["Form"]):
                    result["web_content"][key] = str(value)
                elif isinstance(value, Pagination):
                    result["web_content"][key] = value.to_dict()
        setattr(Field, "__init__", INITIAL_INIT_FIELD)
        result.setdefault("notifications", [])
        result["notifications"].extend(extra_notifications)
        return result

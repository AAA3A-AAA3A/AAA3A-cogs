from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import hmac
import inspect

from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from markupsafe import Markup
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import cached_property
from wtforms import (
    Field,
    Form,
    FormField,
    HiddenField,
    SelectFieldBase,
    SelectMultipleField,
    SubmitField,
    BooleanField,
)  # NOQA
from wtforms.csrf.core import CSRF
from wtforms.fields.core import UnboundField
from wtforms.meta import DefaultMeta
from wtforms.validators import ValidationError
from wtforms.widgets import HiddenInput

INITIAL_INIT_FIELD = Field.__init__


async def get_form_class(
    _self,
    third_party_cog: commands.Cog,
    method: typing.Literal["HEAD", "GET", "OPTIONS", "POST", "PATCH", "DELETE"],
    csrf_token: typing.Tuple[str, str],
    wtf_csrf_secret_key: bytes,
    data: typing.Dict[typing.Literal["form", "json"], typing.Dict[str, typing.Any]],
    **kwargs,
):
    extra_notifications = []
    _Auto = object()

    def _is_submitted() -> bool:
        return method in {"POST", "PUT", "PATCH", "DELETE"}

    class _FlaskFormCSRF(CSRF):
        def setup_form(self, form) -> typing.List[typing.Tuple[str, UnboundField]]:
            self.meta = form.meta
            return super().setup_form(form)

        def generate_csrf_token(self, csrf_token_field) -> str:
            return csrf_token[1]

        def validate_csrf_token(self, form, field) -> None:
            # At this point, the CSRF token should be already validated by the webserver because of the field name in `request.form`.
            data = field.data
            secret_key = self.meta.csrf_secret
            time_limit = self.meta.csrf_time_limit
            if not data:
                raise ValidationError("The CSRF token is missing.")
            s = URLSafeTimedSerializer(secret_key, salt="wtf-csrf-token")
            try:
                token = s.loads(data, max_age=time_limit)
            except SignatureExpired as e:
                raise ValidationError("The CSRF token has expired.") from e
            except BadData as e:
                raise ValidationError("The CSRF token is invalid.") from e
            if not hmac.compare_digest(csrf_token[0], token):
                raise ValidationError("The CSRF tokens do not match.")

    class FlaskForm(Form):
        class Meta(DefaultMeta):
            csrf_class = _FlaskFormCSRF

            @cached_property
            def csrf(self) -> bool:
                return True

            @cached_property
            def csrf_secret(self) -> bytes:
                return wtf_csrf_secret_key

            @cached_property
            def csrf_time_limit(self) -> int:
                return 3600

            def wrap_formdata(self, form, formdata) -> typing.Optional[ImmutableMultiDict]:
                if formdata is _Auto:
                    if _is_submitted():
                        if data["form"]:
                            return ImmutableMultiDict(data["form"])
                        elif data["json"]:
                            return ImmutableMultiDict(data["json"])
                    return None
                return formdata

        def __init__(self, formdata=_Auto, **kwargs) -> None:
            super().__init__(formdata=formdata, **kwargs)

        def is_submitted(self) -> bool:
            return _is_submitted()

        def validate_on_submit(self, extra_validators=None) -> bool:
            if self.is_submitted() and self.validate(extra_validators=extra_validators):
                return True
            if any(field.data for field in self if isinstance(field, SubmitField)) and self.errors:
                for field_name, error_messages in self.errors.items():
                    if isinstance(error_messages[0], typing.Dict):
                        for sub_field_name, sub_error_messages in error_messages[0].items():
                            extra_notifications.append(
                                {
                                    "message": f"{field_name}-{sub_field_name}: {' '.join(sub_error_messages)}",
                                    "category": "warning",
                                }
                            )
                        continue
                    extra_notifications.append(
                        {
                            "message": f"{field_name}: {' '.join(error_messages)}",
                            "category": "warning",
                        }
                    )
            return False

        async def validate_dpy_converters(self) -> bool:
            result = True
            for field in self:
                for validator in field.validators:
                    if not isinstance(validator, DpyObjectConverter):
                        continue
                    if isinstance(field, SelectMultipleField):
                        try:
                            field.data = [await validator.convert(value) for value in field.data]
                        except commands.BadArgument as e:
                            extra_notifications.append(
                                {"message": f"{field.name}: {e}", "category": "warning"}
                            )
                            result = False
                        continue
                    if field.data is None or not field.data.strip():
                        field.data = ""
                        continue
                    try:
                        field.data = await validator.convert(field.data)
                    except commands.BadArgument as e:
                        extra_notifications.append(
                            {"message": f"{field.name}: {e}", "category": "warning"}
                        )
                        result = False
            return result

        def hidden_tag(self, *fields) -> Markup:
            def hidden_fields(fields):
                for f in fields:
                    if isinstance(f, str):
                        f = getattr(self, f, None)
                    if f is None or not isinstance(f.widget, HiddenInput):
                        continue
                    yield f

            return Markup("\n".join(str(f) for f in hidden_fields(fields or self)))

        def __str__(self) -> Markup:
            html_form = [
                '<form action="" method="POST" role="form" enctype="multipart/form-data">',
                f"    {self.hidden_tag()}",
            ]
            for field in self:
                if isinstance(field, (HiddenField, SubmitField)):
                    continue
                html_form.append('    <div class="mb-3">')
                # if not isinstance(field, BooleanField):
                html_form.append('        <div class="form-group">')
                html_form.append(
                    f'            <label class="form-group-label">{field.label}</label>'
                )
                html_form.append(
                    f'            {field(class_="form-control form-control-default")}'
                )
                html_form.append("        </div>")
                # else:
                #     html_form.append('        <div class="form-check form-switch ps-0">')
                #     html_form.append(f'            {field(class_="form-check-input")}')
                #     html_form.append(f'            <label class="form-check-label">{field.label}</label>')
                #     html_form.append("        </div>")
                html_form.append("    </div>")
            html_form.append('    <div class="text-center">')
            for field in self:
                if isinstance(field, SubmitField):
                    if field.render_kw is None:
                        field.render_kw = {}
                    field.render_kw.setdefault(
                        "class", "btn mb-0 bg-gradient-success btn-md w-100 my-4"
                    )
                    html_form.append(f"        {field()}")
            html_form.extend(["    </div>", "</form>"])
            return Markup("\n".join(html_form))

    def init_field(field, *args, **kwargs):
        INITIAL_INIT_FIELD(field, *args, **kwargs)
        if isinstance(field, FormField):
            return
        if hasattr(field, "_value"):
            field._real_value = field._value
        field._value = lambda: (field._real_value() if hasattr(field, "_real_value") else "") or (
            (field.default if isinstance(field.default, typing.List) else str(field.default))
            if field.default is not None
            else ""
        )
        if isinstance(field, SelectFieldBase):
            old_choices_generator = field._choices_generator

            def _choices_generator(choices):
                for value, label, selected, render_kw in old_choices_generator(choices):
                    yield (
                        value,
                        label,
                        selected
                        or (
                            field.coerce(value) in field._value()
                            if isinstance(field._value(), typing.List)
                            else field.coerce(value) == field._value()
                        ),
                        render_kw,
                    )

            field._choices_generator = _choices_generator

    Field.__init__ = init_field

    class DpyObjectConverter:
        def __init__(
            self,
            converter: typing.Callable[[str], typing.Any],
            param: typing.Optional[discord.ext.commands.parameters.Parameter] = None,
        ) -> None:
            self.converter: typing.Callable[[str], typing.Any] = converter
            self.param: discord.ext.commands.parameters.Parameter = (
                param
                or discord.ext.commands.parameters.Parameter(
                    name="converter",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=self.converter,
                )
            )

        def __call__(self, form: Form, field: Field) -> None:
            pass

        async def convert(self, argument: str) -> typing.Any:
            context = await CogsUtils.invoke_command(
                bot=_self.bot,
                author=kwargs["user"],
                channel=kwargs.get(
                    "channel",
                    (
                        kwargs["guild"].text_channels[0]
                        if kwargs.get("guild") is not None
                        else kwargs["user"].create_dm()
                    ),
                ),
                command="ping",
                invoke=False,
                cog=third_party_cog,
            )
            return await discord.ext.commands.converter.run_converters(
                context,
                converter=self.param.converter,
                argument=argument,
                param=self.param,
            )

    def get_sorted_channels(
        guild: discord.Guild,
        types: typing.Optional[typing.Tuple[discord.abc.GuildChannel]] = (
            discord.TextChannel,
            discord.VoiceChannel,
        ),
        filter_func: typing.Optional[
            typing.Callable[[discord.abc.GuildChannel], bool]
        ] = discord.utils.MISSING,
    ) -> typing.List[typing.Tuple[int, str]]:
        if filter_func is discord.utils.MISSING:

            def filter_func(channel: discord.abc.GuildChannel) -> bool:
                bot_permissions = channel.permissions_for(guild.me)
                member = guild.get_member(kwargs["user"].id)
                member_permissions = (
                    channel.permissions_for(member) if member is not None else None
                )
                return (
                    bot_permissions.view_channel
                    and bot_permissions.send_messages
                    and bot_permissions.embed_links
                    and (
                        kwargs["user"].id in _self.bot.owner_ids
                        or (
                            member_permissions is not None
                            and member_permissions.view_channel
                            and member_permissions.send_messages
                            and member_permissions.embed_links
                        )
                    )
                )

        channels = []
        voice_channels = []
        categorized_channels = {}
        for channel in sorted(guild.channels, key=lambda channel: channel.position):
            if not isinstance(channel, types) or (
                filter_func is not None and not filter_func(channel)
            ):
                continue
            if channel.category is not None:
                categorized_channels.setdefault(channel.category, []).append(channel)
            elif isinstance(channel, discord.VoiceChannel):
                voice_channels.append(channel)
            else:
                channels.append(channel)
        channels += voice_channels
        for category in sorted(
            categorized_channels.items(), key=lambda category: category[0].position
        ):
            channels.extend(
                sorted(
                    category[1],
                    key=lambda channel: (
                        1 if isinstance(channel, discord.VoiceChannel) else 0,
                        channel.position,
                    ),
                )
            )
        return [
            (
                str(channel.id),
                f"{'#!' if isinstance(channel, discord.VoiceChannel) else '#'}{channel.name}",
            )
            for channel in channels
        ]

    def get_sorted_roles(
        guild: discord.Guild,
        filter_func: typing.Optional[
            typing.Callable[[discord.Role], bool]
        ] = discord.utils.MISSING,
    ) -> typing.List[typing.Tuple[int, str]]:
        if filter_func is discord.utils.MISSING:
            filter_func = (
                lambda role: not role.is_bot_managed()
            )  # and role.position < guild.me.top_role.position
        return [
            (str(role.id), role.name)
            for role in sorted(guild.roles, reverse=True)
            if not role.is_default() and (filter_func is None or filter_func(role))
        ]

    return (
        FlaskForm,
        DpyObjectConverter,
        extra_notifications,
        get_sorted_channels,
        get_sorted_roles,
    )

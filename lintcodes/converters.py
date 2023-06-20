from redbot.core import commands  # isort:skip
import typing  # isort:skip

import re


class Flake8FlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    count: typing.Optional[bool] = None
    verbose: typing.Optional[bool] = None
    statistics: typing.Optional[bool] = None
    doctests: typing.Optional[bool] = None

    color: typing.Optional[typing.Literal["auto", "always", "never"]] = None

    ignore: typing.Optional[str] = None
    select: typing.Optional[str] = None

    max_line_length: typing.Optional[int] = None
    max_doc_length: typing.Optional[int] = None
    max_complexity: typing.Optional[int] = None

    def to_str(self) -> str:
        def validate_flake8_code(code: str) -> typing.List[str]:
            return re.compile(r"([A-Z]\d{2,4})").findall(code)
        cmd_str = ""

        if self.count:
            cmd_str += " --count"
        if self.verbose:
            cmd_str += " -v"
        if self.statistics:
            cmd_str += " --statistics"
        if self.doctests:
            cmd_str += " --doctests"

        if self.color:
            cmd_str += f" --color={self.color}"

        if self.ignore:
            _ig = self.ignore.replace(",", " ")
            if codes := validate_flake8_code(_ig):
                cmd_str += f" --ignore {','.join(codes)}"
        if self.select:
            _sl = self.select.replace(",", " ")
            if codes := validate_flake8_code(_sl):
                cmd_str += f" --select {','.join(codes)}"

        if self.max_line_length:
            cmd_str += f" --max-line-length {self.max_line_length}"
        if self.max_doc_length:
            cmd_str += f" --max-doc-length {self.max_doc_length}"
        if self.max_complexity:
            cmd_str += f" --max-complexity {self.max_complexity}"

        return cmd_str


class PyLintFlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    confidence: typing.Literal[
        "high", "control_flow", "inference_failure", "undefined", "inference"
    ] = "HIGH CONTROL_FLOW INFERENCE_FAILURE UNDEFINED INFERENCE"

    disable: typing.Optional[str] = None
    enable: typing.Optional[str] = None

    def validate_flag(self) -> str:
        def validate_pylint_code(code: str) -> typing.List[str]:
            return re.compile(r"([A-Z]\d{4})").findall(code)
        cmd_str = ""

        if self.confidence:
            cmd_str += f" --confidence={self.confidence.upper()}"

        if self.disable:
            if codes := validate_pylint_code(self.disable):
                cmd_str += f" --disable={','.join(codes)}"
        if self.enable:
            if codes := validate_pylint_code(self.enable):
                cmd_str += f" --enable={','.join(codes)}"

        return cmd_str


class MyPyFlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    # Import Discovery.
    no_namespace_packages: typing.Optional[bool] = None
    ignore_missing_imports: typing.Optional[bool] = None
    follow_imports: typing.Literal["skip", "silent", "error", "normal"] = "normal"
    no_site_packages: typing.Optional[bool] = None
    no_silence_site_packages: typing.Optional[bool] = None

    # Disallow dynamic typing.
    disallow_any_unimported: typing.Optional[bool] = None
    disallow_any_expr: typing.Optional[bool] = None
    disallow_any_decorated: typing.Optional[bool] = None
    disallow_any_explicit: typing.Optional[bool] = None

    disallow_any_generics: typing.Optional[bool] = None
    allow_any_generics: typing.Optional[bool] = None

    disallow_subclassing_any: typing.Optional[bool] = None
    allow_subclassing_any: typing.Optional[bool] = None

    # Untyped definitions and calls.
    disallow_untyped_calls: typing.Optional[bool] = None
    allow_untyped_calls: typing.Optional[bool] = None

    disallow_untyped_defs: typing.Optional[bool] = None
    allow_untyped_defs: typing.Optional[bool] = None

    disallow_incomplete_defs: typing.Optional[bool] = None
    allow_incomplete_defs: typing.Optional[bool] = None

    check_untyped_defs: typing.Optional[bool] = None
    no_check_untyped_defs: typing.Optional[bool] = None

    disallow_untyped_decorators: typing.Optional[bool] = None
    allow_untyped_decorators: typing.Optional[bool] = None

    # None and Optional handling.
    implicit_optional: typing.Optional[bool] = None
    no_implicit_optional: typing.Optional[bool] = None

    no_strict_optional: typing.Optional[bool] = None
    strict_optional: typing.Optional[bool] = None

    # Configuring warnings.
    warn_redunant_casts: typing.Optional[bool] = None
    no_warn_redunant_casts: typing.Optional[bool] = None

    warn_unused_ignores: typing.Optional[bool] = None
    no_warn_unused_ignores: typing.Optional[bool] = None

    warn_no_return: typing.Optional[bool] = None
    no_warn_no_return: typing.Optional[bool] = None

    warn_return_any: typing.Optional[bool] = None
    no_warn_return_any: typing.Optional[bool] = None

    warn_unreachable: typing.Optional[bool] = None
    no_warn_unreachable: typing.Optional[bool] = None

    # Miscellaneous strictness flags.
    allow_untyped_globals: typing.Optional[bool] = None
    disallow_untyped_globals: typing.Optional[bool] = None

    allow_redifinition: typing.Optional[bool] = None
    disallow_redifinition: typing.Optional[bool] = None

    implicit_reexport: typing.Optional[bool] = None
    no_implicit_reexport: typing.Optional[bool] = None

    strict_equality: typing.Optional[bool] = None
    no_strict_equality: typing.Optional[bool] = None

    strict_concatenate: typing.Optional[bool] = None
    no_strict_concatenate: typing.Optional[bool] = None

    strict: typing.Optional[bool] = None

    # Configuring error messages.
    show_error_context: typing.Optional[bool] = None
    hide_error_context: typing.Optional[bool] = None

    show_column_numbers: typing.Optional[bool] = None
    hide_column_numbers: typing.Optional[bool] = None

    show_error_end: typing.Optional[bool] = None
    hide_error_end: typing.Optional[bool] = None

    show_error_codes: typing.Optional[bool] = None
    hide_error_codes: typing.Optional[bool] = None

    pretty: typing.Optional[bool] = None

    def to_str(self) -> str:
        cmd_str = ""

        if self.no_namespace_packages:
            cmd_str += " --no-namespace-packages"
        if self.ignore_missing_imports:
            cmd_str += " --ignore-missing-imports"
        if self.follow_imports:
            cmd_str += f" --follow-imports {self.follow_imports}"
        if self.no_site_packages:
            cmd_str += " --no-site-packages"
        if self.no_silence_site_packages:
            cmd_str += " --no-silence-site-packages"

        if self.disallow_any_unimported:
            cmd_str += " --disallow-any-unimported"
        if self.disallow_any_expr:
            self += " --disallow-any-expr"
        if self.disallow_any_decorated:
            cmd_str += " --disallow-any-decorated"
        if self.disallow_any_explicit:
            cmd_str += " --disallow-any-explicit"

        if self.disallow_any_generics:
            cmd_str += " --disallow-any-generics"
        if self.allow_any_generics:
            cmd_str += " --allow-any-generics"

        if self.disallow_subclassing_any:
            cmd_str += " --disallow-subclassing-any"
        if self.allow_subclassing_any:
            cmd_str += " --allow-subclassing-any"

        if self.disallow_untyped_calls:
            cmd_str += " --disallow-untyped-calls"
        if self.allow_untyped_calls:
            cmd_str += " --allow-untyped-calls"

        if self.disallow_untyped_defs:
            cmd_str += " --disallow-untyped-defs"
        if self.allow_untyped_defs:
            cmd_str += " --allow-untyped-defs"

        if self.disallow_incomplete_defs:
            cmd_str += " --disallow-incomplete-defs"
        if self.allow_incomplete_defs:
            cmd_str += " --allow-incomplete-defs"

        if self.check_untyped_defs:
            cmd_str += " --check-untyped-defs"
        if self.no_check_untyped_defs:
            cmd_str += " --no-check-untyped-defs"

        if self.disallow_untyped_decorators:
            cmd_str += " --disallow-untyped-decorators"
        if self.allow_untyped_decorators:
            cmd_str += " --allow-untyped-decorators"

        if self.implicit_optional:
            cmd_str += " --implicit-optional"
        if self.no_implicit_optional:
            cmd_str += " --no-implicit-optional"

        if self.no_strict_optional:
            cmd_str += " --no-strict-optional"
        if self.strict_optional:
            cmd_str += " --strict-optional"

        if self.warn_redunant_casts:
            cmd_str += " --warn-redunant-casts"
        if self.no_warn_redunant_casts:
            cmd_str += " --no-warn-redunant-casts"

        if self.warn_unused_ignores:
            cmd_str += " --warn-unused-ignores"
        if self.no_warn_unused_ignores:
            cmd_str += " --no-warn-unused-ignores"

        if self.warn_no_return:
            cmd_str += " --warn-no-return"
        if self.no_warn_no_return:
            cmd_str += " --no-warn-no-return"

        if self.warn_return_any:
            cmd_str += " --warn-return-any"
        if self.no_warn_return_any:
            cmd_str += " --no-warn-return-any"

        if self.warn_unreachable:
            cmd_str += " --warn-unreachable"
        if self.no_warn_unreachable:
            cmd_str += " --no-warn-unreachable"

        if self.allow_untyped_globals:
            cmd_str += " --allow-untyped-globals"
        if self.disallow_untyped_globals:
            cmd_str += " --disallow-untyped-globals"

        if self.allow_redifinition:
            cmd_str += " --allow-redifinition"
        if self.disallow_redifinition:
            cmd_str += " --disallow-redifinition"

        if self.implicit_reexport:
            cmd_str += " --implicit-reexport"
        if self.no_implicit_reexport:
            cmd_str += " --no-implicit-reexport"

        if self.strict_equality:
            cmd_str += " --strict-equality"

        if self.no_strict_equality:
            cmd_str += " --no-strict-equality"

        if self.strict_concatenate:
            cmd_str += " --strict-concatenate"

        if self.no_strict_concatenate:
            cmd_str += " --no-strict-concatenate"

        if self.strict:
            cmd_str += " --strict"

        if self.show_error_context:
            cmd_str += " --show-error-context"
        if self.hide_error_context:
            cmd_str += " --hide-error-context"

        if self.show_column_numbers:
            cmd_str += " --show-column-numbers"
        if self.hide_column_numbers:
            cmd_str += " --hide-column-numbers"

        if self.show_error_end:
            cmd_str += " --show-error-end"
        if self.hide_error_end:
            cmd_str += " --hide-error-end"

        if self.show_error_codes:
            cmd_str += " --show-error-codes"
        if self.hide_error_codes:
            cmd_str += " --hide-error-codes"

        if self.pretty:
            cmd_str += " --pretty"

        return cmd_str


class BanditFlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    read: typing.Optional[bool] = None
    verbose: typing.Optional[bool] = None

    skip: typing.Optional[str] = None

    level: typing.Optional[typing.Literal["low", "medium", "high"]] = None
    confidence: typing.Optional[typing.Literal["low", "medium", "high"]] = None

    def to_str(self) -> str:
        def validate_bandit_code(code: str) -> typing.List[str]:
            return re.compile(r"([A-Z]\d{2,3})").findall(code)
        cmd_str = ""

        if self.read:
            cmd_str += " -r"
        if self.verbose:
            cmd_str += " -v"

        if self.skip:
            _sp = self.skip.replace(" ", "")
            if codes := validate_bandit_code(_sp):
                cmd_str += f" --skip {','.join(codes)}"

        if self.level:
            if self.level == "low":
                cmd_str += " -l"
            elif self.level == "medium":
                cmd_str += " -ll"
            elif self.level == "high":
                cmd_str += " -lll"
        if self.confidence:
            if self.confidence == "low":
                cmd_str += " -i"
            elif self.confidence == "medium":
                cmd_str += " -ii"
            elif self.confidence == "high":
                cmd_str += " -iii"

        return cmd_str


class PyRightFlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    def to_str(self) -> str:
        return ""


class RuffFlagsConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str

    ignore: typing.Optional[str] = None
    select: typing.Optional[str] = None

    line_length: typing.Optional[int] = None
    max_doc_length: typing.Optional[int] = None
    max_complexity: typing.Optional[int] = None

    def to_str(self) -> str:
        def validate_Ruff_code(code: str) -> typing.List[str]:
            return re.compile(r"([A-Z]\d{2,4})").findall(code)
        cmd_str = " "

        if self.ignore:
            _ig = self.ignore.replace(",", " ")
            if codes := validate_Ruff_code(_ig):
                cmd_str += f" --ignore {','.join(codes)}"
        if self.select:
            _sl = self.select.replace(",", " ")
            if codes := validate_Ruff_code(_sl):
                cmd_str += f" --select {','.join(codes)}"

        if self.line_length:
            cmd_str += f" --max-line-length {self.max_complexity}"
        if self.max_doc_length:
            cmd_str += f" --max-doc-length {self.max_doc_length}"
        if self.max_complexity:
            cmd_str += f" --max-complexity {self.max_complexity}"

        return cmd_str

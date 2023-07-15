from AAA3A_utils import Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import json
import os
import re
import tempfile
import time

import autopep8
import bandit
import black
import flake8
import isort
import pkg_resources
import pylint
import pyright
import yapf
from colorama import Fore
from redbot.core.utils.chat_formatting import box

_ = Translator("LintCodes", __file__)


def cleanup_ansi(text: str) -> str:
    for attr in dir(Fore):
        if attr.startswith("_") or not isinstance(getattr(Fore, attr), str):
            continue
        text = text.replace(getattr(Fore, attr), "")
    return text


class Linter:
    def __init__(
        self,
        linter: typing.Literal[
            "flake8",
            "pylint",
            "mypy",
            "bandit",
            "black",
            "isort",
            "yapf",
            "autopep8",
            "pyright",
            "ruff",
        ],
        flags: typing.Optional[typing.Union[commands.FlagConverter, str]] = None,
    ):
        self.linter: typing.Literal[
            "flake8",
            "pylint",
            "mypy",
            "bandit",
            "black",
            "isort",
            "yapf",
            "autopep8",
            "pyright",
            "ruff",
        ] = linter
        self.flags: typing.Optional[typing.Union[commands.FlagConverter, str]] = flags

    async def execute_shell_command(self, shell_command: str, file: str) -> typing.Dict[str, str]:
        proc = await asyncio.create_subprocess_shell(
            f"{shell_command} {file}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        cmd = re.sub(" +", " ", shell_command)  # remove extra spaces
        args = cmd.split(" ")
        command = args[0]
        command = f"{Fore.GREEN}{command}"
        rest = []
        for arg in args[1:]:
            if arg.startswith("-") or arg.startswith("--"):
                arg = f"{Fore.BLUE}{arg}"
            else:
                arg = f"{Fore.YELLOW}{arg}"
            rest.append(arg)
        filename = f"{Fore.CYAN}{file}"
        complete_cmd_str = f"$ {command} {' '.join(rest)} {filename}"

        payload = {
            "main": f"{complete_cmd_str}\n\n{Fore.CYAN}Return Code: {Fore.RED}{proc.returncode}"
        }
        if stdout:
            payload["stdout"] = stdout.decode()
        if stderr:
            payload["stderr"] = stderr.decode()

        return payload

    async def lint(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        if self.flags is None:
            shortcut_linters = {
                "flake8": self.lint_with_flake8,
                "pylint": self.lint_with_pylint,
                "mypy": self.lint_with_mypy,
                "bandit": self.lint_with_bandit,
                "black": self.lint_with_black,
                "isort": self.lint_with_isort,
                "yapf": self.lint_with_yapf,
                "autopep8": self.lint_with_autopep8,
                "pyright": self.lint_with_pyright,
                "ruff": self.lint_with_ruff,
            }
            return await shortcut_linters[self.linter](ctx, code=code)

        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        shell_command = (
            f"{self.linter}{self.flags.to_str()}"
            if isinstance(self.flags, commands.FlagConverter)
            else f"{self.linter} {self.flags}"
        )
        data = await self.execute_shell_command(shell_command, temp_file_name)
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        # if not data:
        #     await ctx.send(_("No output, for the shell command `{shell_command}`.").format(shell_command=shell_command))
        #     return
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = "\n".join(f"{Fore.WHITE}{line}" for line in data["stdout"].splitlines())
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)
        if "stderr" in data:
            _result_str = "\n".join(f"{Fore.WHITE}{line}" for line in data["stderr"].splitlines())
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += f"\n{box(_result_str, lang=OUTPUT_LANG)}"

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data["main"], data

    async def lint_with_flake8(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command(
            "flake8 --color always --max-line-length 99", temp_file.name
        )
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Flake8 Version - {Fore.WHITE}{flake8.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            # json_data: dict = json.loads(data["stdout"])
            # for result in json_data.values():
            #     for error in result:
            #         line = f"{Fore.GREEN}{error['line_number']}"
            #         column = f"{Fore.GREEN}{error['column_number']}"
            #         _code = f"{Fore.RED}{error['code']}"
            #         message = f"{Fore.BLUE}{error['text']}"
            #         physical_line = f"{Fore.CYAN}{error['physical_line']}"
            #         _result_str += f"\n{Fore.WHITE}{temp_file_name}:{line:>2}:{column:<2} - {_code} - {message}\n>>> {physical_line}"
            #         _result_str += f"\n{Fore.WHITE}{'-' * 50}"
            _result_str += data["stdout"]
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)
        if "stderr" in data:
            _result_str = "\n".join(f"{Fore.RED}{line}" for line in data["stderr"].splitlines())
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += f"\n{box(_result_str, lang=OUTPUT_LANG)}"

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_pylint(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("pylint -f json", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Pylint Version - {Fore.WHITE}{pylint.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            json_data: dict = json.loads(data["stdout"])
            for result in json_data:
                line = f"{Fore.GREEN}{result['line']}"
                column = f"{Fore.GREEN}{result['column']}"
                message = f"{Fore.BLUE}{result['message']}"
                message_id = f"{Fore.RED}{result['message-id']}"
                symbol = f"{Fore.WHITE}({Fore.CYAN}{result['symbol']}{Fore.WHITE})"
                _result_str += f"\n{Fore.WHITE}{temp_file_name}:{line:>2}:{column:<2} - {message_id} - {message:<13} {symbol}"
                _result_str += f"\n{Fore.WHITE}{'-' * 50}"
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_mypy(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("mypy --verbose", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            try:
                mypy_version = pkg_resources.get_distribution("mypy").version
            except pkg_resources.DistributionNotFound:
                mypy_version = "1.3.0"
            _result_str += f"{Fore.WHITE}MyPy Version - {Fore.WHITE}{mypy_version}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            _result_str += "\n".join(f"{Fore.WHITE}{line}" for line in data["stdout"].splitlines())
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_bandit(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("bandit -f json", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.MAGENTA}Bandit Version - {Fore.MAGENTA}{bandit.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            json_data: dict = json.loads(data["stdout"])

            # Generated at: Ex format 2023-06-11T17:51:53Z.
            generated_at = datetime.datetime.strptime(
                json_data["generated_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).strftime("%d/%m/%Y %H:%M:%S")
            _result_str += f"{Fore.MAGENTA}Generated at: {Fore.MAGENTA}{generated_at}\n"

            confidence_high = json_data["metrics"]["_totals"]["CONFIDENCE.HIGH"]
            confidence_low = json_data["metrics"]["_totals"]["CONFIDENCE.LOW"]
            confidence_medium = json_data["metrics"]["_totals"]["CONFIDENCE.MEDIUM"]
            confidence_undefined = json_data["metrics"]["_totals"]["CONFIDENCE.UNDEFINED"]
            _result_str += f"{Fore.WHITE}Confidence: {Fore.RED}{confidence_high} High {Fore.WHITE}- {Fore.YELLOW}{confidence_medium} Medium {Fore.WHITE}- {Fore.GREEN}{confidence_low} Low {Fore.WHITE}- {Fore.CYAN}{confidence_undefined} Undefined"

            severity_high = json_data["metrics"]["_totals"]["SEVERITY.HIGH"]
            severity_low = json_data["metrics"]["_totals"]["SEVERITY.LOW"]
            severity_medium = json_data["metrics"]["_totals"]["SEVERITY.MEDIUM"]
            severity_undefined = json_data["metrics"]["_totals"]["SEVERITY.UNDEFINED"]
            _result_str += f"\n{Fore.WHITE}Severity  : {Fore.RED}{severity_high} High {Fore.WHITE}- {Fore.YELLOW}{severity_medium} Medium {Fore.WHITE}- {Fore.GREEN}{severity_low} Low {Fore.WHITE}- {Fore.CYAN}{severity_undefined} Undefined"

            loc = json_data["metrics"]["_totals"]["loc"]
            nosec = json_data["metrics"]["_totals"]["nosec"]
            skipped_tests = json_data["metrics"]["_totals"]["skipped_tests"]
            _result_str += f"\n{Fore.WHITE}Lines of Code {Fore.WHITE}{loc} - {Fore.RED}Lines of Code (#NoSec) {nosec} {Fore.WHITE}- {Fore.YELLOW}Skipped Tests {skipped_tests}\n"

            for result in json_data["results"]:
                _code = f"{Fore.CYAN}{result['code']}"
                col_offset = f"{Fore.GREEN}{result['col_offset']}"
                # end_col_offset = f"{Fore.GREEN}{result['end_col_offset']}"
                issue_confidence = f"{Fore.WHITE}{result['issue_confidence']}"
                issue_severity = f"{Fore.WHITE}{result['issue_severity']}"
                issue_text = f"{Fore.BLUE}{result['issue_text']}"
                line_number = f"{Fore.GREEN}{result['line_number']}"
                # line_range = f"{Fore.WHITE}{result['line_range']}"
                more_info = f"{Fore.WHITE}{result['more_info']}"
                test_id = f"{Fore.RED}{result['test_id']}"
                test_name = f"{Fore.WHITE}{result['test_name']}"
                if result.get("issue_cwe"):
                    issue_cwe_id = f"{Fore.WHITE}{result['issue_cwe']['id']}"
                    issue_cwe_link = f"{Fore.WHITE}{result['issue_cwe']['link']}"
                else:
                    issue_cwe_id = f"{Fore.WHITE}None"
                    issue_cwe_link = f"{Fore.WHITE}None"
                _result_str += (
                    f"\n\n{Fore.YELLOW}>> Issue [{test_id:>4}:{test_name:<9}] {issue_text}\n"
                    f"{Fore.WHITE}   Severity : {issue_severity:<6}  Confidence: {issue_confidence:<6}\n"
                    f"{Fore.WHITE}   CWE ID   : {issue_cwe_id:<6}  CWE Link: {issue_cwe_link}\n"
                    f"{Fore.WHITE}   More Info: {more_info}\n"
                    f"{Fore.WHITE}   Location : {temp_file_name}{line_number:>2}:{col_offset:<2}\n"
                    f"{Fore.WHITE}   Code     :\n{_code}\n"
                    f"{Fore.WHITE}{'-'*50}"
                )
                _result_str += f"\n{Fore.WHITE}{'-' * 50}"
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_black(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command(
            "black --diff --color --verbose --line-length 99", temp_file_name
        )
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Black Version - {Fore.WHITE}{black.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"
            _result_str += data["stdout"]
            result_str += box(_result_str, lang="py")

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_isort(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command(
            "isort --diff --verbose --only-modified --line-length 99 --stdout", temp_file_name
        )
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Isort Version - {Fore.WHITE}{isort.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"
            _result_str += data["stdout"]
            result_str += box(_result_str, lang="py")

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_yapf(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("yapf --diff --verbose", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Yapf Version - {Fore.WHITE}{yapf.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"
            _result_str += data["stdout"]
            result_str += box(_result_str, lang="py")

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_autopep8(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command(
            "autopep8 --diff --verbose --max-line-length 99", temp_file_name
        )
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}AutoPep8 Version - {Fore.WHITE}{autopep8.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"
            _result_str += data["stdout"]
            result_str += box(_result_str, lang="py")

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_pyright(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("pyright --outputjson", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            _result_str += f"{Fore.WHITE}Pyright Version - {Fore.WHITE}{pyright.__version__}\n"
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            json_data: dict = json.loads(data["stdout"])
            _result_str += f"\n{Fore.RED}{json_data['summary']['errorCount']} errors - {Fore.YELLOW}{json_data['summary']['warningCount']} warnings - {Fore.BLUE}{json_data['summary']['informationCount']} informations"
            _result_str += f"\n\n{Fore.MAGENTA}Diagnosed completed in {json_data['summary']['timeInSec']} seconds\n"
            if json_data["generalDiagnostics"]:
                _result_str += f"{Fore.WHITE}General Diagnostics:\n"
                for error in json_data["generalDiagnostics"]:
                    file = f"{Fore.WHITE}{temp_file_name}"
                    line = f"{Fore.GREEN}{error['range']['start']['line']}:{error['range']['end']['line']}"
                    severity = error["severity"]
                    if severity.lower() == "error":
                        severity = f"{Fore.RED}{severity}"
                    elif severity.lower() == "warning":
                        severity = f"{Fore.YELLOW}{severity}"
                    elif severity.lower() == "information":
                        severity = f"{Fore.BLUE}{severity}"

                    message = f"{Fore.BLUE}{error['message']}"
                    rule = f"{Fore.WHITE}({Fore.CYAN}{error.get('rule', 'N/A')}{Fore.WHITE})"

                    _result_str += f"\n{file}:{line} - {severity} - {message} {rule}"
                    _result_str += f"\n{Fore.WHITE}{'-' * 50}"
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)
        if "stderr" in data:
            _result_str = "\n".join(f"{Fore.RED}{line}" for line in data["stderr"].splitlines())
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += f"\n{box(_result_str, lang=OUTPUT_LANG)}"

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

    async def lint_with_ruff(
        self, ctx: typing.Optional[commands.Context], code: str
    ) -> typing.Dict[str, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", prefix=f"linter-{self.linter}-", delete=False
        ) as temp_file:
            temp_file.write(code.encode(encoding="utf-8"))
            temp_file_name = temp_file.name

        start = time.time()
        data = await self.execute_shell_command("ruff --format=json", temp_file_name)
        end = time.time()
        try:
            os.remove(temp_file_name)
        except FileNotFoundError:
            pass
        temp_file_name = temp_file_name.replace("\\", "/").split("/")[-1]

        OUTPUT_LANG = "py" if ctx.author.is_on_mobile() else "ansi"
        result_str = ""
        if "stdout" in data:
            _result_str = ""
            try:
                ruff_version = pkg_resources.get_distribution("ruff").version
            except pkg_resources.DistributionNotFound:
                ruff_version = "0.0.272"
            _result_str += f"{Fore.WHITE}Ruff Version - {Fore.WHITE}{ruff_version}\n"  # No version number available easely.
            _result_str += f"{Fore.GREEN}[Executed in {int(end - start)} seconds]\n"

            json_data: dict = json.loads(data["stdout"])
            for result in json_data:
                _code = f"{Fore.RED}{result['code']}"
                message = f"{Fore.BLUE}{result['message']}."
                location_row = f'{Fore.YELLOW}{result["location"]["row"]}'
                location_col = f'{Fore.YELLOW}{result["location"]["column"]}'

                end_location_row = f'{Fore.YELLOW}{result["end_location"]["row"]}'
                end_location_col = f'{Fore.YELLOW}{result["end_location"]["column"]}'

                _result_str += f"\n{Fore.WHITE}{temp_file_name}:{location_row}:{location_col}{Fore.WHITE}-{end_location_row}:{end_location_col} {Fore.WHITE}- {_code} {Fore.WHITE}\n{message}"
                if result["fix"]:
                    applicability = f'{Fore.CYAN}{result["fix"]["applicability"]}'
                    fix_message = f'{Fore.GREEN}{result["fix"]["message"]}'
                    _result_str += f"\n{Fore.WHITE}Fix: {fix_message} {Fore.WHITE}({applicability}{Fore.WHITE})."
                else:
                    _result_str += f"\n{Fore.WHITE}Fix: {Fore.RED}No Fix available at this moment."
                _result_str += f"\n{Fore.WHITE}{'-' * 50}"
            if OUTPUT_LANG != "ansi":
                _result_str = cleanup_ansi(_result_str)
            result_str += box(_result_str, lang=OUTPUT_LANG)

        prefix = data["main"]
        if OUTPUT_LANG != "ansi":
            prefix = cleanup_ansi(prefix)
        prefix = box(prefix, lang=OUTPUT_LANG)
        if ctx is not None:
            await Menu(pages=result_str, prefix=prefix).start(ctx)

        return data

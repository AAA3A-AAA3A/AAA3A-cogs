import asyncio
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from dotenv import load_dotenv
from jsonrpc_websocket import Server

from redbot import __version__ as red_str_ver

load_dotenv(".env")

token = os.environ.get("DISCORD_BOT_TOKEN")

python_version = subprocess.check_output([sys.executable, "-V"]).decode("utf-8")

print("=== Red's logs are available to view as an Artifact on the main matrix page ===\n")

print(f"Starting Red {red_str_ver} with {python_version}")

file = open("red.log", "w")
proc = subprocess.Popen(
    ["redbot", "workflow", "--no-prompt", "--rpc", "--debug"],
    stdout=file,
    stderr=subprocess.STDOUT,
    env={**os.environ, "RED_TOKEN": token},  # Not in the command line, visible to all processes.
)

# let Red boot up
time.sleep(10)

# All the cogs of the repo: the folders with an `info.json` file and an `__init__.py` file.
cogs = sorted(
    path.parent.name
    for path in Path(__file__).parents[3].glob("*/info.json")
    if (path.parent / "__init__.py").exists()
)


async def leswebsockets() -> tuple[dict[str, Any], dict[str, Any]]:
    print("Connecting to Red via RPC")

    server = Server("ws://localhost:6133")
    try:
        await server.ws_connect()

        print("Loading cogs")
        load_results: dict[str, Any] = await server.CORE__LOAD(cogs)
        await asyncio.sleep(1)
        print("Unloading cogs")
        unload_results: dict[str, Any] = await server.CORE__UNLOAD(cogs)
    finally:
        await server.close()

    return load_results, unload_results


load, unload = asyncio.run(leswebsockets())

print("Stopping Red")

proc.terminate()

exit_code = 0

fail_load = []
for i in (
    "failed_packages",
    "invalid_pkg_names",
    "notfound_packages",
    "alreadyloaded_packages",
    "failed_with_reason_packages",
):
    fail_load.extend(load[i])

if fail_load:
    exit_code = 1
    print("\N{CROSS MARK} Failed to load cogs " + ", ".join(fail_load))
    print("See the artifact on the main matrix page for more information")
else:
    print("\N{HEAVY CHECK MARK} Loaded all cogs successfully")

if unload["notloaded_packages"]:
    exit_code = 1
    print("\N{CROSS MARK} Failed to unload cogs " + ", ".join(unload["notloaded_packages"]))
    print("See the artifact on the main matrix page for more information")
else:
    print("\N{HEAVY CHECK MARK} Unloaded all cogs successfully")

sys.exit(exit_code)

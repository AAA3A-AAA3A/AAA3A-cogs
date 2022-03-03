import asyncio
import os
import subprocess
import sys
import time
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from jsonrpc_websocket import Server
from redbot import __version__ as red_str_ver

load_dotenv(".env")

token = os.environ.get("DISCORD_BOT_TOKEN")

python_version = subprocess.check_output(["python", "-V"]).decode("utf-8")

print("=== Red's logs are available to view as an Artifact on the main matrix page ===\n")

print(f"Starting Red {red_str_ver} with {python_version}")

file = open("red.log", "w")
proc = subprocess.Popen(
    f"redbot workflow --no-prompt --token {token} --rpc --debug",
    stdout=file,
    stderr=subprocess.STDOUT,
    shell=True,
)

# let Red boot up
time.sleep(10)

# not compatible with dpy 1.x
# ["buttonpoll", "ghissues"]

all_cogs = [
    "AntiNuke",
    "Calculator",
    "ClearChannel",
    "CmdChannel",
    "CtxVar",
    "EditFile",
    "Ip",
    "MemberPrefix",
    "ReactToCommand",
    "RolesButtons",
    "SimpleSanction",
    "Sudo",
    "TicketTool",
    "TransferChannel"
]
cogs = []
for cog in cogs:
    cogs.append(cog.lower())


async def leswebsockets() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    print("Connecting to Red via RPC")

    server = Server("ws://localhost:6133")
    try:
        await server.ws_connect()

        print("Loading cogs")
        load_results: Dict[str, Any] = await server.CORE__LOAD(cogs)
        await asyncio.sleep(1)
        print("Unloading cogs")
        unload_results: Dict[str, Any] = await server.CORE__UNLOAD(cogs)
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

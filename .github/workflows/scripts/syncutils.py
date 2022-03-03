# Thanks to @Vexed01 on GitHub pour this code and this workflow! (https://github.com/Vexed01/Vex-Cogs)
# copy the utils from https://github.com/AAA3A-AAA3A/AAA3A_utils to each cog in this repo

import datetime
import json
import os
import shutil
from pathlib import Path

import git
import requests
from git import Repo

README_MD_TEXT = """## My utils

Hello there! If you're contributing or taking a look, everything in this folder
is synced from a master repo at https://github.com/AAA3A-AAA3A/AAA3A_utils by GitHub Actions -
so it's probably best to look/edit there.

---

Last sync at: {time}

Commit: [`{commit}`](https://github.com/AAA3A-AAA3A/AAA3A_utils/commit/{commit})
"""

utils_repo_clone_location = Path("temp-utils-repo")
utils_repo = Repo.clone_from(
    "https://github.com/AAA3A-AAA3A/AAA3A_utils.git", utils_repo_clone_location
)

utils_location = utils_repo_clone_location / "AAA3A_utils"

readme = README_MD_TEXT.format(
    time=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z"),
    commit=utils_repo.head.commit,
)

with open(utils_location / "README.md", "w") as fp:
    fp.write(readme)

with open(utils_location / "commit.json", "w") as fp:
    fp.write(json.dumps({"latest_commit": str(utils_repo.head.commit)}))

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
cog_folders = []
for cog in cogs:
    cog_folders.append(cog.lower())

for cog in cog_folders:
    destination = Path(cog) / "AAA3A_utils"
    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(utils_location, destination)

utils_repo.close()
git.rmtree(utils_repo_clone_location)
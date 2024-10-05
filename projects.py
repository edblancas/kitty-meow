import argparse
import json
import os
import subprocess
from datetime import datetime
from typing import List

from kitty.boss import Boss

parser = argparse.ArgumentParser(description="meow")

parser.add_argument("command", nargs="?", default="load")

parser.add_argument(
    "--dir",
    dest="dirs",
    action="append",
    default=[],
    help="directories to find projects",
)


def load_main(args, opts):
    # FIXME: How to call boss in the main function?
    # data = boss.call_remote_control(None, ("ls",))
    kitty_ls = json.loads(
        subprocess.run(
            ["kitty", "@", "ls"], capture_output=True, text=True
        ).stdout.strip("\n")
    )

    tabs = [tab["title"] for tab in kitty_ls[0]["tabs"] if not tab['is_focused']]
    tabs_and_projects = tabs[:]
    projects = []

    for dir in opts.dirs:
        if dir.endswith("/"):
            for f in os.scandir(dir):
                if f.is_dir():
                    name = os.path.basename(f.path)
                    pretty_path = f.path.replace(os.path.expanduser("~"), "~", 1)
                    projects.append(pretty_path)
                    if name not in tabs_and_projects:
                        tabs_and_projects.append(pretty_path.replace("~/projects/", ""))
        else:
            name = os.path.basename(dir)
            projects.append(dir)
            if name not in tabs_and_projects:
                tabs_and_projects.append(dir)

    bin_path = os.getenv("BIN_PATH", "")

    args = [
        f"{bin_path}fzf",
        "--multi",
        "--reverse",
        f"--prompt=🐈>",
    ]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = p.communicate(input="\n".join(tabs_and_projects).encode())[0]
    output = out.decode().strip()

    if output == "":
        return []

    return output.split("\n")


def load_project(boss, path, dir):
    kitty_ls = json.loads(boss.call_remote_control(None, ("ls",)))
    for tab in kitty_ls[0]["tabs"]:
        if tab["title"] == dir:
            boss.call_remote_control(None, ("focus-tab", "--match", f"title:^{dir}$"))
            return

    window_id = boss.call_remote_control(
        None,
        (
            "launch",
            "--type",
            "tab",
            "--tab-title",
            dir,
            "--cwd",
            path,
        ),
    )

    parent_window = boss.window_id_map.get(int(window_id))

    boss.call_remote_control(parent_window, ("send-text", "${EDITOR:-vim}\n"))


def load_handler(answer: str, boss: Boss):
    if not answer:
        return

    for selection in answer:
        path, *rest = selection.split()
        dir = os.path.basename(path)
        load_project(boss, path, dir)


def main(args: List[str]) -> list[str]:
    opts = parser.parse_args(args[1:])
    return load_main(args, opts)


def handle_result(
    answer: str, boss: Boss
) -> None:
    return load_handler(answer, boss)

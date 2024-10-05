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
                        tabs_and_projects.append(pretty_path)
        else:
            name = os.path.basename(dir)
            projects.append(dir)
            if name not in tabs_and_projects:
                tabs_and_projects.append(dir)

    bin_path = os.getenv("BIN_PATH", "")

    default_prompt = "🐈tabs> "
    # NOTE: Can't use ' char within any of the binds
    binds = [
        'ctrl-p:change-prompt(🐈projects> )+reload(printf "{0}")'.format(
            "\n".join(projects)
        ),
        'ctrl-o:change-prompt({0})+reload(printf "{1}")'.format(
            default_prompt, "\n".join(tabs)
        ),
        'ctrl-e:change-prompt(🐈> )+reload(printf "{0}")'.format("\n".join(tabs_and_projects))
    ]
    args = [
        f"{bin_path}fzf",
        "--multi",
        "--reverse",
        "--header=ctrl-p: project | ctrl-e: tabs | ctrl-o: tabs&projects",
        f"--prompt={default_prompt}",
        f"--bind={','.join(binds)}",
    ]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = p.communicate(input="\n".join(tabs).encode())[0]
    output = out.decode().strip()

    # from kittens.tui.loop import debug
    # debug(output)

    if output == "":
        return []

    return output.split("\n")


def load_project(boss, path, dir):
    with open(f"{os.path.expanduser('~')}/.config/kitty/meow/history", "a") as history:
        history.write(f"{dir} {datetime.now().isoformat()}\n")
        history.close()

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


def load_handler(args: List[str], answer: str, target_window_id: int, boss: Boss):
    opts = parser.parse_args(args[1:])

    # This is the dir we clone repos into, for me it's not a big deal if they get cloned to the
    # first dir. But some people might want to pick which dir to clone to? How could that be
    # supported?
    projects_root = opts.dirs[0]

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
    args: List[str], answer: str, target_window_id: int, boss: Boss
) -> None:
    return load_handler(args, answer, target_window_id, boss)

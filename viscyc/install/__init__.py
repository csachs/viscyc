import os
import shutil
import sys
from pathlib import Path
from subprocess import run

unit = f"""
[Unit]
Description=viscyc

[Service]
ExecStart={sys.executable} -m viscyc.manager

[Install]
WantedBy=default.target
"""

unit_path = Path("~/.config/systemd/user/viscyc.service").expanduser()


def example(arg):
    print(" ".join(arg))


def prompt():
    while True:
        result = input('Continue? [Y/N] ')
        if result.lower() == 'y':
            break
        else:
            raise SystemExit


def run_prompt(commands, message):

    print(message)

    for command in commands:
        example(command)

    prompt()

    for command in commands:
        run(command)


def main():
    if unit_path.exists():
        print("A unit file is already in place.")
        return

    print(f"Will create {unit_path} with the following content:")
    print()
    print(unit)
    print()

    prompt()

    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(unit)

    run_prompt(
        commands=[
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "enable", "viscyc"],
            ["systemctl", "--user", "start", "viscyc"],
        ],
        message="Will activate the unit: ",
    )

    run_prompt(
        commands=[
            ["sudo", "loginctl", "enable-linger", os.getlogin()],
            [
                "sudo",
                "setcap",
                "cap_net_raw+eip",
                os.path.realpath(shutil.which('node')),
            ],
        ],
        message="Will enable lingering for current user "
        + "and give node necessary Bluetooth capabilities",
    )

    print("Installation finished.")
    print()
    print("You can stop viscyc by running")
    example(["systemctl", "--user", "stop", "viscyc"])
    print()
    print("Disable it via")
    example(["systemctl", "--user", "disable", "viscyc"])
    print()
    print(f"And remove the unit by")
    example(["rm", unit_path])

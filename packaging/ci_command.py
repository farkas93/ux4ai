"""Keep native CI failures readable in public job annotations as well as logs."""

import subprocess
import sys
from collections import deque


def escape(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    title, *command = sys.argv[1:]
    if command and command[0] == "--":
        command.pop(0)
    recent = deque(maxlen=120)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace")
    for line in process.stdout:
        print(line, end="", flush=True)
        recent.append(line)
    result = process.wait()
    if result:
        detail = "".join(recent)[-6000:]
        print(f"::error title={escape(title)}::{escape(detail)}", flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

"""Keep native CI failures readable in public job annotations as well as logs."""

import os
import re
import subprocess
import sys
from collections import deque


def escape(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    title, *command = sys.argv[1:]
    if command and command[0] == "--":
        command.pop(0)
    # Windows runners can use a legacy console encoding even when the child
    # process emits UTF-8. A failed diagnostic must not hide the original error.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    initial = []
    context = deque(maxlen=40)
    recent = deque(maxlen=120)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", env=environment)
    except OSError as exc:
        print(f"::error title={escape(title)}::{escape(str(exc))}", flush=True)
        return 1
    for line in process.stdout:
        print(line, end="", flush=True)
        if len(initial) < 30:
            initial.append(line)
        if re.search(r"failed|error|traceback|exception|pandas|meson|not found|unknown compiler",
                     line, re.IGNORECASE):
            context.append(line)
        recent.append(line)
    result = process.wait()
    if result:
        for label, detail in ((title, "".join(context)[-6000:]),
                              (title + " — initial output", "".join(initial)[:6000]),
                              (title + " — final output", "".join(recent)[-6000:])):
            if detail:
                print(f"::error title={escape(label)}::{escape(detail)}", flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

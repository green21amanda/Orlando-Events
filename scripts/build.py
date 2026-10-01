"""Run every fetcher, then merge everything into data/events.json.

Designed to run daily (see the project README for scheduling it). Each
fetcher runs in its own subprocess so a single broken source (a site
redesign, a timeout) can't take down the whole build -- we log the failure
and keep going with whatever sources still work.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent

FETCHERS = [
    "fetch_4roots_farm.py",
    "fetch_house_on_lang.py",
    "fetch_those_guys_cafe.py",
]


def run(script_name):
    print(f"=== {script_name} ===")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name)],
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(f"!! {script_name} failed:\n{result.stderr}", file=sys.stderr)
        return False
    return True


def main():
    results = {name: run(name) for name in FETCHERS}
    failed = [name for name, ok in results.items() if not ok]

    print("=== merge.py ===")
    merge_result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "merge.py")],
        capture_output=True,
        text=True,
    )
    print(merge_result.stdout, end="")
    if merge_result.returncode != 0:
        print(f"!! merge.py failed:\n{merge_result.stderr}", file=sys.stderr)
        return 1

    shutil.copyfile(PROJECT_DIR / "data" / "events.json", PROJECT_DIR / "site" / "events.json")
    print("copied data/events.json -> site/events.json")

    if failed:
        print(f"\nCompleted with {len(failed)} source(s) failing: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

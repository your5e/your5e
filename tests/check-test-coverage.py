#!/usr/bin/env python

import re
import sys
from pathlib import Path


def main():
    failed = False
    sync_md = Path("tests/sync.md").read_text()
    checked_bats = set()
    checked_ts = set()

    for section in re.findall(r"### `([^`]+\.bats)`", sync_md):
        expected = extract_md_tests(sync_md, section)

        bats_files = list(Path("tests").glob(section))
        if not bats_files:
            print(f"✗ {section} has no matching bats files")
            failed = True
        for file in sorted(bats_files):
            checked_bats.add(file)
            if not check_bats(file, expected):
                failed = True

        ts_pattern = section.replace("_", "-").replace(".bats", ".test.ts")
        ts_files = list(Path("obsidian-plugin/tests").glob(ts_pattern))
        if not ts_files:
            print(f"✗ {ts_pattern} has no matching TypeScript files")
            failed = True
        for file in sorted(ts_files):
            checked_ts.add(file)
            if not check_ts(file, expected):
                failed = True

    for file in sorted(Path("tests").glob("*sync*.bats")):
        if file not in checked_bats:
            print(f"✗ {file.name} not documented in sync.md")
            failed = True

    for file in sorted(Path("obsidian-plugin/tests").glob("*sync*.test.ts")):
        if file not in checked_ts:
            print(f"✗ {file.name} not documented in sync.md")
            failed = True

    if failed:
        sys.exit(1)


def extract_md_tests(content, section):
    escaped = re.escape(section)
    match = re.search(
        rf"### `{escaped}`\n.*?\n\| Test \|.*?\n\|[-|]+\n(.*?)(?=\n###|\n\n[^|]|\Z)",
        content,
        re.DOTALL,
    )
    if not match:
        return []
    return [
        line.split("|")[1].strip()
        for line in match.group(1).strip().split("\n")
        if line.startswith("|")
    ]


def check_bats(file, expected):
    content = file.read_text()
    actual = re.findall(r'^@test "([^"]+)"', content, re.MULTILINE)
    return compare(file.name, expected, actual)


def check_ts(file, expected):
    content = file.read_text()
    actual = re.findall(r'test\("([^"]+)"', content)
    return compare(file.name, expected, actual)


def compare(label, expected, actual):
    if expected == actual:
        print(f"✓ {label}")
        return True
    print(f"✗ {label}")
    for i, (e, a) in enumerate(zip(expected, actual, strict=False)):
        if e != a:
            print(f"  line {i + 1}: expected '{e}', got '{a}'")
    if len(expected) > len(actual):
        print(f"  missing {len(expected) - len(actual)} tests")
    elif len(actual) > len(expected):
        print(f"  extra {len(actual) - len(expected)} tests")
    return False


if __name__ == "__main__":
    main()

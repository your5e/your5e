#!/usr/bin/env python

import re
import sys
from difflib import unified_diff
from pathlib import Path


def main():
    suite = None
    if len(sys.argv) > 1:
        suite = sys.argv[1]
    if suite not in (None, "bats", "ts"):
        print(f"Usage: {sys.argv[0]} [bats|ts]", file=sys.stderr)
        sys.exit(1)

    check_bats_suite = suite in (None, "bats")
    check_ts_suite = suite in (None, "ts")

    failed = False
    sync_md = Path("tests/sync.md").read_text()
    checked_bats = set()
    checked_ts = set()

    for section in re.findall(r"### `([^`]+\.bats)`", sync_md):
        expected = extract_md_tests(sync_md, section)

        if check_bats_suite:
            bats_files = list(Path("tests").glob(section))
            if not bats_files:
                print(f"✗ {section} has no matching bats files")
                failed = True
            for file in sorted(bats_files):
                checked_bats.add(file)
                if not check_bats(file, expected):
                    failed = True

        if check_ts_suite:
            ts_pattern = section.replace("_", "-").replace(".bats", ".test.ts")
            ts_files = list(Path("obsidian-plugin/tests").glob(ts_pattern))
            if not ts_files:
                print(f"✗ {ts_pattern} has no matching TypeScript files")
                failed = True
            for file in sorted(ts_files):
                checked_ts.add(file)
                if not check_ts(file, expected):
                    failed = True

    if check_bats_suite:
        for file in sorted(Path("tests").glob("*sync*.bats")):
            if file not in checked_bats:
                print(f"✗ {file.name} not documented in sync.md")
                failed = True

    if check_ts_suite:
        for file in sorted(Path("obsidian-plugin/tests").glob("*sync*.test.ts")):
            if file not in checked_ts:
                print(f"✗ {file.name} not documented in sync.md")
                failed = True

    if check_bats_suite and not check_setup_parity():
        failed = True

    if check_ts_suite and not check_ts_setup_parity():
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


PARITY_SUITES = [
    "first_sync_*.bats",
    "subsequent_sync_*.bats",
]


def check_setup_parity():
    passed = True
    for suite_pattern in PARITY_SUITES:
        if not check_suite_parity(suite_pattern):
            passed = False
    return passed


def check_suite_parity(suite_pattern):
    prefix = suite_pattern.replace("_*.bats", "")

    sync_md = Path("tests/sync.md").read_text()
    expected = extract_md_tests(sync_md, suite_pattern)

    pull_file = Path(f"tests/{prefix}_pull.bats")
    push_file = Path(f"tests/{prefix}_push.bats")

    pull_tests = parse_test_setups(pull_file.read_text())
    push_tests = parse_test_setups(push_file.read_text())

    passed = True

    for name in expected:
        pull_setup = pull_tests[name]
        push_setup = push_tests[name]

        if pull_setup == push_setup:
            print(f"\u2713 setup: {name}")
        else:
            print(f"\u2717 setup: {name}")
            # Ensure both end with newline so trailing blank lines show clearly
            pull_lines = (pull_setup + "\n").splitlines(keepends=True)
            push_lines = (push_setup + "\n").splitlines(keepends=True)
            diff = unified_diff(
                pull_lines,
                push_lines,
                fromfile="pull",
                tofile="push",
                n=3,
            )
            print("".join(diff))
            passed = False

    return passed


def parse_test_setups(content):
    tests = {}
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        match = re.match(r'^@test ["\'](.+)["\'] \{', lines[i])
        if match:
            name = match.group(1)
            setup_lines = []
            i += 1

            while i < len(lines):
                line = lines[i]
                if line.lstrip().startswith("run "):
                    break
                setup_lines.append(line)
                i += 1

            # Filter out direction-specific comments (# push: or # pull:)
            filtered = [
                line for line in setup_lines
                if not re.match(r'^\s*#\s*(push|pull):', line)
            ]
            tests[name] = "\n".join(filtered)
        i += 1

    return tests


def check_ts_setup_parity():
    passed = True
    for suite_pattern in PARITY_SUITES:
        if not check_ts_suite_parity(suite_pattern):
            passed = False
    return passed


def check_ts_suite_parity(suite_pattern):
    prefix = suite_pattern.replace("_*.bats", "").replace("_", "-")

    sync_md = Path("tests/sync.md").read_text()
    expected = extract_md_tests(sync_md, suite_pattern)

    pull_file = Path(f"obsidian-plugin/tests/{prefix}-pull.test.ts")
    push_file = Path(f"obsidian-plugin/tests/{prefix}-push.test.ts")

    pull_tests = parse_ts_test_setups(pull_file.read_text())
    push_tests = parse_ts_test_setups(push_file.read_text())

    passed = True

    for name in expected:
        pull_setup = pull_tests[name]
        push_setup = push_tests[name]

        if pull_setup == push_setup:
            print(f"\u2713 ts setup: {name}")
        else:
            print(f"\u2717 ts setup: {name}")
            pull_lines = (pull_setup + "\n").splitlines(keepends=True)
            push_lines = (push_setup + "\n").splitlines(keepends=True)
            diff = unified_diff(
                pull_lines,
                push_lines,
                fromfile="pull",
                tofile="push",
                n=3,
            )
            print("".join(diff))
            passed = False

    return passed


def parse_ts_test_setups(content):
    tests = {}
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        match = re.match(r'^\s*test\("([^"]+)"', lines[i])
        if match:
            name = match.group(1)
            setup_lines = []
            i += 1

            while i < len(lines):
                line = lines[i]
                if "const result" in line:
                    break
                setup_lines.append(line)
                i += 1

            # Filter out direction-specific comments (// push: or // pull:)
            filtered = [
                line for line in setup_lines
                if not re.match(r'^\s*//\s*(push|pull):', line)
            ]
            tests[name] = "\n".join(filtered)
        i += 1

    return tests


if __name__ == "__main__":
    main()

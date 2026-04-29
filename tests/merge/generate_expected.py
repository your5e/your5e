import re
from pathlib import Path

from diff_match_patch import diff_match_patch


def parse_matrix():
    content = Path("tests/merge/tests.md").read_text()
    lines = content.split("\n")
    remote_ops = []
    local_ops = []

    for line in lines:
        if line.startswith("|") and "unchanged" in line and "append" in line:
            remote_ops = [h.strip() for h in line.split("|")[2:-1]]
        elif line.startswith("| **"):
            match = re.match(r"\| \*\*(.+?)\*\*", line)
            local_ops.append(match.group(1))
        elif remote_ops and local_ops and not line.startswith("|"):
            break

    for local_op in local_ops:
        for remote_op in remote_ops:
            yield local_op, remote_op


def three_way_merge(base, local, remote):
    dmp = diff_match_patch()
    patches = dmp.patch_make(base, local)
    merged, results = dmp.patch_apply(patches, remote)
    if not all(results):
        return local
    return merged


def main():
    Path("tests/merge/expected").mkdir(exist_ok=True)
    base = Path("tests/merge/inputs/base.md").read_text()

    for local_op, remote_op in parse_matrix():
        local = Path(f"tests/merge/inputs/{local_op}.md").read_text()
        remote = Path(f"tests/merge/inputs/{remote_op}.md").read_text()

        merged = three_way_merge(base, local, remote)

        output = Path(f"tests/merge/expected/{local_op}-{remote_op}.md")
        output.write_text(merged)
        print(f"Generated {output.name}")


if __name__ == "__main__":
    main()

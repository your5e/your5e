import re
from pathlib import Path

import pytest

from wikis.models import Page


def parse_matrix():
    content = Path("tests/merge/tests.md").read_text()
    lines = content.split("\n")
    server_ops = []
    client_ops = []

    for line in lines:
        if line.startswith("|") and "unchanged" in line and "append" in line:
            server_ops = [h.strip() for h in line.split("|")[2:-1]]
        elif line.startswith("| **"):
            match = re.match(r"\| \*\*(.+?)\*\*", line)
            client_ops.append(match.group(1))
        elif server_ops and client_ops and not line.startswith("|"):
            break

    for client_op in client_ops:
        for server_op in server_ops:
            yield client_op, server_op


@pytest.mark.parametrize("client_op,server_op", list(parse_matrix()))
def test_merge(client_op, server_op):
    base = Path("tests/merge/inputs/base.md").read_text()
    client = Path(f"tests/merge/inputs/{client_op}.md").read_text()
    server = Path(f"tests/merge/inputs/{server_op}.md").read_text()
    expected = Path(f"tests/merge/expected/{client_op}-{server_op}.md").read_text()

    merged, _ = Page.three_way_merge(base, server, client)

    assert merged == expected

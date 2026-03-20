# Simple line-length checker.
#
# Usage: awk -f check-line-length.awk [-v max=N] files...
#
# Add "# noqa" or "// noqa" to the end of a line to skip lines that are deliberately long,
# or on a line by itself to skip the following line.

BEGIN {
    if (!max) max = 88
}

/^[[:space:]]*(#|\/\/) noqa[[:space:]]*$/ {
    skip_next = 1
    next
}

skip_next {
    skip_next = 0
    next
}

/(#|\/\/) noqa/ {
    next
}

length > max {
    tail = substr($0, max + 1)
    if (tail ~ /^[[:space:]]*\\$/) next
    print FILENAME ":" FNR ": " length " chars > " max
    print
    err = 1
}

END {
    exit err
}

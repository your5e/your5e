#!/usr/bin/env -S bash -euo pipefail

parse_matrix() {
    local server_ops=()
    local -a rows=()

    while IFS= read -r line; do
        if [[ "$line" == "|"* ]] && [[ "$line" == *"unchanged"* ]] && [[ "$line" == *"append"* ]]; then
            IFS='|' read -ra parts <<< "$line"
            for ((i=2; i<${#parts[@]}; i++)); do
                local trimmed
                trimmed=$(echo "${parts[i]}" | xargs)
                [[ -n "$trimmed" ]] && server_ops+=("$trimmed")
            done
        elif [[ "$line" == "| **"* ]]; then
            rows+=("$line")
        elif [[ ${#server_ops[@]} -gt 0 ]] && [[ ${#rows[@]} -gt 0 ]] && [[ "$line" != "|"* ]]; then
            break
        fi
    done < "tests/merge/tests.md"

    for row in "${rows[@]}"; do
        local client_op
        client_op=$(echo "$row" | sed -n 's/| \*\*\([^*]*\)\*\*.*/\1/p')

        IFS='|' read -ra cells <<< "$row"
        for ((i=0; i<${#server_ops[@]}; i++)); do
            local cell="${cells[i+2]}"
            local server_op="${server_ops[i]}"
            if [[ "$cell" == *"✗"* ]]; then
                echo "${client_op}-${server_op}:skip"
            else
                echo "${client_op}-${server_op}:test"
            fi
        done
    done
}

cat << 'HEADER'
bats_require_minimum_version 1.7.0

setup() {
    export YOUR5E_API_TOKEN="dummy"
    export YOUR5E_API_BASE="http://localhost"
    source "$BATS_TEST_DIRNAME/sync-notebook.sh"
    cp "tests/merge/inputs/base.md" "$BATS_TEST_TMPDIR/base.md"
}
HEADER

while IFS=: read -r test_name action; do
    for client_file in tests/merge/inputs/*.md; do
        name="${client_file##*/}"
        name="${name%.md}"
        if [[ "$test_name" == "$name-"* ]]; then
            client_op="$name"
            server_op="${test_name#"$name"-}"
            skip=''
            if [[ "$action" == "skip" ]]; then
                skip="skip 'git cannot merge'"
            fi
            cat <<EOF

@test "$test_name" {
    $skip
    cp "tests/merge/inputs/${client_op}.md" \\
        "\$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \\
        "\$BATS_TEST_TMPDIR/base.md" \\
        "tests/merge/inputs/${server_op}.md" \\
        "\$BATS_TEST_TMPDIR/client.md"

    diff -u \\
        "tests/merge/expected/${client_op}-${server_op}.md" \\
        "\$BATS_TEST_TMPDIR/client.md"
}
EOF
        fi
    done
done < <(parse_matrix)

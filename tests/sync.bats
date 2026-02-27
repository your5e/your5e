bats_require_minimum_version 1.7.0

setup() {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/api.token")"
    export YOUR5E_API_BASE="http://localhost:5843"
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "reports all files on initial sync" {
    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ sessions/session-01.md
        ++ Home.md
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    diff -u <(echo "$expected_output") <(echo "$output")
    diff -ru "$output_dir" "$fixtures/campaign-notes"
    [ $status -eq 0 ]
}

@test "skips unchanged files" {
    expected_output=""

    cp -r "$fixtures/campaign-notes" "$output_dir"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    diff -u <(echo "$expected_output") <(echo "$output")
    diff -ru "$output_dir" "$fixtures/campaign-notes"
    [ $status -eq 0 ]
}

@test "preserves unknown files and removes soft-deleted files" {
    expected_output=$(sed -e 's/^        //' <<-EOF
        -- Old Notes.md
	EOF
    )

    cp -r "$fixtures/campaign-notes" "$output_dir"
    echo "old notes content" > "$output_dir/Old Notes.md"
    echo "unknown file" > "$output_dir/extra.txt"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    diff -u <(echo "$expected_output") <(echo "$output")
    diff -ru --exclude="extra.txt" "$output_dir" "$fixtures/campaign-notes"
    [ -f "$output_dir/extra.txt" ]
    [ ! -f "$output_dir/Old Notes.md" ]
    [ $status -eq 0 ]
}

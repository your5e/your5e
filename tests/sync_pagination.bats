bats_require_minimum_version 1.7.0

load 'setup_helpers.sh'

setup_file() {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"
    export YOUR5E_API_BASE="http://localhost:5854"
    export page_size=$(sed -n 's/^PAGE_SIZE = //p' api/notebooks/views.py)
    export pages_to_create=$((page_size + 1))
    restore_database

    for i in $(seq 1 "$pages_to_create"); do
        curl -s \
            -X POST \
            -H "Authorization: Token $YOUR5E_API_TOKEN" \
            -F "file=@-;filename=page-${i}.md" \
                "${YOUR5E_API_BASE}/v1/notebooks/norm/campaign-notes/" \
                    <<< "# Page ${i}"
    done
}

setup() {
    fail_on_single_listing_call
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "sync fetches all pages across pagination boundaries" {
    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(
        sed -e 's/^            //' <<-EOF
            pull: "random-hexmap-7.png" (v1)
            pull: "index.md" (v1)
            pull: "Home.md" (v2)
            pull: "sessions/session-01.md" (v1)
            pull: "Bestiary.md" (v2)
            pull: "characters/NPCs.md" (v2)
            pull: "The Old Café.md" (v1)
            pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
		EOF
        for i in $(seq 1 $pages_to_create); do
            printf 'pull: "page-%s.md" (v1)\n' "$i"
        done
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    for i in $(seq 1 "$pages_to_create"); do
        diff -u <(echo "# Page ${i}") "$output_dir/page-${i}.md"
        assert_file_in_state "page-${i}.md"
    done
    assert_file_downloaded "Home.md"
    assert_file_downloaded "Bestiary.md"
    assert_file_downloaded "index.md"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "sessions/session-01.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_file_downloaded "World Regions/Northern Kingdoms/Frosthold.md"
    assert_last_updated_exists
    [ $status -eq 0 ]
}

# Subsequent sync algorithm test suite
#
# Tests for syncing to a directory that has been synced before
# (.sync-state file exists). See first_sync.bats for initial sync tests.
#
# This file tests the reference implementation (sync-notebook.sh) and documents
# the expected behaviour of ANY notebook sync client. Implementers should use
# these scenarios to verify their own sync logic produces the same outcomes.

bats_require_minimum_version 1.7.0

load 'setup_helpers.sh'

setup_file() {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"
    export YOUR5E_API_BASE="http://localhost:5844"
    export BATS_FILE_TMPDIR="${BATS_FILE_TMPDIR:-$(mktemp -d)}"

    restore_database

    # fetch page metadata from API once for all tests
    curl -s -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/api/notebooks/norm/campaign-notes/" \
        | jq -r '.results[] | [.filename, .uuid, .content_hash, (.deleted_at // "")] | @tsv' \
        > "$BATS_FILE_TMPDIR/pages"
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
    init_synced_dir
}


@test "no change" {
    fail_on_multiple_curl_calls

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "untracked file" {
    create_file "scratchpad.txt"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "scratchpad.txt"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_state_matches_fixture
    assert_success
}

@test "untracked file, local edited, directory" {
    untrack_and_remove_file "Bestiary.md"
    create_file "Bestiary.md/notes.txt"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot pull "Bestiary.md", blocked by local directory
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "Bestiary.md/notes.txt"
    assert_file_not_downloaded "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "untracked file, local edited" {
    untrack_file "Home.md"
    modify_file "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot pull "Home.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "Home.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "untracked file, remote renamed" {
    set_older_filename "characters/NPCs.md" "NPCs.md"
    create_file "characters/NPCs.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "characters/NPCs.md" "NPCs.md"
    assert_file_ignored "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "untracked file, local edited, remote renamed" {
    set_older_filename "Home.md" "Welcome.md"
    set_older_content "Welcome.md"
    create_file "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot rename "Welcome.md" to "Home.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "Home.md"
    assert_tracked_file_intact "Welcome.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "remote edited" {
    set_older_content "Bestiary.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed" {
    set_older_filename "The Old Café.md" "café.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "café.md" to "The Old Café.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, local edited, directory" {
    set_older_filename "characters/NPCs.md" "NPCs.md"
    create_file "characters/NPCs.md/notes.txt"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", blocked by local directory
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "NPCs.md"
    assert_file_ignored "characters/NPCs.md/notes.txt"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "remote edited, remote renamed" {
    set_older_filename "Home.md" "Welcome.md"
    set_older_content "Welcome.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "Welcome.md" to "Home.md"
        pull: "Home.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, swapped" {
    set_older_filename "characters/NPCs.md" "temp.md"
    set_older_filename "sessions/session-01.md" "characters/NPCs.md"
    set_older_filename "temp.md" "sessions/session-01.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "characters/NPCs.md" to "sessions/session-01.md"
        pull: renamed "sessions/session-01.md" to "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, chain" {
    set_older_filename "sessions/session-01.md" "old.md"
    set_older_filename "characters/NPCs.md" "sessions/session-01.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "old.md" to "sessions/session-01.md"
        pull: renamed "sessions/session-01.md" to "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, chain reversed" {
    set_older_filename "characters/NPCs.md" "old.md"
    set_older_filename "sessions/session-01.md" "characters/NPCs.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "characters/NPCs.md" to "sessions/session-01.md"
        pull: renamed "old.md" to "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, cycle" {
    set_older_filename "Bestiary.md" "temp.md"
    set_older_filename "Home.md" "Bestiary.md"
    set_older_filename "index.md" "Home.md"
    set_older_filename "temp.md" "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "Home.md" to "index.md"
        pull: renamed "Bestiary.md" to "Home.md"
        pull: renamed "index.md" to "Bestiary.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "remote renamed, cycle, local edited" {
    set_older_filename "Bestiary.md" "temp.md"
    set_older_filename "Home.md" "Bestiary.md"
    set_older_filename "index.md" "Home.md"
    set_older_filename "temp.md" "index.md"
    modify_file "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "Home.md" to "index.md", local changes would be lost
        pull: ERROR cannot rename "Bestiary.md" to "Home.md", blocked by local file
        pull: ERROR cannot rename "index.md" to "Bestiary.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home.md"
    assert_file_in_state "Home.md"
    assert_tracked_file_matches_fixture "Home.md" "Bestiary.md"
    assert_tracked_file_matches_fixture "Bestiary.md" "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "remote renamed, cycle, untracked file" {
    set_older_filename "Bestiary.md" "temp.md"
    set_older_filename "Home.md" "Bestiary.md"
    set_older_filename "index.md" "Home.md"
    set_older_filename "temp.md" "index.md"
    untrack_file "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot pull "index.md", blocked by local file
        pull: ERROR cannot rename "Bestiary.md" to "Home.md", blocked by local file
        pull: ERROR cannot rename "index.md" to "Bestiary.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "Home.md"
    assert_file_not_in_state "Home.md"
    assert_tracked_file_matches_fixture "Home.md" "Bestiary.md"
    assert_tracked_file_matches_fixture "Bestiary.md" "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local edited" {
    modify_file "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "index.md"
    assert_file_in_state "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local edited, remote edited" {
    set_older_content "Bestiary.md"
    modify_file "Bestiary.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING pull "Bestiary.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Bestiary.md"
    assert_file_in_state "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local edited, remote renamed" {
    set_older_filename "characters/NPCs.md" "NPCs.md"
    modify_file "NPCs.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "NPCs.md"
    assert_file_in_state "NPCs.md"
    assert_file_not_downloaded "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local edited, remote edited, remote renamed" {
    set_older_filename "Home.md" "Welcome.md"
    set_older_content "Welcome.md"
    modify_file "Welcome.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "Welcome.md" to "Home.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Welcome.md"
    assert_file_in_state "Welcome.md"
    assert_file_not_downloaded "Home.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "remote deleted" {
    file_tracks_deleted_remote "archive/Old Notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "archive/Old Notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "archive/Old Notes.md"
    assert_empty_dir_removed "archive"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "remote deleted, local edited" {
    file_tracks_deleted_remote "Old Notes.md"
    modify_file "Old Notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING delete "Old Notes.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Old Notes.md"
    assert_file_in_state "Old Notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "stale file" {
    add_stale_file "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "my-notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "stale file, remote edited" {
    mark_file_stale "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "stale file, local edited" {
    mark_file_stale "index.md"
    modify_file "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING delete "index.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "index.md"
    assert_file_in_state "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "stale file, local deleted" {
    add_stale_file "my-notes.md"
    delete_tracked_file "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "stale file, local deleted, remote edited" {
    mark_file_stale "index.md"
    delete_tracked_file "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "local deleted" {
    delete_tracked_file "index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING pull "index.md", already deleted locally
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_not_restored "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local deleted, remote edited" {
    set_older_content "Bestiary.md"
    delete_tracked_file "Bestiary.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "local deleted, remote renamed" {
    set_older_filename "characters/NPCs.md" "NPCs.md"
    delete_tracked_file "NPCs.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", "NPCs.md" deleted locally
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_not_restored "NPCs.md"
    assert_file_not_downloaded "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local deleted, remote edited, remote renamed" {
    set_older_filename "Home.md" "Welcome.md"
    set_older_content "Welcome.md"
    delete_tracked_file "Welcome.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Home.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "local deleted, local edited, remote edited, remote renamed" {
    set_older_filename "Home.md" "Welcome.md"
    set_older_content "Welcome.md"
    delete_tracked_file "Welcome.md"
    create_file "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot rename "Welcome.md" to "Home.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home.md"
    assert_file_not_in_state "Home.md"
    assert_tracked_file_not_restored "Welcome.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local deleted, remote deleted" {
    file_tracks_deleted_remote "Old Notes.md"
    delete_tracked_file "Old Notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "Old Notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "Old Notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed" {
    rename_local_file "index.md" "renamed-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "renamed-index.md"
    assert_file_in_state "renamed-index.md"
    assert_file_not_in_state "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited" {
    rename_local_file "index.md" "renamed-index.md"
    modify_file "renamed-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "renamed-index.md"
    assert_file_in_state "renamed-index.md"
    assert_file_not_in_state "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, remote edited" {
    rename_local_file "Bestiary.md" "renamed-bestiary.md"
    set_older_content "renamed-bestiary.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Bestiary.md" to "renamed-bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "Bestiary.md" "renamed-bestiary.md"
    assert_file_in_state "renamed-bestiary.md"
    assert_file_not_in_state "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited, remote edited" {
    rename_local_file "Bestiary.md" "renamed-bestiary.md"
    set_older_content "renamed-bestiary.md"
    modify_file "renamed-bestiary.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING pull "Bestiary.md" to "renamed-bestiary.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "renamed-bestiary.md"
    assert_file_in_state "renamed-bestiary.md"
    assert_file_not_in_state "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, remote renamed" {
    set_older_filename "index.md" "original.md"
    rename_local_file "original.md" "my-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "original.md" to "index.md", already "my-index.md" locally
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "original.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited, remote renamed" {
    set_older_filename "index.md" "original.md"
    rename_local_file "original.md" "my-index.md"
    modify_file "my-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "original.md" to "index.md", already "my-index.md" locally
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "original.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, remote edited, remote renamed" {
    set_older_filename "index.md" "original.md"
    set_older_content "original.md"
    rename_local_file "original.md" "my-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "original.md" to "index.md", already "my-index.md" locally
        pull: "index.md" to "my-index.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "original.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited, remote edited, remote renamed" {
    set_older_filename "index.md" "original.md"
    set_older_content "original.md"
    rename_local_file "original.md" "my-index.md"
    modify_file "my-index.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING rename "original.md" to "index.md", already "my-index.md" locally
        pull: SKIPPING pull "index.md" to "my-index.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "original.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, remote deleted" {
    file_tracks_deleted_remote "Old Notes.md"
    rename_local_file "Old Notes.md" "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "Old Notes.md" (was "my-notes.md")
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_file_not_in_state "Old Notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited, remote deleted" {
    file_tracks_deleted_remote "Old Notes.md"
    rename_local_file "Old Notes.md" "my-notes.md"
    modify_file "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING delete "Old Notes.md" (at "my-notes.md"), local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "my-notes.md"
    assert_file_in_state "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, stale file" {
    add_stale_file "original.md"
    rename_local_file "original.md" "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "my-notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

@test "local renamed, local edited, stale file" {
    add_stale_file "original.md"
    rename_local_file "original.md" "my-notes.md"
    modify_file "my-notes.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: SKIPPING delete "my-notes.md", local changes would be lost
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "my-notes.md"
    assert_file_in_state "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_success
}

# New tests should use or create helpers so as not to obscure what the test is actually doing.

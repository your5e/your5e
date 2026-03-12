# First sync algorithm test suite
#
# Tests for syncing to a directory that has never been synced before
# (no .sync-state file exists).
#
# This file tests the reference implementation (sync-notebook.sh) and documents
# the expected behaviour of ANY notebook sync client. Implementers should use
# these scenarios to verify their own sync logic produces the same outcomes.

bats_require_minimum_version 1.7.0

load 'setup_helpers.sh'

setup_file() {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"
    export YOUR5E_API_BASE="http://localhost:5843"
    restore_database
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "empty directory" {
    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_not_downloaded "Old Notes.md"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "local files" {
    create_file "Home.md"
    create_file "index.md"
    create_file "notes.txt"
    create_file "sessions/notes.txt"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: ERROR cannot pull "index.md", blocked by local file
        pull: ERROR cannot pull "Home.md", blocked by local file
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "Home.md"
    assert_file_ignored "index.md"
    assert_file_ignored "notes.txt"
    assert_file_ignored "sessions/notes.txt"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "sessions/session-01.md"
    assert_file_downloaded "Bestiary.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_success
}

@test "local matches remote" {
    copy_fixture "Home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: tracking "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_success
}

@test "local file clashes" {
    create_file "sessions"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: ERROR cannot pull "sessions/session-01.md", blocked by local file
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "sessions"
    assert_file_not_downloaded "sessions/session-01.md"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "index.md"
    assert_file_downloaded "Home.md"
    assert_file_downloaded "Bestiary.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_success
}

@test "local dir clashes" {
    create_file "Bestiary.md/notes.txt"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: ERROR cannot pull "Bestiary.md", blocked by local directory
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "Bestiary.md/notes.txt"
    assert_file_not_downloaded "Bestiary.md"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "index.md"
    assert_file_downloaded "Home.md"
    assert_file_downloaded "sessions/session-01.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_success
}

@test "case collision" {
    create_file "home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: ERROR cannot pull "Home.md", blocked by local file with different case
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_ignored "home.md"
    assert_file_not_in_state "Home.md"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "index.md"
    assert_file_downloaded "sessions/session-01.md"
    assert_file_downloaded "Bestiary.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_success
}

@test "case collision, matches" {
    copy_fixture "Home.md" "home.md"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: ERROR cannot pull "Home.md", blocked by local file with different case
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "Home.md" "home.md"
    assert_file_not_in_state "Home.md"
    assert_file_downloaded "random-hexmap-7.png"
    assert_file_downloaded "index.md"
    assert_file_downloaded "sessions/session-01.md"
    assert_file_downloaded "Bestiary.md"
    assert_file_downloaded "characters/NPCs.md"
    assert_file_downloaded "The Old Café.md"
    assert_success
}

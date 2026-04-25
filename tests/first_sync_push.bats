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
    export YOUR5E_API_BASE="http://localhost:5854"
    export SHORT_HOST="$(hostname -s)"
}

setup() {
    restore_database

    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "empty directory" {
    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_not_downloaded "Old Notes.md"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_last_updated_matches_expected
    assert_success
}

@test "empty notebook" {
    fail_on_since_parameter
    run tests/sync-notebook.sh norm/empty-notebook "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_output_dir_exists
    assert_state_has_no_files
    assert_last_updated_is_epoch
    assert_success
}

@test "local files" {
    create_file "Home.md"
    create_file "index.md"
    create_file "notes.txt"
    create_file "sessions/notes.txt"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"
        push: "Home (conflict ${SHORT_HOST}).md" (v1)
        push: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"
        push: "index (conflict ${SHORT_HOST}).md" (v1)
        push: "notes.txt" (v1)
        push: "sessions/notes.txt" (v1)
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Home (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_file_unchanged "index (conflict ${SHORT_HOST}).md"
    assert_file_pushed "index (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_file_pushed "notes.txt" "text/plain"
    assert_file_pushed "sessions/notes.txt" "text/plain"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

@test "local matches remote" {
    copy_fixture "Home.md"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: tracking "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_last_updated_matches_expected
    assert_success
}

@test "local file clashes" {
    create_file "sessions"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "sessions": Filename must have an extension.
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: renamed "sessions" to "sessions (conflict ${SHORT_HOST})"
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "sessions (conflict ${SHORT_HOST})"
    assert_file_not_in_state "sessions (conflict ${SHORT_HOST})"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

@test "local dir clashes" {
    create_file "Bestiary.md/notes.txt"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"
        push: "Bestiary (conflict ${SHORT_HOST}).md/notes.txt" (v1)
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Bestiary (conflict ${SHORT_HOST}).md/notes.txt"
    assert_file_pushed "Bestiary (conflict ${SHORT_HOST}).md/notes.txt" "text/plain"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

@test "hidden files ignored" {
    create_file ".hidden.md"
    create_file ".obsidian/app.json"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".hidden.md": No hidden files.
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged ".hidden.md"
    assert_file_unchanged ".obsidian/app.json"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

@test "case collision" {
    create_file "home.md"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"
        push: "home (conflict ${SHORT_HOST}).md" (v1)
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "home (conflict ${SHORT_HOST}).md"
    assert_file_pushed "home (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

@test "case collision, matches" {
    copy_fixture "Home.md" "home.md"

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"
        push: "home (conflict ${SHORT_HOST}).md" (v1)
        pull: "random-hexmap-7.png" (v1)
        pull: "index.md" (v1)
        pull: "Home.md" (v2)
        pull: "sessions/session-01.md" (v1)
        pull: "Bestiary.md" (v2)
        pull: "characters/NPCs.md" (v2)
        pull: "The Old Café.md" (v1)
        pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "Home.md" "home (conflict ${SHORT_HOST}).md"
    assert_file_pushed "home (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_fixture_files_downloaded
    assert_fixture_files_in_state
    assert_last_updated_matches_expected
    assert_success
}

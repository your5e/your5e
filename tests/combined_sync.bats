# Combined sync scenario test suite
#
# Tests that repeated syncs do not break in unexpected ways. Each test makes
# one change and syncs, building on the state from the previous test.

bats_require_minimum_version 1.7.0

load 'setup_helpers.sh'

setup_file() {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"
    export YOUR5E_API_BASE="http://localhost:5854"
    export SHORT_HOST="$(hostname -s)"

    restore_database
    setup_pages_file

    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_FILE_TMPDIR/output"
    state_file="$output_dir/.sync-state"

    mkdir -p "$output_dir"
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_FILE_TMPDIR/output"
    state_file="$output_dir/.sync-state"
}


@test "initial sync" {
    create_file "my-notes.md"
    create_file ".obsidian/app.json"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        push: "my-notes.md" (v1)
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
    assert_success

    assert_file_pushed "my-notes.md" "text/markdown"
    assert_file_unchanged ".obsidian/app.json"
    assert_file_not_in_state ".obsidian/app.json"
}

@test "stable sync" {
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success
}

@test "local edit" {
    modify_file "my-notes.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "my-notes.md" (v2)
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_pushed "my-notes.md" "text/markdown"
}

@test "server edit" {
    server_edit_content "$(uuid_for "The Old Café.md")"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        pull: "The Old Café.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_server_edited_content "The Old Café.md"
}

@test "merged edit" {
    modify_file "Bestiary.md" "$(mergeable_orc)"
    server_edit_content "$(uuid_for "Bestiary.md")" "$(mergeable_troll)"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v4, merged)
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success
}

@test "replaced edit" {
    modify_file "index.md"
    server_edit_content "$(uuid_for "index.md")"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "index.md" (v3, replaced)
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success
}

@test "conflicting new file" {
    server_create "Quests.md"
    create_file "Quests.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        info: renamed "Quests.md" to "Quests (conflict ${SHORT_HOST}).md"
        push: "Quests (conflict ${SHORT_HOST}).md" (v1)
        pull: "Quests.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_unchanged "Quests (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Quests (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_tracked_file_intact "Quests.md"
}

@test "local rename, aware" {
    tracked_rename "my-notes.md" "notes/my-notes.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "my-notes.md" to "notes/my-notes.md"
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_in_state "notes/my-notes.md"
    assert_file_not_in_state "my-notes.md"
}

@test "server delete" {
    server_delete "characters/NPCs.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        pull: deleted "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_tracked_file_deleted "characters/NPCs.md"
}

@test "server rename" {
    session_uuid=$(uuid_for "sessions/session-01.md")
    server_rename "$session_uuid" "logs/Session 01.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
        pull: renamed "sessions/session-01.md" to "logs/Session 01.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_tracked_file_deleted "sessions/session-01.md"
    assert_file_in_state "logs/Session 01.md"
    assert_file_not_in_state "sessions/session-01.md"
    assert_empty_dir_removed "sessions"
}

@test "local rename, unaware" {
    move_file "index.md" "moved-index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: detected rename "index.md" to "moved-index.md"
        push: renamed "index.md" to "moved-index.md"
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_in_state "moved-index.md"
    assert_file_not_in_state "index.md"
}

@test "local delete, aware" {
    tracked_delete "Home.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "Home.md"
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_deleted_on_server "Home.md"
    assert_file_not_in_state "Home.md"
}

@test "local delete, unaware" {
    remove_file "The Old Café.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "The Old Café.md"
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_deleted_on_server "The Old Café.md"
    assert_file_not_in_state "The Old Café.md"
}

@test "stale file" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    server_purge "$bestiary_uuid"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success
    assert_file_in_state "Bestiary.md"
}

@test "stale file, full sync" {
    force_full_sync

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "Bestiary.md"
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_tracked_file_deleted "Bestiary.md"
    assert_file_not_in_state "Bestiary.md"
}

@test "final stable state" {
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success

    assert_file_unchanged ".obsidian/app.json"
    assert_file_not_in_state ".obsidian/app.json"
    assert_file_in_state "notes/my-notes.md"
    assert_file_in_state "Quests.md"
    assert_file_in_state "Quests (conflict ${SHORT_HOST}).md"
    assert_file_in_state "logs/Session 01.md"
    assert_file_not_in_state "Bestiary.md"
    assert_file_not_in_state "sessions/session-01.md"
    assert_file_not_in_state "Home.md"
    assert_file_not_in_state "The Old Café.md"
    assert_sync_metadata_updated
}

@test "final stable sync" {
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push ".obsidian/app.json": No hidden files.
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_success
}

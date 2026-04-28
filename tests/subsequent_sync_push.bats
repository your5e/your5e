# Subsequent sync algorithm test suite (push enabled)
#
# Tests for syncing with push enabled. Same scenarios as subsequent_sync.bats
# but with push operations happening before pull.
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
    setup_pages_file

    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
    init_synced_dir
    setup_recent_sync_metadata
    fail_on_missing_since_parameter
}


@test "no change, outdated timestamp" {
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_sync_metadata_updated
    assert_success
}

@test "no change, recent timestamp" {
    fail_on_multiple_curl_calls
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_last_updated_exists
    assert_success
}

@test "untracked file" {
    create_file "scratchpad.txt"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "scratchpad.txt" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "scratchpad.txt"
    assert_file_pushed "scratchpad.txt" "text/plain"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited, directory" {
    server_create "Rumours.md"
    create_file "Rumours.md/notes.txt"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Rumours.md" to "Rumours (conflict ${SHORT_HOST}).md"
        push: "Rumours (conflict ${SHORT_HOST}).md/notes.txt" (v1)
        pull: "Rumours.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Rumours (conflict ${SHORT_HOST}).md/notes.txt"
    assert_file_pushed "Rumours (conflict ${SHORT_HOST}).md/notes.txt" "text/plain"
    assert_tracked_file_intact "Rumours.md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited" {
    server_create "Quests.md"
    create_file "Quests.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Quests.md" to "Quests (conflict ${SHORT_HOST}).md"
        push: "Quests (conflict ${SHORT_HOST}).md" (v1)
        pull: "Quests.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Quests (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Quests (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_tracked_file_intact "Quests.md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, remote renamed" {
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    create_file "npcs/Major.md"
    server_rename "$npcs_uuid" "npcs/Major.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "npcs/Major.md" to "npcs/Major (conflict ${SHORT_HOST}).md"
        push: "npcs/Major (conflict ${SHORT_HOST}).md" (v1)
        pull: renamed "characters/NPCs.md" to "npcs/Major.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "npcs/Major (conflict ${SHORT_HOST}).md"
    assert_file_pushed "npcs/Major (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_uuid_local_filename "$npcs_uuid" "npcs/Major.md"
    assert_file_matches_fixture "characters/NPCs.md" "npcs/Major.md"
    assert_fixtures_intact_except "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited, remote renamed" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    create_file "Monsters.md"
    server_rename "$bestiary_uuid" "Monsters.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Monsters.md" to "Monsters (conflict ${SHORT_HOST}).md"
        push: "Monsters (conflict ${SHORT_HOST}).md" (v1)
        pull: renamed "Bestiary.md" to "Monsters.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Monsters (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Monsters (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_uuid_local_filename "$bestiary_uuid" "Monsters.md"
    assert_file_matches_fixture "Bestiary.md" "Monsters.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote edited" {
    server_edit_content "$(uuid_for "Bestiary.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Bestiary.md" (v3)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "Bestiary.md"
    assert_file_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed" {
    cafe_uuid=$(uuid_for "The Old Café.md")
    server_rename "$cafe_uuid" "The New Café.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "The Old Café.md" to "The New Café.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [[ ! -f "$output_dir/The Old Café.md" ]]
    assert_file_matches_fixture "The Old Café.md" "The New Café.md"
    assert_file_in_state "The New Café.md"
    assert_file_not_in_state "The Old Café.md"
    assert_fixtures_intact_except "The Old Café.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, local edited, directory" {
    session_uuid=$(uuid_for "sessions/session-01.md")
    server_rename "$session_uuid" "logs/Session 01.md"
    create_file "logs/Session 01.md/notes.txt"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "logs/Session 01.md" to "logs/Session 01 (conflict ${SHORT_HOST}).md"
        push: "logs/Session 01 (conflict ${SHORT_HOST}).md/notes.txt" (v1)
        pull: renamed "sessions/session-01.md" to "logs/Session 01.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "logs/Session 01 (conflict ${SHORT_HOST}).md/notes.txt"
    assert_file_pushed "logs/Session 01 (conflict ${SHORT_HOST}).md/notes.txt" "text/plain"
    assert_uuid_local_filename "$session_uuid" "logs/Session 01.md"
    assert_file_matches_fixture "sessions/session-01.md" "logs/Session 01.md"
    assert_fixtures_intact_except "sessions/session-01.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote edited, remote renamed" {
    home_uuid=$(uuid_for "Home.md")
    server_edit_content "$home_uuid"
    server_rename "$home_uuid" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "Home.md" to "Welcome.md"
        pull: "Welcome.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "Welcome.md"
    assert_file_not_downloaded "Home.md"
    assert_file_in_state "Welcome.md"
    assert_fixtures_intact_except "Home.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, swapped" {
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    session_uuid=$(uuid_for "sessions/session-01.md")
    server_rename "$npcs_uuid" "temp.md"
    server_rename "$session_uuid" "characters/NPCs.md"
    server_rename "$npcs_uuid" "sessions/session-01.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "sessions/session-01.md" to "characters/NPCs.md"
        pull: renamed "characters/NPCs.md" to "sessions/session-01.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "characters/NPCs.md" "sessions/session-01.md"
    assert_file_matches_fixture "sessions/session-01.md" "characters/NPCs.md"
    assert_file_in_state "sessions/session-01.md"
    assert_file_in_state "characters/NPCs.md"
    assert_fixtures_intact_except "sessions/session-01.md" "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, chain" {
    session_uuid=$(uuid_for "sessions/session-01.md")
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    server_rename "$session_uuid" "old.md"
    server_rename "$npcs_uuid" "sessions/session-01.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "sessions/session-01.md" to "old.md"
        pull: renamed "characters/NPCs.md" to "sessions/session-01.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "sessions/session-01.md" "old.md"
    assert_file_matches_fixture "characters/NPCs.md" "sessions/session-01.md"
    assert_file_not_downloaded "characters/NPCs.md"
    assert_file_in_state "old.md"
    assert_file_in_state "sessions/session-01.md"
    assert_fixtures_intact_except "sessions/session-01.md" "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, chain reversed" {
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    session_uuid=$(uuid_for "sessions/session-01.md")
    server_rename "$npcs_uuid" "old.md"
    server_rename "$session_uuid" "characters/NPCs.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "characters/NPCs.md" to "old.md"
        pull: renamed "sessions/session-01.md" to "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "characters/NPCs.md" "old.md"
    assert_file_matches_fixture "sessions/session-01.md" "characters/NPCs.md"
    assert_file_not_downloaded "sessions/session-01.md"
    assert_file_in_state "old.md"
    assert_file_in_state "characters/NPCs.md"
    assert_fixtures_intact_except "sessions/session-01.md" "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    home_uuid=$(uuid_for "Home.md")
    index_uuid=$(uuid_for "index.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$home_uuid" "Bestiary.md"
    server_rename "$index_uuid" "Home.md"
    server_rename "$bestiary_uuid" "index.md"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "Home.md" to "Bestiary.md"
        pull: renamed "index.md" to "Home.md"
        pull: renamed "Bestiary.md" to "index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "Bestiary.md" "index.md"
    assert_file_matches_fixture "Home.md" "Bestiary.md"
    assert_file_matches_fixture "index.md" "Home.md"
    assert_file_in_state "index.md"
    assert_file_in_state "Bestiary.md"
    assert_file_in_state "Home.md"
    assert_fixtures_intact_except "Bestiary.md" "Home.md" "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle, local edited, mergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    home_uuid=$(uuid_for "Home.md")
    index_uuid=$(uuid_for "index.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$home_uuid" "Bestiary.md"
    server_rename "$index_uuid" "Home.md"
    server_rename "$bestiary_uuid" "index.md"
    modify_file "Bestiary.md" "$(mergeable_orc)"
    server_edit_content "$bestiary_uuid" "$(mergeable_troll)"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # push: attempted operations:
    # 1. local Bestiary.md has been updated, so rename remote index.md (same UUID as our
    #    Bestiary.md) back to Bestiary.md -- fails, path exists
    # 2. push merged content to index.md
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot rename "index.md" to "Bestiary.md": Path 'bestiary' already exists.
        pull: renamed "Home.md" to "Bestiary.md"
        pull: renamed "index.md" to "Home.md"
        pull: renamed "Bestiary.md" to "index.md"
        pull: "index.md" (v5, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(merged_orc_troll) "$output_dir/index.md"
    assert_uuid_local_filename "$bestiary_uuid" "index.md"
    assert_uuid_local_filename "$home_uuid" "Bestiary.md"
    assert_uuid_local_filename "$index_uuid" "Home.md"
    assert_fixtures_intact_except "Bestiary.md" "Home.md" "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle, local edited, unmergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    home_uuid=$(uuid_for "Home.md")
    index_uuid=$(uuid_for "index.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$home_uuid" "Bestiary.md"
    server_rename "$index_uuid" "Home.md"
    server_rename "$bestiary_uuid" "index.md"
    modify_file "Bestiary.md"
    server_edit_content "$bestiary_uuid"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # push: attempted operations:
    # 1. local Bestiary.md has been updated, so rename remote index.md (same UUID as our
    #    Bestiary.md) back to Bestiary.md -- fails, path exists
    # 2. push content (replaced) to index.md
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot rename "index.md" to "Bestiary.md": Path 'bestiary' already exists.
        pull: renamed "Home.md" to "Bestiary.md"
        pull: renamed "index.md" to "Home.md"
        info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"
        pull: "index.md" (v5)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary (conflict ${SHORT_HOST}).md"
    assert_file_not_in_state "Bestiary (conflict ${SHORT_HOST}).md"
    assert_server_edited_content "index.md"
    assert_uuid_local_filename "$bestiary_uuid" "index.md"
    assert_uuid_local_filename "$home_uuid" "Bestiary.md"
    assert_uuid_local_filename "$index_uuid" "Home.md"
    assert_fixtures_intact_except "Bestiary.md" "Home.md" "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle, untracked file" {
    home_uuid=$(uuid_for "Home.md")
    index_uuid=$(uuid_for "index.md")
    bestiary_uuid=$(uuid_for "Bestiary.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$home_uuid" "Bestiary.md"
    server_rename "$index_uuid" "Home.md"
    server_rename "$bestiary_uuid" "index.md"
    untrack_and_remove_file "Home.md"
    create_file "Home.md"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # attempted operations:
    # 1. new Home.md, so push it -- fails, path exists
    # 2. break the rename cycle -- fails, local changes to Home.md would be lost
    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"
        push: "Home (conflict ${SHORT_HOST}).md" (v1)
        pull: renamed "index.md" to "Home.md"
        pull: renamed "Bestiary.md" to "index.md"
        pull: "Bestiary.md" (v3)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Home (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_uuid_local_filename "$index_uuid" "Home.md"
    assert_uuid_local_filename "$bestiary_uuid" "index.md"
    assert_uuid_local_filename "$home_uuid" "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md" "Home.md" "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited" {
    modify_file "index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "index.md"
    assert_file_pushed "index.md" "text/markdown"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, CRLF line endings" {
    printf "First line\r\nSecond line\r\nThird line" > "$output_dir/Home.md"

    # push: first run, sends the modification, server will normalise line endings
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Home.md" (v3)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")
    assert_sync_metadata_updated
    assert_success

    expected_content=$'First line\nSecond line\nThird line\n'
    assert_file_content "Home.md" "$expected_content"

    # second run, no changes as the on-server modified Home.md has been pulled
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "Home.md"
    assert_fixtures_intact_except "Home.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, mergeable" {
    modify_file "Bestiary.md" "$(mergeable_orc)"
    server_edit_content "$(uuid_for "Bestiary.md")" "$(mergeable_troll)"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v4, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(merged_orc_troll) "$output_dir/Bestiary.md"

    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, unmergeable" {
    modify_file "Bestiary.md"
    server_edit_content "$(uuid_for "Bestiary.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v4, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, same content" {
    modify_file "Bestiary.md"
    server_edit_content "$(uuid_for "Bestiary.md")" "modified local content"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, no common ancestor" {
    index_uuid=$(uuid_for "index.md")
    modify_file "index.md"
    server_edit_content "$index_uuid"
    set_base_hash "index.md" "no-common-ancestor"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "index.md" (v3, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "index.md"
    assert_file_pushed "index.md" "text/markdown"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote renamed" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    modify_file "Bestiary.md"
    server_rename "$bestiary_uuid" "renamed-bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "renamed-bestiary.md" to "Bestiary.md"
        push: "Bestiary.md" (v5)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_file_in_state "Bestiary.md"
    assert_file_not_in_state "renamed-bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, remote renamed, mergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    modify_file "Bestiary.md" "$(mergeable_orc)"
    server_edit_content "$bestiary_uuid" "$(mergeable_troll)"
    server_rename "$bestiary_uuid" "renamed-bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "renamed-bestiary.md" to "Bestiary.md"
        push: "Bestiary.md" (v6, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(merged_orc_troll) "$output_dir/Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_file_in_state "Bestiary.md"
    assert_file_not_in_state "renamed-bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, remote renamed, unmergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    modify_file "Bestiary.md"
    server_edit_content "$bestiary_uuid"
    server_rename "$bestiary_uuid" "renamed-bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "renamed-bestiary.md" to "Bestiary.md"
        push: "Bestiary.md" (v6, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_file_in_state "Bestiary.md"
    assert_file_not_in_state "renamed-bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote deleted" {
    server_delete "characters/NPCs.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "characters/NPCs.md"
    assert_empty_dir_removed "characters"
    assert_fixtures_intact_except "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote deleted, local edited" {
    server_delete "Bestiary.md"
    modify_file "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v3, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, incremental sync" {
    add_stale_file "my-notes.md"

    # incremental sync cannot detect stale files (see fetch_remote_state)
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    diff -u <(echo "") <(echo "$output")
    assert_file_unchanged "my-notes.md"
    assert_file_in_state "my-notes.md"
    assert_fixtures_intact
    assert_last_updated_exists
    assert_success
}

@test "stale file, full sync" {
    add_stale_file "my-notes.md"
    setup_old_sync_metadata

    # full sync detects stale files by comparing against complete server state
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "my-notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, remote edited, incremental sync" {
    mark_file_stale "index.md"
    server_edit_content "$(uuid_for "index.md")"

    # incremental sync can deduce file is stale, as there is no report of
    # the file being renamed, but another uuid is using the filename
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_not_in_state "stale-uuid"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, remote edited, full sync" {
    mark_file_stale "index.md"
    server_edit_content "$(uuid_for "index.md")"
    setup_old_sync_metadata

    # full sync detects stale file, removes it, downloads new file
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local edited, incremental sync" {
    add_stale_file "my-notes.md"
    modify_file "my-notes.md"

    # push: incremental sync learns UUID is stale update is 404, pushes new file
    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "my-notes.md" to "my-notes (conflict ${SHORT_HOST}).md"
        push: "my-notes (conflict ${SHORT_HOST}).md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes (conflict ${SHORT_HOST}).md"
    assert_file_in_state "my-notes (conflict ${SHORT_HOST}).md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local edited, full sync" {
    add_stale_file "my-notes.md"
    modify_file "my-notes.md"
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # push: full sync knows UUID is stale
    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "my-notes.md" to "my-notes (conflict ${SHORT_HOST}).md"
        push: "my-notes (conflict ${SHORT_HOST}).md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes (conflict ${SHORT_HOST}).md"
    assert_file_in_state "my-notes (conflict ${SHORT_HOST}).md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local edited, remote edited, incremental sync" {
    mark_file_stale "index.md"
    modify_file "index.md"
    server_edit_content "$(uuid_for "index.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"
        push: "index (conflict ${SHORT_HOST}).md" (v1)
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_file_modified "index (conflict ${SHORT_HOST}).md"
    assert_file_pushed "index (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local edited, remote edited, full sync" {
    mark_file_stale "index.md"
    modify_file "index.md"
    server_edit_content "$(uuid_for "index.md")"
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"
        push: "index (conflict ${SHORT_HOST}).md" (v1)
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_file_modified "index (conflict ${SHORT_HOST}).md"
    assert_file_pushed "index (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local deleted" {
    add_stale_file "my-notes.md"
    delete_tracked_file "my-notes.md"
    assert_in_state "stale-uuid"
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_not_in_state "stale-uuid"
    assert_dir_matches_fixture
    assert_state_matches_fixture
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local deleted, remote edited, incremental sync" {
    mark_file_stale "index.md"
    delete_tracked_file "index.md"
    server_edit_content "$(uuid_for "index.md")"
    assert_in_state "stale-uuid"

    # incremental sync can deduce stale entry: another uuid claims the filename
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, local deleted, remote edited, full sync" {
    mark_file_stale "index.md"
    delete_tracked_file "index.md"
    server_edit_content "$(uuid_for "index.md")"
    setup_old_sync_metadata

    # full sync detects stale entry by comparing against complete server state
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "index.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_not_in_state "stale-uuid"
    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, aware" {
    index_uuid=$(uuid_for "index.md")
    delete_tracked_file "index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_deleted_on_server "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, unaware" {
    index_uuid=$(uuid_for "index.md")
    remove_file "index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_deleted_on_server "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote edited" {
    delete_tracked_file "Bestiary.md"
    server_edit_content "$(uuid_for "Bestiary.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Bestiary.md" (v3, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "Bestiary.md"
    assert_file_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote renamed" {
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    delete_tracked_file "characters/NPCs.md"
    server_rename "$npcs_uuid" "NPCs.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "NPCs.md" to "characters/NPCs.md"
        push: deleted "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_deleted_on_server "characters/NPCs.md"
    assert_fixtures_intact_except "characters/NPCs.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote edited, remote renamed" {
    home_uuid=$(uuid_for "Home.md")
    delete_tracked_file "Home.md"
    server_edit_content "$home_uuid"
    server_rename "$home_uuid" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: "Welcome.md" (v4, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "Welcome.md"
    assert_file_not_downloaded "Home.md"
    assert_file_in_state "Welcome.md"
    assert_file_not_in_state "Home.md"
    assert_fixtures_intact_except "Home.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, aware, local edited, remote edited" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    delete_tracked_file "Bestiary.md"
    create_file "Bestiary.md"
    server_edit_content "$bestiary_uuid"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"
        push: "Bestiary (conflict ${SHORT_HOST}).md" (v1)
        pull: "Bestiary.md" (v3, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Bestiary (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Bestiary (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_server_edited_content "Bestiary.md"
    assert_uuid_local_filename "$bestiary_uuid" "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, unaware, local edited, remote edited" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    remove_file "Bestiary.md"
    create_file "Bestiary.md"
    server_edit_content "$bestiary_uuid"

    # there is no way to differentiate file deleted/recreated vs edited,
    # so we do not create a conflict file, just replace the content
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v4, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, aware, local edited, remote edited, remote renamed" {
    home_uuid=$(uuid_for "Home.md")
    delete_tracked_file "Home.md"
    create_file "Welcome.md"
    server_edit_content "$home_uuid"
    server_rename "$home_uuid" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "Welcome.md" to "Welcome (conflict ${SHORT_HOST}).md"
        push: "Welcome (conflict ${SHORT_HOST}).md" (v1)
        pull: "Welcome.md" (v4, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Welcome (conflict ${SHORT_HOST}).md"
    assert_file_pushed "Welcome (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_server_edited_content "Welcome.md"
    assert_uuid_local_filename "$home_uuid" "Welcome.md"
    assert_fixtures_intact_except "Home.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, unaware, local edited, remote edited, remote renamed" {
    home_uuid=$(uuid_for "Home.md")
    remove_file "Home.md"
    create_file "Home.md"
    server_edit_content "$home_uuid"
    server_rename "$home_uuid" "Welcome.md"

    # there is no way to differentiate file deleted/recreated vs edited,
    # so we do not create a conflict file, just replace the content
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Welcome.md" to "Home.md"
        push: "Home.md" (v6, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home.md"
    assert_file_pushed "Home.md" "text/markdown"
    assert_fixtures_intact_except "Home.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote deleted" {
    delete_tracked_file "Bestiary.md"
    server_delete "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed" {
    rename_local_file "index.md" "renamed-index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "index.md" to "renamed-index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "renamed-index.md"
    assert_file_in_state "renamed-index.md"
    assert_file_not_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited" {
    rename_local_file "index.md" "renamed-index.md"
    modify_file "renamed-index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "index.md" to "renamed-index.md"
        push: "renamed-index.md" (v3)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "renamed-index.md"
    assert_file_pushed "renamed-index.md" "text/markdown"
    assert_file_not_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote edited" {
    rename_local_file "Bestiary.md" "renamed-bestiary.md"
    server_edit_content "$(uuid_for "Bestiary.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "renamed-bestiary.md"
        pull: "renamed-bestiary.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "renamed-bestiary.md"
    assert_file_in_state "renamed-bestiary.md"
    assert_file_not_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited, mergeable" {
    rename_local_file "Bestiary.md" "renamed-bestiary.md"
    modify_file "renamed-bestiary.md" "$(mergeable_orc)"
    server_edit_content "$(uuid_for "Bestiary.md")" "$(mergeable_troll)"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "renamed-bestiary.md"
        push: "renamed-bestiary.md" (v5, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(merged_orc_troll) "$output_dir/renamed-bestiary.md"
    assert_file_pushed "renamed-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited, unmergeable" {
    rename_local_file "Bestiary.md" "renamed-bestiary.md"
    modify_file "renamed-bestiary.md"
    server_edit_content "$(uuid_for "Bestiary.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "renamed-bestiary.md"
        push: "renamed-bestiary.md" (v5, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "renamed-bestiary.md"
    assert_file_pushed "renamed-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote renamed" {
    index_uuid=$(uuid_for "index.md")
    rename_local_file "index.md" "my-index.md"
    server_rename "$index_uuid" "server-index.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-index.md" to "my-index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "server-index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote renamed" {
    index_uuid=$(uuid_for "index.md")
    rename_local_file "index.md" "my-index.md"
    modify_file "my-index.md"
    server_rename "$index_uuid" "server-index.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-index.md" to "my-index.md"
        push: "my-index.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-index.md"
    assert_file_pushed "my-index.md" "text/markdown"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "server-index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote edited, remote renamed" {
    index_uuid=$(uuid_for "index.md")
    rename_local_file "index.md" "my-index.md"
    server_edit_content "$index_uuid"
    server_rename "$index_uuid" "server-index.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-index.md" to "my-index.md"
        pull: "my-index.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "my-index.md"
    assert_file_in_state "my-index.md"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "server-index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited, remote renamed, mergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    rename_local_file "Bestiary.md" "my-bestiary.md"
    modify_file "my-bestiary.md" "$(mergeable_orc)"
    server_edit_content "$bestiary_uuid" "$(mergeable_troll)"
    server_rename "$bestiary_uuid" "server-bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-bestiary.md" to "my-bestiary.md"
        push: "my-bestiary.md" (v6, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(merged_orc_troll) "$output_dir/my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_file_not_in_state "server-bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited, remote renamed, unmergeable" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    rename_local_file "Bestiary.md" "my-bestiary.md"
    modify_file "my-bestiary.md"
    server_edit_content "$bestiary_uuid"
    server_rename "$bestiary_uuid" "server-bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-bestiary.md" to "my-bestiary.md"
        push: "my-bestiary.md" (v6, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_file_not_in_state "server-bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote deleted" {
    rename_local_file "Bestiary.md" "my-bestiary.md"
    server_delete "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "my-bestiary.md" (revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote deleted" {
    rename_local_file "Bestiary.md" "my-bestiary.md"
    modify_file "my-bestiary.md"
    server_delete "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "my-bestiary.md" (revivified)
        push: "my-bestiary.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_fixtures_intact_except "Bestiary.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, stale file" {
    add_stale_file "original.md"
    rename_local_file "original.md" "my-notes.md"
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: deleted "my-notes.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_deleted "my-notes.md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, stale file" {
    add_stale_file "original.md"
    rename_local_file "original.md" "my-notes.md"
    modify_file "my-notes.md"
    setup_old_sync_metadata

    fail_on_since_parameter
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: renamed "my-notes.md" to "my-notes (conflict ${SHORT_HOST}).md"
        push: "my-notes (conflict ${SHORT_HOST}).md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes (conflict ${SHORT_HOST}).md"
    assert_file_pushed "my-notes (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed untracked, hash match" {
    rename_local_file_untracked "index.md" "renamed-index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        info: detected rename "index.md" to "renamed-index.md"
        push: renamed "index.md" to "renamed-index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "index.md" "renamed-index.md"
    assert_file_in_state "renamed-index.md"
    assert_file_not_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed untracked, hash mismatch" {
    index_uuid=$(uuid_for "index.md")
    rename_local_file_untracked "index.md" "renamed-index.md"
    modify_file "renamed-index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "index.md"
        push: "renamed-index.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "renamed-index.md"
    assert_file_pushed "renamed-index.md" "text/markdown"
    assert_file_deleted_on_server "index.md"
    assert_file_in_state "renamed-index.md"
    assert_file_not_in_state "index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed untracked, hash mismatch, remote edited" {
    rename_local_file_untracked "index.md" "renamed-index.md"
    modify_file "renamed-index.md"
    server_edit_content "$(uuid_for "index.md")"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "renamed-index.md" (v1)
        pull: "index.md" (v2, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "index.md"
    assert_file_in_state "index.md"
    assert_file_modified "renamed-index.md"
    assert_file_pushed "renamed-index.md" "text/markdown"
    assert_file_in_state "renamed-index.md"
    assert_fixtures_intact_except "index.md"
    assert_sync_metadata_updated
    assert_success
}

@test "conflict hostname exists" {
    server_create "Quests.md"
    create_file "Quests.md"
    create_file "Quests (conflict ${SHORT_HOST}).md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    today=$(date +%Y%m%d)
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Quests (conflict ${SHORT_HOST}).md" (v1)
        info: renamed "Quests.md" to "Quests (conflict ${SHORT_HOST} ${today}).md"
        push: "Quests (conflict ${SHORT_HOST} ${today}).md" (v1)
        pull: "Quests.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Quests (conflict ${SHORT_HOST}).md"
    assert_file_unchanged "Quests (conflict ${SHORT_HOST} ${today}).md"
    assert_file_pushed "Quests (conflict ${SHORT_HOST}).md" "text/markdown"
    assert_file_pushed "Quests (conflict ${SHORT_HOST} ${today}).md" "text/markdown"
    assert_tracked_file_intact "Quests.md"
    assert_file_in_state "Quests (conflict ${SHORT_HOST}).md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

@test "conflict hostname exists, conflict date exists" {
    today=$(date +%Y%m%d)
    before=$(date +%Y%m%d%H%M%S)
    server_create "Quests.md"
    create_file "Quests.md"
    create_file "Quests (conflict ${SHORT_HOST}).md"
    create_file "Quests (conflict ${SHORT_HOST} ${today}).md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    timestamp_file=$(
        echo "$output" \
            | grep -o "Quests (conflict ${SHORT_HOST} [0-9]\{14\}).md" \
            | head -1
    )
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Quests (conflict ${SHORT_HOST} ${today}).md" (v1)
        push: "Quests (conflict ${SHORT_HOST}).md" (v1)
        info: renamed "Quests.md" to "${timestamp_file}"
        push: "${timestamp_file}" (v1)
        pull: "Quests.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    # this will obviously fail if the day ticks over during the test,
    # so don't run the tests at almost-midnight
    after=$(date +%Y%m%d%H%M%S)
    timestamp=$(echo "$timestamp_file" | grep -o '[0-9]\{14\}')
    assert_timestamp_in_range "$timestamp" "$before" "$after"
    assert_file_unchanged "Quests (conflict ${SHORT_HOST}).md"
    assert_file_unchanged "Quests (conflict ${SHORT_HOST} ${today}).md"
    assert_file_unchanged "${timestamp_file}"
    assert_file_pushed "${timestamp_file}" "text/markdown"
    assert_tracked_file_intact "Quests.md"
    assert_file_in_state "Quests (conflict ${SHORT_HOST}).md"
    assert_file_in_state "Quests (conflict ${SHORT_HOST} ${today}).md"
    assert_fixtures_intact
    assert_sync_metadata_updated
    assert_success
}

# New tests should use or create helpers so as not to obscure what the test is actually doing.

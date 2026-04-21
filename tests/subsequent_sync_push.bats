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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited, directory" {
    server_create "Rumours.md"
    create_file "Rumours.md/notes.txt"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "Rumours.md/notes.txt": Path 'rumours' already exists.
        pull: ERROR cannot pull "Rumours.md", blocked by local directory
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Rumours.md/notes.txt"
    assert_file_not_in_state "Rumours.md/notes.txt"
    assert_file_not_downloaded "Rumours.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited" {
    server_create "Quests.md"
    create_file "Quests.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "Quests.md": Path 'quests' already exists.
        pull: ERROR cannot pull "Quests.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Quests.md"
    assert_file_not_in_state "Quests.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, remote renamed" {
    create_file "npcs/Major.md"
    server_rename "$(uuid_for "characters/NPCs.md")" "npcs/Major.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "npcs/Major.md": Path 'npcs/major' already exists.
        pull: ERROR cannot rename "characters/NPCs.md" to "npcs/Major.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "npcs/Major.md"
    assert_file_not_in_state "npcs/Major.md"
    assert_file_matches_fixture "characters/NPCs.md" "characters/NPCs.md"
    assert_file_in_state "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "untracked file, local edited, remote renamed" {
    create_file "Monsters.md"
    server_rename "$(uuid_for "Bestiary.md")" "Monsters.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "Monsters.md": Path 'monsters' already exists.
        pull: ERROR cannot rename "Bestiary.md" to "Monsters.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Monsters.md"
    assert_file_not_in_state "Monsters.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed" {
    server_rename "$(uuid_for "The Old Café.md")" "The New Café.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, local edited, directory" {
    server_rename "$(uuid_for "sessions/session-01.md")" "logs/Session 01.md"
    create_file "logs/Session 01.md/notes.txt"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "logs/Session 01.md/notes.txt": Path 'logs/session-01' already exists.
        pull: ERROR cannot rename "sessions/session-01.md" to "logs/Session 01.md", blocked by local directory
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "sessions/session-01.md"
    assert_file_unchanged "logs/Session 01.md/notes.txt"
    assert_file_not_in_state "logs/Session 01.md/notes.txt"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote edited, remote renamed" {
    server_edit_content "$(uuid_for "Home.md")"
    server_rename "$(uuid_for "Home.md")" "Welcome.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, swapped" {
    npcs_uuid=$(uuid_for "characters/NPCs.md")
    server_rename "$npcs_uuid" "temp.md"
    server_rename "$(uuid_for "sessions/session-01.md")" "characters/NPCs.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, chain" {
    server_rename "$(uuid_for "sessions/session-01.md")" "old.md"
    server_rename "$(uuid_for "characters/NPCs.md")" "sessions/session-01.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, chain reversed" {
    server_rename "$(uuid_for "characters/NPCs.md")" "old.md"
    server_rename "$(uuid_for "sessions/session-01.md")" "characters/NPCs.md"

    fail_when_results_not 2
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "sessions/session-01.md" to "characters/NPCs.md"
        pull: renamed "characters/NPCs.md" to "old.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_matches_fixture "characters/NPCs.md" "old.md"
    assert_file_matches_fixture "sessions/session-01.md" "characters/NPCs.md"
    assert_file_not_downloaded "sessions/session-01.md"
    assert_file_in_state "old.md"
    assert_file_in_state "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$(uuid_for "Home.md")" "Bestiary.md"
    server_rename "$(uuid_for "index.md")" "Home.md"
    server_rename "$bestiary_uuid" "index.md"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "index.md" to "Home.md"
        pull: renamed "Home.md" to "Bestiary.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle, local edited" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$(uuid_for "Home.md")" "Bestiary.md"
    server_rename "$(uuid_for "index.md")" "Home.md"
    server_rename "$bestiary_uuid" "index.md"
    modify_file "Home.md"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # attempted operations:
    # 1. local Home.md has been updated, so rename remote Bestiary.md (same UUID as our
    #    Home.md) back to Home.md -- fails, path exists
    # 2. break the rename cycle -- fails, local changes to Home.md would be lost
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot rename "Bestiary.md" to "Home.md": Path 'home' already exists.
        pull: ERROR cannot rename "index.md" to "Home.md", blocked by local file
        pull: SKIPPING rename "Home.md" to "Bestiary.md", local changes would be lost
        pull: ERROR cannot rename "Bestiary.md" to "index.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Home.md"
    assert_file_in_state "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote renamed, cycle, untracked file" {
    bestiary_uuid=$(uuid_for "Bestiary.md")
    server_rename "$bestiary_uuid" "temp.md"
    server_rename "$(uuid_for "Home.md")" "Bestiary.md"
    server_rename "$(uuid_for "index.md")" "Home.md"
    server_rename "$bestiary_uuid" "index.md"
    untrack_and_remove_file "Home.md"
    create_file "Home.md"

    fail_when_results_not 3
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    # attempted operations:
    # 1. new Home.md, so push it -- fails, path exists
    # 2. break the rename cycle -- fails, local changes to Home.md would be lost
    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot push "Home.md": Path 'home' already exists.
        pull: ERROR cannot pull "Bestiary.md", blocked by local file
        pull: ERROR cannot rename "index.md" to "Home.md", blocked by local file
        pull: ERROR cannot rename "Bestiary.md" to "index.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Home.md"
    assert_file_not_in_state "Home.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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

    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited" {
    modify_file "Bestiary.md" "$(sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Orc

        Large and aggressive.
	EOF
    )"

    server_edit_content "$(uuid_for "Bestiary.md")" "$(sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Troll

        Regenerates health.
	EOF
    )"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v4, merged)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    expected_content=$(sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Orc

        Large and aggressive.

        ## Troll

        Regenerates health.
	EOF
    )
    diff -u <(echo "$expected_content") "$output_dir/Bestiary.md"

    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, no common ancestor" {
    modify_file "index.md"
    server_edit_content "$(uuid_for "index.md")"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote renamed" {
    modify_file "Bestiary.md"
    server_rename "$(uuid_for "Bestiary.md")" "renamed-bestiary.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local edited, remote edited, remote renamed" {
    modify_file "Home.md"
    server_edit_content "$(uuid_for "Home.md")"
    server_rename "$(uuid_for "Home.md")" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Welcome.md" to "Home.md"
        push: "Home.md" (v6, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Home.md"
    assert_file_pushed "Home.md" "text/markdown"
    assert_file_in_state "Home.md"
    assert_file_not_in_state "Welcome.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "remote deleted, local edited" {
    server_delete "Bestiary.md"
    modify_file "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: "Bestiary.md" (v3)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "Bestiary.md"
    assert_file_pushed "Bestiary.md" "text/markdown"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "stale file, remote edited, incremental sync" {
    mark_file_stale "index.md"
    server_edit_content "$(uuid_for "index.md")"

    # incremental sync cannot detect stale file (see fetch_remote_state)
    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: ERROR cannot pull "index.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "index.md"
    assert_in_state "stale-uuid"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
        push: "my-notes.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes.md"
    assert_file_in_state "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
        push: "my-notes.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes.md"
    assert_file_in_state "my-notes.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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

    # push: discovers stale entry via 404 when attempting to delete
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted" {
    delete_tracked_file "index.md"

    fail_when_results_not 0
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: deleted "index.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_deleted_on_server "index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote renamed" {
    delete_tracked_file "characters/NPCs.md"
    server_rename "$(uuid_for "characters/NPCs.md")" "NPCs.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "NPCs.md" to "characters/NPCs.md"
        push: deleted "characters/NPCs.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_deleted_on_server "characters/NPCs.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, remote edited, remote renamed" {
    delete_tracked_file "Home.md"
    server_edit_content "$(uuid_for "Home.md")"
    server_rename "$(uuid_for "Home.md")" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        pull: renamed "Home.md" to "Welcome.md"
        pull: "Welcome.md" (v4, revivified)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_server_edited_content "Welcome.md"
    assert_file_not_downloaded "Home.md"
    assert_file_in_state "Welcome.md"
    assert_file_not_in_state "Home.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local deleted, local edited, remote edited, remote renamed" {
    delete_tracked_file "Home.md"
    create_file "Welcome.md"
    server_edit_content "$(uuid_for "Home.md")"
    server_rename "$(uuid_for "Home.md")" "Welcome.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: ERROR cannot delete "Home.md", server has updates.
        push: ERROR cannot push "Welcome.md": Path 'welcome' already exists.
        pull: ERROR cannot rename "Home.md" to "Welcome.md", blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "Welcome.md"
    assert_tracked_file_not_restored "Home.md"
    assert_file_not_in_state "Welcome.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited" {
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote renamed" {
    rename_local_file "index.md" "my-index.md"
    server_rename "$(uuid_for "index.md")" "server-index.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote renamed" {
    rename_local_file "index.md" "my-index.md"
    modify_file "my-index.md"
    server_rename "$(uuid_for "index.md")" "server-index.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote edited, remote renamed" {
    rename_local_file "index.md" "my-index.md"
    server_edit_content "$(uuid_for "index.md")"
    server_rename "$(uuid_for "index.md")" "server-index.md"

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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, local edited, remote edited, remote renamed" {
    rename_local_file "index.md" "my-index.md"
    modify_file "my-index.md"
    server_edit_content "$(uuid_for "index.md")"
    server_rename "$(uuid_for "index.md")" "server-index.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "server-index.md" to "my-index.md"
        push: "my-index.md" (v5, replaced)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-index.md"
    assert_file_pushed "my-index.md" "text/markdown"
    assert_file_not_in_state "index.md"
    assert_file_not_in_state "server-index.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed, remote deleted" {
    rename_local_file "Bestiary.md" "my-bestiary.md"
    server_delete "Bestiary.md"

    fail_when_results_not 1
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        push: renamed "Bestiary.md" to "my-bestiary.md"
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
        push: renamed "Bestiary.md" to "my-bestiary.md"
        push: "my-bestiary.md" (v4)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-bestiary.md"
    assert_file_pushed "my-bestiary.md" "text/markdown"
    assert_file_not_in_state "Bestiary.md"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
        push: "my-notes.md" (v1)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_modified "my-notes.md"
    assert_file_pushed "my-notes.md" "text/markdown"
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "index.md"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

@test "local renamed untracked, hash mismatch" {
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
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
    assert_tracked_file_intact "random-hexmap-7.png"
    assert_tracked_file_intact "Home.md"
    assert_tracked_file_intact "sessions/session-01.md"
    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_intact "characters/NPCs.md"
    assert_tracked_file_intact "The Old Café.md"
    assert_tracked_file_intact "World Regions/Northern Kingdoms/Frosthold.md"
    assert_sync_metadata_updated
    assert_success
}

# New tests should use or create helpers so as not to obscure what the test is actually doing.

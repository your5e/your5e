# Sync permission test suite
#
# Tests for sync script behaviour with different user permission levels.
#
# This file tests the reference implementation (sync-notebook.sh) and documents
# the expected behaviour of ANY notebook sync client. Implementers should use
# these scenarios to verify their own sync logic produces the same outcomes.

bats_require_minimum_version 1.7.0

load 'setup_helpers.sh'

setup_file() {
    export YOUR5E_API_BASE="http://localhost:5844"
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"
    export -f invalidate_token
    export -f downgrade_to_viewer

    restore_database
    setup_pages_file

    if [[ "${BATS_TEST_DESCRIPTION:-}" =~ mid-sync ]]; then
        if [[ "${BATS_TEST_DESCRIPTION:-}" =~ downgraded ]]; then
            export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/wendy.token")"
        fi
        init_synced_dir
        setup_recent_sync_metadata
        fail_on_missing_since_parameter
    else
        fail_on_since_parameter
    fi
}


@test "full sync switches to pull" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/susan.token")"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: NOTE read-only access, switching to pull-only mode
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


@test "pull, non-collaborator, public" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/hugh.token")"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

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


@test "pull, non-collaborator, private" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/hugh.token")"

    run tests/sync-notebook.sh -p wendy/world-building "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR notebook not found
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}


@test "pull, invalid token" {
    export YOUR5E_API_TOKEN="invalid-token-12345"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}


@test "pull, no token" {
    unset YOUR5E_API_TOKEN

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token missing
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}


@test "pull, non-existent, owner" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/norm.token")"

    run tests/sync-notebook.sh -p norm/does-not-exist "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR notebook not found
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}

@test "pull, non-existent, editor" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/wendy.token")"

    run tests/sync-notebook.sh -p norm/does-not-exist "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR notebook not found
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}

@test "pull, non-existent, viewer" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/susan.token")"

    run tests/sync-notebook.sh -p norm/does-not-exist "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR notebook not found
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}

@test "pull, non-existent, non-collaborator" {
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/hugh.token")"

    run tests/sync-notebook.sh -p norm/does-not-exist "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR notebook not found
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_no_output_dir
    assert_last_updated_not_set
    assert_failure
}


@test "mid-sync, revoked, new file" {
    create_file "newfile.md"
    export AFTER_FETCH_HOOK="invalidate_token '$YOUR5E_API_TOKEN'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "newfile.md"
    assert_tracked_file_matches_fixture "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_state_matches_fixture
    assert_last_updated_unchanged
    assert_failure
}

@test "mid-sync, downgraded, new file" {
    set_older_content "Bestiary.md"
    create_file "newfile.md"
    export AFTER_FETCH_HOOK="downgrade_to_viewer 'wendy' 'norm' 'campaign-notes'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: NOTE permission denied, switching to pull-only mode
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "newfile.md"
    assert_tracked_file_matches_fixture "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_sync_metadata_updated
    assert_success
}

@test "mid-sync, revoked, local update" {
    modify_file "index.md"
    export AFTER_FETCH_HOOK="invalidate_token '$YOUR5E_API_TOKEN'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_state_matches_fixture
    assert_last_updated_unchanged
    assert_failure
}

@test "mid-sync, downgraded, local update" {
    set_older_content "Bestiary.md"
    modify_file "index.md"
    export AFTER_FETCH_HOOK="downgrade_to_viewer 'wendy' 'norm' 'campaign-notes'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: NOTE permission denied, switching to pull-only mode
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_unchanged "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_sync_metadata_updated
    assert_success
}

@test "mid-sync, revoked, local rename" {
    rename_local_file "index.md" "renamed.md"
    export AFTER_FETCH_HOOK="invalidate_token '$YOUR5E_API_TOKEN'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_matches_fixture "index.md" "renamed.md"
    assert_file_not_downloaded "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_last_updated_unchanged
    assert_failure
}

@test "mid-sync, downgraded, local rename" {
    set_older_content "Bestiary.md"
    rename_local_file "index.md" "renamed.md"
    export AFTER_FETCH_HOOK="downgrade_to_viewer 'wendy' 'norm' 'campaign-notes'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: NOTE permission denied, switching to pull-only mode
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_matches_fixture "index.md" "renamed.md"
    assert_file_not_downloaded "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_sync_metadata_updated
    assert_success
}

@test "mid-sync, revoked, local delete" {
    remove_file "index.md"
    export AFTER_FETCH_HOOK="invalidate_token '$YOUR5E_API_TOKEN'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_not_restored "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_last_updated_unchanged
    assert_failure
}

@test "mid-sync, downgraded, local delete" {
    set_older_content "Bestiary.md"
    remove_file "index.md"
    export AFTER_FETCH_HOOK="downgrade_to_viewer 'wendy' 'norm' 'campaign-notes'"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: NOTE permission denied, switching to pull-only mode
        pull: SKIPPING pull "index.md", already deleted locally
        pull: "Bestiary.md" (v2)
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_not_restored "index.md"
    assert_tracked_file_matches_fixture "Bestiary.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_sync_metadata_updated
    assert_success
}

@test "mid-sync, revoked, content update" {
    set_older_content "Bestiary.md"
    export AFTER_FETCH_HOOK="invalidate_token '$YOUR5E_API_TOKEN'"

    run tests/sync-notebook.sh -p norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        sync: ERROR API token invalid
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_tracked_file_intact "Bestiary.md"
    assert_tracked_file_matches_fixture "index.md"
    assert_tracked_file_matches_fixture "Home.md"
    assert_tracked_file_matches_fixture "characters/NPCs.md"
    assert_tracked_file_matches_fixture "sessions/session-01.md"
    assert_tracked_file_matches_fixture "The Old Café.md"
    assert_tracked_file_matches_fixture "random-hexmap-7.png"
    assert_last_updated_unchanged
    assert_failure
}

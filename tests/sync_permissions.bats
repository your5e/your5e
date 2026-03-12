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
    restore_database
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "full sync switches to pull when user is viewer" {
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
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_not_downloaded "Old Notes.md"
    assert_dir_matches_fixture
    assert_state_matches_fixture
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
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    assert_file_not_downloaded "Old Notes.md"
    assert_dir_matches_fixture
    assert_state_matches_fixture
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
    assert_failure
}

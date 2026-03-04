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
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/api.token")"
    export YOUR5E_API_BASE="http://localhost:5843"
}

setup() {
    fixtures="$BATS_TEST_DIRNAME/fixtures"
    output_dir="$BATS_TEST_TMPDIR/output"
}


@test "first sync to empty directory" {
    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
        ++ sessions/session-01.md
        ++ Home.md
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -ru --exclude=".sync-state" "$output_dir" "$fixtures/campaign-notes"

    # Old Notes.md is soft-deleted on server, should not appear
    assert_not_in_state "Old Notes"
    [ ! -f "$output_dir/Old Notes.md" ]

    # UUIDs are non-deterministic, compare only filename and hash
    expected_state=$(sed -e 's/^        //' <<-EOF
        Bestiary.md	53ff06a20c413033e4df6a193154b33add649a8dbb9275fc0f0aef885dca0307
        Home.md	eae6d1cae46f87787001ff65f70edf4820c996a21a595d5a7b3e0b3780a75ae6
        characters/NPCs.md	d4bfe27b0485dd98beaacffd5953ae0eabf4ab44b72244a898f5b0db6bb4efe8
        index.md	698f2e61564436ed84ce8e72be283dad46f6b48967c491f1f2d49b8c2df31549
        random-hexmap-7.png	7c31741747c5e948ef888893889db97b5e15388479b2a1ee730a01ef9c0d9c59
        sessions/session-01.md	17531ff51858eb42bcfe4bd7a711564b6989472a8b8017c7c933196e37b7bd10
	EOF
    )
    diff -u <(echo "$expected_state") <(cut -f2,3 "$output_dir/.sync-state" | sort)

    [ $status -eq 0 ]
}

@test "first sync to non-empty directory preserves all local files" {
    mkdir -p "$output_dir/sessions"
    echo "my home" > "$output_dir/Home.md"
    echo "my index" > "$output_dir/index.md"
    echo "my notes" > "$output_dir/notes.txt"
    echo "my session notes" > "$output_dir/sessions/notes.txt"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
        ++ sessions/session-01.md
           Home.md has local modifications, skipped
           index.md has local modifications, skipped
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ "$(cat "$output_dir/Home.md")" = "my home" ]
    [ "$(cat "$output_dir/index.md")" = "my index" ]
    [ "$(cat "$output_dir/notes.txt")" = "my notes" ]
    [ "$(cat "$output_dir/sessions/notes.txt")" = "my session notes" ]
    [ $status -eq 0 ]
}

@test "first sync local file matches remote" {
    mkdir -p "$output_dir"
    cp "$fixtures/campaign-notes/Home.md" "$output_dir/Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
        ++ sessions/session-01.md
           Home.md matches remote, tracking
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Home.md" "$output_dir/Home.md"
    grep -q "Home.md" "$output_dir/.sync-state"
    [ $status -eq 0 ]
}

@test "first sync local file without extension blocks remote subdirectory" {
    mkdir -p "$output_dir"
    echo "local file" > "$output_dir/sessions"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
           sessions/session-01.md blocked by local file, skipped
        ++ Home.md
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -f "$output_dir/sessions" ]
    [ "$(cat "$output_dir/sessions")" = "local file" ]
    [ $status -eq 0 ]
}

@test "first sync local directory blocks remote file" {
    mkdir -p "$output_dir/Bestiary.md"
    echo "local file" > "$output_dir/Bestiary.md/notes.txt"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
           Bestiary.md blocked by local directory, skipped
        ++ sessions/session-01.md
        ++ Home.md
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -d "$output_dir/Bestiary.md" ]
    [ "$(cat "$output_dir/Bestiary.md/notes.txt")" = "local file" ]
    [ $status -eq 0 ]
}

@test "first sync case sensitivity collision" {
    mkdir -p "$output_dir"
    echo "local home" > "$output_dir/home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
        ++ sessions/session-01.md
           Home.md blocked by local file with different case, skipped
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ "$(cat "$output_dir/home.md")" = "local home" ]
    [ $status -eq 0 ]
}

@test "first sync case sensitivity collision, content matches" {
    mkdir -p "$output_dir"
    cp "$fixtures/campaign-notes/Home.md" "$output_dir/home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ characters/NPCs.md
        ++ Bestiary.md
        ++ sessions/session-01.md
           Home.md blocked by local file with different case, skipped
        ++ index.md
        ++ random-hexmap-7.png
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Home.md" "$output_dir/home.md"
    [ $status -eq 0 ]
}

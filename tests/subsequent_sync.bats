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
    export YOUR5E_API_TOKEN="$(cat "$BATS_TEST_DIRNAME/api.token")"
    export YOUR5E_API_BASE="http://localhost:5843"
    export BATS_FILE_TMPDIR="${BATS_FILE_TMPDIR:-$(mktemp -d)}"

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
    # ensures no curl commands executed, except to list the notebook
    curl() {
        [[ "$*" == *"/norm/campaign-notes/" ]] || return 1
        command curl "$@"
    }
    export -f curl

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -ru --exclude=".sync-state" "$output_dir" "$fixtures/campaign-notes"
    [ $status -eq 0 ]
}

@test "untracked file" {
    create_file "scratchpad.txt"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -f "$output_dir/scratchpad.txt" ]
    [ $status -eq 0 ]
}

@test "untracked file blocked by directory" {
    untrack_file "Bestiary.md"
    replace_with_directory "Bestiary.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Bestiary.md blocked by local directory, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -d "$output_dir/Bestiary.md" ]
    diff -u <(echo "local notes") <(cat "$output_dir/Bestiary.md/notes.txt")
    [ $status -eq 0 ]
}

@test "untracked file, content update" {
    untrack_file "Home.md"
    modify_file "Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Home.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/Home.md")
    [ $status -eq 0 ]
}

@test "untracked file, filename update" {
    move_cached_file "characters/NPCs.md" "NPCs.md"
    create_file "characters/NPCs.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           NPCs.md -> characters/NPCs.md blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -f "$output_dir/NPCs.md" ]
    diff -u <(echo "local content") <(cat "$output_dir/characters/NPCs.md")
    [ $status -eq 0 ]
}

@test "untracked file, content update, filename update" {
    rewind_homemd_state
    create_file "Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Welcome.md -> Home.md blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local content") <(cat "$output_dir/Home.md")
    [ -f "$output_dir/Welcome.md" ]
    [ $status -eq 0 ]
}

@test "content update" {
    rewind_bestiarymd_state

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ Bestiary.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Bestiary.md" "$output_dir/Bestiary.md"
    [ $status -eq 0 ]
}

@test "filename update" {
    move_cached_file "The Old Café.md" "café.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           café.md -> The Old Café.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/The Old Café.md" "$output_dir/The Old Café.md"
    [ ! -f "$output_dir/café.md" ]
    [ $status -eq 0 ]
}

@test "filename update blocked by directory" {
    move_cached_file "characters/NPCs.md" "NPCs.md"
    replace_with_directory "characters/NPCs.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           NPCs.md -> characters/NPCs.md blocked by local directory, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -f "$output_dir/NPCs.md" ]
    [ -d "$output_dir/characters/NPCs.md" ]
    diff -u <(echo "local notes") <(cat "$output_dir/characters/NPCs.md/notes.txt")
    [ $status -eq 0 ]
}

@test "content update, filename update" {
    rewind_homemd_state

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Welcome.md -> Home.md
        ++ Home.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Home.md" "$output_dir/Home.md"
    [ ! -f "$output_dir/Welcome.md" ]
    [ $status -eq 0 ]
}

@test "filename update swapped" {
    move_cached_file "characters/NPCs.md" "temp.md"
    move_cached_file "sessions/session-01.md" "characters/NPCs.md"
    move_cached_file "temp.md" "sessions/session-01.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           characters/NPCs.md -> sessions/session-01.md
           sessions/session-01.md -> characters/NPCs.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/characters/NPCs.md" "$output_dir/characters/NPCs.md"
    diff -u "$fixtures/campaign-notes/sessions/session-01.md" "$output_dir/sessions/session-01.md"
    [ $status -eq 0 ]
}

@test "filename update chain" {
    move_cached_file "sessions/session-01.md" "old.md"
    move_cached_file "characters/NPCs.md" "sessions/session-01.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           old.md -> sessions/session-01.md
           sessions/session-01.md -> characters/NPCs.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/characters/NPCs.md" "$output_dir/characters/NPCs.md"
    diff -u "$fixtures/campaign-notes/sessions/session-01.md" "$output_dir/sessions/session-01.md"
    [ ! -f "$output_dir/old.md" ]
    [ $status -eq 0 ]
}

@test "filename update chain, reversed" {
    move_cached_file "characters/NPCs.md" "old.md"
    move_cached_file "sessions/session-01.md" "characters/NPCs.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           characters/NPCs.md -> sessions/session-01.md
           old.md -> characters/NPCs.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/characters/NPCs.md" "$output_dir/characters/NPCs.md"
    diff -u "$fixtures/campaign-notes/sessions/session-01.md" "$output_dir/sessions/session-01.md"
    [ ! -f "$output_dir/old.md" ]
    [ $status -eq 0 ]
}

@test "filename update cycle" {
    move_cached_file "Bestiary.md" "temp.md"
    move_cached_file "Home.md" "Bestiary.md"
    move_cached_file "index.md" "Home.md"
    move_cached_file "temp.md" "index.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Home.md -> index.md
           Bestiary.md -> Home.md
           index.md -> Bestiary.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Bestiary.md" "$output_dir/Bestiary.md"
    diff -u "$fixtures/campaign-notes/Home.md" "$output_dir/Home.md"
    diff -u "$fixtures/campaign-notes/index.md" "$output_dir/index.md"
    [ $status -eq 0 ]
}

@test "filename update cycle, local modification blocks cycle" {
    move_cached_file "Bestiary.md" "temp.md"
    move_cached_file "Home.md" "Bestiary.md"
    move_cached_file "index.md" "Home.md"
    move_cached_file "temp.md" "index.md"
    modify_file "Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Home.md has local modifications, skipped
           Bestiary.md -> Home.md blocked by local file
           index.md -> Bestiary.md blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/Home.md")
    [ $status -eq 0 ]
}

@test "filename update cycle, untracked file blocks cycle" {
    move_cached_file "Bestiary.md" "temp.md"
    move_cached_file "Home.md" "Bestiary.md"
    move_cached_file "index.md" "Home.md"
    move_cached_file "temp.md" "index.md"
    untrack_file "Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           index.md has local modifications, skipped
           Bestiary.md -> Home.md blocked by local file
           index.md -> Bestiary.md blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/index.md" "$output_dir/Home.md"
    [ $status -eq 0 ]
}

@test "local update" {
    modify_file "index.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/index.md")
    [ $status -eq 0 ]
}

@test "local update, content update" {
    rewind_bestiarymd_state
    modify_file "Bestiary.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Bestiary.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/Bestiary.md")
    [ $status -eq 0 ]
}

@test "local update, filename update" {
    move_cached_file "characters/NPCs.md" "NPCs.md"
    modify_file "NPCs.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           NPCs.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/NPCs.md")
    [ ! -f "$output_dir/characters/NPCs.md" ]
    [ $status -eq 0 ]
}

@test "local update, content update, filename update" {
    rewind_homemd_state
    modify_file "Welcome.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Welcome.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/Welcome.md")
    [ ! -f "$output_dir/Home.md" ]
    [ $status -eq 0 ]
}

@test "remote deleted" {
    file_tracks_deleted_remote "archive/Old Notes.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        -- archive/Old Notes.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ ! -f "$output_dir/archive/Old Notes.md" ]
    [ ! -d "$output_dir/archive" ]
    [ $status -eq 0 ]
}

@test "remote deleted, local update" {
    file_tracks_deleted_remote "Old Notes.md"
    modify_file "Old Notes.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Old Notes.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/Old Notes.md")
    [ $status -eq 0 ]
}

@test "stale file" {
    add_stale_file

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           my-notes.md deleted from server, keeping
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ -f "$output_dir/my-notes.md" ]
    [ $status -eq 0 ]
}

@test "stale file, content update" {
    mark_file_stale

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           index.md deleted from server, keeping
           index.md has new remote content, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/index.md" "$output_dir/index.md"
    grep -q "stale-uuid-" "$output_dir/.sync-state"
    assert_not_in_state "$(uuid_for "index.md")"
    [ $status -eq 0 ]
}

@test "stale file, local update" {
    mark_file_stale
    modify_file "index.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           index.md deleted from server, keeping
           index.md has local modifications, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local modifications") <(cat "$output_dir/index.md")
    [ $status -eq 0 ]
}

@test "stale file, local delete" {
    add_stale_file
    file_deleted_locally "my-notes.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=""
    diff -u <(echo "$expected_output") <(echo "$output")

    [ ! -f "$output_dir/my-notes.md" ]
    assert_not_in_state "stale-uuid-"
    [ $status -eq 0 ]
}

@test "stale file, local delete, server reuses filename" {
    mark_file_stale
    file_deleted_locally "index.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ index.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/index.md" "$output_dir/index.md"
    assert_not_in_state "stale-uuid-"
    grep -q "$(uuid_for "index.md")" "$output_dir/.sync-state"
    [ $status -eq 0 ]
}

@test "local delete" {
    file_deleted_locally "index.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           index.md deleted locally, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ ! -f "$output_dir/index.md" ]
    [ $status -eq 0 ]
}

@test "local delete, content update" {
    rewind_bestiarymd_state
    file_deleted_locally "Bestiary.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ Bestiary.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Bestiary.md" "$output_dir/Bestiary.md"
    [ $status -eq 0 ]
}

@test "local delete, filename update" {
    move_cached_file "characters/NPCs.md" "NPCs.md"
    file_deleted_locally "NPCs.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           NPCs.md deleted locally, skipped
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ ! -f "$output_dir/NPCs.md" ]
    [ ! -f "$output_dir/characters/NPCs.md" ]
    [ $status -eq 0 ]
}

@test "local delete, content update, filename update" {
    rewind_homemd_state
    file_deleted_locally "Welcome.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        ++ Home.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u "$fixtures/campaign-notes/Home.md" "$output_dir/Home.md"
    [ ! -f "$output_dir/Welcome.md" ]
    [ $status -eq 0 ]
}

@test "local delete, content update, filename update blocked" {
    rewind_homemd_state
    file_deleted_locally "Welcome.md"
    create_file "Home.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
           Welcome.md -> Home.md blocked by local file
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    diff -u <(echo "local content") <(cat "$output_dir/Home.md")
    [ ! -f "$output_dir/Welcome.md" ]
    [ $status -eq 0 ]
}

@test "local delete, remote deleted" {
    file_tracks_deleted_remote "Old Notes.md"
    file_deleted_locally "Old Notes.md"

    run tests/sync-notebook.sh norm/campaign-notes "$output_dir"

    expected_output=$(sed -e 's/^        //' <<-EOF
        -- Old Notes.md
	EOF
    )
    diff -u <(echo "$expected_output") <(echo "$output")

    [ ! -f "$output_dir/Old Notes.md" ]
    [ $status -eq 0 ]
}

# New tests should use or create helpers so as not to obscure what the test is actually doing.

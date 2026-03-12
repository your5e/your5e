bats_require_minimum_version 1.7.0

source tests/sync-notebook.sh
export -f update_sync_state
export -f get_sync_state
export -f update_remote_state
export -f get_remote_state

setup() {
    export state_file="$BATS_TEST_TMPDIR/sync-state"
    export remote_state_file="$BATS_TEST_TMPDIR/remote-state"
}

given_sync_entry() {
    printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >> "$state_file"
}

given_remote_entry() {
    printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "${5:-}" >> "$remote_state_file"
}

@test "update_sync_state creates" {
    rm -f "$state_file"

    run update_sync_state "uuid-1" "file.md" "file.md" "abc123" "abc123"
    [ $status -eq 0 ]

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1	file.md	file.md	abc123	abc123
	EOF
    )
    diff -u <(echo "$expected") "$state_file"
}

@test "update_sync_state appends" {
    given_sync_entry "uuid-1" "first.md" "first.md" "hash1" "hash1"

    run update_sync_state "uuid-2" "second.md" "second.md" "hash2" "hash2"

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1	first.md	first.md	hash1	hash1
        uuid-2	second.md	second.md	hash2	hash2
	EOF
    )
    diff -u <(echo "$expected") "$state_file"
}

@test "update_sync_state updates" {
    given_sync_entry "uuid-1" "file.md" "file.md" "hash1" "hash1"

    run update_sync_state "uuid-1" "" "" "hash2" "hash2"

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1	file.md	file.md	hash2	hash2
	EOF
    )
    diff -u <(echo "$expected") "$state_file"
}

@test "update_sync_state updates with missing args" {
    given_sync_entry "uuid-1" "old.md" "old.md" "hash1" "hash1"

    run update_sync_state "uuid-1" "" "renamed.md"

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1	old.md	renamed.md	hash1	hash1
	EOF
    )
    diff -u <(echo "$expected") "$state_file"
}

@test "update_sync_state deletes" {
    given_sync_entry "uuid-1" "file.md" "file.md" "hash1" "hash1"
    given_sync_entry "uuid-2" "other.md" "other.md" "hash2" "hash2"

    run update_sync_state -d "uuid-1"

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-2	other.md	other.md	hash2	hash2
	EOF
    )
    diff -u <(echo "$expected") "$state_file"
}

@test "update_sync_state delete survives missing file" {
    run update_sync_state -d "uuid-1"
    [[ $status -eq 0 ]]
}

@test "get_sync_state server_filename" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "uuid-1" server_filename

    diff -u <(echo "server.md") <(echo "$output")
}

@test "get_sync_state local_filename" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "uuid-1" local_filename

    diff -u <(echo "local.md") <(echo "$output")
}

@test "get_sync_state hash" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "uuid-1" hash

    diff -u <(echo "hash1") <(echo "$output")
}

@test "get_sync_state local_hash" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "uuid-1" local_hash

    diff -u <(echo "hash2") <(echo "$output")
}

@test "get_sync_state uuid" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "local.md" uuid

    diff -u <(echo "uuid-1") <(echo "$output")
}

@test "get_sync_state missing entry" {
    given_sync_entry "uuid-1" "server.md" "local.md" "hash1" "hash2"

    run get_sync_state "uuid-missing" hash

    diff -u <(echo "") <(echo "$output")
}

@test "get_sync_state missing file" {
    run get_sync_state "uuid-1" hash

    diff -u <(echo "") <(echo "$output")
}

@test "update_remote_state creates" {
    rm -f "$remote_state_file"

    run update_remote_state "uuid-1" "file.md" "hash1" "1"

    expected=$(sed -e 's/^        //'  <<-EOF
        uuid-1	file.md	hash1	1	
	EOF
    )
    diff -u <(echo "$expected") "$remote_state_file"
}

@test "update_remote_state appends" {
    given_remote_entry "uuid-1" "first.md" "hash1" "1"

    run update_remote_state "uuid-2" "second.md" "hash2" "1"

    expected=$(sed -e 's/^        //'  <<-EOF
        uuid-1	first.md	hash1	1	
        uuid-2	second.md	hash2	1	
	EOF
    )
    diff -u <(echo "$expected") "$remote_state_file"
}

@test "update_remote_state updates" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"

    run update_remote_state "uuid-1" "" "hash2" "2"

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1	file.md	hash2	2	
	EOF
    )
    diff -u <(echo "$expected") "$remote_state_file"
}

@test "update_remote_state updates with missing args" {
    given_remote_entry "uuid-1" "old.md" "hash1" "1"

    run update_remote_state "uuid-1" "renamed.md"

    expected=$(sed -e 's/^        //'  <<-EOF
        uuid-1	renamed.md	hash1	1	
	EOF
    )
    diff -u <(echo "$expected") "$remote_state_file"
}

@test "update_remote_state deletes" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"
    given_remote_entry "uuid-2" "other.md" "hash2" "1"

    run update_remote_state -d "uuid-1"

    expected=$(sed -e 's/^        //'  <<-EOF
        uuid-2	other.md	hash2	1	
	EOF
    )
    diff -u <(echo "$expected") "$remote_state_file"
}

@test "update_remote_state delete survives missing file" {
    run update_remote_state -d "uuid-1"
    [[ $status -eq 0 ]]
}

@test "get_remote_state filename" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"

    run get_remote_state "uuid-1" filename

    diff -u <(echo "file.md") <(echo "$output")
}

@test "get_remote_state hash" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"

    run get_remote_state "uuid-1" hash

    diff -u <(echo "hash1") <(echo "$output")
}

@test "get_remote_state version" {
    given_remote_entry "uuid-1" "file.md" "hash1" "42"

    run get_remote_state "uuid-1" version

    diff -u <(echo "42") <(echo "$output")
}

@test "get_remote_state uuid" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"

    run get_remote_state "file.md" uuid

    diff -u <(echo "uuid-1") <(echo "$output")
}

@test "get_remote_state missing entry" {
    given_remote_entry "uuid-1" "file.md" "hash1" "1"

    run get_remote_state "uuid-missing" hash

    diff -u <(echo "") <(echo "$output")
}

@test "get_remote_state missing file" {
    run get_remote_state "uuid-1" hash

    diff -u <(echo "") <(echo "$output")
}

@test "get_remote_state deleted_uuids" {
    given_remote_entry "uuid-1" "file1.md" "hash1" "1"
    given_remote_entry "uuid-2" "file2.md" "hash2" "1" "2024-01-01"
    given_remote_entry "uuid-3" "file3.md" "hash3" "1" "2024-01-02"

    run get_remote_state "" deleted_uuids

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-2
        uuid-3
	EOF
    )
    diff -u <(echo "$expected") <(echo "$output")
}

@test "get_remote_state active_uuids" {
    given_remote_entry "uuid-1" "file1.md" "hash1" "1"
    given_remote_entry "uuid-2" "file2.md" "hash2" "1" "2024-01-01"
    given_remote_entry "uuid-3" "file3.md" "hash3" "1"

    run get_remote_state "" active_uuids

    expected=$(sed -e 's/^        //' <<-EOF
        uuid-1
        uuid-3
	EOF
    )
    diff -u <(echo "$expected") <(echo "$output")
}

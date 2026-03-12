# Shared test helpers for sync algorithm tests

# shellcheck shell=bash
declare fixtures output_dir BATS_FILE_TMPDIR

function restore_database {
    docker compose exec -T db psql -U your5e -c \
        "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" your5e >/dev/null 2>&1
    docker compose exec -T db psql -U your5e your5e \
        < "$BATS_TEST_DIRNAME/seed.sql" >/dev/null 2>&1
}

function uuid_for {
    grep "^$1"$'\t' "$BATS_FILE_TMPDIR/pages" | cut -f2
}

function init_synced_dir {
    # create directory as if it was already synced
    cp -r "$fixtures/campaign-notes" "$output_dir"
    # cache format: uuid server_filename local_filename hash
    # after a sync, both filenames are the same
    awk -F'\t' '$4 == "" {print $2"\t"$1"\t"$1"\t"$3}' "$BATS_FILE_TMPDIR/pages" \
        > "$output_dir/.sync-state"
}

function set_cached_state {
    local uuid="$1" filename="$2" content="$3"
    local hash
    hash=$(printf '%s' "$content" | shasum -a 256 | cut -d' ' -f1)
    local state_file="$output_dir/.sync-state"

    # remove existing file for this UUID if different
    local old_file
    old_file=$(grep "^$uuid"$'\t' "$state_file" | cut -f3)
    [[ -n "$old_file" && "$old_file" != "$filename" ]] && rm -f "$output_dir/$old_file"

    # create file with content
    mkdir -p "$(dirname "$output_dir/$filename")"
    printf "%s" "$content" > "$output_dir/$filename"

    # update cache (both filenames same after reconciliation)
    grep -v "^$uuid"$'\t' "$state_file" > "$state_file.new"
    printf "%s\t%s\t%s\t%s\n" \
        "$uuid" "$filename" "$filename" "$hash" >> "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function untrack_file {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    awk -F'\t' -v f="$filename" '$3 != f' "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function untrack_and_remove_file {
    local filename="$1"
    untrack_file "$filename"
    rm -rf "${output_dir:?}/$filename"
}

function delete_tracked_file {
    rm "$output_dir/$1"
}

function set_older_filename {
    local from="$1" to="$2"
    local state_file="$output_dir/.sync-state"

    mkdir -p "$(dirname "$output_dir/$to")"
    mv "$output_dir/$from" "$output_dir/$to"
    rmdir -p "$(dirname "$output_dir/$from")" 2>/dev/null || true

    # rewind cache to before server renamed: both filenames set to old name
    local uuid
    uuid=$(awk -F'\t' -v f="$from" '$3 == f {print $1; exit}' "$state_file")
    awk -F'\t' -v u="$uuid" -v old="$to" -v OFS='\t' \
        '$1 == u {$2 = old; $3 = old} {print}' "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function rename_local_file {
    local from="$1" to="$2"
    local state_file="$output_dir/.sync-state"

    mkdir -p "$(dirname "$output_dir/$to")"
    mv "$output_dir/$from" "$output_dir/$to"
    rmdir -p "$(dirname "$output_dir/$from")" 2>/dev/null || true

    # update only local_filename (col 3), server_filename (col 2) stays unchanged
    awk -F'\t' -v old="$from" -v new="$to" -v OFS='\t' \
        '$3 == old {$3 = new} {print}' "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function set_older_content {
    local filename="$1"
    local state_file="$output_dir/.sync-state"
    local content="old content"
    local hash
    hash=$(printf '%s' "$content" | shasum -a 256 | cut -d' ' -f1)

    # update file content
    printf "%s" "$content" > "$output_dir/$filename"

    # update only the hash column, preserving server_fn and local_fn
    awk -F'\t' -v f="$filename" -v h="$hash" -v OFS='\t' \
        '$3 == f {$4 = h} {print}' "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function modify_file {
    echo "local content" > "$output_dir/$1"
}


function mark_file_stale {
    local filename="$1"
    local state_file="$output_dir/.sync-state"
    local old_uuid
    old_uuid=$(awk -F'\t' -v f="$filename" '$3 == f {print $1; exit}' "$state_file")

    awk -F'\t' -v u="$old_uuid" -v new="stale-uuid-$RANDOM" -v OFS='\t' \
        '$1 == u {$1 = new} {print}' "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function create_file {
    mkdir -p "$(dirname "$output_dir/$1")"
    echo "local content" > "$output_dir/$1"
}

function copy_fixture {
    local source="$1"
    local dest="${2:-$1}"
    mkdir -p "$(dirname "$output_dir/$dest")"
    cp "$fixtures/campaign-notes/$source" "$output_dir/$dest"
}

function add_stale_file {
    local filename="$1"
    set_cached_state "stale-uuid-$RANDOM" "$filename" "local content"
}

function file_tracks_deleted_remote {
    local content=$'# Old Notes\n\nThese notes are no longer needed.\n'
    set_cached_state "$(uuid_for "Old Notes.md")" "$1" "$content"
}

function assert_not_in_state {
    ! grep "$1" "$output_dir/.sync-state" || false
}

function assert_file_not_downloaded {
    local filename="$1"
    [[ ! -f "$output_dir/$filename" ]]
    assert_file_not_in_state "$filename"
}

function assert_tracked_file_deleted {
    local filename="$1"
    [[ ! -f "$output_dir/$filename" ]]
    assert_file_not_in_state "$filename"
}

function assert_tracked_file_not_restored {
    local filename="$1"
    [[ ! -f "$output_dir/$filename" ]]
    assert_file_in_state "$filename"
}

function assert_empty_dir_removed {
    local dirname="$1"
    [[ ! -d "$output_dir/$dirname" ]]
}

function assert_file_not_in_state {
    local filename="$1"
    ! awk -F'\t' -v f="$filename" '$3 == f {found=1; exit} END {exit !found}' \
        "$output_dir/.sync-state"
}

function assert_tracked_file_intact {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    [[ -f "$output_dir/$filename" ]]

    local cached_hash
    cached_hash=$(awk -F'\t' -v f="$filename" '$3 == f {print $4; exit}' "$state_file")
    [[ -n "$cached_hash" ]]

    local actual_hash
    actual_hash=$(shasum -a 256 "$output_dir/$filename" | cut -d' ' -f1)
    [[ "$actual_hash" == "$cached_hash" ]]
}

function assert_file_in_state {
    local filename="$1"
    awk -F'\t' -v f="$filename" '$3 == f {found=1; exit} END {exit !found}' \
        "$output_dir/.sync-state"
}

function assert_file_unchanged {
    local filename="$1"
    diff -u <(echo "local content") "$output_dir/$filename"
}

function assert_file_matches_fixture {
    local fixture="${1}"
    local filename="${2:-$1}"
    diff -u "$fixtures/campaign-notes/$fixture" "$output_dir/$filename"
}

function assert_tracked_file_matches_fixture {
    local fixture="$1"
    local filename="${2:-$1}"

    [[ -f "$output_dir/$filename" ]]
    diff -q "$fixtures/campaign-notes/$fixture" "$output_dir/$filename" >/dev/null
    awk -F'\t' -v f="$filename" '$3 == f {found=1; exit} END {exit !found}' \
        "$output_dir/.sync-state"
}

function assert_file_ignored {
    local filename="$1"
    assert_file_unchanged "$filename"
    assert_file_not_in_state "$filename"
}

function assert_file_downloaded {
    local filename="$1"
    assert_file_matches_fixture "$filename"
    assert_file_in_state "$filename"
}

function assert_state_matches_fixture {
    local expected
    expected=$(
        find "$fixtures/campaign-notes" -type f ! -name ".sync-state" -print0 \
            | while IFS= read -r -d '' file; do
                local relative="${file#"$fixtures"/campaign-notes/}"
                local hash
                hash=$(shasum -a 256 "$file" | cut -d' ' -f1)
                printf "%s\t%s\n" "$relative" "$hash"
            done | sort
    )
    diff -u <(echo "$expected") <(cut -f3,4 "$output_dir/.sync-state" | sort)
}

function assert_dir_matches_fixture {
    diff -ru --exclude=".sync-state" "$output_dir" "$fixtures/campaign-notes"
}

function assert_success {
    # shellcheck disable=SC2154  # $status is set by bats
    [[ $status -eq 0 ]]
}

function assert_failure {
    # shellcheck disable=SC2154  # $status is set by bats
    [[ $status -ne 0 ]]
}

function assert_no_output_dir {
    [[ ! -d "$output_dir" ]]
}

function fail_on_multiple_curl_calls {
    # shellcheck disable=SC2329  # invoked indirectly via export -f
    curl() {
        local marker="${BATS_TEST_TMPDIR}/.curl_called"
        if [[ -f "$marker" ]]; then
            echo "TEST GUARD: multiple curl calls not permitted" >&2
            return 1
        fi
        touch "$marker"
        command curl "$@"
    }
    export -f curl
}

function assert_file_pushed {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    local uuid
    uuid=$(awk -F'\t' -v f="$filename" '$3 == f {print $1; exit}' "$state_file")
    [[ -n "$uuid" ]]

    local cached_hash
    cached_hash=$(awk -F'\t' -v f="$filename" '$3 == f {print $4; exit}' "$state_file")
    local actual_hash
    actual_hash=$(shasum -a 256 "$output_dir/$filename" | cut -d' ' -f1)
    [[ "$actual_hash" == "$cached_hash" ]]

    local server_content
    server_content=$(curl -s \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/api/notebooks/norm/campaign-notes/$uuid")
    diff -u "$output_dir/$filename" <(echo "$server_content")
}

function assert_server_file_deleted {
    local filename="$1"

    local response
    response=$(curl -s \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/api/notebooks/norm/campaign-notes/" \
        | jq -r ".results[] | select(.filename == \"$filename\") | .deleted_at")
    [[ -n "$response" && "$response" != "null" ]]
}

function assert_file_deleted_on_server {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    ! awk -F'\t' -v f="$filename" \
        '$3 == f {found=1; exit} END {exit !found}' "$state_file"
    [[ ! -f "$output_dir/$filename" ]]
    assert_server_file_deleted "$filename"
}

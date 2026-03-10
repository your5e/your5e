# Shared test helpers for sync algorithm tests

# shellcheck shell=bash
declare fixtures output_dir BATS_FILE_TMPDIR

function uuid_for {
    grep "^$1"$'\t' "$BATS_FILE_TMPDIR/pages" | cut -f2
}

function init_synced_dir {
    # create directory as if it was already synced
    cp -r "$fixtures/campaign-notes" "$output_dir"
    awk -F'\t' '$4 == "" {print $2"\t"$1"\t"$3}' "$BATS_FILE_TMPDIR/pages" \
        > "$output_dir/.sync-state"
}

function set_cached_state {
    local uuid="$1" filename="$2" content="$3"
    local hash
    hash=$(printf '%s' "$content" | shasum -a 256 | cut -d' ' -f1)
    local state_file="$output_dir/.sync-state"

    # remove existing file for this UUID if different
    local old_file
    old_file=$(grep "^$uuid"$'\t' "$state_file" | cut -f2)
    [[ -n "$old_file" && "$old_file" != "$filename" ]] && rm -f "$output_dir/$old_file"

    # create file with content
    mkdir -p "$(dirname "$output_dir/$filename")"
    printf "%s" "$content" > "$output_dir/$filename"

    # update cache
    grep -v "^$uuid"$'\t' "$state_file" > "$state_file.new"
    printf "%s\t%s\t%s\n" "$uuid" "$filename" "$hash" >> "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function untrack_file {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    grep -v $'\t'"$filename"$'\t' "$state_file" > "$state_file.new"
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

    local uuid
    uuid=$(grep $'\t'"$from"$'\t' "$state_file" | cut -f1)
    sed "s|$uuid\t$from\t|$uuid\t$to\t|" "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function set_older_content {
    local filename="$1"
    local uuid
    uuid=$(grep $'\t'"$filename"$'\t' "$output_dir/.sync-state" | cut -f1)
    set_cached_state "$uuid" "$filename" "old content"
}

function modify_file {
    echo "local content" > "$output_dir/$1"
}


function mark_file_stale {
    local filename="$1"
    local state_file="$output_dir/.sync-state"
    local old_uuid
    old_uuid=$(grep $'\t'"$filename"$'\t' "$state_file" | cut -f1)

    sed "s/^$old_uuid	/stale-uuid-$RANDOM	/" "$state_file" > "$state_file.new"
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
    set_cached_state "$(uuid_for "Old Notes.md")" "$1" "old content"
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
    ! grep $'\t'"$filename"$'\t' "$output_dir/.sync-state"
}

function assert_tracked_file_intact {
    local filename="$1"
    local state_file="$output_dir/.sync-state"

    [[ -f "$output_dir/$filename" ]]

    local cached_hash
    cached_hash=$(grep $'\t'"$filename"$'\t' "$state_file" | cut -f3)
    [[ -n "$cached_hash" ]]

    local actual_hash
    actual_hash=$(shasum -a 256 "$output_dir/$filename" | cut -d' ' -f1)
    [[ "$actual_hash" == "$cached_hash" ]]
}

function assert_file_in_state {
    local filename="$1"
    grep -q $'\t'"$filename"$'\t' "$output_dir/.sync-state"
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
    grep -q $'\t'"$filename"$'\t' "$output_dir/.sync-state"
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
    diff -u <(echo "$expected") <(cut -f2,3 "$output_dir/.sync-state" | sort)
}

function assert_dir_matches_fixture {
    diff -ru --exclude=".sync-state" "$output_dir" "$fixtures/campaign-notes"
}

function assert_success {
    # shellcheck disable=SC2154  # $status is set by bats
    [[ $status -eq 0 ]]
}

function fail_on_file_download {
    # shellcheck disable=SC2329  # invoked indirectly via export -f
    curl() {
        [[ "$*" == *"-o"* ]] && return 1
        command curl "$@"
    }
    export -f curl
}

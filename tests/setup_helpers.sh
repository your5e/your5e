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

function move_cached_file {
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

function replace_cached_uuid {
    local filename="$1" new_uuid="$2"
    local state_file="$output_dir/.sync-state"
    local old_uuid
    old_uuid=$(uuid_for "$filename")

    sed "s/^$old_uuid\t/$new_uuid\t/" "$state_file" > "$state_file.new"
    mv "$state_file.new" "$state_file"
}

function rewind_bestiarymd_state {
    set_cached_state "$(uuid_for "Bestiary.md")" "Bestiary.md" "old content"
}

function modify_file {
    echo "local modifications" > "$output_dir/$1"
}

function file_deleted_locally {
    rm "$output_dir/$1"
}

function rewind_homemd_state {
    set_cached_state "$(uuid_for "Home.md")" "Welcome.md" "old content"
}

function mark_file_stale {
    replace_cached_uuid "index.md" "stale-uuid-$RANDOM"
}

function create_file {
    mkdir -p "$(dirname "$output_dir/$1")"
    echo "local content" > "$output_dir/$1"
}

function add_stale_file {
    set_cached_state "stale-uuid-no-server-file" "my-notes.md" "local content"
}

function file_tracks_deleted_remote {
    set_cached_state "$(uuid_for "Old Notes.md")" "$1" "old content"
}

function assert_not_in_state {
    ! grep "$1" "$output_dir/.sync-state" || false
}

function replace_with_directory {
    local filename="$1"
    local filepath="$output_dir/$filename"

    [[ -f "$filepath" ]] && rm "$filepath"
    mkdir -p "$filepath"
    echo "local notes" > "$filepath/notes.txt"
}

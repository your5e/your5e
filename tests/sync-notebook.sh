#!/usr/bin/env -S bash -euo pipefail
#
# Reference implementation of the recommended notebook sync algorithm.
#
# See sync.md for the algorithm description, and the *.bats tests for test
# scenarios that any sync client implementation should consider.

api_token="${YOUR5E_API_TOKEN:-}"
base_url="${YOUR5E_API_BASE:-http://localhost:5843}"
state_file=""
all_pages=()
all_deleted=()
declare -A seen_uuids

function main {
    while getopts "b:ht:" opt; do
        case "$opt" in
            b)  base_url="$OPTARG" ;;
            h)  usage ;;
            t)  api_token="$OPTARG" ;;
            *)  usage ;;
        esac
    done
    shift $((OPTIND-1))

    [[ -z "$api_token" || $# -ne 2 ]] \
        && usage

    sync_notebook "$@"
}

function usage {
    sed -e 's/^        //' >&2 <<-EOF
        Usage: $0 [-b <base_url>] <username/notebook> <output_dir>

            -b  Base URL  (default: \$YOUR5E_API_BASE or http://localhost:5843)
            -t  API token (default: \$YOUR5E_API_TOKEN)

        Example:
          $0 norm/campaign-notes ./backup
	EOF
    exit 1
}

function sync_notebook {
    local notebook="$1"
    local output_dir="$2"
    state_file="${output_dir}/.sync-state"

    fetch_notebook_data "$notebook"
    handle_deletions "$output_dir"
    handle_updates "$notebook" "$output_dir" "" "${all_pages[@]:+"${all_pages[@]}"}"
    report_stale_files "$output_dir"

    [[ -t 1 ]] \
        && printf "\e[2K"

    exit 0
}

function fetch_notebook_data {
    local notebook="$1"
    local next_page="${base_url}/api/notebooks/${notebook}/"
    local response

    while [[ -n "$next_page" ]]; do
        response=$(
            curl -s -H "Authorization: Token $api_token" "$next_page"
        )
        next_page=$(
            echo "$response" \
                | jq -r '.next // ""'
        )

        mapfile -t pages < <(
            echo "$response" \
                | jq -r '
                    .results[]
                    | select(.deleted_at == null)
                    | [.uuid, .filename, .content_hash]
                    | @tsv
                '
        )

        mapfile -t deleted < <(
            echo "$response" \
                | jq -r '
                    .results[]
                    | select(.deleted_at != null)
                    | .uuid
                '
        )

        all_pages+=("${pages[@]:+"${pages[@]}"}")
        all_deleted+=("${deleted[@]:+"${deleted[@]}"}")
    done

    for uuid in "${all_deleted[@]:+"${all_deleted[@]}"}"; do
        seen_uuids["$uuid"]=1
    done
    for page in "${all_pages[@]:+"${all_pages[@]}"}"; do
        IFS=$'\t' read -r uuid file hash <<< "$page"
        seen_uuids["$uuid"]=1
    done
}

function handle_deletions {
    local output_dir="$1"

    for uuid in "${all_deleted[@]:+"${all_deleted[@]}"}"; do
        if is_untracked "$uuid"; then
            continue
        fi

        local cached_file
        cached_file=$(get_cached_filename "$uuid")
        local filepath="${output_dir}/${cached_file}"

        if has_local_changes "$uuid" "$filepath"; then
            printf "   %s has local modifications, skipped\n" "$cached_file"
        else
            remove_file "$uuid" "$filepath"
            printf -- "-- %s\n" "$cached_file"
        fi
    done
}

function handle_updates {
    local notebook="$1"
    local output_dir="$2"
    local vacating="$3"
    shift 3

    # In order to handle rename cycles (file a renamed to b, b renamed c, c renamed a),
    # handle_updates is a recursive function that can call itself with the current
    # argument removed. So two things are unintuitive about this function, that it will
    # process its arguments in reverse order (see below), and that it will return
    # success early when there are no arguments to signal a cycle can be broken:
    [[ $# -eq 0 ]] \
        && return 0

    local uuid dest_file hash
    IFS=$'\t' read -r uuid dest_file hash <<< "$1"
    shift

    local src_file
    src_file=$(get_cached_filename "$uuid")
    local src_path="${output_dir}/${src_file}"

    # To break rename cycles, we need to know which paths will be vacated by other
    # renames (when we get to processing c->a last, we need to know that a is trying
    # to move away to know we can rename it successfully). If any intervening part
    # of the cycle produces a complication, a would not be in $vacating,
    # and the rename is therefore blocked.
    local new_vacating="$vacating"
    is_being_renamed "$uuid" "$dest_file" \
        && ! source_deleted "$src_path" \
        && ! has_local_changes "$uuid" "$src_path" \
        && new_vacating="${vacating:+$vacating:}$src_file"

    # Deal with any remaining arguments.
    handle_updates "$notebook" "$output_dir" "$new_vacating" "$@"

    # Now everything else has been dealt with, we can process the current update.
    local dest_path="${output_dir}/${dest_file}"

    [[ -t 1 ]] \
        && printf "\e[2K%s\r" "$dest_file"

    local cached_uuid
    cached_uuid=$(get_cached_uuid "$dest_file")

    if is_cached_uuid_stale "$cached_uuid" "$uuid"; then
        seen_uuids["$cached_uuid"]=1

        if [[ -f "$dest_path" ]]; then
            printf "   %s deleted from server, keeping\n" "$dest_file"

            if has_local_changes "$cached_uuid" "$dest_path"; then
                printf "   %s has local modifications, skipped\n" "$dest_file"
            else
                printf "   %s has new remote content, skipped\n" "$dest_file"
            fi
            return 0
        fi

        del_cached "$cached_uuid"
    fi

    if file_blocked_by_directory "$dest_path" "$uuid" "$dest_file"; then
        printf "   %s blocked by local directory, skipped\n" "$dest_file"

    elif parent_blocked_by_file "$output_dir" "$dest_file"; then
        printf "   %s blocked by local file, skipped\n" "$dest_file"

    elif file_exists_with_different_case "$dest_path" "$dest_file"; then
        printf "   %s blocked by local file with different case, skipped\n" \
            "$dest_file"

    elif file_matches_hash "$dest_path" "$hash" && is_untracked "$uuid"; then
        printf "   %s matches remote, tracking\n" "$dest_file"
        set_cached "$uuid" "$dest_file" "$hash"

    elif is_being_renamed "$uuid" "$dest_file"; then
        # To break a rename cycle, the last in the chain is put in a temporary location.
        [[ -e "${src_path}.vacated" ]] \
            && src_path="${src_path}.vacated"

        if has_local_changes "$uuid" "$src_path"; then
            printf "   %s has local modifications, skipped\n" "$src_file"

        elif destination_occupied "$dest_path"; then
            if [[ ":$vacating:" == *":$dest_file:"* ]]; then
                # Here is where the rename cycle is broken. The desired destination
                # is going to be vacated, so this can be renamed, but needs to be
                # moved aside temporarily.
                mv "$dest_path" "${dest_path}.vacated"
                rename_file "$src_path" "$dest_path"
                printf "   %s -> %s\n" "$src_file" "$dest_file"

            else
                printf "   %s -> %s blocked by local file\n" \
                    "$src_file" "$dest_file"
            fi

        elif [[ -d "$dest_path" ]]; then
            printf "   %s -> %s blocked by local directory, skipped\n" \
                "$src_file" "$dest_file"

        elif source_deleted "$src_path"; then
            if has_remote_changes "$uuid" "$hash"; then
                download_file \
                    "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
                printf "++ %s\n" "$dest_file"
            else
                printf "   %s deleted locally, skipped\n" "$src_file"
            fi

        else
            rename_file "$src_path" "$dest_path"
            printf "   %s -> %s\n" "$src_file" "$dest_file"

            if file_matches_hash "$dest_path" "$hash"; then
                set_cached "$uuid" "$dest_file" "$hash"
            else
                download_file "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
                printf "++ %s\n" "$dest_file"
            fi
        fi

    elif has_local_changes "$uuid" "$dest_path"; then
        if is_untracked "$uuid"; then
            printf "   %s has local modifications, skipped\n" "$dest_file"

        elif has_remote_changes "$uuid" "$hash"; then
            printf "   %s has local modifications, skipped\n" "$dest_file"
        fi

    elif deleted_locally_no_new_content "$uuid" "$dest_file" "$dest_path" "$hash"; then
        printf "   %s deleted locally, skipped\n" "$dest_file"

    else
        if file_matches_hash "$dest_path" "$hash"; then
            set_cached "$uuid" "$dest_file" "$hash"
        else
            download_file "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
            printf "++ %s\n" "$dest_file"
        fi
    fi
}

function report_stale_files {
    local output_dir="$1"

    [[ ! -f "$state_file" ]] \
        && return 0

    while IFS=$'\t' read -r uuid file hash; do
        [[ -n "${seen_uuids[$uuid]:-}" ]] \
            && continue

        if [[ ! -f "$output_dir/$file" ]]; then
            del_cached "$uuid"
            continue
        fi

        printf "   %s deleted from server, keeping\n" "$file"
    done < "$state_file"
}

function get_cached_filename {
    local uuid="$1"

    [[ ! -f "$state_file" ]] \
        && return

    awk \
        -F'\t' \
        -v u="$uuid" \
        '
            $1 != u { next }
            { print $2; exit }
        ' \
            "$state_file"
}

function get_cached_hash {
    local uuid="$1"

    [[ ! -f "$state_file" ]] \
        && return

    awk \
        -F'\t' \
        -v u="$uuid" \
        '
            $1 != u { next }
            { print $3; exit }
        ' \
            "$state_file"
}

function get_cached_uuid {
    local file="$1"

    [[ ! -f "$state_file" ]] \
        && return

    awk \
        -F'\t' \
        -v f="$file" \
        '
            $2 != f { next }
            { print $1; exit }
        ' \
            "$state_file"
}

function set_cached {
    local uuid="$1"
    local filename="$2"
    local hash="$3"
    local tmp

    tmp=$(mktemp)
    if [[ -f "$state_file" ]]; then
        # remove this UUID and any other UUID tracking the same path
        awk \
            -F'\t' \
            -v u="$uuid" \
            -v f="$filename" \
            '
                $1 == u { next }
                $2 == f { next }
                { print }
            ' \
                "$state_file" \
                    > "$tmp"
    fi

    printf "%s\t%s\t%s\n" "$uuid" "$filename" "$hash" >> "$tmp"
    mv "$tmp" "$state_file"
}

function del_cached {
    local uuid="$1"

    [[ ! -f "$state_file" ]] \
        && return

    local tmp
    tmp=$(mktemp)

    awk \
        -F'\t' \
        -v u="$uuid" \
        '
            $1 == u { next }
            { print }
        ' \
            "$state_file" \
                > "$tmp"
    mv "$tmp" "$state_file"
}

function hash_file {
    local file="$1"

    shasum -a 256 "$file" | cut -d' ' -f1
}

function download_file {
    local notebook="$1"
    local output_dir="$2"
    local uuid="$3"
    local file="$4"
    local hash="$5"
    local filepath="${output_dir}/${file}"

    mkdir -p "$(dirname "$filepath")"

    local tmp
    tmp=$(mktemp)

    curl \
        -s \
        -H "Authorization: Token $api_token" \
        -o "$tmp" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"

    mv "$tmp" "$filepath"
    set_cached "$uuid" "$file" "$hash"
}

function rename_file {
    local old_filepath="$1"
    local new_filepath="$2"

    mkdir -p "$(dirname "$new_filepath")"
    mv "$old_filepath" "$new_filepath"
    rmdir -p "$(dirname "$old_filepath")" 2>/dev/null || true
}

function remove_file {
    local uuid="$1"
    local filepath="$2"

    if [[ -f "$filepath" ]]; then
        rm "$filepath"
        rmdir -p "$(dirname "$filepath")" 2>/dev/null || true
    fi

    del_cached "$uuid"
}

function is_untracked {
    local uuid="$1"

    [[ -z $(get_cached_filename "$uuid") ]]
}

function is_being_renamed {
    local uuid="$1"
    local file="$2"

    local cached_file
    cached_file=$(get_cached_filename "$uuid")

    [[ -n "$cached_file" && "$cached_file" != "$file" ]]
}

function is_cached_uuid_stale {
    local cached_uuid="$1"
    local uuid="$2"

    [[ -n "$cached_uuid" ]] \
        && [[ "$cached_uuid" != "$uuid" ]] \
        && [[ -z "${seen_uuids[$cached_uuid]:-}" ]]
}

function has_local_changes {
    local uuid="$1"
    local filepath="$2"

    [[ ! -f "$filepath" ]] \
        && return 1

    [[ "$(get_cached_hash "$uuid")" != "$(hash_file "$filepath")" ]]
}

function has_remote_changes {
    local uuid="$1"
    local hash="$2"

    [[ "$(get_cached_hash "$uuid")" != "$hash" ]]
}

function file_blocked_by_directory {
    local filepath="$1"
    local uuid="$2"
    local dest_file="$3"

    [[ -d "$filepath" ]] \
        &&  ! is_being_renamed "$uuid" "$dest_file"
}

function parent_blocked_by_file {
    local output_dir="$1"
    local file="$2"

    local check_path="$output_dir"
    local dir_part
    dir_part=$(dirname "$file")

    [[ "$dir_part" == "." ]] \
        && return 1

    IFS='/' read -ra path_parts <<< "$dir_part"
    for part in "${path_parts[@]}"; do
        check_path="${check_path}/${part}"
        if [[ -f "$check_path" ]]; then
            return 0
        fi
    done

    return 1
}

function file_matches_hash {
    local filepath="$1"
    local hash="$2"

    [[ ! -f "$filepath" ]] \
        && return 1

    [[ "$(hash_file "$filepath")" == "$hash" ]]
}

function file_exists_with_different_case {
    local filepath="$1"
    local file="$2"

    local dir_path base_name actual_file
    dir_path=$(dirname "$filepath")
    base_name=$(basename "$file")

    actual_file=$(
        find "$dir_path" -maxdepth 1 -iname "$base_name" -print -quit 2>/dev/null
    )

    [[ -z "$actual_file" ]] && return 1
    [[ "$(basename "$actual_file")" == "$base_name" ]] && return 1
    return 0
}

function deleted_locally_no_new_content {
    local uuid="$1"
    local file="$2"
    local filepath="$3"
    local hash="$4"

    [[ -f "$filepath" ]] \
        && return 1

    ! is_untracked "$uuid" \
        && ! is_being_renamed "$uuid" "$file" \
        && ! has_remote_changes "$uuid" "$hash"
}

function source_deleted {
    local filepath="$1"

    [[ ! -f "$filepath" ]]
}

function destination_occupied {
    local filepath="$1"

    [[ -f "$filepath" ]]
}

[[ "${BASH_SOURCE[0]}" != "$0" ]] || main "$@"

#!/usr/bin/env -S bash -euo pipefail
#
# Reference implementation of the recommended notebook sync algorithm.
#
# See sync.md for the algorithm description, and the *.bats tests for test
# scenarios that any sync client implementation should consider.

api_token="${YOUR5E_API_TOKEN:-}"
base_url="${YOUR5E_API_BASE:-http://localhost:5843}"
pull_only=0
state_file=""
remote_state_file="$(mktemp)"
trap 'rm -f "$remote_state_file"' EXIT

function main {
    while getopts "b:hpt:" opt; do
        case "$opt" in
            b)  base_url="$OPTARG" ;;
            h)  usage ;;
            p)  pull_only=1 ;;
            t)  api_token="$OPTARG" ;;
            *)  usage ;;
        esac
    done
    shift $((OPTIND-1))

    [[ $# -ne 2 ]] \
        && usage

    if [[ -z "$api_token" ]]; then
        echo "sync: ERROR API token missing"
        exit 1
    fi

    local notebook="$1"
    local output_dir="$2"
    state_file="${output_dir}/.sync-state"

    fetch_remote_state "$notebook"

    [[ $pull_only -eq 0 ]] \
        && apply_local_updates "$notebook" "$output_dir"

    # shellcheck disable=SC2046
    apply_remote_deletions "$output_dir" $(get_deleted_uuids)

    # shellcheck disable=SC2046
    apply_remote_updates "$notebook" "$output_dir" "" $(get_active_uuids)

    check_for_stale_files "$output_dir"

    # [[ -t 1 ]] \
    #     && printf "\e[2K"

    exit 0
}

function usage {
    sed -e 's/^        //' >&2 <<-EOF
        Usage: $0 [-b URL] [-h] [-p] [-t TOKEN] <username/notebook> <output_dir>

            -b  Base URL   (default: \$YOUR5E_API_BASE or http://localhost:5843)
            -p  Pull only  (do not push local changes)
            -t  API token  (default: \$YOUR5E_API_TOKEN)

        Example:
          $0 norm/campaign-notes ./backup
	EOF
    exit 1
}

function fetch_remote_state {
    local notebook="$1"
    local next_page="${base_url}/api/notebooks/${notebook}/"
    local body first_page=1 http_code response

    while [[ -n "$next_page" ]]; do
        response=$(
            curl -s -w "\n%{http_code}" \
                -H "Authorization: Token $api_token" "$next_page"
        )
        http_code=$(echo "$response" | tail -1)
        body=$(echo "$response" | sed '$d')

        if [[ "$http_code" == "401" || "$http_code" == "403" ]]; then
            echo "sync: ERROR API token invalid"
            exit 1
        fi

        if [[ "$http_code" == "404" ]]; then
            echo "sync: ERROR notebook not found"
            exit 1
        fi

        if [[ "$http_code" != "200" ]]; then
            echo "sync: ERROR unexpected response (HTTP $http_code)"
            exit 1
        fi

        if [[ $first_page -eq 1 ]]; then
            first_page=0
            local editable
            editable=$(echo "$body" | jq -r '.editable')
            if [[ "$editable" == "false" && $pull_only -eq 0 ]]; then
                echo "sync: NOTE read-only access, switching to pull-only mode"
                pull_only=1
            fi
        fi

        next_page=$(
            echo "$body" \
                | jq -r '.next // ""'
        )

        echo "$body" \
            | jq -r '
                    .results[]
                        | [.uuid, .filename, .content_hash, .version, .deleted_at // ""]
                        | @tsv
                ' \
            >> "$remote_state_file"
    done
}

function apply_local_updates {
    local notebook="$1"
    local output_dir="$2"

    [[ -d "$output_dir" ]] \
        || return 0

    local -a stale_uuids=()

    if has_local_state; then
        while IFS=$'\t' read -r uuid _ local_fn hash; do
            local filepath="$output_dir/$local_fn"
            local remote_filename
            remote_filename=$(get_remote_filename "$uuid")

            if exists_remotely_and_renamed_locally "$uuid"; then
                rename_remote_file \
                    "$notebook" "$uuid" "$remote_filename" "$local_fn" \
                        || continue
                remote_filename="$local_fn"
            fi

            if local_file_was_removed "$filepath"; then
                if remote_file_was_renamed "$uuid"; then
                    # local file was deleted but renamed remotely;
                    # rename it back before deleting; local change takes precedence
                    rename_remote_file \
                        "$notebook" "$uuid" "$remote_filename" "$local_fn" \
                            || continue
                    remote_filename="$local_fn"
                fi

                delete_remote_file "$notebook" "$uuid"
                continue
            fi

            if local_file_was_edited "$filepath" "$hash"; then
                if local_file_is_stale "$uuid"; then
                    create_remote_file "$notebook" "$local_fn" "$filepath" "$uuid" \
                        || stale_uuids+=("$uuid")
                    continue
                fi

                if remote_file_was_renamed "$uuid"; then
                    rename_remote_file \
                        "$notebook" "$uuid" "$remote_filename" "$local_fn" \
                            || continue
                    remote_filename="$local_fn"
                fi

                update_remote_file "$notebook" "$uuid" "$local_fn" "$filepath"
            fi
        done < "$state_file"
    fi

    # check for new files
    while IFS= read -r -d '' filepath; do
        local file="${filepath#"$output_dir"/}"

        file_is_already_tracked "$file" \
            && continue
        remote_has_identical_file "$file" "$filepath" \
            && continue

        create_remote_file "$notebook" "$file" "$filepath" \
            || true
    done < <(find "$output_dir" -type f ! -name ".sync-state" -print0 | sort -z)

    # stale UUIDs must stay in cache until after the new files loop,
    # otherwise the file would be picked up as "new" and tried again
    for uuid in "${stale_uuids[@]:+"${stale_uuids[@]}"}"; do
        del_cached "$uuid"
    done
}

function apply_remote_deletions {
    local output_dir="$1"
    shift

    for uuid in "$@"; do
        is_untracked "$uuid" && continue

        local cached_local_file
        cached_local_file=$(get_cached_local_filename "$uuid")
        local cached_remote_file
        cached_remote_file=$(get_cached_remote_filename "$uuid")
        local filepath="${output_dir}/${cached_local_file}"

        if has_local_changes "$uuid" "$filepath"; then
            if [[ "$cached_local_file" != "$cached_remote_file" ]]; then
                printf 'pull: SKIPPING delete "%s" (at "%s"), ' \
                    "$cached_remote_file" "$cached_local_file"
                printf 'local changes would be lost\n'
            else
                printf 'pull: SKIPPING delete "%s", local changes would be lost\n' \
                    "$cached_local_file"
            fi
        else
            remove_file "$uuid" "$filepath"
            if [[ "$cached_local_file" != "$cached_remote_file" ]]; then
                printf 'pull: deleted "%s" (was "%s")\n' \
                    "$cached_remote_file" "$cached_local_file"
            else
                printf "pull: deleted \"%s\"\n" "$cached_local_file"
            fi
        fi
    done
}

function apply_remote_updates {
    local notebook="$1"
    local output_dir="$2"
    local vacating="$3"
    shift 3

    # In order to handle rename cycles (file a renamed to b, b renamed c, c renamed a),
    # apply_remote_updates_impl is a recursive function that can call itself with the
    # current argument removed. So two things are unintuitive about this function, that
    # it will process its arguments in reverse order (see below), and that it will
    # return success early when there are no arguments to signal a cycle can be broken:
    [[ $# -eq 0 ]] \
        && return 0

    local uuid="$1"
    shift

    local dest_file
    dest_file=$(get_remote_filename "$uuid")
    local hash
    hash=$(get_remote_hash "$uuid")
    local version
    version=$(get_remote_version "$uuid")

    local src_file
    src_file=$(get_cached_local_filename "$uuid")
    local src_path="${output_dir}/${src_file}"

    # To break rename cycles, we need to know which paths will be vacated by other
    # renames (when we get to processing c->a last, we need to know that a is trying
    # to move away to know we can rename it successfully). If any intervening part
    # of the cycle produces a complication, a would not be in $vacating,
    # and the rename is therefore blocked.
    local new_vacating="$vacating"
    is_being_renamed "$uuid" "$dest_file" \
        && ! local_file_was_removed "$src_path" \
        && ! has_local_changes "$uuid" "$src_path" \
        && new_vacating="${vacating:+$vacating:}$src_file"

    # Deal with any remaining arguments.
    apply_remote_updates "$notebook" "$output_dir" "$new_vacating" "$@"

    # Now everything else has been dealt with, we can process the current update.
    local dest_path="${output_dir}/${dest_file}"

    # [[ -t 1 ]] \
    #     && printf "\e[2K%s\r" "$dest_file"

    local cached_uuid
    cached_uuid=$(get_cached_uuid "$dest_file")

    if is_cached_uuid_stale "$cached_uuid" "$uuid"; then
        if [[ -f "$dest_path" ]] && has_local_changes "$cached_uuid" "$dest_path"; then
            printf 'pull: SKIPPING delete "%s", local changes would be lost\n' \
                "$dest_file"
            return 0
        fi

        remove_file "$cached_uuid" "$dest_path"
    fi

    if file_blocked_by_directory "$dest_path" "$uuid" "$dest_file"; then
        printf "pull: ERROR cannot pull \"%s\", blocked by local directory\n" \
            "$dest_file"

    elif parent_blocked_by_file "$output_dir" "$dest_file"; then
        printf "pull: ERROR cannot pull \"%s\", blocked by local file\n" "$dest_file"

    elif file_exists_with_different_case "$dest_path" "$dest_file"; then
        printf 'pull: ERROR cannot pull "%s", ' "$dest_file"
        printf "blocked by local file with different case\n"

    elif file_matches_hash "$dest_path" "$hash" && is_untracked "$uuid"; then
        printf "pull: tracking \"%s\" (v%s)\n" "$dest_file" "$version"
        update_sync_state "$uuid" "$dest_file" "$hash"

    elif is_being_renamed "$uuid" "$dest_file"; then
        # To break a rename cycle, the last in the chain is put in a temporary location.
        [[ -e "${src_path}.vacated" ]] \
            && src_path="${src_path}.vacated"

        if is_locally_renamed "$uuid"; then
            local cached_remote_fn
            cached_remote_fn=$(get_cached_remote_filename "$uuid")
            printf 'pull: SKIPPING rename "%s" to "%s", already "%s" locally\n' \
                "$cached_remote_fn" "$dest_file" "$src_file"

            if has_remote_changes "$uuid" \
                    && has_local_changes "$uuid" "$src_path"; then
                printf 'pull: SKIPPING pull "%s" to "%s", ' "$dest_file" "$src_file"
                printf 'local changes would be lost\n'
            elif has_remote_changes "$uuid"; then
                fetch_remote_to_local_path \
                    "$notebook" "$output_dir" "$uuid" "$src_file" "$hash"
                printf 'pull: "%s" to "%s" (v%s)\n' "$dest_file" "$src_file" "$version"
            fi

        elif has_local_changes "$uuid" "$src_path"; then
            printf 'pull: SKIPPING rename "%s" to "%s", ' "$src_file" "$dest_file"
            printf "local changes would be lost\n"

        elif destination_occupied "$dest_path"; then
            if [[ ":$vacating:" == *":$dest_file:"* ]]; then
                # Here is where the rename cycle is broken. The desired destination
                # is going to be vacated, so this can be renamed, but needs to be
                # moved aside temporarily.
                mv "$dest_path" "${dest_path}.vacated"
                rename_file "$src_path" "$dest_path"
                printf "pull: renamed \"%s\" to \"%s\"\n" "$src_file" "$dest_file"

                if file_matches_hash "$dest_path" "$hash"; then
                    update_sync_state "$uuid" "$dest_file" "$hash"
                else
                    fetch_remote_file \
                        "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
                    printf "pull: \"%s\" (v%s)\n" "$dest_file" "$version"
                fi

            else
                printf 'pull: ERROR cannot rename "%s" to "%s", ' \
                    "$src_file" "$dest_file"
                printf "blocked by local file\n"
            fi

        elif [[ -d "$dest_path" ]]; then
            printf 'pull: ERROR cannot rename "%s" to "%s", ' \
                "$src_file" "$dest_file"
            printf "blocked by local directory\n"

        elif local_file_was_removed "$src_path"; then
            if has_remote_changes "$uuid"; then
                fetch_remote_file \
                    "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
                printf "pull: \"%s\" (v%s)\n" "$dest_file" "$version"
            else
                printf 'pull: SKIPPING rename "%s" to "%s", ' "$src_file" "$dest_file"
                printf '"%s" deleted locally\n' "$src_file"
            fi

        else
            rename_file "$src_path" "$dest_path"
            printf "pull: renamed \"%s\" to \"%s\"\n" "$src_file" "$dest_file"

            if file_matches_hash "$dest_path" "$hash"; then
                update_sync_state "$uuid" "$dest_file" "$hash"
            else
                fetch_remote_file "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
                printf "pull: \"%s\" (v%s)\n" "$dest_file" "$version"
            fi
        fi

    elif has_local_changes "$uuid" "$dest_path"; then
        if is_untracked "$uuid"; then
            printf "pull: ERROR cannot pull \"%s\", blocked by local file\n" \
                "$dest_file"

        elif has_remote_changes "$uuid"; then
            printf 'pull: SKIPPING pull "%s", local changes would be lost\n' \
                "$dest_file"
        fi

    elif deleted_locally_no_new_content "$uuid" "$dest_file" "$dest_path"; then
        printf 'pull: SKIPPING pull "%s", already deleted locally\n' "$dest_file"

    elif is_locally_renamed "$uuid" && ! has_remote_changes "$uuid"; then
        :  # local rename, no remote changes - nothing to do

    elif is_locally_renamed "$uuid" && has_local_changes "$uuid" "$src_path"; then
        printf 'pull: SKIPPING pull "%s" to "%s", local changes would be lost\n' \
            "$dest_file" "$src_file"

    elif is_locally_renamed "$uuid" && has_remote_changes "$uuid"; then
        fetch_remote_to_local_path \
            "$notebook" "$output_dir" "$uuid" "$src_file" "$hash"
        printf 'pull: "%s" to "%s" (v%s)\n' "$dest_file" "$src_file" "$version"

    else
        if file_matches_hash "$dest_path" "$hash"; then
            update_sync_state "$uuid" "$dest_file" "$hash"
        else
            fetch_remote_file "$notebook" "$output_dir" "$uuid" "$dest_file" "$hash"
            printf "pull: \"%s\" (v%s)\n" "$dest_file" "$version"
        fi
    fi
}

function check_for_stale_files {
    local output_dir="$1"

    [[ ! -f "$state_file" ]] \
        && return 0

    while IFS=$'\t' read -r uuid _ local_fn hash; do
        is_uuid_on_remote "$uuid" && continue

        # Skip if filename now belongs to a different UUID on remote
        # (we already handled this in apply_remote_updates_impl)
        local remote_uuid
        remote_uuid=$(get_remote_uuid_by_filename "$local_fn")
        [[ -n "$remote_uuid" ]] && continue

        local filepath="$output_dir/$local_fn"

        if [[ ! -f "$filepath" ]]; then
            del_cached "$uuid"
            continue
        fi

        if has_local_changes "$uuid" "$filepath"; then
            printf 'pull: SKIPPING delete "%s", local changes would be lost\n' \
                "$local_fn"
        else
            remove_file "$uuid" "$filepath"
            printf "pull: deleted \"%s\"\n" "$local_fn"
        fi
    done < "$state_file"
}

function get_deleted_uuids {
    awk -F'\t' '$5 != "" {print $1}' "$remote_state_file"
}

function get_active_uuids {
    awk -F'\t' '$5 == "" {print $1}' "$remote_state_file"
}

function get_remote_uuid_by_filename {
    local filename="$1"
    awk -F'\t' -v f="$filename" '$2 == f && $5 == "" {print $1; exit}' \
        "$remote_state_file"
}

function get_remote_filename {
    local uuid="$1"
    awk -F'\t' -v u="$uuid" '$1 == u {print $2; exit}' "$remote_state_file"
}

function add_remote_state {
    local uuid="$1"
    local filename="$2"
    local hash="$3"
    local version="$4"
    printf "%s\t%s\t%s\t%s\t\n" "$uuid" "$filename" "$hash" "$version" \
        >> "$remote_state_file"
}

function update_remote_state {
    local uuid="$1"
    local hash="$2"
    local version="$3"
    local filename="${4:-}"
    local tmp

    tmp=$(mktemp)
    awk \
        -F'\t' \
        -v u="$uuid" \
        -v f="$filename" \
        -v h="$hash" \
        -v ver="$version" \
        -v OFS='\t' '
            $1 == u {
                if (f != "") $2 = f
                $3 = h
                $4 = ver
                $5 = ""
            }
            { print }
        ' \
            "$remote_state_file" \
                > "$tmp"
    mv "$tmp" "$remote_state_file"
}

function del_remote_state {
    local uuid="$1"
    local tmp

    tmp=$(mktemp)
    awk \
        -F'\t' \
        -v u="$uuid" '
            $1 == u { next }
            { print }
        ' \
            "$remote_state_file" \
                > "$tmp"
    mv "$tmp" "$remote_state_file"
}

function update_sync_state {
    local uuid="$1"
    local filename="$2"
    local hash="$3"
    local tmp

    tmp=$(mktemp)
    if [[ -f "$state_file" ]]; then
        awk \
            -F'\t' \
            -v u="$uuid" \
            '
                $1 == u { next }
                { print }
            ' \
                "$state_file" \
                    > "$tmp"
    fi

    # after reconciliation, both remote_filename and local_filename are the same
    printf "%s\t%s\t%s\t%s\n" "$uuid" "$filename" "$filename" "$hash" >> "$tmp"
    mv "$tmp" "$state_file"
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
            { print $4; exit }
        ' \
            "$state_file"
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

function get_cached_local_filename {
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

function get_cached_remote_filename {
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

function get_cached_uuid {
    local file="$1"

    [[ ! -f "$state_file" ]] \
        && return

    awk \
        -F'\t' \
        -v f="$file" \
        '
            $3 != f { next }
            { print $1; exit }
        ' \
            "$state_file"
}

function get_remote_hash {
    local uuid="$1"
    awk -F'\t' -v u="$uuid" '$1 == u {print $3; exit}' "$remote_state_file"
}

function get_remote_version {
    local uuid="$1"
    awk -F'\t' -v u="$uuid" '$1 == u {print $4; exit}' "$remote_state_file"
}

function hash_file {
    local file="$1"

    shasum -a 256 "$file" | cut -d' ' -f1
}

function update_cached_hash {
    local uuid="$1"
    local hash="$2"

    [[ ! -f "$state_file" ]] \
        && return

    local tmp
    tmp=$(mktemp)

    awk \
        -F'\t' \
        -v u="$uuid" \
        -v h="$hash" \
        -v OFS='\t' \
        '
            $1 == u { $4 = h }
            { print }
        ' \
            "$state_file" \
                > "$tmp"
    mv "$tmp" "$state_file"
}

function rename_remote_file {
    local notebook="$1"
    local uuid="$2"
    local old_file="$3"
    local new_file="$4"

    local payload="{\"filename\": \"$new_file\"}"
    is_remote_deleted "$uuid" \
        && payload="{\"filename\": \"$new_file\", \"restore\": true}"

    local response
    response=$(
        curl -s -w "\n%{http_code}" \
            -X PATCH \
            -H "Authorization: Token $api_token" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"
    )

    local http_code body
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "409" ]]; then
        local error_msg
        error_msg=$(echo "$body" | jq -r '.error')
        printf 'push: ERROR cannot rename "%s": %s\n' "$new_file" "$error_msg"
        return 1
    fi

    if [[ "$http_code" != "200" ]]; then
        printf 'push: ERROR failed to rename "%s" (HTTP %s)\n' "$new_file" "$http_code"
        return 1
    fi

    local new_hash version
    new_hash=$(echo "$body" | jq -r '.content_hash')
    version=$(echo "$body" | jq -r '.version')

    update_remote_state "$uuid" "$new_hash" "$version" "$new_file"
    update_sync_state "$uuid" "$new_file" "$(get_cached_hash "$uuid")"

    printf 'push: renamed "%s" to "%s"\n' "$old_file" "$new_file"
}

function delete_remote_file {
    local notebook="$1"
    local uuid="$2"
    local filename had_changes http_code response

    filename=$(get_cached_local_filename "$uuid")
    had_changes=0
    has_remote_changes "$uuid" \
        && had_changes=1
    response=$(
        curl -s -w "\n%{http_code}" \
            -X DELETE \
            -H "Authorization: Token $api_token" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"
    )
    http_code=$(echo "$response" | tail -1)

    if [[ "$http_code" != "204" && "$http_code" != "404" ]]; then
        printf 'push: ERROR failed to delete "%s" (HTTP %s)\n' "$filename" "$http_code"
        return 1
    fi

    del_remote_state "$uuid"
    del_cached "$uuid"

    if [[ "$http_code" == "204" ]]; then
        if [[ $had_changes -eq 1 ]]; then
            printf 'push: deleted "%s" (had remote changes)\n' "$filename"
        else
            printf 'push: deleted "%s"\n' "$filename"
        fi
    fi
}

function create_remote_file {
    local notebook="$1"
    local file="$2"
    local filepath="$3"
    local old_uuid="${4:-}"
    local body error_msg http_code new_hash response uuid

    response=$(
        curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Authorization: Token $api_token" \
            -F "file=@$filepath" \
            -F "filename=$file" \
            "${base_url}/api/notebooks/${notebook}/"
    )
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "400" || "$http_code" == "409" ]]; then
        error_msg=$(echo "$body" | jq -r '.error')
        printf "push: ERROR cannot push \"%s\": %s\n" "$file" "$error_msg"
        return 2
    fi

    if [[ "$http_code" != "201" ]]; then
        printf "   %s failed to upload (HTTP %s)\n" "$file" "$http_code"
        return 1
    fi

    uuid=$(echo "$body" | jq -r '.uuid')
    new_hash=$(echo "$body" | jq -r '.content_hash')

    [[ -n "$old_uuid" ]] \
        && del_cached "$old_uuid"

    add_remote_state "$uuid" "$file" "$new_hash" "1"
    update_sync_state "$uuid" "$file" "$new_hash"

    printf 'push: "%s" (v1)\n' "$file"
}

function update_remote_file {
    local notebook="$1"
    local uuid="$2"
    local file="$3"
    local filepath="$4"
    local body cached_hash http_code mime_type new_hash previous_hash response version

    cached_hash=$(get_cached_hash "$uuid")
    mime_type=$(file --mime-type -b "$filepath")
    response=$(
        curl -s -w "\n%{http_code}" \
            -X PUT \
            -H "Authorization: Token $api_token" \
            -H "Content-Type: $mime_type" \
            --data-binary "@$filepath" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"
    )
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" != "200" ]]; then
        printf "   %s failed to upload (HTTP %s)\n" "$file" "$http_code"
        return 1
    fi

    previous_hash=$(echo "$body" | jq -r '.previous_hash')
    new_hash=$(echo "$body" | jq -r '.content_hash')
    version=$(echo "$body" | jq -r '.version')

    update_remote_state "$uuid" "$new_hash" "$version"
    update_sync_state "$uuid" "$file" "$new_hash"

    if [[ "$previous_hash" != "$cached_hash" ]]; then
        printf "push: \"%s\" (v%s, remote changes overwritten)\n" "$file" "$version"
    else
        printf "push: \"%s\" (v%s)\n" "$file" "$version"
    fi
}

function fetch_remote_to_local_path {
    local notebook="$1"
    local output_dir="$2"
    local uuid="$3"
    local local_file="$4"
    local hash="$5"
    local filepath="${output_dir}/${local_file}"

    mkdir -p "$(dirname "$filepath")"

    local tmp
    tmp=$(mktemp)

    curl \
        -s \
        -H "Authorization: Token $api_token" \
        -o "$tmp" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"

    mv "$tmp" "$filepath"
    update_cached_hash "$uuid" "$hash"
}

function local_file_was_removed {
    local filepath="$1"

    [[ ! -f "$filepath" ]]
}

function file_is_already_tracked {
    local file="$1"

    [[ ! -f "$state_file" ]] \
        && return 1

    awk \
        -F'\t' \
        -v f="$file" '
            $3 == f {found=1; exit} END {exit !found}
        ' \
            "$state_file"
}

function remote_has_identical_file {
    local file="$1"
    local filepath="$2"
    local remote_hash

    remote_hash=$(
        awk \
            -F'\t' \
            -v f="$file" '
                $2 == f {print $3; exit}
            ' \
                "$remote_state_file"
    )

    [[ -z "$remote_hash" ]] \
        && return 1
    [[ "$remote_hash" == "$(hash_file "$filepath")" ]]
}

function local_file_was_edited {
    local filepath="$1"
    local cached_hash="$2"

    [[ ! -f "$filepath" ]] \
        && return 1
    ! file_matches_hash "$filepath" "$cached_hash"
}

function file_matches_hash {
    local filepath="$1"
    local hash="$2"

    [[ ! -f "$filepath" ]] \
        && return 1

    [[ "$(hash_file "$filepath")" == "$hash" ]]
}

function is_untracked {
    local uuid="$1"

    [[ -z $(get_cached_local_filename "$uuid") ]]
}

function has_local_state {
    [[ -f "$state_file" ]]
}

function local_file_is_stale {
    local uuid="$1"
    local remote_filename

    remote_filename=$(get_remote_filename "$uuid")

    [[ -z "$remote_filename" ]]
}

function has_local_changes {
    local uuid="$1"
    local filepath="$2"

    [[ ! -f "$filepath" ]] \
        && return 1

    [[ "$(get_cached_hash "$uuid")" != "$(hash_file "$filepath")" ]]
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

function is_cached_uuid_stale {
    local cached_uuid="$1"
    local uuid="$2"

    [[ -n "$cached_uuid" ]] \
        && [[ "$cached_uuid" != "$uuid" ]] \
        && ! is_uuid_on_remote "$cached_uuid"
}

function is_uuid_on_remote {
    local uuid="$1"

    awk \
        -F'\t' \
        -v u="$uuid" '
            $1 == u {found=1; exit} END {exit !found}
        ' \
            "$remote_state_file"
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

function file_exists_with_different_case {
    local filepath="$1"
    local file="$2"

    local dir_path base_name actual_file
    dir_path=$(dirname "$filepath")
    base_name=$(basename "$file")

    actual_file=$(
        find "$dir_path" -maxdepth 1 -iname "$base_name" -print -quit 2>/dev/null
    )

    [[ -z "$actual_file" ]] \
        && return 1
    [[ "$(basename "$actual_file")" == "$base_name" ]] \
        && return 1
    return 0
}

function is_being_renamed {
    local uuid="$1"
    local file="$2"
    local cached_remote_file

    cached_remote_file=$(get_cached_remote_filename "$uuid")

    [[ -z "$cached_remote_file" ]] \
        && return 1
    [[ "$cached_remote_file" != "$file" ]]
}

function is_locally_renamed {
    local uuid="$1"
    local cached_local_file
    local cached_remote_file

    cached_local_file=$(get_cached_local_filename "$uuid")
    cached_remote_file=$(get_cached_remote_filename "$uuid")

    [[ -z "$cached_local_file" ]] \
        && return 1
    [[ -z "$cached_remote_file" ]] \
        && return 1
    [[ "$cached_local_file" != "$cached_remote_file" ]]
}

function exists_remotely_and_renamed_locally {
    local uuid="$1"

    is_uuid_on_remote "$uuid" && is_locally_renamed "$uuid"
}

function remote_file_was_renamed {
    local uuid="$1"
    local remote_filename
    local local_fn

    remote_filename=$(get_remote_filename "$uuid")
    local_fn=$(get_cached_local_filename "$uuid")

    [[ -z "$remote_filename" ]] \
        && return 1
    [[ "$remote_filename" != "$local_fn" ]]
}

function has_remote_changes {
    local uuid="$1"

    [[ "$(get_remote_hash "$uuid")" != "$(get_cached_hash "$uuid")" ]]
}

function destination_occupied {
    local filepath="$1"

    [[ -f "$filepath" ]]
}

function rename_file {
    local old_filepath="$1"
    local new_filepath="$2"

    mkdir -p "$(dirname "$new_filepath")"
    mv "$old_filepath" "$new_filepath"
    rmdir -p "$(dirname "$old_filepath")" 2>/dev/null \
        || true
}

function fetch_remote_file {
    local notebook="$1"
    local output_dir="$2"
    local uuid="$3"
    local file="$4"
    local hash="$5"
    local filepath="${output_dir}/${file}"
    local tmp

    tmp=$(mktemp)
    mkdir -p "$(dirname "$filepath")"

    curl \
        -s \
        -H "Authorization: Token $api_token" \
        -o "$tmp" \
            "${base_url}/api/notebooks/${notebook}/${uuid}"

    mv "$tmp" "$filepath"
    update_sync_state "$uuid" "$file" "$hash"
}

function deleted_locally_no_new_content {
    local uuid="$1"
    local file="$2"
    local filepath="$3"

    [[ -f "$filepath" ]] \
        && return 1

    ! is_untracked "$uuid" \
        && ! is_being_renamed "$uuid" "$file" \
        && ! is_locally_renamed "$uuid" \
        && ! has_remote_changes "$uuid"
}

function is_remote_deleted {
    local uuid="$1"
    awk -F'\t' -v u="$uuid" '$1 == u && $5 != "" {found=1; exit} END {exit !found}' \
        "$remote_state_file"
}

[[ "${BASH_SOURCE[0]}" != "$0" ]] || main "$@"

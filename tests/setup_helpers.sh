# Shared test helpers for sync algorithm tests
#
# The fixtures in tests/fixtures are copies of what is created in the database
# in seed_development.py, so editing just the files will not work.

# shellcheck shell=bash
declare fixtures output_dir BATS_FILE_TMPDIR

# shellcheck source=/dev/null
source tests/state-helpers.sh

function restore_database {
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \
    docker compose -p your5e-test exec -T db \
        psql -U your5e postgres >/dev/null 2>&1 <<-SQL
        SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity WHERE datname = 'your5e_test';
        DROP DATABASE IF EXISTS your5e_test;
        CREATE DATABASE your5e_test WITH TEMPLATE your5e_seed;
	SQL
}

function setup_pages_file {
    curl -s -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/" \
        | jq -r '
            .results[]
            | [.filename, .uuid, .content_hash, (.deleted_at // "")]
            | @tsv' \
        > "$BATS_FILE_TMPDIR/pages"
}

function uuid_for {
    grep "^$1"$'\t' "$BATS_FILE_TMPDIR/pages" | cut -f2
}

function init_synced_dir {
    # create directory as if it was already synced
    cp -r "$fixtures/campaign-notes" "$output_dir"
    # cache format: uuid server_filename local_filename server_hash local_hash
    # after a sync, both filenames are the same, both hashes are the same
    awk -F'\t' '$4 == "" {print $2"\t"$1"\t"$1"\t"$3"\t"$3}' "$BATS_FILE_TMPDIR/pages" \
        > "$output_dir/.sync-state"
    state_file="$output_dir/.sync-state"
}

function set_cached_state {
    local uuid="$1" filename="$2" content="$3"
    local hash
    hash=$(printf '%s\n' "$content" | shasum -a 256 | cut -d' ' -f1)

    # remove existing file for this UUID if different
    local old_file
    old_file=$(get_sync_state "$uuid" local_filename)
    [[ -n "$old_file" && "$old_file" != "$filename" ]] && rm -f "$output_dir/$old_file"

    # create file with content
    mkdir -p "$(dirname "$output_dir/$filename")"
    printf "%s\n" "$content" > "$output_dir/$filename"

    # update cache (both filenames same, both hashes same after reconciliation)
    update_sync_state "$uuid" "$filename" "$filename" "$hash" "$hash"
}

function untrack_file {
    local filename="$1"
    local uuid
    uuid=$(get_sync_state "$filename" uuid)
    [[ -n "$uuid" ]] && update_sync_state -d "$uuid"
}

function untrack_and_remove_file {
    local filename="$1"
    untrack_file "$filename"
    rm -rf "${output_dir:?}/$filename"
}

function tracked_delete {
    local filename="$1"
    rm "$output_dir/$filename"

    # set local_filename to '.' to mark as aware deletion
    local uuid
    uuid=$(get_sync_state "$filename" uuid)
    update_sync_state "$uuid" "" "."
}

function tracked_rename {
    local from="$1" to="$2"

    mkdir -p "$(dirname "$output_dir/$to")"
    mv "$output_dir/$from" "$output_dir/$to"
    rmdir -p "$(dirname "$output_dir/$from")" 2>/dev/null || true

    # update only local_filename, server_filename stays unchanged
    local uuid
    uuid=$(get_sync_state "$from" uuid)
    update_sync_state "$uuid" "" "$to"
}

function move_file {
    local from="$1" to="$2"

    mkdir -p "$(dirname "$output_dir/$to")"
    mv "$output_dir/$from" "$output_dir/$to"
    rmdir -p "$(dirname "$output_dir/$from")" 2>/dev/null || true
}

function modify_file {
    local content="${2:-modified local content}"
    printf '%s\n' "$content" > "$output_dir/$1"
}

function mergeable_orc {
    sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Orc

        Large and aggressive.
	EOF
}

function mergeable_troll {
    sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Troll

        Regenerates health.
	EOF
}

function merged_orc_troll {
    sed -e 's/^        //' <<-'EOF'
        # Bestiary

        Creatures encountered.

        ## Goblin

        Small and cunning.

        ## Orc

        Large and aggressive.

        ## Troll

        Regenerates health.
	EOF
}

function mark_file_stale {
    local filename="$1"
    local old_uuid server_fn local_fn hash local_hash

    old_uuid=$(get_sync_state "$filename" uuid)
    server_fn=$(get_sync_state "$old_uuid" server_filename)
    local_fn=$(get_sync_state "$old_uuid" local_filename)
    hash=$(get_sync_state "$old_uuid" hash)
    local_hash=$(get_sync_state "$old_uuid" local_hash)

    update_sync_state -d "$old_uuid"
    update_sync_state \
        "stale-uuid-$RANDOM" "$server_fn" "$local_fn" "$hash" "$local_hash"
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

function set_base_hash {
    local filename="$1"
    local hash="$2"
    local uuid
    uuid=$(get_sync_state "$filename" uuid)
    update_sync_state "$uuid" "" "" "$hash"
}

function assert_not_in_state {
    ! grep "$1" "$output_dir/.sync-state" || false
}

function assert_in_state {
    grep -q "$1" "$output_dir/.sync-state"
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
    local uuid="$1"
    local filename="$2"
    local state_file="$output_dir/.sync-state"

    [[ ! -f "$output_dir/$filename" ]]
    awk \
        -F'\t' \
        -v u="$uuid" \
        '
            $1 == u {found=1; exit}
            END {exit !found}
        ' \
            "$state_file"
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

function assert_uuid_local_filename {
    local uuid="$1"
    local expected_filename="$2"
    local actual_filename

    actual_filename=$(get_sync_state "$uuid" local_filename)
    [[ "$actual_filename" == "$expected_filename" ]]
}

function assert_uuid_remote_filename {
    local uuid="$1"
    local expected_filename="$2"
    local actual_filename

    actual_filename=$(get_sync_state "$uuid" server_filename)
    [[ "$actual_filename" == "$expected_filename" ]]
}

function assert_tracked_file_intact {
    local filename="$1"

    [[ -f "$output_dir/$filename" ]]

    local uuid cached_hash
    uuid=$(get_sync_state "$filename" uuid)
    cached_hash=$(get_sync_state "$uuid" hash)
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

function assert_file_modified {
    local filename="$1"
    diff -u <(echo "modified local content") "$output_dir/$filename"
}

function assert_server_edited_content {
    local filename="$1"
    local content="${2:-server edited content}"
    diff -u <(echo "$content") "$output_dir/$filename"
}

function assert_file_content {
    local filename="$1"
    local content="$2"
    diff -u <(printf '%s' "$content") "$output_dir/$filename"
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

function assert_timestamp_in_range {
    local timestamp="$1"
    local before="$2"
    local after="$3"

    [[ $timestamp -ge $before && $timestamp -le $after ]]
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
    diff -u <(echo "$expected") <(
        awk -F'\t' '
            $1 != "LAST_UPDATED" && $1 != "LAST_FULL_SYNC" {
                print $3 "\t" $4
            }
        ' "$output_dir/.sync-state" | sort
    )
}

function assert_fixture_files_in_state {
    while IFS= read -r -d '' file; do
        local relative="${file#"$fixtures"/campaign-notes/}"
        local expected_hash
        expected_hash=$(shasum -a 256 "$file" | cut -d' ' -f1)
        local actual_hash
        actual_hash=$(
            awk \
                -F'\t' \
                -v f="$relative" \
                '
                    $3 == f {print $4; exit}
                ' \
                    "$output_dir/.sync-state"
        )
        [[ "$actual_hash" == "$expected_hash" ]]
    done < <(find "$fixtures/campaign-notes" -type f -print0)
}

function assert_dir_matches_fixture {
    diff -ru \
        --exclude=".sync-state" \
        "$output_dir" "$fixtures/campaign-notes"
}

# shellcheck disable=SC2119
function assert_fixture_files_downloaded {
    assert_fixtures_intact_except
}

# shellcheck disable=SC2119
function assert_fixtures_intact {
    assert_fixtures_intact_except
}

# shellcheck disable=SC2120
function assert_fixtures_intact_except {
    local -a excluded=("$@")
    while IFS= read -r -d '' file; do
        local rel="${file#"$fixtures"/campaign-notes/}"
        for exc in "${excluded[@]}"; do
            [[ "$rel" == "$exc" ]] && continue 2
        done
        assert_tracked_file_matches_fixture "$rel"
    done < <(find "$fixtures/campaign-notes" -type f -print0)
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

function assert_output_dir_exists {
    [[ -d "$output_dir" ]]
}

function assert_state_has_no_files {
    [[ -f "$output_dir/.sync-state" ]]
    local file_count
    file_count=$(
        awk -F'\t' '
            $1 != "LAST_UPDATED" && $1 != "LAST_FULL_SYNC" {print}
        ' "$output_dir/.sync-state" | wc -l
    )
    [[ $file_count -eq 0 ]]
}

function fail_on_multiple_curl_calls {
    # shellcheck disable=SC2317,SC2329  # invoked indirectly via export -f
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

function fail_on_single_listing_call {
    # shellcheck disable=SC2317,SC2329  # invoked indirectly via export -f
    curl() {
        local marker="${BATS_TEST_TMPDIR}/.listing_count"
        local is_listing=0

        if [[ "$*" == *"-X GET"* ]] || [[ "$*" != *"-X "* ]]; then
            if [[ "$*" == *"/v1/notebooks/"*"/" ]] \
                    && [[ "$*" != *"/v1/notebooks/"*"/"*"/" ]]; then
                is_listing=1
            fi
        fi

        if [[ "$is_listing" -eq 1 ]]; then
            # check since= not used
            if [[ "$*" == *"since="* ]]; then
                echo "TEST GUARD: since parameter forbidden but was passed" >&2
                return 1
            fi
            echo "1" >> "$marker"
        else
            # check pagination happened
            if [[ -f "$marker" ]]; then
                local count
                count=$(wc -l < "$marker" | tr -d ' ')
                if [[ "$count" -eq 1 ]]; then
                    echo "TEST GUARD: expected multiple listing calls, got 1" >&2
                    return 1
                fi
            fi
        fi
        command curl "$@"
    }
    export -f curl
}

function fail_on_missing_since_parameter {
    # shellcheck disable=SC2317,SC2329  # invoked indirectly via export -f
    curl() {
        if [[ "$*" == *"-X GET"* ]] || [[ "$*" != *"-X "* ]]; then
            if [[ "$*" == *"/v1/notebooks/"*"/" ]] \
                    && [[ "$*" != *"/v1/notebooks/"*"/"*"/" ]] \
                    && [[ "$*" != *"since="* ]]; then
                echo "TEST GUARD: since parameter required but not passed" >&2
                return 1
            fi
        fi
        command curl "$@"
    }
    export -f curl
}

function fail_on_since_parameter {
    # shellcheck disable=SC2317,SC2329  # invoked indirectly via export -f
    curl() {
        if [[ "$*" == *"since="* ]]; then
            echo "TEST GUARD: since parameter forbidden but was passed" >&2
            return 1
        fi
        command curl "$@"
    }
    export -f curl
}

function fail_when_results_not {
    export EXPECTED_RESULTS="$1"
    # shellcheck disable=SC2317,SC2329  # invoked indirectly via export -f
    curl() {
        local response
        response=$(command curl "$@")
        if [[ "$*" == *"/v1/notebooks/"*"?"*"since="* ]]; then
            local total
            total=$(echo "$response" | sed '$d' | jq -r '.total_results')
            if [[ "$total" != "$EXPECTED_RESULTS" ]]; then
                printf "TEST GUARD: since= query returned %s results, " "$total" >&2
                echo "expected $EXPECTED_RESULTS" >&2
                return 1
            fi
        fi
        echo "$response"
    }
    export -f curl
}

function setup_recent_sync_metadata {
    local last_update
    last_update=$(cat "$BATS_TEST_DIRNAME/last_update")
    awk -F'\t' -v OFS='\t' '
        $1 != "LAST_UPDATED" && $1 != "LAST_FULL_SYNC"
    ' "$output_dir/.sync-state" > "$output_dir/.sync-state.tmp" || true
    printf "LAST_UPDATED\t%s\t\t\t\n" "$last_update" >> "$output_dir/.sync-state.tmp"
    local now_iso
    now_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf "LAST_FULL_SYNC\t%s\t\t\t\n" "$now_iso" >> "$output_dir/.sync-state.tmp"
    mv "$output_dir/.sync-state.tmp" "$output_dir/.sync-state"
}

function setup_old_sync_metadata {
    local state="$output_dir/.sync-state"
    awk -F'\t' -v OFS='\t' '
        $1 != "LAST_UPDATED" && $1 != "LAST_FULL_SYNC"
    ' "$state" > "$state.tmp" || true
    printf "LAST_UPDATED\t2020-01-01T00:00:00Z\t\t\t\n" >> "$state.tmp"
    printf "LAST_FULL_SYNC\t2020-01-01T00:00:00Z\t\t\t\n" >> "$state.tmp"
    mv "$state.tmp" "$state"
}

function force_full_sync {
    update_sync_state "LAST_FULL_SYNC" "2020-01-01T00:00:00Z" "" "" ""
}

function assert_last_updated_matches_expected {
    local timestamp expected state="$output_dir/.sync-state"
    timestamp=$(awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state")
    [[ -n "$timestamp" ]]
    expected=$(cat "$BATS_TEST_DIRNAME/last_update")
    diff -u <(echo "$expected") <(echo "$timestamp")
}

function assert_last_updated_exists {
    local timestamp state="$output_dir/.sync-state"
    timestamp=$(awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state")
    [[ "$timestamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$ ]]  # noqa
}

function assert_last_updated_not_set {
    local timestamp state="$output_dir/.sync-state"
    [[ ! -f "$state" ]] && return 0
    timestamp=$(awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state")
    [[ -z "$timestamp" ]]
}

function assert_last_updated_is_epoch {
    local timestamp expected state="$output_dir/.sync-state"
    timestamp=$(awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state")
    [[ -n "$timestamp" ]]
    expected="0001-01-01T00:00:00.000000Z"
    diff -u <(echo "$expected") <(echo "$timestamp")
}

function assert_sync_metadata_updated {
    local last_updated last_full_sync state="$output_dir/.sync-state"
    last_updated=$(
        awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state"
    )
    [[ -n "$last_updated" ]]
    [[ "$last_updated" != "2020-01-01T00:00:00Z" ]]

    last_full_sync=$(
        awk -F'\t' '$1 == "LAST_FULL_SYNC" {print $2; exit}' "$state"
    )
    [[ -n "$last_full_sync" ]]

    local now last_full_sync_epoch age_seconds
    now=$(date +%s)
    last_full_sync_epoch=$(
        TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_full_sync" +%s 2>/dev/null \
            || date -d "$last_full_sync" +%s 2>/dev/null
    )
    age_seconds=$((now - last_full_sync_epoch))
    [[ $age_seconds -lt 60 ]]
}

function assert_last_updated_unchanged {
    local expected timestamp state="$output_dir/.sync-state"
    expected=$(cat "$BATS_TEST_DIRNAME/last_update")
    timestamp=$(awk -F'\t' '$1 == "LAST_UPDATED" {print $2; exit}' "$state")
    [[ "$timestamp" == "$expected" ]]
}

function assert_file_pushed {
    local filename="$1"
    local expected_content_type="$2"
    local actual_hash body cached_hash headers response uuid

    uuid=$(get_sync_state "$filename" uuid)
    [[ -n "$uuid" ]]

    cached_hash=$(get_sync_state "$uuid" hash)
    actual_hash=$(shasum -a 256 "$output_dir/$filename" | cut -d' ' -f1)
    [[ "$actual_hash" == "$cached_hash" ]]

    response=$(curl -s -i \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/$uuid")
    headers=$(echo "$response" | sed '/^\r$/q' | tr -d '\r')
    body=$(echo "$response" | sed '1,/^\r$/d')

    diff -u "$output_dir/$filename" <(echo "$body")

    if [[ -n "$expected_content_type" ]]; then
        local actual_content_type
        actual_content_type=$(
            echo "$headers" \
                | grep -i '^content-type:' \
                | cut -d' ' -f2
        )
        diff -u <(echo "$expected_content_type") <(echo "$actual_content_type")
    fi
}

function assert_server_file_deleted {
    local filename="$1"

    local response
    response=$(curl -s \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/" \
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

function invalidate_token {
    local token="$1"
    local token_key="${token:0:15}"
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \
    docker compose -p your5e-test exec -T db \
        psql -U your5e your5e_test \
        -c "DELETE FROM users_authtoken WHERE token_key = '$token_key'" \
        >/dev/null 2>&1
}

function downgrade_to_viewer {
    local username="$1" notebook_owner="$2" notebook_slug="$3"
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \
    docker compose -p your5e-test exec -T db \
        psql -U your5e your5e_test \
        -c "UPDATE notebooks_notebookpermission SET role = 'viewer'
            FROM users_user u, notebooks_notebook n
            WHERE notebooks_notebookpermission.user_id = u.id
            AND notebooks_notebookpermission.notebook_id = n.wiki_ptr_id
            AND u.username = '$username'
            AND n.owner_id = (
                SELECT id FROM users_user WHERE username = '$notebook_owner')
            AND n.slug = '$notebook_slug'" \
        >/dev/null 2>&1
}

function delete_page_by_uuid {
    local page_uuid="$1"
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \
    docker compose -p your5e-test exec -T db \
        psql -U your5e your5e_test \
        -c "UPDATE wikis_page SET deleted_at = NOW()
            WHERE uuid = '$page_uuid'" \
        >/dev/null 2>&1
}

function remove_file {
    rm "$output_dir/$1"
}

function server_edit_content {
    local uuid="$1"
    local content="${2:-server edited content}"

    curl -s -X PUT \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        -H "Content-Type: text/markdown" \
        -d "$content" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/$uuid" \
        >/dev/null
}

function server_rename {
    local uuid="$1"
    local to="$2"

    curl -s -X PATCH \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"filename\": \"$to\"}" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/$uuid" \
        >/dev/null
}

function server_delete {
    local filename="$1"
    local uuid
    uuid=$(grep "^$filename"$'\t' "$BATS_FILE_TMPDIR/pages" | cut -f2)

    curl -s -X DELETE \
        -H "Authorization: Token $YOUR5E_API_TOKEN" \
        "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/$uuid" \
        >/dev/null
}

function server_purge {
    local uuid="$1"

    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \
    docker compose -p your5e-test exec -T db \
        psql -U your5e your5e_test >/dev/null 2>&1 <<-SQL
        DELETE FROM wikis_version WHERE page_id = (
            SELECT id FROM wikis_page WHERE uuid = '$uuid'
        );
        DELETE FROM wikis_page WHERE uuid = '$uuid';
	SQL
}

function server_create {
    local filename="$1"
    local content="${2:-# $(basename "$filename" .md)}"
    local response

    response=$(
        curl -s -X POST \
            -H "Authorization: Token $YOUR5E_API_TOKEN" \
            -F "file=@-;filename=$filename" \
            "$YOUR5E_API_BASE/v1/notebooks/norm/campaign-notes/" \
            <<< "$content"
    )
    echo "$response" | jq -r '.uuid'
}

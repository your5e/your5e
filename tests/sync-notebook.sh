#!/usr/bin/env -S bash -euo pipefail

api_token="${YOUR5E_API_TOKEN:-}"
base_url="${YOUR5E_API_BASE:-http://localhost:5843}"

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

    download_notebook "$@"
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

function download_notebook {
    local notebook="$1"
    local output_dir="$2"
    local next_page="${base_url}/api/notebooks/${notebook}/"
    local filename response

    local tmpfile="$(mktemp)"
    trap "rm -f '$tmpfile'" EXIT

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
                    | [.uuid, .filename]
                    | @tsv
                '
        )

        mapfile -t deleted < <(
            echo "$response" \
                | jq -r '
                    .results[]
                    | select(.deleted_at != null)
                    | .filename
                '
        )

        for file in "${deleted[@]}"; do
            [[ -z "$file" ]] && continue
            filename="${output_dir}/${file}"
            if [[ -f "$filename" ]]; then
                rm "$filename"
                printf -- "-- %s\n" "$file"
            fi
        done

        for page in "${pages[@]}"; do
            IFS=$'\t' read -r uuid file <<< "$page"

            filename="${output_dir}/${file}"
            mkdir -p "$(dirname "$filename")"

            [[ -t 1 ]] \
                && printf "\033[2K%s\r" "$file"

            curl \
                -s \
                -H "Authorization: Token $api_token" \
                -o "$tmpfile" \
                    "${base_url}/api/notebooks/${notebook}/${uuid}"

            if ! cmp -s "$tmpfile" "$filename"; then
                mv "$tmpfile" "$filename"
                printf "++ %s\n" "$file"
            fi
        done
    done

    [[ -t 1 ]] \
        && printf "\033[2K"

    exit 0
}

main "$@"

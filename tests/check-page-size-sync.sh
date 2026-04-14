#!/usr/bin/env -S bash -euo pipefail

# Extract PAGE_SIZE from Django view
django_page_size=$(sed -n 's/^PAGE_SIZE = //p' api/notebooks/views.py)

# Extract PAGE_SIZE from TypeScript test
ts_page_size=$(sed -n 's/^const PAGE_SIZE = \(.*\);.*/\1/p' \
    obsidian-plugin/tests/sync-pagination.test.ts)

if [[ -z "$django_page_size" ]]; then
    echo "ERROR: Could not find PAGE_SIZE in api/notebooks/views.py"
    exit 1
fi

if [[ -z "$ts_page_size" ]]; then
    echo "ERROR: Could not find PAGE_SIZE in obsidian-plugin/tests/pagination.test.ts"
    exit 1
fi

if [[ "$django_page_size" != "$ts_page_size" ]]; then
    echo "ERROR: PAGE_SIZE mismatch!"
    echo "  api/notebooks/views.py:                      $django_page_size"
    echo "  obsidian-plugin/tests/pagination.test.ts:    $ts_page_size"
    exit 1
fi

exit 0

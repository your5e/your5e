bats_require_minimum_version 1.7.0

setup() {
    export YOUR5E_API_TOKEN="dummy"
    export YOUR5E_API_BASE="http://localhost"
    source "$BATS_TEST_DIRNAME/sync-notebook.sh"
    cp "tests/merge/inputs/base.md" "$BATS_TEST_TMPDIR/base.md"
}

@test "unchanged-unchanged" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-append-wyvern" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-prepend-banshee" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-insert-naga" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-edit-orc" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-delete-goblin" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-delete-orc" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "unchanged-all-fey" {
    
    cp "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/unchanged-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-unchanged" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-append-wyvern" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-prepend-banshee" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-insert-naga" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-edit-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-delete-goblin" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-delete-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "append-zombie-all-fey" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/append-zombie.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/append-zombie-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-unchanged" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-append-wyvern" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-prepend-banshee" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-insert-naga" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-edit-orc" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-delete-goblin" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-delete-orc" {
    
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-goblin-to-gargoyle" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "prepend-aboleth-all-fey" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/prepend-aboleth.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/prepend-aboleth-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-unchanged" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-append-wyvern" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-prepend-banshee" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-insert-naga" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-edit-orc" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-delete-goblin" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-delete-orc" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "insert-ogre-all-fey" {
    
    cp "tests/merge/inputs/insert-ogre.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/insert-ogre-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-unchanged" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-append-wyvern" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-prepend-banshee" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-insert-naga" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-edit-orc" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-delete-goblin" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-delete-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-goblin-sneaky-all-fey" {
    
    cp "tests/merge/inputs/edit-goblin-sneaky.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-goblin-sneaky-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-unchanged" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-append-wyvern" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-prepend-banshee" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-insert-naga" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-edit-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-delete-goblin" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-delete-orc" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "edit-orc-all-fey" {
    
    cp "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/edit-orc-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-unchanged" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-append-wyvern" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-prepend-banshee" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-insert-naga" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-edit-orc" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-delete-goblin" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-delete-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-goblin-all-fey" {
    
    cp "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-goblin-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-unchanged" {
    
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-append-wyvern" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-prepend-banshee" {
    
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-insert-naga" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-edit-goblin-stupid" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-edit-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-delete-goblin" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-delete-orc" {
    
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-goblin-to-gargoyle" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "delete-orc-all-fey" {
    
    cp "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/delete-orc-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-unchanged" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-append-wyvern" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-prepend-banshee" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-insert-naga" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-edit-orc" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-delete-goblin" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-delete-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "goblin-to-ghoul-all-fey" {
    
    cp "tests/merge/inputs/goblin-to-ghoul.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/goblin-to-ghoul-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-unchanged" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-unchanged.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-append-wyvern" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-append-wyvern.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-prepend-banshee" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-prepend-banshee.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-insert-naga" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-insert-naga.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-edit-goblin-stupid" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-edit-goblin-stupid.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-edit-orc" {
    skip 'git cannot merge'
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-edit-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-delete-goblin" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-delete-goblin.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-delete-orc" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-delete-orc.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-goblin-to-gargoyle" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-goblin-to-gargoyle.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

@test "all-dragons-all-fey" {
    
    cp "tests/merge/inputs/all-dragons.md" \
        "$BATS_TEST_TMPDIR/client.md"

    run three_way_merge \
        "$BATS_TEST_TMPDIR/base.md" \
        "tests/merge/inputs/all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"

    diff -u \
        "tests/merge/expected/all-dragons-all-fey.md" \
        "$BATS_TEST_TMPDIR/client.md"
}

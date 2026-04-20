import * as fs from "node:fs/promises";
import * as path from "node:path";
import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import type { SyncStateEntry } from "../src/sync/types.js";
import {
    API_BASE,
    addStaleFile,
    assertDirMatchesFixture,
    assertEmptyDirRemoved,
    assertFileIgnored,
    assertFileInState,
    assertFileMatchesFixture,
    assertFileModified,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertInState,
    assertIncrementalResults,
    assertNotInState,
    assertServerEditedContent,
    assertStateMatchesFixture,
    assertSyncMetadataUpdated,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
    assertTrackedFileNotRestored,
    cleanupTestDir,
    clearPagesCache,
    createFile,
    createTestDir,
    deleteTrackedFile,
    getExpectedLastUpdate,
    getToken,
    initSyncedDir,
    markFileStale,
    modifyFile,
    renameLocalFile,
    renameLocalFileUntracked,
    restoreDatabase,
    serverCreate,
    serverDelete,
    serverEditContent,
    serverRename,
    setBaseHash,
    untrackAndRemoveFile,
    untrackFile,
    uuidFor,
} from "./helpers.js";

describe("subsequent sync pull", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let initialState: Map<string, SyncStateEntry>;
    let recentTimestamp: string;
    let lastUpdate: string;

    beforeAll(async () => {
        token = await getToken();
    });

    beforeEach(async () => {
        restoreDatabase();
        clearPagesCache();
        ({ testDir, outputDir } = await createTestDir());
        initialState = await initSyncedDir(outputDir, token);
        recentTimestamp = new Date().toISOString();
        lastUpdate = await getExpectedLastUpdate();
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
        vi.restoreAllMocks();
    });

    function createSync(
        overrides: {
            lastFullSync?: string;
            pullOnly?: boolean;
        } = {},
    ): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
            pullOnly: overrides.pullOnly ?? true,
            lastUpdate,
            lastFullSync: overrides.lastFullSync ?? recentTimestamp,
        });
    }

    test("no change, outdated timestamp", async () => {
        const fetchSpy = vi.spyOn(global, "fetch");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        // Verify full sync (no ?since= parameter)
        const firstFetch = fetchSpy.mock.calls[0][0];
        expect(firstFetch).not.toContain("since=");

        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("no change, recent timestamp", async () => {
        const fetchSpy = vi.spyOn(global, "fetch");

        const sync = createSync();

        const result = await sync.run();

        // Verify incremental sync (with ?since= parameter, single call)
        expect(fetchSpy).toHaveBeenCalledTimes(1);
        const firstFetch = fetchSpy.mock.calls[0][0];
        const encodedLastUpdate = encodeURIComponent(lastUpdate);
        expect(firstFetch).toContain(`?since=${encodedLastUpdate}`);

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file", async () => {
        await createFile(outputDir, "scratchpad.txt");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileIgnored(outputDir, "scratchpad.txt", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited, directory", async () => {
        await serverCreate(token, "Rumours.md");
        await createFile(outputDir, "Rumours.md/notes.txt");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Rumours.md", blocked by local directory',
        ]);
        await assertFileIgnored(outputDir, "Rumours.md/notes.txt", result.state);
        await assertFileNotDownloaded(outputDir, "Rumours.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited", async () => {
        await serverCreate(token, "Quests.md");
        await createFile(outputDir, "Quests.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Quests.md", blocked by local file',
        ]);
        await assertFileUnchanged(outputDir, "Quests.md");
        assertFileNotInState("Quests.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, remote renamed", async () => {
        await createFile(outputDir, "npcs/Major.md");
        await serverRename(
            token,
            await uuidFor(initialState, "characters/NPCs.md"),
            "npcs/Major.md",
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot rename "characters/NPCs.md" to "npcs/Major.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "npcs/Major.md");
        assertFileNotInState("npcs/Major.md", result.state);
        await assertFileMatchesFixture(
            outputDir,
            "characters/NPCs.md",
            "characters/NPCs.md",
        );
        assertFileInState("characters/NPCs.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited, remote renamed", async () => {
        await createFile(outputDir, "Monsters.md");
        await serverRename(
            token,
            await uuidFor(initialState, "Bestiary.md"),
            "Monsters.md",
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Bestiary.md" to "Monsters.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Monsters.md");
        assertFileNotInState("Monsters.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote edited", async () => {
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "Bestiary.md" (v3)']);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed", async () => {
        await serverRename(
            token,
            await uuidFor(initialState, "The Old Café.md"),
            "The New Café.md",
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "The Old Café.md" to "The New Café.md"',
        ]);
        // biome-ignore format: line length
        await assertFileMatchesFixture(
            outputDir,
            "The Old Café.md",
            "The New Café.md",
        );
        assertFileInState("The New Café.md", result.state);
        assertFileNotInState("The Old Café.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, local edited, directory", async () => {
        await serverRename(
            token,
            await uuidFor(initialState, "sessions/session-01.md"),
            "logs/Session 01.md",
        );
        await createFile(outputDir, "logs/Session 01.md/notes.txt");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot rename "sessions/session-01.md" to ' +
                '"logs/Session 01.md", blocked by local directory',
        ]);
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertFileUnchanged(outputDir, "logs/Session 01.md/notes.txt");
        assertFileNotInState("logs/Session 01.md/notes.txt", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "Home.md");
        await serverRename(token, uuid, "Welcome.md");
        await serverEditContent(token, uuid);

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "Welcome.md"',
            'pull: "Welcome.md" (v4)',
        ]);
        await assertServerEditedContent(outputDir, "Welcome.md");
        assertFileInState("Welcome.md", result.state);
        assertFileNotInState("Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, swapped", async () => {
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        await serverRename(token, npcsUuid, "temp.md");
        await serverRename(token, sessionUuid, "characters/NPCs.md");
        await serverRename(token, npcsUuid, "sessions/session-01.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 2);
        expect(result.output).toEqual([
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
        ]);
        await assertFileMatchesFixture(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        await assertFileMatchesFixture(
            outputDir,
            "characters/NPCs.md",
            "sessions/session-01.md",
        );
        assertFileInState("sessions/session-01.md", result.state);
        assertFileInState("characters/NPCs.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain", async () => {
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        await serverRename(token, sessionUuid, "old.md");
        await serverRename(token, npcsUuid, "sessions/session-01.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 2);
        expect(result.output).toEqual([
            'pull: renamed "sessions/session-01.md" to "old.md"',
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "sessions/session-01.md", "old.md");
        await assertFileMatchesFixture(
            outputDir,
            "characters/NPCs.md",
            "sessions/session-01.md",
        );
        assertFileInState("old.md", result.state);
        assertFileInState("sessions/session-01.md", result.state);
        assertFileNotInState("characters/NPCs.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain reversed", async () => {
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        await serverRename(token, npcsUuid, "old.md");
        await serverRename(token, sessionUuid, "characters/NPCs.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 2);
        expect(result.output).toEqual([
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
            'pull: renamed "characters/NPCs.md" to "old.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "characters/NPCs.md", "old.md");
        await assertFileMatchesFixture(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        assertFileInState("old.md", result.state);
        assertFileInState("characters/NPCs.md", result.state);
        assertFileNotInState("sessions/session-01.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        const homeUuid = await uuidFor(initialState, "Home.md");
        const indexUuid = await uuidFor(initialState, "index.md");
        await serverRename(token, bestiaryUuid, "temp.md");
        await serverRename(token, homeUuid, "Bestiary.md");
        await serverRename(token, indexUuid, "Home.md");
        await serverRename(token, bestiaryUuid, "index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: renamed "index.md" to "Home.md"',
            'pull: renamed "Home.md" to "Bestiary.md"',
            'pull: renamed "Bestiary.md" to "index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        assertFileInState("index.md", result.state);
        assertFileInState("Home.md", result.state);
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle, local edited", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        const homeUuid = await uuidFor(initialState, "Home.md");
        const indexUuid = await uuidFor(initialState, "index.md");
        await serverRename(token, bestiaryUuid, "temp.md");
        await serverRename(token, homeUuid, "Bestiary.md");
        await serverRename(token, indexUuid, "Home.md");
        await serverRename(token, bestiaryUuid, "index.md");
        await modifyFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: ERROR cannot rename "index.md" to "Home.md", ' +
                "blocked by local file",
            'pull: SKIPPING rename "Home.md" to "Bestiary.md", ' +
                "local changes would be lost",
            'pull: ERROR cannot rename "Bestiary.md" to "index.md", ' +
                "blocked by local file",
        ]);
        await assertFileModified(outputDir, "Home.md");
        assertFileInState("Home.md", result.state);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFileMatchesFixture(outputDir, "index.md", "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle, untracked file", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        const homeUuid = await uuidFor(initialState, "Home.md");
        const indexUuid = await uuidFor(initialState, "index.md");
        await serverRename(token, bestiaryUuid, "temp.md");
        await serverRename(token, homeUuid, "Bestiary.md");
        await serverRename(token, indexUuid, "Home.md");
        await serverRename(token, bestiaryUuid, "index.md");
        untrackFile(initialState, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Bestiary.md", blocked by local file',
            'pull: ERROR cannot rename "index.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "Bestiary.md" to "index.md", ' +
                "blocked by local file",
        ]);
        await assertFileMatchesFixture(outputDir, "Home.md", "Home.md");
        assertFileNotInState("Home.md", result.state);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFileMatchesFixture(outputDir, "index.md", "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited", async () => {
        await modifyFile(outputDir, "index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, CRLF line endings", async () => {
        await createFile(
            outputDir,
            "Home.md",
            "First line\r\nSecond line\r\nThird line",
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        const homeContent = await fs.readFile(path.join(outputDir, "Home.md"), "utf-8");
        expect(homeContent).toBe("First line\r\nSecond line\r\nThird line");
        assertFileInState("Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited", async () => {
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));
        await modifyFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, same content", async () => {
        await serverEditContent(
            token,
            await uuidFor(initialState, "Bestiary.md"),
            "modified local content",
        );
        await modifyFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, no common ancestor", async () => {
        await modifyFile(outputDir, "index.md");
        await serverEditContent(token, await uuidFor(initialState, "index.md"));
        setBaseHash(initialState, "index.md", "no-common-ancestor");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote renamed", async () => {
        await modifyFile(outputDir, "Bestiary.md");
        await serverRename(
            token,
            await uuidFor(initialState, "Bestiary.md"),
            "renamed-bestiary.md",
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "Bestiary.md" to "renamed-bestiary.md", ' +
                "local changes would be lost",
        ]);
        await assertFileModified(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFileNotDownloaded(outputDir, "renamed-bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "Home.md");
        await serverRename(token, uuid, "Welcome.md");
        await serverEditContent(token, uuid);
        await modifyFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "Home.md" to "Welcome.md", ' +
                "local changes would be lost",
        ]);
        await assertFileModified(outputDir, "Home.md");
        assertFileInState("Home.md", result.state);
        await assertFileNotDownloaded(outputDir, "Welcome.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote deleted", async () => {
        await serverDelete(token, await uuidFor(initialState, "characters/NPCs.md"));

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: deleted "characters/NPCs.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "characters/NPCs.md");
        await assertEmptyDirRemoved(outputDir, "characters");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote deleted, local edited", async () => {
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));
        await modifyFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING delete "Bestiary.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

        // Incremental sync cannot detect stale files
        const incrementalSync = createSync();
        const incrementalResult = await incrementalSync.run();

        assertIncrementalResults(incrementalResult.incrementalResults, 0);
        expect(incrementalResult.output).toEqual([]);
        await assertFileUnchanged(outputDir, "my-notes.md");
        assertFileInState("my-notes.md", incrementalResult.state);

        // Full sync detects stale files by comparing against complete server state
        const fullSync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });
        const result = await fullSync.run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, remote edited", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await serverEditContent(token, uuid);

        // Incremental sync cannot detect stale file
        const incrementalSync = createSync();
        const incrementalResult = await incrementalSync.run();

        assertIncrementalResults(incrementalResult.incrementalResults, 1);
        expect(incrementalResult.output).toEqual([
            'pull: ERROR cannot pull "index.md", blocked by local file',
        ]);

        // Full sync detects stale file, removes it, downloads new file
        const fullSync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });
        const result = await fullSync.run();

        expect(result.output).toEqual(['pull: "index.md" (v2)']);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "my-notes.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "my-notes.md");
        assertFileInState("my-notes.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local deleted", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await deleteTrackedFile(outputDir, "my-notes.md");
        assertInState(initialState, "stale-uuid");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local deleted, remote edited", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");
        await serverEditContent(token, uuid);
        assertInState(initialState, "stale-uuid");

        // Incremental sync cannot detect stale entry
        const incrementalSync = createSync();
        const incrementalResult = await incrementalSync.run();

        assertIncrementalResults(incrementalResult.incrementalResults, 1);
        expect(incrementalResult.output).toEqual(['pull: "index.md" (v2)']);
        assertInState(incrementalResult.state, "stale-uuid");
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", incrementalResult.state);

        // Reset conditions
        restoreDatabase();
        clearPagesCache();
        await fs.rm(outputDir, { recursive: true });
        await fs.mkdir(outputDir, { recursive: true });
        const freshState = await initSyncedDir(outputDir, token);
        const freshUuid = await uuidFor(freshState, "index.md");
        markFileStale(freshState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");
        await serverEditContent(token, freshUuid);
        const freshLastUpdate = await getExpectedLastUpdate();

        // Full sync detects stale entry by comparing against complete server state
        const fullSync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState: freshState,
            pullOnly: true,
            lastUpdate: freshLastUpdate,
            lastFullSync: "2020-01-01T00:00:00Z",
        });
        const result = await fullSync.run();

        expect(result.output).toEqual(['pull: "index.md" (v2)']);
        assertNotInState(result.state, "stale-uuid");
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted", async () => {
        await deleteTrackedFile(outputDir, "index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", already deleted locally',
        ]);
        await assertTrackedFileNotRestored(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote edited", async () => {
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));
        await deleteTrackedFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "Bestiary.md" (v3, revivified)']);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote renamed", async () => {
        await serverRename(
            token,
            await uuidFor(initialState, "characters/NPCs.md"),
            "NPCs.md",
        );
        await deleteTrackedFile(outputDir, "characters/NPCs.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "characters/NPCs.md" to "NPCs.md", ' +
                '"characters/NPCs.md" deleted locally',
        ]);
        await assertTrackedFileNotRestored(
            outputDir,
            result.state,
            "characters/NPCs.md",
        );
        await assertFileNotDownloaded(outputDir, "NPCs.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "Home.md");
        await serverRename(token, uuid, "Welcome.md");
        await serverEditContent(token, uuid);
        await deleteTrackedFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "Welcome.md"',
            'pull: "Welcome.md" (v4, revivified)',
        ]);
        await assertServerEditedContent(outputDir, "Welcome.md");
        assertFileInState("Welcome.md", result.state);
        assertFileNotInState("Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, local edited, remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "Home.md");
        await serverRename(token, uuid, "Welcome.md");
        await serverEditContent(token, uuid);
        await deleteTrackedFile(outputDir, "Home.md");
        await createFile(outputDir, "Welcome.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Home.md" to "Welcome.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Welcome.md");
        assertFileNotInState("Welcome.md", result.state);
        assertFileInState("Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote deleted", async () => {
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));
        await deleteTrackedFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: deleted "Bestiary.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote edited", async () => {
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await serverEditContent(
            token,
            await uuidFor(initialState, "renamed-bestiary.md"),
        );

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v3)',
        ]);
        await assertServerEditedContent(outputDir, "renamed-bestiary.md");
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote edited", async () => {
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await serverEditContent(
            token,
            await uuidFor(initialState, "renamed-bestiary.md"),
        );
        await modifyFile(outputDir, "renamed-bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md" to "renamed-bestiary.md", ' +
                "local changes would be lost",
        ]);
        await assertFileModified(outputDir, "renamed-bestiary.md");
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote renamed", async () => {
        await serverRename(
            token,
            await uuidFor(initialState, "index.md"),
            "server-index.md",
        );
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "index.md" to "server-index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("server-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote renamed", async () => {
        await serverRename(
            token,
            await uuidFor(initialState, "index.md"),
            "server-index.md",
        );
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "index.md" to "server-index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileModified(outputDir, "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("server-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        await serverRename(token, uuid, "server-index.md");
        await serverEditContent(token, uuid);
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "index.md" to "server-index.md", ' +
                'already "my-index.md" locally',
            'pull: "server-index.md" to "my-index.md" (v3)',
        ]);
        await assertServerEditedContent(outputDir, "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("server-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        await serverRename(token, uuid, "server-index.md");
        await serverEditContent(token, uuid);
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING rename "index.md" to "server-index.md", ' +
                'already "my-index.md" locally',
            'pull: SKIPPING pull "server-index.md" to "my-index.md", ' +
                "local changes would be lost",
        ]);
        await assertFileModified(outputDir, "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("server-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote deleted", async () => {
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: deleted "Bestiary.md" (was "my-bestiary.md")',
        ]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-bestiary.md");
        assertFileNotInState("Bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote deleted", async () => {
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await modifyFile(outputDir, "my-bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: SKIPPING delete "Bestiary.md" (at "my-bestiary.md"), ' +
                "local changes would be lost",
        ]);
        await assertFileModified(outputDir, "my-bestiary.md");
        assertFileInState("my-bestiary.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "my-notes.md", local changes would be lost',
        ]);
        await assertFileModified(outputDir, "my-notes.md");
        assertFileInState("my-notes.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash match", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'info: detected rename "index.md" to "renamed-index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash mismatch", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", already deleted locally',
        ]);
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileNotInState("renamed-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash mismatch, remote edited", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");
        await serverEditContent(token, await uuidFor(initialState, "index.md"));

        const sync = createSync();

        const result = await sync.run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: "index.md" (v2, revivified)',
        ]);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileNotInState("renamed-index.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });
});

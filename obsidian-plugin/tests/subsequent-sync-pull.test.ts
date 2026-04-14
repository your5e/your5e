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
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertNotInState,
    assertStateMatchesFixture,
    assertSyncMetadataUpdated,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
    assertTrackedFileMatchesFixture,
    assertTrackedFileNotRestored,
    cleanupTestDir,
    clearPagesCache,
    createFile,
    createTestDir,
    deleteTrackedFile,
    fileTracksDeletedRemote,
    getToken,
    initSyncedDir,
    markFileStale,
    modifyFile,
    renameLocalFile,
    renameLocalFileUntracked,
    restoreDatabase,
    setOlderContent,
    setOlderFilename,
    untrackAndRemoveFile,
    untrackFile,
} from "./helpers.js";

describe("subsequent sync pull", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let initialState: Map<string, SyncStateEntry>;
    let recentTimestamp: string;

    beforeAll(async () => {
        token = await getToken();
        restoreDatabase();
        clearPagesCache();
    });

    beforeEach(async () => {
        ({ testDir, outputDir } = await createTestDir());
        initialState = await initSyncedDir(outputDir, token);
        recentTimestamp = new Date().toISOString();
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
        vi.restoreAllMocks();
    });

    function createSync(
        overrides: {
            lastFullSync?: string;
        } = {},
    ): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
            pullOnly: true,
            lastUpdate: "2020-01-01T00:00:00Z",
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
        expect(firstFetch).toContain("?since=2020-01-01T00%3A00%3A00Z");

        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file", async () => {
        await createFile(outputDir, "scratchpad.txt");

        const sync = createSync();

        const result = await sync.run();

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
        await untrackAndRemoveFile(outputDir, initialState, "Bestiary.md");
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Bestiary.md", blocked by local directory',
        ]);
        await assertFileIgnored(outputDir, "Bestiary.md/notes.txt", result.state);
        await assertFileNotDownloaded(outputDir, "Bestiary.md", result.state);
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

    test("untracked file, local edited", async () => {
        untrackFile(initialState, "Home.md");
        await modifyFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Home.md", blocked by local file',
        ]);
        await assertFileIgnored(outputDir, "Home.md", result.state);
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

    test("untracked file, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await createFile(outputDir, "characters/NPCs.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local file",
        ]);
        await assertFileMatchesFixture(outputDir, "characters/NPCs.md", "NPCs.md");
        await assertFileIgnored(outputDir, "characters/NPCs.md", result.state);
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
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Welcome.md" to "Home.md", ' +
                "blocked by local file",
        ]);
        await assertFileIgnored(outputDir, "Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "Welcome.md");
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

    test("remote edited", async () => {
        await setOlderContent(outputDir, initialState, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Bestiary.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "The Old Café.md", "café.md");

        const sync = createSync();

        const result = await sync.run();

        const expected = ['pull: renamed "café.md" to "The Old Café.md"'];
        expect(result.output).toEqual(expected);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, local edited, directory", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await createFile(outputDir, "characters/NPCs.md/notes.txt");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local directory",
        ]);
        await assertTrackedFileIntact(outputDir, result.state, "NPCs.md");
        await assertFileIgnored(
            outputDir,
            "characters/NPCs.md/notes.txt",
            result.state,
        );
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

    test("remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Welcome.md" to "Home.md"',
            'pull: "Home.md" (v2)',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, swapped", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "temp.md",
        );
        await setOlderFilename(
            outputDir,
            initialState,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        await setOlderFilename(
            outputDir,
            initialState,
            "temp.md",
            "sessions/session-01.md",
        );

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "sessions/session-01.md",
            "old.md",
        );
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "sessions/session-01.md",
        );

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "old.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain reversed", async () => {
        await setOlderFilename(outputDir, initialState, "characters/NPCs.md", "old.md");
        await setOlderFilename(
            outputDir,
            initialState,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "old.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle", async () => {
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "index.md"',
            'pull: renamed "Bestiary.md" to "Home.md"',
            'pull: renamed "index.md" to "Bestiary.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle, local edited", async () => {
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");
        await modifyFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "Home.md" to "index.md", ' +
                "local changes would be lost",
            'pull: ERROR cannot rename "Bestiary.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "index.md" to "Bestiary.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
        assertFileInState("Home.md", result.state);
        await assertTrackedFileMatchesFixture(
            outputDir,
            result.state,
            "Home.md",
            "Bestiary.md",
        );
        await assertTrackedFileMatchesFixture(
            outputDir,
            result.state,
            "Bestiary.md",
            "index.md",
        );
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
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");
        untrackFile(initialState, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "index.md", blocked by local file',
            'pull: ERROR cannot rename "Bestiary.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "index.md" to "Bestiary.md", ' +
                "blocked by local file",
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        assertFileNotInState("Home.md", result.state);
        await assertTrackedFileMatchesFixture(
            outputDir,
            result.state,
            "Home.md",
            "Bestiary.md",
        );
        await assertTrackedFileMatchesFixture(
            outputDir,
            result.state,
            "Bestiary.md",
            "index.md",
        );
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

        expect(result.output).toEqual([]);
        await assertFileUnchanged(outputDir, "index.md");
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
        await setOlderContent(outputDir, initialState, "Bestiary.md");
        await modifyFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "Bestiary.md");
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

    test("local edited, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await modifyFile(outputDir, "NPCs.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "NPCs.md");
        assertFileInState("NPCs.md", result.state);
        await assertFileNotDownloaded(outputDir, "characters/NPCs.md", result.state);
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

    test("local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await modifyFile(outputDir, "Welcome.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "Welcome.md" to "Home.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "Welcome.md");
        assertFileInState("Welcome.md", result.state);
        await assertFileNotDownloaded(outputDir, "Home.md", result.state);
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
        await fileTracksDeletedRemote(
            outputDir,
            initialState,
            "archive/Old Notes.md",
            token,
        );

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "archive/Old Notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "archive/Old Notes.md");
        await assertEmptyDirRemoved(outputDir, "archive");
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

    test("remote deleted, local edited", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await modifyFile(outputDir, "Old Notes.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "Old Notes.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "Old Notes.md");
        assertFileInState("Old Notes.md", result.state);
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

    test("stale file", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

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

    test("stale file, remote edited", async () => {
        markFileStale(initialState, "index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited", async () => {
        markFileStale(initialState, "index.md");
        await modifyFile(outputDir, "index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "index.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "index.md");
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

    test("stale file, local deleted", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await deleteTrackedFile(outputDir, "my-notes.md");

        const sync = createSync({ lastFullSync: "2020-01-01T00:00:00Z" });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local deleted, remote edited", async () => {
        markFileStale(initialState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted", async () => {
        await deleteTrackedFile(outputDir, "index.md");

        const sync = createSync();

        const result = await sync.run();

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
        await setOlderContent(outputDir, initialState, "Bestiary.md");
        await deleteTrackedFile(outputDir, "Bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Bestiary.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await deleteTrackedFile(outputDir, "NPCs.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", ' +
                '"NPCs.md" deleted locally',
        ]);
        await assertTrackedFileNotRestored(outputDir, result.state, "NPCs.md");
        await assertFileNotDownloaded(outputDir, "characters/NPCs.md", result.state);
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
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Home.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Welcome.md" to "Home.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
        assertFileNotInState("Home.md", result.state);
        await assertTrackedFileNotRestored(outputDir, result.state, "Welcome.md");
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
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await deleteTrackedFile(outputDir, "Old Notes.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "Old Notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "Old Notes.md");
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

    test("local renamed", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");

        const sync = createSync();

        const result = await sync.run();

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

        expect(result.output).toEqual([]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
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
        await setOlderContent(outputDir, initialState, "renamed-bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v2)',
        ]);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "renamed-bestiary.md");
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
        await setOlderContent(outputDir, initialState, "renamed-bestiary.md");
        await modifyFile(outputDir, "renamed-bestiary.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md" to "renamed-bestiary.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "renamed-bestiary.md");
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
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("original.md", result.state);
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
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("original.md", result.state);
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
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await setOlderContent(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
            'pull: "index.md" to "my-index.md" (v1)',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("original.md", result.state);
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
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await setOlderContent(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
            'pull: SKIPPING pull "index.md" to "my-index.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        assertFileInState("my-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        assertFileNotInState("original.md", result.state);
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
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await renameLocalFile(outputDir, initialState, "Old Notes.md", "my-notes.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: deleted "Old Notes.md" (was "my-notes.md")',
        ]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        assertFileNotInState("Old Notes.md", result.state);
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

    test("local renamed, local edited, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await renameLocalFile(outputDir, initialState, "Old Notes.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = createSync();

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "Old Notes.md" (at "my-notes.md"), ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "my-notes.md");
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
        await assertFileUnchanged(outputDir, "my-notes.md");
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

        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", already deleted locally',
        ]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
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

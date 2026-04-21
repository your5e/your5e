/**
 * Subsequent sync push tests
 *
 * Tests for syncing to a directory that has been synced before
 * (sync state exists), with push enabled.
 *
 * Ported from tests/subsequent_sync_push.bats
 */

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
    assertFileDeletedOnServer,
    assertFileInState,
    assertFileMatchesFixture,
    assertFileModified,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFilePushed,
    assertFileUnchanged,
    assertInState,
    assertIncrementalResults,
    assertNotInState,
    assertServerEditedContent,
    assertServerFileDeleted,
    assertStateMatchesFixture,
    assertSyncMetadataUpdated,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
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
    uuidFor,
} from "./helpers.js";

describe("subsequent sync push", () => {
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
        } = {},
    ): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
            lastUpdate,
            lastFullSync: overrides.lastFullSync ?? recentTimestamp,
        });
    }

    test("no change, outdated timestamp", async () => {
        const fetchSpy = vi.spyOn(global, "fetch");

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

        const result = await createSync().run();

        // Verify incremental sync (with ?since= parameter, single call)
        expect(fetchSpy).toHaveBeenCalledTimes(1);
        const firstFetch = fetchSpy.mock.calls[0][0];
        expect(firstFetch).toContain(`?since=${encodeURIComponent(lastUpdate)}`);

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file", async () => {
        await createFile(outputDir, "scratchpad.txt");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual(['push: "scratchpad.txt" (v1)']);
        await assertFileUnchanged(outputDir, "scratchpad.txt");
        await assertFilePushed(
            outputDir,
            "scratchpad.txt",
            result.state,
            token,
            "text/plain",
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
        await assertTrackedFileIntact(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited, directory", async () => {
        await serverCreate(token, "Rumours.md");
        await createFile(outputDir, "Rumours.md/notes.txt");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `push: ERROR cannot push "Rumours.md/notes.txt": ` +
                `Path 'rumours' already exists.`,
            'pull: ERROR cannot pull "Rumours.md", blocked by local directory',
        ]);
        await assertFileUnchanged(outputDir, "Rumours.md/notes.txt");
        assertFileNotInState("Rumours.md/notes.txt", result.state);
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `push: ERROR cannot push "Quests.md": Path 'quests' already exists.`,
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `push: ERROR cannot push "npcs/Major.md": ` +
                `Path 'npcs/major' already exists.`,
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `push: ERROR cannot push "Monsters.md": Path 'monsters' already exists.`,
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

        const result = await createSync().run();

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

        const result = await createSync().run();

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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `push: ERROR cannot push "logs/Session 01.md/notes.txt": ` +
                `Path 'logs/session-01' already exists.`,
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
        await serverEditContent(token, uuid);
        await serverRename(token, uuid, "Welcome.md");

        const result = await createSync().run();

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
        await serverRename(token, npcsUuid, "temp.md");
        await serverRename(
            token,
            await uuidFor(initialState, "sessions/session-01.md"),
            "characters/NPCs.md",
        );
        await serverRename(token, npcsUuid, "sessions/session-01.md");

        const result = await createSync().run();

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
        await serverRename(
            token,
            await uuidFor(initialState, "sessions/session-01.md"),
            "old.md",
        );
        await serverRename(
            token,
            await uuidFor(initialState, "characters/NPCs.md"),
            "sessions/session-01.md",
        );

        const result = await createSync().run();

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
        await serverRename(
            token,
            await uuidFor(initialState, "characters/NPCs.md"),
            "old.md",
        );
        await serverRename(
            token,
            await uuidFor(initialState, "sessions/session-01.md"),
            "characters/NPCs.md",
        );

        const result = await createSync().run();

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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: renamed "index.md" to "Home.md"',
            'pull: renamed "Home.md" to "Bestiary.md"',
            'pull: renamed "Bestiary.md" to "index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'push: ERROR cannot rename "Bestiary.md" to "Home.md": ' +
                "Path 'home' already exists.",
            'pull: ERROR cannot rename "index.md" to "Home.md", ' +
                "blocked by local file",
            'pull: SKIPPING rename "Home.md" to "Bestiary.md", ' +
                "local changes would be lost",
            'pull: ERROR cannot rename "Bestiary.md" to "index.md", ' +
                "blocked by local file",
        ]);
        await assertFileModified(outputDir, "Home.md");
        assertFileInState("Home.md", result.state);
        await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
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
        await untrackAndRemoveFile(outputDir, initialState, "Home.md");
        await createFile(outputDir, "Home.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            `push: ERROR cannot push "Home.md": Path 'home' already exists.`,
            'pull: ERROR cannot pull "Bestiary.md", blocked by local file',
            'pull: ERROR cannot rename "index.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "Bestiary.md" to "index.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
        assertFileNotInState("Home.md", result.state);
        assertFileInState("Bestiary.md", result.state);
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual(['push: "index.md" (v2)']);
        await assertFileModified(outputDir, "index.md");
        await assertFilePushed(
            outputDir,
            "index.md",
            result.state,
            token,
            "text/markdown",
        );
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

        // push: first run, sends the modification, server will normalise line endings
        const result1 = await createSync().run();

        assertIncrementalResults(result1.incrementalResults, 0);
        expect(result1.output).toEqual(['push: "Home.md" (v3)']);
        const normalizedContent = await fs.readFile(
            path.join(outputDir, "Home.md"),
            "utf-8",
        );
        expect(normalizedContent).toBe("First line\nSecond line\nThird line\n");

        const sync2 = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState: result1.state,
            lastUpdate: result1.lastUpdate,
            lastFullSync: recentTimestamp,
        });

        // second run, no changes as the on-server modified Home.md has been pulled
        const result2 = await sync2.run();

        assertIncrementalResults(result2.incrementalResults, 1);
        expect(result2.output).toEqual([]);
        await assertTrackedFileIntact(outputDir, result2.state, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, result2.state, "index.md");
        await assertTrackedFileIntact(outputDir, result2.state, "Home.md");
        await assertTrackedFileIntact(
            outputDir,
            result2.state,
            "sessions/session-01.md",
        );
        await assertTrackedFileIntact(outputDir, result2.state, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, result2.state, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, result2.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result2.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        assertSyncMetadataUpdated(result2.lastUpdate, result2.lastFullSync);
    });

    test("local edited, remote edited", async () => {
        // Local adds Orc section
        await createFile(
            outputDir,
            "Bestiary.md",
            `# Bestiary

Creatures encountered.

## Goblin

Small and cunning.

## Orc

Large and aggressive.
`,
        );
        // Server adds Troll section
        await serverEditContent(
            token,
            await uuidFor(initialState, "Bestiary.md"),
            `# Bestiary

Creatures encountered.

## Goblin

Small and cunning.

## Troll

Regenerates health.
`,
        );

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['push: "Bestiary.md" (v4, merged)']);

        const content = await fs.readFile(path.join(outputDir, "Bestiary.md"), "utf-8");
        expect(content).toContain("## Orc");
        expect(content).toContain("## Troll");

        await assertFilePushed(
            outputDir,
            "Bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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
        await createFile(outputDir, "Bestiary.md", "identical content\n");
        await serverEditContent(
            token,
            await uuidFor(initialState, "Bestiary.md"),
            "identical content\n",
        );

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([]);
        const content = await fs.readFile(path.join(outputDir, "Bestiary.md"), "utf-8");
        expect(content).toBe("identical content\n");
        await assertFilePushed(
            outputDir,
            "Bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['push: "index.md" (v3, replaced)']);
        await assertFileModified(outputDir, "index.md");
        await assertFilePushed(
            outputDir,
            "index.md",
            result.state,
            token,
            "text/markdown",
        );
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "renamed-bestiary.md" to "Bestiary.md"',
            'push: "Bestiary.md" (v5)',
        ]);
        await assertFileModified(outputDir, "Bestiary.md");
        await assertFilePushed(
            outputDir,
            "Bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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
        await modifyFile(outputDir, "Home.md");
        await serverEditContent(token, await uuidFor(initialState, "Home.md"));
        await serverRename(token, await uuidFor(initialState, "Home.md"), "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "Welcome.md" to "Home.md"',
            'push: "Home.md" (v6, replaced)',
        ]);
        await assertFileModified(outputDir, "Home.md");
        await assertFilePushed(
            outputDir,
            "Home.md",
            result.state,
            token,
            "text/markdown",
        );
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

        const result = await createSync().run();

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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['push: "Bestiary.md" (v3)']);
        await assertFileModified(outputDir, "Bestiary.md");
        await assertFilePushed(
            outputDir,
            "Bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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

    test("stale file, incremental sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

        // Incremental sync cannot detect stale files
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
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
    });

    test("stale file, full sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

        // Full sync detects stale files by comparing against complete server state
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

    test("stale file, remote edited, incremental sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await serverEditContent(token, uuid);

        // Incremental sync cannot detect stale file
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: ERROR cannot pull "index.md", blocked by local file',
        ]);
        await assertTrackedFileIntact(outputDir, result.state, "index.md");
        assertInState(result.state, "stale-uuid");
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
    });

    test("stale file, remote edited, full sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await serverEditContent(token, uuid);

        // Full sync detects stale file, removes it, downloads new file
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

    test("stale file, local edited, incremental sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        // push: incremental sync learns UUID is stale from 404, creates new file
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual(['push: "my-notes.md" (v1)']);
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

    test("stale file, local edited, full sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        // push: full sync already knows UUID is stale, creates new file
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual(['push: "my-notes.md" (v1)']);
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local deleted, remote edited, incremental sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");
        await serverEditContent(token, uuid);
        assertInState(initialState, "stale-uuid");

        // push: Push discovers stale entry via 404 when attempting to delete
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
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

    test("stale file, local deleted, remote edited, full sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");
        await serverEditContent(token, uuid);

        // Full sync detects stale entry by comparing against complete server state
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual(['push: deleted "index.md"']);
        await assertFileDeletedOnServer(outputDir, result.state, "index.md", token);
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
        await deleteTrackedFile(outputDir, "Bestiary.md");
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));

        const result = await createSync().run();

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
        await deleteTrackedFile(outputDir, "characters/NPCs.md");
        await serverRename(
            token,
            await uuidFor(initialState, "characters/NPCs.md"),
            "NPCs.md",
        );

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "NPCs.md" to "characters/NPCs.md"',
            'push: deleted "characters/NPCs.md"',
        ]);
        await assertFileDeletedOnServer(
            outputDir,
            result.state,
            "characters/NPCs.md",
            token,
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

    test("local deleted, remote edited, remote renamed", async () => {
        await deleteTrackedFile(outputDir, "Home.md");
        await serverEditContent(token, await uuidFor(initialState, "Home.md"));
        await serverRename(token, await uuidFor(initialState, "Home.md"), "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "Welcome.md"',
            'pull: "Welcome.md" (v4, revivified)',
        ]);
        await assertServerEditedContent(outputDir, "Welcome.md");
        await assertFileNotDownloaded(outputDir, "Home.md", result.state);
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
        await deleteTrackedFile(outputDir, "Home.md");
        await createFile(outputDir, "Welcome.md");
        await serverEditContent(token, await uuidFor(initialState, "Home.md"));
        await serverRename(token, await uuidFor(initialState, "Home.md"), "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: ERROR cannot delete "Home.md", server has updates.',
            "push: ERROR cannot push \"Welcome.md\": Path 'welcome' already exists.",
            'pull: ERROR cannot rename "Home.md" to "Welcome.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Welcome.md");
        const homeExists = await fs
            .stat(path.join(outputDir, "Home.md"))
            .then((stat) => stat.isFile())
            .catch(() => false);
        expect(homeExists).toBe(false);
        assertFileInState("Home.md", result.state);
        assertFileNotInState("Welcome.md", result.state);
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
        await deleteTrackedFile(outputDir, "Bestiary.md");
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([]);
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'push: renamed "index.md" to "renamed-index.md"',
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

    test("local renamed, local edited", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'push: renamed "index.md" to "renamed-index.md"',
            'push: "renamed-index.md" (v3)',
        ]);
        await assertFileModified(outputDir, "renamed-index.md");
        await assertFilePushed(
            outputDir,
            "renamed-index.md",
            result.state,
            token,
            "text/markdown",
        );
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
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await serverEditContent(token, uuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "renamed-bestiary.md"',
            'pull: "renamed-bestiary.md" (v4)',
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
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await modifyFile(outputDir, "renamed-bestiary.md");
        await serverEditContent(token, uuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "renamed-bestiary.md"',
            'push: "renamed-bestiary.md" (v5, replaced)',
        ]);
        await assertFileModified(outputDir, "renamed-bestiary.md");
        await assertFilePushed(
            outputDir,
            "renamed-bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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
        const uuid = await uuidFor(initialState, "index.md");
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "server-index.md" to "my-index.md"',
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
        const uuid = await uuidFor(initialState, "index.md");
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "server-index.md" to "my-index.md"',
            'push: "my-index.md" (v4)',
        ]);
        await assertFileModified(outputDir, "my-index.md");
        await assertFilePushed(
            outputDir,
            "my-index.md",
            result.state,
            token,
            "text/markdown",
        );
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
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await serverEditContent(token, uuid);
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "server-index.md" to "my-index.md"',
            'pull: "my-index.md" (v4)',
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
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");
        await serverEditContent(token, uuid);
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "server-index.md" to "my-index.md"',
            'push: "my-index.md" (v5, replaced)',
        ]);
        await assertFileModified(outputDir, "my-index.md");
        await assertFilePushed(
            outputDir,
            "my-index.md",
            result.state,
            token,
            "text/markdown",
        );
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
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await serverDelete(token, uuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "my-bestiary.md"',
        ]);
        await assertTrackedFileIntact(outputDir, result.state, "my-bestiary.md");
        await assertFilePushed(
            outputDir,
            "my-bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await modifyFile(outputDir, "my-bestiary.md");
        await serverDelete(token, uuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "my-bestiary.md"',
            'push: "my-bestiary.md" (v4)',
        ]);
        await assertFileModified(outputDir, "my-bestiary.md");
        await assertFilePushed(
            outputDir,
            "my-bestiary.md",
            result.state,
            token,
            "text/markdown",
        );
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

    test("local renamed, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual(['push: "my-notes.md" (v1)']);
        await assertFileModified(outputDir, "my-notes.md");
        await assertFilePushed(
            outputDir,
            "my-notes.md",
            result.state,
            token,
            "text/markdown",
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'info: detected rename "index.md" to "renamed-index.md"',
            'push: renamed "index.md" to "renamed-index.md"',
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'push: deleted "index.md"',
            'push: "renamed-index.md" (v1)',
        ]);
        await assertFileModified(outputDir, "renamed-index.md");
        await assertFilePushed(
            outputDir,
            "renamed-index.md",
            result.state,
            token,
            "text/markdown",
        );
        await assertFileDeletedOnServer(outputDir, result.state, "index.md", token);
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

    test("local renamed untracked, hash mismatch, remote edited", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");
        await serverEditContent(token, await uuidFor(initialState, "index.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'push: "renamed-index.md" (v1)',
            'pull: "index.md" (v2, revivified)',
        ]);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFileModified(outputDir, "renamed-index.md");
        await assertFilePushed(
            outputDir,
            "renamed-index.md",
            result.state,
            token,
            "text/markdown",
        );
        assertFileInState("renamed-index.md", result.state);
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

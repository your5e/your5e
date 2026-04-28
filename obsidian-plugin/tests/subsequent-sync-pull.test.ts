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
    assertFileContent,
    assertFileIgnored,
    assertFileInState,
    assertFileMatchesFixture,
    assertFileModified,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertFixturesIntact,
    assertFixturesIntactExcept,
    assertInState,
    assertIncrementalResults,
    assertNotInState,
    assertServerEditedContent,
    assertStateMatchesFixture,
    assertSyncMetadataUpdated,
    assertTimestampInRange,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
    assertTrackedFileNotRestored,
    assertUuidLocalFilename,
    assertUuidRemoteFilename,
    cleanupTestDir,
    clearPagesCache,
    createFile,
    createTestDir,
    deleteTrackedFile,
    getExpectedLastUpdate,
    getToken,
    initSyncedDir,
    markFileStale,
    mergeableOrc,
    mergeableTroll,
    mergedOrcTroll,
    modifyFile,
    modifyFileWithContent,
    nowTimestamp,
    renameLocalFile,
    renameLocalFileUntracked,
    restoreDatabase,
    serverCreate,
    serverDelete,
    serverEditContent,
    serverRename,
    setBaseHash,
    shortHostname,
    todayDate,
    untrackAndRemoveFile,
    uuidFor,
} from "./helpers.js";

describe("subsequent sync pull", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let initialState: Map<string, SyncStateEntry>;
    let recentTimestamp: string;
    let lastUpdate: string;
    let SHORT_HOST: string;

    beforeAll(async () => {
        token = await getToken();
        SHORT_HOST = shortHostname();
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

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileIgnored(outputDir, "scratchpad.txt", result.state);
        await assertFixturesIntact(outputDir, result.state);
        await assertStateMatchesFixture(result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited, directory", async () => {
        await serverCreate(token, "Rumours.md");
        await createFile(outputDir, "Rumours.md/notes.txt");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Rumours.md" to "Rumours (conflict ${SHORT_HOST}).md"`,
            'pull: "Rumours.md" (v1)',
        ]);
        await assertFileUnchanged(
            outputDir,
            `Rumours (conflict ${SHORT_HOST}).md/notes.txt`,
        );
        assertFileNotInState(
            `Rumours (conflict ${SHORT_HOST}).md/notes.txt`,
            result.state,
        );
        await assertTrackedFileIntact(outputDir, result.state, "Rumours.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited", async () => {
        await serverCreate(token, "Quests.md");
        await createFile(outputDir, "Quests.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Quests.md" to "Quests (conflict ${SHORT_HOST}).md"`,
            'pull: "Quests.md" (v1)',
        ]);
        await assertFileUnchanged(outputDir, `Quests (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Quests (conflict ${SHORT_HOST}).md`, result.state);
        await assertTrackedFileIntact(outputDir, result.state, "Quests.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, remote renamed", async () => {
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        await createFile(outputDir, "npcs/Major.md");
        await serverRename(token, npcsUuid, "npcs/Major.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "npcs/Major.md" to "npcs/Major (conflict ${SHORT_HOST}).md"`,
            'pull: renamed "characters/NPCs.md" to "npcs/Major.md"',
        ]);
        await assertFileUnchanged(outputDir, `npcs/Major (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`npcs/Major (conflict ${SHORT_HOST}).md`, result.state);
        assertUuidLocalFilename(result.state, npcsUuid, "npcs/Major.md");
        await assertFileMatchesFixture(
            outputDir,
            "characters/NPCs.md",
            "npcs/Major.md",
        );
        await assertFixturesIntactExcept(outputDir, result.state, "characters/NPCs.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("untracked file, local edited, remote renamed", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await createFile(outputDir, "Monsters.md");
        await serverRename(token, bestiaryUuid, "Monsters.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Monsters.md" to "Monsters (conflict ${SHORT_HOST}).md"`,
            'pull: renamed "Bestiary.md" to "Monsters.md"',
        ]);
        await assertFileUnchanged(outputDir, `Monsters (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Monsters (conflict ${SHORT_HOST}).md`, result.state);
        assertUuidLocalFilename(result.state, bestiaryUuid, "Monsters.md");
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "Monsters.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote edited", async () => {
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "Bestiary.md" (v3)']);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed", async () => {
        const cafeUuid = await uuidFor(initialState, "The Old Café.md");
        await serverRename(token, cafeUuid, "The New Café.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "The Old Café.md" to "The New Café.md"',
        ]);
        assertUuidLocalFilename(result.state, cafeUuid, "The New Café.md");
        // noqa
        await assertFileMatchesFixture(outputDir, "The Old Café.md", "The New Café.md");
        await assertFixturesIntactExcept(outputDir, result.state, "The Old Café.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, local edited, directory", async () => {
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        await serverRename(token, sessionUuid, "logs/Session 01.md");
        await createFile(outputDir, "logs/Session 01.md/notes.txt");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "logs/Session 01.md" to ` +
                `"logs/Session 01 (conflict ${SHORT_HOST}).md"`,
            'pull: renamed "sessions/session-01.md" to "logs/Session 01.md"',
        ]);
        await assertFileUnchanged(
            outputDir,
            `logs/Session 01 (conflict ${SHORT_HOST}).md/notes.txt`,
        );
        assertFileNotInState(
            `logs/Session 01 (conflict ${SHORT_HOST}).md/notes.txt`,
            result.state,
        );
        assertUuidLocalFilename(result.state, sessionUuid, "logs/Session 01.md");
        await assertFileMatchesFixture(
            outputDir,
            "sessions/session-01.md",
            "logs/Session 01.md",
        );
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "sessions/session-01.md",
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
        await assertFixturesIntactExcept(outputDir, result.state, "Home.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, swapped", async () => {
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        await serverRename(token, npcsUuid, "temp.md");
        await serverRename(token, sessionUuid, "characters/NPCs.md");
        await serverRename(token, npcsUuid, "sessions/session-01.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 2);
        expect(result.output).toEqual([
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
        ]);
        await assertFileMatchesFixture(
            outputDir,
            "characters/NPCs.md",
            "sessions/session-01.md",
        );
        await assertFileMatchesFixture(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        assertUuidLocalFilename(result.state, sessionUuid, "characters/NPCs.md");
        assertUuidLocalFilename(result.state, npcsUuid, "sessions/session-01.md");
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain", async () => {
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        await serverRename(token, sessionUuid, "old.md");
        await serverRename(token, npcsUuid, "sessions/session-01.md");

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
        assertUuidLocalFilename(result.state, sessionUuid, "old.md");
        assertUuidLocalFilename(result.state, npcsUuid, "sessions/session-01.md");
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, chain reversed", async () => {
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        const sessionUuid = await uuidFor(initialState, "sessions/session-01.md");
        await serverRename(token, npcsUuid, "old.md");
        await serverRename(token, sessionUuid, "characters/NPCs.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 2);
        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "old.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "characters/NPCs.md", "old.md");
        await assertFileMatchesFixture(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        assertUuidLocalFilename(result.state, npcsUuid, "old.md");
        assertUuidLocalFilename(result.state, sessionUuid, "characters/NPCs.md");
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "sessions/session-01.md",
            "characters/NPCs.md",
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
            'pull: renamed "Home.md" to "Bestiary.md"',
            'pull: renamed "index.md" to "Home.md"',
            'pull: renamed "Bestiary.md" to "index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        assertUuidLocalFilename(result.state, bestiaryUuid, "index.md");
        assertUuidLocalFilename(result.state, homeUuid, "Bestiary.md");
        assertUuidLocalFilename(result.state, indexUuid, "Home.md");
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "index.md",
            "Home.md",
            "Bestiary.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle, local edited, mergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        const homeUuid = await uuidFor(initialState, "Home.md");
        const indexUuid = await uuidFor(initialState, "index.md");
        await serverRename(token, bestiaryUuid, "temp.md");
        await serverRename(token, homeUuid, "Bestiary.md");
        await serverRename(token, indexUuid, "Home.md");
        await serverRename(token, bestiaryUuid, "index.md");
        await modifyFileWithContent(outputDir, "Bestiary.md", mergeableOrc());
        await serverEditContent(token, bestiaryUuid, mergeableTroll());

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "Bestiary.md"',
            'pull: renamed "index.md" to "Home.md"',
            'pull: renamed "Bestiary.md" to "index.md"',
            'pull: "index.md" (v5, merged)',
        ]);
        await assertFileContent(outputDir, "index.md", mergedOrcTroll());
        assertFileInState("index.md", result.state);
        // After cycle: Home.md has original index.md content
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        assertFileInState("Home.md", result.state);
        // After cycle: Bestiary.md has original Home.md content
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "index.md",
            "Home.md",
            "Bestiary.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote renamed, cycle, local edited, unmergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        const homeUuid = await uuidFor(initialState, "Home.md");
        const indexUuid = await uuidFor(initialState, "index.md");
        await serverRename(token, bestiaryUuid, "temp.md");
        await serverRename(token, homeUuid, "Bestiary.md");
        await serverRename(token, indexUuid, "Home.md");
        await serverRename(token, bestiaryUuid, "index.md");
        await modifyFile(outputDir, "Bestiary.md");
        await serverEditContent(token, bestiaryUuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 3);
        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "Bestiary.md"',
            'pull: renamed "index.md" to "Home.md"',
            `pull: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "index.md" (v5)',
        ]);
        await assertFileModified(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        assertFileInState("Home.md", result.state);
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "index.md",
            "Home.md",
            "Bestiary.md",
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
            `info: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"`,
            'pull: renamed "index.md" to "Home.md"',
            'pull: renamed "Bestiary.md" to "index.md"',
            'pull: "Bestiary.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, `Home (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Home (conflict ${SHORT_HOST}).md`, result.state);
        assertUuidLocalFilename(result.state, indexUuid, "Home.md");
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        assertUuidLocalFilename(result.state, bestiaryUuid, "index.md");
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        await assertFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertFixturesIntactExcept(
            outputDir,
            result.state,
            "Bestiary.md",
            "Home.md",
            "index.md",
        );
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited", async () => {
        await modifyFile(outputDir, "index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, CRLF line endings", async () => {
        await createFile(
            outputDir,
            "Home.md",
            "First line\r\nSecond line\r\nThird line",
        );

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        const homeContent = await fs.readFile(path.join(outputDir, "Home.md"), "utf-8");
        expect(homeContent).toBe("First line\r\nSecond line\r\nThird line");
        assertFileInState("Home.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Home.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, mergeable", async () => {
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
        expect(result.output).toEqual(['pull: "Bestiary.md" (v3, merged)']);
        const content = await fs.readFile(path.join(outputDir, "Bestiary.md"), "utf-8");
        expect(content).toContain("## Orc");
        expect(content).toContain("## Troll");
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, unmergeable", async () => {
        await modifyFile(outputDir, "Bestiary.md");
        await serverEditContent(token, await uuidFor(initialState, "Bestiary.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "Bestiary.md" (v3)',
        ]);
        await assertFileModified(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
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
        assertFileInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, no common ancestor", async () => {
        const indexUuid = await uuidFor(initialState, "index.md");
        await modifyFile(outputDir, "index.md");
        await serverEditContent(token, indexUuid);
        setBaseHash(initialState, "index.md", "no-common-ancestor");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"`,
            'pull: "index.md" (v2)',
        ]);
        await assertFileModified(outputDir, `index (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`index (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote renamed", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await modifyFile(outputDir, "Bestiary.md");
        await serverRename(token, bestiaryUuid, "renamed-bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "Bestiary.md" to "renamed-bestiary.md"',
        ]);
        await assertFileModified(outputDir, "renamed-bestiary.md");
        assertUuidLocalFilename(result.state, bestiaryUuid, "renamed-bestiary.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, remote renamed, mergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await modifyFileWithContent(outputDir, "Bestiary.md", mergeableOrc());
        await serverEditContent(token, bestiaryUuid, mergeableTroll());
        await serverRename(token, bestiaryUuid, "renamed-bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: renamed "Bestiary.md" to "renamed-bestiary.md"',
            'pull: "renamed-bestiary.md" (v4, merged)',
        ]);
        await assertFileContent(outputDir, "renamed-bestiary.md", mergedOrcTroll());
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local edited, remote edited, remote renamed, unmergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await modifyFile(outputDir, "Bestiary.md");
        await serverEditContent(token, bestiaryUuid);
        await serverRename(token, bestiaryUuid, "renamed-bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `pull: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "renamed-bestiary.md" (v4)',
        ]);
        await assertFileModified(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "renamed-bestiary.md");
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote deleted", async () => {
        await serverDelete(token, await uuidFor(initialState, "characters/NPCs.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: deleted "characters/NPCs.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "characters/NPCs.md");
        await assertEmptyDirRemoved(outputDir, "characters");
        await assertFixturesIntactExcept(outputDir, result.state, "characters/NPCs.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("remote deleted, local edited", async () => {
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));
        await modifyFile(outputDir, "Bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: deleted "Bestiary.md"',
        ]);
        await assertFileModified(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
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
        await assertFixturesIntact(outputDir, result.state);
    });

    test("stale file, full sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

        // Full sync detects stale files by comparing against complete server state
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, remote edited, incremental sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await serverEditContent(token, uuid);

        // Incremental sync can deduce file is stale: another uuid claims the filename
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "index.md" (v2)']);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        assertNotInState(result.state, "stale-uuid");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
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
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited, incremental sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        // pull: incremental sync cannot detect stale files (see fetch_remote_state)
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "my-notes.md");
        assertFileInState("my-notes.md", result.state);
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited, full sync", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        // pull: full sync detects stale file, renames local and deletes from state
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual([
            `info: renamed "my-notes.md" to "my-notes (conflict ${SHORT_HOST}).md"`,
        ]);
        await assertFileModified(outputDir, `my-notes (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`my-notes (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState("my-notes.md", result.state);
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited, remote edited, incremental sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await modifyFile(outputDir, "index.md");
        await serverEditContent(token, uuid);

        // pull: Incremental sync can deduce stale entry from remote edit
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"`,
            'pull: "index.md" (v2)',
        ]);
        assertNotInState(result.state, "stale-uuid");
        await assertFileModified(outputDir, `index (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`index (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local edited, remote edited, full sync", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        markFileStale(initialState, "index.md");
        await modifyFile(outputDir, "index.md");
        await serverEditContent(token, uuid);

        // Full sync detects stale entry by comparing against complete server state
        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual([
            `info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"`,
            'pull: "index.md" (v2)',
        ]);
        assertNotInState(result.state, "stale-uuid");
        await assertFileModified(outputDir, `index (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`index (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("stale file, local deleted", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await deleteTrackedFile(outputDir, "my-notes.md");
        assertInState(initialState, "stale-uuid");

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

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

        // pull: Incremental sync can deduce stale entry
        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "index.md" (v2)']);
        assertNotInState(result.state, "stale-uuid");
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
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
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, aware", async () => {
        await deleteTrackedFile(outputDir, "index.md", initialState);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertTrackedFileNotRestored(outputDir, result.state, "index.md");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, unaware", async () => {
        await deleteTrackedFile(outputDir, "index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertTrackedFileNotRestored(outputDir, result.state, "index.md");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
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
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote renamed", async () => {
        const npcsUuid = await uuidFor(initialState, "characters/NPCs.md");
        await deleteTrackedFile(outputDir, "characters/NPCs.md");
        await serverRename(token, npcsUuid, "NPCs.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, result.state, "characters/NPCs.md");
        await assertTrackedFileNotRestored(outputDir, result.state, "NPCs.md");
        assertUuidLocalFilename(result.state, npcsUuid, "NPCs.md");
        assertUuidRemoteFilename(result.state, npcsUuid, "NPCs.md");
        await assertFixturesIntactExcept(outputDir, result.state, "characters/NPCs.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote edited, remote renamed", async () => {
        const homeUuid = await uuidFor(initialState, "Home.md");
        await deleteTrackedFile(outputDir, "Home.md");
        await serverEditContent(token, homeUuid);
        await serverRename(token, homeUuid, "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "Welcome.md" (v4, revivified)']);
        await assertServerEditedContent(outputDir, "Welcome.md");
        assertUuidLocalFilename(result.state, homeUuid, "Welcome.md");
        assertFileNotInState("Home.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Home.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, aware, local edited, remote edited", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await deleteTrackedFile(outputDir, "Bestiary.md", initialState);
        await createFile(outputDir, "Bestiary.md");
        await serverEditContent(token, bestiaryUuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "Bestiary.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertUuidLocalFilename(result.state, bestiaryUuid, "Bestiary.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, unaware, local edited, remote edited", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await deleteTrackedFile(outputDir, "Bestiary.md");
        await createFile(outputDir, "Bestiary.md");
        await serverEditContent(token, bestiaryUuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "Bestiary.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, `Bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "Bestiary.md");
        assertUuidLocalFilename(result.state, bestiaryUuid, "Bestiary.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    // noqa
    test("local deleted, aware, local edited, remote edited, remote renamed", async () => {
        const homeUuid = await uuidFor(initialState, "Home.md");
        await deleteTrackedFile(outputDir, "Home.md", initialState);
        await createFile(outputDir, "Welcome.md");
        await serverEditContent(token, homeUuid);
        await serverRename(token, homeUuid, "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "Welcome.md" to "Welcome (conflict ${SHORT_HOST}).md"`,
            'pull: "Welcome.md" (v4, revivified)',
        ]);
        await assertFileUnchanged(outputDir, `Welcome (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Welcome (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "Welcome.md");
        assertUuidLocalFilename(result.state, homeUuid, "Welcome.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Home.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    // noqa
    test("local deleted, unaware, local edited, remote edited, remote renamed", async () => {
        // Unaware: delete Home.md without marking state, then recreate Home.md
        // Server renames to Welcome.md, but locally we still have Home.md
        const homeUuid = await uuidFor(initialState, "Home.md");
        await deleteTrackedFile(outputDir, "Home.md");
        await createFile(outputDir, "Home.md");
        await serverEditContent(token, homeUuid);
        await serverRename(token, homeUuid, "Welcome.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `pull: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"`,
            'pull: "Welcome.md" (v4)',
        ]);
        await assertFileUnchanged(outputDir, `Home (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Home (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "Welcome.md");
        assertUuidLocalFilename(result.state, homeUuid, "Welcome.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Home.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local deleted, remote deleted", async () => {
        await deleteTrackedFile(outputDir, "Bestiary.md");
        await serverDelete(token, await uuidFor(initialState, "Bestiary.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: deleted "Bestiary.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "Bestiary.md");
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
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
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v3)',
        ]);
        await assertServerEditedContent(outputDir, "renamed-bestiary.md");
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote edited, mergeable", async () => {
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await modifyFileWithContent(outputDir, "renamed-bestiary.md", mergeableOrc());
        await serverEditContent(token, uuid, mergeableTroll());

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v3, merged)',
        ]);
        await assertFileContent(outputDir, "renamed-bestiary.md", mergedOrcTroll());
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote edited, unmergeable", async () => {
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
            `info: renamed "renamed-bestiary.md" to ` +
                `"renamed-bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v3)',
        ]);
        await assertFileModified(
            outputDir,
            `renamed-bestiary (conflict ${SHORT_HOST}).md`,
        );
        assertFileNotInState(
            `renamed-bestiary (conflict ${SHORT_HOST}).md`,
            result.state,
        );
        await assertServerEditedContent(outputDir, "renamed-bestiary.md");
        assertFileInState("renamed-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        assertUuidLocalFilename(result.state, uuid, "my-index.md");
        assertUuidRemoteFilename(result.state, uuid, "server-index.md");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, remote renamed", async () => {
        const uuid = await uuidFor(initialState, "index.md");
        await renameLocalFile(outputDir, initialState, "index.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");
        await serverRename(token, uuid, "server-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([]);
        await assertFileModified(outputDir, "my-index.md");
        assertUuidLocalFilename(result.state, uuid, "my-index.md");
        assertUuidRemoteFilename(result.state, uuid, "server-index.md");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
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
            'pull: "server-index.md" to "my-index.md" (v3)',
        ]);
        await assertServerEditedContent(outputDir, "my-index.md");
        assertUuidLocalFilename(result.state, uuid, "my-index.md");
        assertUuidRemoteFilename(result.state, uuid, "server-index.md");
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    // noqa
    test("local renamed, local edited, remote edited, remote renamed, mergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await modifyFileWithContent(outputDir, "my-bestiary.md", mergeableOrc());
        await serverEditContent(token, bestiaryUuid, mergeableTroll());
        await serverRename(token, bestiaryUuid, "server-bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            'pull: "server-bestiary.md" to "my-bestiary.md" (v4, merged)',
        ]);
        await assertFileContent(outputDir, "my-bestiary.md", mergedOrcTroll());
        assertFileInState("my-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    // noqa
    test("local renamed, local edited, remote edited, remote renamed, unmergeable", async () => {
        const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await modifyFile(outputDir, "my-bestiary.md");
        await serverEditContent(token, bestiaryUuid);
        await serverRename(token, bestiaryUuid, "server-bestiary.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual([
            `info: renamed "my-bestiary.md" to ` +
                `"my-bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "server-bestiary.md" to "my-bestiary.md" (v4)',
        ]);
        await assertFileModified(outputDir, `my-bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`my-bestiary (conflict ${SHORT_HOST}).md`, result.state);
        await assertServerEditedContent(outputDir, "my-bestiary.md");
        assertFileInState("my-bestiary.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, remote deleted", async () => {
        const uuid = await uuidFor(initialState, "Bestiary.md");
        await renameLocalFile(outputDir, initialState, "Bestiary.md", "my-bestiary.md");
        await serverDelete(token, uuid);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: deleted "Bestiary.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "my-bestiary.md");
        assertFileNotInState("Bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
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
            `info: renamed "my-bestiary.md" to ` +
                `"my-bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: deleted "Bestiary.md"',
        ]);
        await assertFileModified(outputDir, `my-bestiary (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`my-bestiary (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState("Bestiary.md", result.state);
        assertFileNotInState("my-bestiary.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "Bestiary.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed, local edited, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const result = await createSync({ lastFullSync: "2020-01-01T00:00:00Z" }).run();

        expect(result.output).toEqual([
            `info: renamed "my-notes.md" to "my-notes (conflict ${SHORT_HOST}).md"`,
        ]);
        await assertFileModified(outputDir, `my-notes (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`my-notes (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState("original.md", result.state);
        assertFileNotInState("my-notes.md", result.state);
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash match", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([
            'info: detected rename "index.md" to "renamed-index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        assertFileInState("renamed-index.md", result.state);
        assertFileNotInState("index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash mismatch", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 0);
        expect(result.output).toEqual([]);
        await assertTrackedFileNotRestored(outputDir, result.state, "index.md");
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileNotInState("renamed-index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("local renamed untracked, hash mismatch, remote edited", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");
        await serverEditContent(token, await uuidFor(initialState, "index.md"));

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        expect(result.output).toEqual(['pull: "index.md" (v2, revivified)']);
        await assertServerEditedContent(outputDir, "index.md");
        assertFileInState("index.md", result.state);
        await assertFileModified(outputDir, "renamed-index.md");
        assertFileNotInState("renamed-index.md", result.state);
        await assertFixturesIntactExcept(outputDir, result.state, "index.md");
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("conflict hostname exists", async () => {
        await serverCreate(token, "Quests.md");
        await createFile(outputDir, "Quests.md");
        await createFile(outputDir, `Quests (conflict ${SHORT_HOST}).md`);

        const result = await createSync().run();

        assertIncrementalResults(result.incrementalResults, 1);
        const today = todayDate();
        expect(result.output).toEqual([
            `info: renamed "Quests.md" to ` +
                `"Quests (conflict ${SHORT_HOST} ${today}).md"`,
            'pull: "Quests.md" (v1)',
        ]);
        await assertFileUnchanged(outputDir, `Quests (conflict ${SHORT_HOST}).md`);
        await assertFileUnchanged(
            outputDir,
            `Quests (conflict ${SHORT_HOST} ${today}).md`,
        );
        assertFileNotInState(`Quests (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState(
            `Quests (conflict ${SHORT_HOST} ${today}).md`,
            result.state,
        );
        await assertTrackedFileIntact(outputDir, result.state, "Quests.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });

    test("conflict hostname exists, conflict date exists", async () => {
        const today = todayDate();
        await serverCreate(token, "Quests.md");
        await createFile(outputDir, "Quests.md");
        await createFile(outputDir, `Quests (conflict ${SHORT_HOST}).md`);
        await createFile(outputDir, `Quests (conflict ${SHORT_HOST} ${today}).md`);

        const before = nowTimestamp();
        const result = await createSync().run();
        const after = nowTimestamp();

        assertIncrementalResults(result.incrementalResults, 1);
        // Extract the actual timestamp from the output - find the info: line
        const renameOutput = result.output.find((line) => line.startsWith("info:"));
        if (!renameOutput) {
            throw new Error("Expected info output");
        }
        const match = renameOutput.match(/Quests \(conflict [^)]+\s(\d{14})\)\.md/);
        if (!match) {
            throw new Error("Expected timestamp match");
        }
        const timestamp = match[1];
        assertTimestampInRange(timestamp, before, after);
        expect(result.output).toEqual([
            `info: renamed "Quests.md" to ` +
                `"Quests (conflict ${SHORT_HOST} ${timestamp}).md"`,
            'pull: "Quests.md" (v1)',
        ]);
        await assertFileUnchanged(outputDir, `Quests (conflict ${SHORT_HOST}).md`);
        await assertFileUnchanged(
            outputDir,
            `Quests (conflict ${SHORT_HOST} ${today}).md`,
        );
        await assertFileUnchanged(
            outputDir,
            `Quests (conflict ${SHORT_HOST} ${timestamp}).md`,
        );
        assertFileNotInState(`Quests (conflict ${SHORT_HOST}).md`, result.state);
        assertFileNotInState(
            `Quests (conflict ${SHORT_HOST} ${today}).md`,
            result.state,
        );
        assertFileNotInState(
            `Quests (conflict ${SHORT_HOST} ${timestamp}).md`,
            result.state,
        );
        await assertTrackedFileIntact(outputDir, result.state, "Quests.md");
        await assertFixturesIntact(outputDir, result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
    });
});

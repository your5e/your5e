/**
 * Combined sync scenario tests
 *
 * Tests that repeated syncs do not break in unexpected ways. Each test makes
 * one change and syncs, building on the state from the previous test.
 *
 * Ported from tests/combined_sync.bats
 */

import { afterAll, beforeAll, describe, expect, test, vi } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import type { SyncStateEntry } from "../src/sync/types.js";
import {
    API_BASE,
    assertEmptyDirRemoved,
    assertFileDeletedOnServer,
    assertFileInState,
    assertFileNotInState,
    assertFilePushed,
    assertFileUnchanged,
    assertIncrementalResults,
    assertServerEditedContent,
    assertSyncMetadataUpdated,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
    cleanupTestDir,
    createFile,
    createTestDir,
    getToken,
    mergeableOrc,
    mergeableTroll,
    modifyFile,
    modifyFileWithContent,
    moveFile,
    removeFile,
    restoreDatabase,
    serverCreate,
    serverDelete,
    serverEditContent,
    serverPurge,
    serverRename,
    shortHostname,
    trackedDelete,
    trackedRename,
    uuidFor,
} from "./helpers.js";

describe("combined sync", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let SHORT_HOST: string;

    let currentState: Map<string, SyncStateEntry>;
    let lastUpdate: string | undefined;
    let lastFullSync: string | undefined;

    beforeAll(async () => {
        token = await getToken();
        SHORT_HOST = shortHostname();
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
        currentState = new Map();
    });

    afterAll(async () => {
        await cleanupTestDir(testDir);
    });

    function createSync(): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState: currentState,
            lastUpdate,
            lastFullSync,
        });
    }

    test("initial sync", async () => {
        await createFile(outputDir, "my-notes.md");
        await createFile(outputDir, ".obsidian/app.json");

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            'push: "my-notes.md" (v1)',
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFilePushed(
            outputDir,
            "my-notes.md",
            result.state,
            token,
            "text/markdown",
        );
        await assertFileUnchanged(outputDir, ".obsidian/app.json");
        assertFileNotInState(".obsidian/app.json", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("stable sync", async () => {
        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("local edit", async () => {
        await modifyFile(outputDir, "my-notes.md");

        const result = await createSync().run();

        const expectedOutput = [
            'push: "my-notes.md" (v2)',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 0);

        await assertFilePushed(
            outputDir,
            "my-notes.md",
            result.state,
            token,
            "text/markdown",
        );

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("server edit", async () => {
        await serverEditContent(token, await uuidFor(currentState, "The Old Café.md"));

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            'pull: "The Old Café.md" (v2)',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 2);

        await assertServerEditedContent(outputDir, "The Old Café.md");

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("merged edit", async () => {
        await modifyFileWithContent(outputDir, "Bestiary.md", mergeableOrc());
        await serverEditContent(
            token,
            await uuidFor(currentState, "Bestiary.md"),
            mergeableTroll(),
        );

        const result = await createSync().run();

        const expectedOutput = [
            'push: "Bestiary.md" (v4, merged)',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("replaced edit", async () => {
        await modifyFile(outputDir, "index.md");
        await serverEditContent(token, await uuidFor(currentState, "index.md"));

        const result = await createSync().run();

        const expectedOutput = [
            'push: "index.md" (v3, replaced)',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 2);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("conflicting new file", async () => {
        await serverCreate(token, "Quests.md");
        await createFile(outputDir, "Quests.md");

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            `info: renamed "Quests.md" to "Quests (conflict ${SHORT_HOST}).md"`,
            `push: "Quests (conflict ${SHORT_HOST}).md" (v1)`,
            'pull: "Quests.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 2);

        await assertFileUnchanged(outputDir, `Quests (conflict ${SHORT_HOST}).md`);
        const conflictFile = `Quests (conflict ${SHORT_HOST}).md`;
        await assertFilePushed(
            outputDir,
            conflictFile,
            result.state,
            token,
            "text/markdown",
        );
        await assertTrackedFileIntact(outputDir, result.state, "Quests.md");

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("local rename, aware", async () => {
        await trackedRename(
            outputDir,
            currentState,
            "my-notes.md",
            "notes/my-notes.md",
        );

        const result = await createSync().run();

        const expectedOutput = [
            'push: renamed "my-notes.md" to "notes/my-notes.md"',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        assertFileInState("notes/my-notes.md", result.state);
        assertFileNotInState("my-notes.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("server delete", async () => {
        await serverDelete(token, await uuidFor(currentState, "characters/NPCs.md"));

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            'pull: deleted "characters/NPCs.md"',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 2);

        await assertTrackedFileDeleted(outputDir, result.state, "characters/NPCs.md");

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("server rename", async () => {
        const sessionUuid = await uuidFor(currentState, "sessions/session-01.md");
        await serverRename(token, sessionUuid, "logs/Session 01.md");

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            'pull: renamed "sessions/session-01.md" to "logs/Session 01.md"',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        await assertTrackedFileDeleted(
            outputDir,
            result.state,
            "sessions/session-01.md",
        );
        assertFileInState("logs/Session 01.md", result.state);
        assertFileNotInState("sessions/session-01.md", result.state);
        await assertEmptyDirRemoved(outputDir, "sessions");

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("local rename, unaware", async () => {
        await moveFile(outputDir, "index.md", "moved-index.md");

        const result = await createSync().run();

        const expectedOutput = [
            'info: detected rename "index.md" to "moved-index.md"',
            'push: renamed "index.md" to "moved-index.md"',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 0);

        assertFileInState("moved-index.md", result.state);
        assertFileNotInState("index.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("local delete, aware", async () => {
        await trackedDelete(outputDir, "Home.md", currentState);

        const result = await createSync().run();

        const expectedOutput = [
            'push: deleted "Home.md"',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        await assertFileDeletedOnServer(outputDir, result.state, "Home.md", token);
        assertFileNotInState("Home.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("local delete, unaware", async () => {
        await removeFile(outputDir, "The Old Café.md");

        const result = await createSync().run();

        const expectedOutput = [
            'push: deleted "The Old Café.md"',
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        await assertFileDeletedOnServer(
            outputDir,
            result.state,
            "The Old Café.md",
            token,
        );
        assertFileNotInState("The Old Café.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("stale file", async () => {
        const bestiaryUuid = await uuidFor(currentState, "Bestiary.md");
        serverPurge(bestiaryUuid);

        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 1);

        assertFileInState("Bestiary.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("stale file, full sync", async () => {
        lastFullSync = "2020-01-01T00:00:00Z";
        const fetchSpy = vi.spyOn(global, "fetch");

        const result = await createSync().run();

        // Verify full sync (no ?since= parameter)
        const firstFetch = fetchSpy.mock.calls[0][0];
        expect(firstFetch).not.toContain("since=");
        vi.restoreAllMocks();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
            'pull: deleted "Bestiary.md"',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertTrackedFileDeleted(outputDir, result.state, "Bestiary.md");
        assertFileNotInState("Bestiary.md", result.state);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("final stable state", async () => {
        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 0);

        await assertFileUnchanged(outputDir, ".obsidian/app.json");
        assertFileNotInState(".obsidian/app.json", result.state);
        assertFileInState("notes/my-notes.md", result.state);
        assertFileInState("Quests.md", result.state);
        assertFileInState(`Quests (conflict ${SHORT_HOST}).md`, result.state);
        assertFileInState("logs/Session 01.md", result.state);
        assertFileNotInState("Bestiary.md", result.state);
        assertFileNotInState("sessions/session-01.md", result.state);
        assertFileNotInState("Home.md", result.state);
        assertFileNotInState("The Old Café.md", result.state);
        assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);

        currentState = result.state;
        lastUpdate = result.lastUpdate;
        lastFullSync = result.lastFullSync;
    });

    test("final stable sync", async () => {
        const result = await createSync().run();

        const expectedOutput = [
            'push: ERROR cannot push ".obsidian/app.json": No hidden files.',
        ];
        expect(result.output).toEqual(expectedOutput);
        assertIncrementalResults(result.incrementalResults, 0);
    });
});

/**
 * Subsequent sync push tests
 *
 * Tests for syncing to a directory that has been synced before
 * (sync state exists), with push enabled.
 *
 * Ported from tests/subsequent_sync_push.bats
 */

import { afterEach, beforeAll, beforeEach, describe, expect, test } from "vitest";
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
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFilePushed,
    assertFileUnchanged,
    assertNotInState,
    assertServerFileDeleted,
    assertStateMatchesFixture,
    assertTrackedFileDeleted,
    assertTrackedFileIntact,
    assertTrackedFileMatchesFixture,
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

describe("subsequent sync push", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let initialState: Map<string, SyncStateEntry>;

    beforeAll(async () => {
        token = await getToken();
    });

    beforeEach(async () => {
        restoreDatabase();
        clearPagesCache();
        ({ testDir, outputDir } = await createTestDir());
        initialState = await initSyncedDir(outputDir, token);
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
    });

    test("no change", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("untracked file", async () => {
        await createFile(outputDir, "scratchpad.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

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
    });

    test("untracked file, local edited, directory", async () => {
        await untrackAndRemoveFile(outputDir, initialState, "Bestiary.md");
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "Bestiary.md/notes.txt": ` +
                `Path 'bestiary' already exists.`,
            'pull: ERROR cannot pull "Bestiary.md", blocked by local directory',
        ]);
        await assertFileUnchanged(outputDir, "Bestiary.md/notes.txt");
        assertFileNotInState("Bestiary.md/notes.txt", result.state);
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
    });

    test("untracked file, local edited", async () => {
        untrackFile(initialState, "Home.md");
        await modifyFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "Home.md": Path 'home' already exists.`,
            'pull: ERROR cannot pull "Home.md", blocked by local file',
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
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
    });

    test("untracked file, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await createFile(outputDir, "characters/NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "characters/NPCs.md": ` +
                `Path 'characters/npcs' already exists.`,
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "characters/NPCs.md");
        assertFileNotInState("characters/NPCs.md", result.state);
        await assertFileMatchesFixture(outputDir, "characters/NPCs.md", "NPCs.md");
        assertFileInState("NPCs.md", result.state);
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
    });

    test("untracked file, local edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "Home.md": Path 'home' already exists.`,
            'pull: ERROR cannot rename "Welcome.md" to "Home.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
        assertFileNotInState("Home.md", result.state);
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
    });

    test("remote edited", async () => {
        await setOlderContent(outputDir, initialState, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Bestiary.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "The Old Café.md", "café.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        const expected = ['pull: renamed "café.md" to "The Old Café.md"'];
        expect(result.output).toEqual(expected);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("remote renamed, local edited, directory", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await createFile(outputDir, "characters/NPCs.md/notes.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "characters/NPCs.md/notes.txt": ` +
                `Path 'characters/npcs' already exists.`,
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local directory",
        ]);
        await assertTrackedFileIntact(outputDir, result.state, "NPCs.md");
        await assertFileUnchanged(outputDir, "characters/NPCs.md/notes.txt");
        assertFileNotInState("characters/NPCs.md/notes.txt", result.state);
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
    });

    test("remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Welcome.md" to "Home.md"',
            'pull: "Home.md" (v2)',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
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

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
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

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "old.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("remote renamed, chain reversed", async () => {
        await setOlderFilename(outputDir, initialState, "characters/NPCs.md", "old.md");
        await setOlderFilename(
            outputDir,
            initialState,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "old.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("remote renamed, cycle", async () => {
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "index.md"',
            'pull: renamed "Bestiary.md" to "Home.md"',
            'pull: renamed "index.md" to "Bestiary.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("remote renamed, cycle, local edited", async () => {
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");
        await modifyFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot rename "Home.md": Path 'home' already exists.`,
            'pull: SKIPPING rename "Home.md" to "index.md", ' +
                "local changes would be lost",
            'pull: ERROR cannot rename "Bestiary.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "index.md" to "Bestiary.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
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
    });

    test("remote renamed, cycle, untracked file", async () => {
        await setOlderFilename(outputDir, initialState, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, initialState, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, initialState, "index.md", "Home.md");
        await setOlderFilename(outputDir, initialState, "temp.md", "index.md");
        untrackFile(initialState, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "Home.md": Path 'home' already exists.`,
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
    });

    test("local edited", async () => {
        await modifyFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['push: "index.md" (v2)']);
        await assertFileUnchanged(outputDir, "index.md");
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
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local edited, remote edited", async () => {
        await setOlderContent(outputDir, initialState, "Bestiary.md");
        await modifyFile(outputDir, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: "Bestiary.md" (v3, remote changes overwritten)',
        ]);
        await assertFileUnchanged(outputDir, "Bestiary.md");
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
    });

    test("local edited, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await modifyFile(outputDir, "NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "characters/NPCs.md" to "NPCs.md"',
            'push: "NPCs.md" (v4)',
        ]);
        await assertFilePushed(
            outputDir,
            "NPCs.md",
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
        await assertTrackedFileIntact(outputDir, result.state, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            result.state,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await modifyFile(outputDir, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Home.md" to "Welcome.md"',
            'push: "Welcome.md" (v4, remote changes overwritten)',
        ]);
        await assertFilePushed(
            outputDir,
            "Welcome.md",
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
    });

    test("remote deleted", async () => {
        await fileTracksDeletedRemote(
            outputDir,
            initialState,
            "archive/Old Notes.md",
            token,
        );

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

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
    });

    test("remote deleted, local edited", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await modifyFile(outputDir, "Old Notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['push: "Old Notes.md" (v2)']);
        await assertFileUnchanged(outputDir, "Old Notes.md");
        await assertFilePushed(
            outputDir,
            "Old Notes.md",
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
    });

    test("stale file", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

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
    });

    test("stale file, remote edited", async () => {
        markFileStale(initialState, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("stale file, local edited", async () => {
        markFileStale(initialState, "index.md");
        await modifyFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            `push: ERROR cannot push "index.md": Path 'index' already exists.`,
            'pull: ERROR cannot pull "index.md", blocked by local file',
        ]);
        await assertFileUnchanged(outputDir, "index.md");
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
    });

    test("stale file, local deleted", async () => {
        await addStaleFile(outputDir, initialState, "my-notes.md");
        await deleteTrackedFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, result.state, "my-notes.md");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("stale file, local deleted, remote edited", async () => {
        markFileStale(initialState, "index.md");
        await deleteTrackedFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        assertNotInState(result.state, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("local deleted", async () => {
        await deleteTrackedFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

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
    });

    test("local deleted, remote edited", async () => {
        await setOlderContent(outputDir, initialState, "Bestiary.md");
        await deleteTrackedFile(outputDir, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: deleted "Bestiary.md" (had remote changes)',
        ]);
        await assertFileDeletedOnServer(outputDir, result.state, "Bestiary.md", token);
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
    });

    test("local deleted, remote renamed", async () => {
        await setOlderFilename(
            outputDir,
            initialState,
            "characters/NPCs.md",
            "NPCs.md",
        );
        await deleteTrackedFile(outputDir, "NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "characters/NPCs.md" to "NPCs.md"',
            'push: deleted "NPCs.md"',
        ]);
        await assertFileDeletedOnServer(outputDir, result.state, "NPCs.md", token);
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
    });

    test("local deleted, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Home.md" to "Welcome.md"',
            'push: deleted "Welcome.md" (had remote changes)',
        ]);
        await assertFileDeletedOnServer(outputDir, result.state, "Welcome.md", token);
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
    });

    test("local deleted, local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, initialState, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Home.md" to "Welcome.md"',
            'push: deleted "Welcome.md" (had remote changes)',
            'push: "Home.md" (v1)',
        ]);
        await assertServerFileDeleted("Welcome.md", token);
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
    });

    test("local deleted, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await deleteTrackedFile(outputDir, "Old Notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
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
    });

    test("local renamed", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

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
    });

    test("local renamed, local edited", async () => {
        await renameLocalFile(outputDir, initialState, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "index.md" to "renamed-index.md"',
            'push: "renamed-index.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
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
    });

    test("local renamed, remote edited", async () => {
        await renameLocalFile(
            outputDir,
            initialState,
            "Bestiary.md",
            "renamed-bestiary.md",
        );
        await setOlderContent(outputDir, initialState, "renamed-bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "renamed-bestiary.md"',
            'pull: "renamed-bestiary.md" (v3)',
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

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Bestiary.md" to "renamed-bestiary.md"',
            'push: "renamed-bestiary.md" (v4, remote changes overwritten)',
        ]);
        await assertFileUnchanged(outputDir, "renamed-bestiary.md");
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
    });

    test("local renamed, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['push: renamed "index.md" to "my-index.md"']);
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
    });

    test("local renamed, local edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "index.md" to "my-index.md"',
            'push: "my-index.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        await assertFilePushed(
            outputDir,
            "my-index.md",
            result.state,
            token,
            "text/markdown",
        );
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
    });

    test("local renamed, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await setOlderContent(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "index.md" to "my-index.md"',
            'pull: "my-index.md" (v2)',
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
    });

    test("local renamed, local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, initialState, "index.md", "original.md");
        await setOlderContent(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "index.md" to "my-index.md"',
            'push: "my-index.md" (v3, remote changes overwritten)',
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        await assertFilePushed(
            outputDir,
            "my-index.md",
            result.state,
            token,
            "text/markdown",
        );
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
    });

    test("local renamed, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await renameLocalFile(outputDir, initialState, "Old Notes.md", "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Old Notes.md" to "my-notes.md"',
        ]);
        await assertTrackedFileIntact(outputDir, result.state, "my-notes.md");
        await assertFilePushed(
            outputDir,
            "my-notes.md",
            result.state,
            token,
            "text/markdown",
        );
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
    });

    test("local renamed, local edited, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, initialState, "Old Notes.md", token);
        await renameLocalFile(outputDir, initialState, "Old Notes.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: renamed "Old Notes.md" to "my-notes.md"',
            'push: "my-notes.md" (v3)',
        ]);
        await assertFileUnchanged(outputDir, "my-notes.md");
        await assertFilePushed(
            outputDir,
            "my-notes.md",
            result.state,
            token,
            "text/markdown",
        );
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
    });

    test("local renamed, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

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
    });

    test("local renamed, local edited, stale file", async () => {
        await addStaleFile(outputDir, initialState, "original.md");
        await renameLocalFile(outputDir, initialState, "original.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['push: "my-notes.md" (v1)']);
        await assertFileUnchanged(outputDir, "my-notes.md");
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
    });

    test("local renamed untracked, hash match", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

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
    });

    test("local renamed untracked, hash mismatch", async () => {
        await renameLocalFileUntracked(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            initialState,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'push: deleted "index.md"',
            'push: "renamed-index.md" (v1)',
        ]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
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
    });
});

import { afterEach, beforeAll, beforeEach, describe, expect, test } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
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

    beforeAll(async () => {
        token = await getToken();
        restoreDatabase();
        clearPagesCache();
    });

    beforeEach(async () => {
        ({ testDir, outputDir } = await createTestDir());
        await initSyncedDir(outputDir, token);
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
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("untracked file", async () => {
        await createFile(outputDir, "scratchpad.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertFileIgnored(outputDir, "scratchpad.txt");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
        await assertStateMatchesFixture(outputDir);
    });

    test("untracked file, local edited, directory", async () => {
        await untrackAndRemoveFile(outputDir, "Bestiary.md");
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Bestiary.md", blocked by local directory',
        ]);
        await assertFileIgnored(outputDir, "Bestiary.md/notes.txt");
        await assertFileNotDownloaded(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("untracked file, local edited", async () => {
        await untrackFile(outputDir, "Home.md");
        await modifyFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "Home.md", blocked by local file',
        ]);
        await assertFileIgnored(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("untracked file, remote renamed", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "NPCs.md");
        await createFile(outputDir, "characters/NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local file",
        ]);
        await assertFileMatchesFixture(outputDir, "characters/NPCs.md", "NPCs.md");
        await assertFileIgnored(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("untracked file, local edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Welcome.md" to "Home.md", ' +
                "blocked by local file",
        ]);
        await assertFileIgnored(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "Welcome.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("remote edited", async () => {
        await setOlderContent(outputDir, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Bestiary.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed", async () => {
        await setOlderFilename(outputDir, "The Old Café.md", "café.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expected = ['pull: renamed "café.md" to "The Old Café.md"'];
        expect(result.output).toEqual(expected);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, local edited, directory", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "NPCs.md");
        await createFile(outputDir, "characters/NPCs.md/notes.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "NPCs.md" to "characters/NPCs.md", ' +
                "blocked by local directory",
        ]);
        await assertTrackedFileIntact(outputDir, "NPCs.md");
        await assertFileIgnored(outputDir, "characters/NPCs.md/notes.txt");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Welcome.md" to "Home.md"',
            'pull: "Home.md" (v2)',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, swapped", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "temp.md");
        await setOlderFilename(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );
        await setOlderFilename(outputDir, "temp.md", "sessions/session-01.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, chain", async () => {
        await setOlderFilename(outputDir, "sessions/session-01.md", "old.md");
        await setOlderFilename(
            outputDir,
            "characters/NPCs.md",
            "sessions/session-01.md",
        );

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "old.md" to "sessions/session-01.md"',
            'pull: renamed "sessions/session-01.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, chain reversed", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "old.md");
        await setOlderFilename(
            outputDir,
            "sessions/session-01.md",
            "characters/NPCs.md",
        );

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "characters/NPCs.md" to "sessions/session-01.md"',
            'pull: renamed "old.md" to "characters/NPCs.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, cycle", async () => {
        await setOlderFilename(outputDir, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, "index.md", "Home.md");
        await setOlderFilename(outputDir, "temp.md", "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: renamed "Home.md" to "index.md"',
            'pull: renamed "Bestiary.md" to "Home.md"',
            'pull: renamed "index.md" to "Bestiary.md"',
        ]);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("remote renamed, cycle, local edited", async () => {
        await setOlderFilename(outputDir, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, "index.md", "Home.md");
        await setOlderFilename(outputDir, "temp.md", "index.md");
        await modifyFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

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
        await assertFileInState(outputDir, "Home.md");
        await assertTrackedFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertTrackedFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("remote renamed, cycle, untracked file", async () => {
        await setOlderFilename(outputDir, "Bestiary.md", "temp.md");
        await setOlderFilename(outputDir, "Home.md", "Bestiary.md");
        await setOlderFilename(outputDir, "index.md", "Home.md");
        await setOlderFilename(outputDir, "temp.md", "index.md");
        await untrackFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot pull "index.md", blocked by local file',
            'pull: ERROR cannot rename "Bestiary.md" to "Home.md", ' +
                "blocked by local file",
            'pull: ERROR cannot rename "index.md" to "Bestiary.md", ' +
                "blocked by local file",
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "Home.md");
        await assertFileNotInState(outputDir, "Home.md");
        await assertTrackedFileMatchesFixture(outputDir, "Home.md", "Bestiary.md");
        await assertTrackedFileMatchesFixture(outputDir, "Bestiary.md", "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
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
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertFileUnchanged(outputDir, "index.md");
        await assertFileInState(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local edited, remote edited", async () => {
        await setOlderContent(outputDir, "Bestiary.md");
        await modifyFile(outputDir, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "Bestiary.md");
        await assertFileInState(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "NPCs.md");
        await modifyFile(outputDir, "NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "NPCs.md");
        await assertFileInState(outputDir, "NPCs.md");
        await assertFileNotDownloaded(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, "Welcome.md");
        await modifyFile(outputDir, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "Welcome.md" to "Home.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "Welcome.md");
        await assertFileInState(outputDir, "Welcome.md");
        await assertFileNotDownloaded(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, "archive/Old Notes.md", token);

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "archive/Old Notes.md"']);
        await assertTrackedFileDeleted(outputDir, "archive/Old Notes.md");
        await assertEmptyDirRemoved(outputDir, "archive");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("remote deleted, local edited", async () => {
        await fileTracksDeletedRemote(outputDir, "Old Notes.md", token);
        await modifyFile(outputDir, "Old Notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "Old Notes.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "Old Notes.md");
        await assertFileInState(outputDir, "Old Notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("stale file", async () => {
        await addStaleFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, "my-notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("stale file, remote edited", async () => {
        await markFileStale(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        await assertNotInState(outputDir, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("stale file, local edited", async () => {
        await markFileStale(outputDir, "index.md");
        await modifyFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "index.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "index.md");
        await assertFileInState(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("stale file, local deleted", async () => {
        await addStaleFile(outputDir, "my-notes.md");
        await deleteTrackedFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertTrackedFileDeleted(outputDir, "my-notes.md");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("stale file, local deleted, remote edited", async () => {
        await markFileStale(outputDir, "index.md");
        await deleteTrackedFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "index.md" (v1)']);
        await assertNotInState(outputDir, "stale-uuid");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("local deleted", async () => {
        await deleteTrackedFile(outputDir, "index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", already deleted locally',
        ]);
        await assertTrackedFileNotRestored(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local deleted, remote edited", async () => {
        await setOlderContent(outputDir, "Bestiary.md");
        await deleteTrackedFile(outputDir, "Bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Bestiary.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("local deleted, remote renamed", async () => {
        await setOlderFilename(outputDir, "characters/NPCs.md", "NPCs.md");
        await deleteTrackedFile(outputDir, "NPCs.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "NPCs.md" to "characters/NPCs.md", ' +
                '"NPCs.md" deleted locally',
        ]);
        await assertTrackedFileNotRestored(outputDir, "NPCs.md");
        await assertFileNotDownloaded(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local deleted, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: "Home.md" (v2)']);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("local deleted, local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "Home.md", "Welcome.md");
        await setOlderContent(outputDir, "Welcome.md");
        await deleteTrackedFile(outputDir, "Welcome.md");
        await createFile(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: ERROR cannot rename "Welcome.md" to "Home.md", ' +
                "blocked by local file",
        ]);
        await assertFileUnchanged(outputDir, "Home.md");
        await assertFileNotInState(outputDir, "Home.md");
        await assertTrackedFileNotRestored(outputDir, "Welcome.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local deleted, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, "Old Notes.md", token);
        await deleteTrackedFile(outputDir, "Old Notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "Old Notes.md"']);
        await assertTrackedFileDeleted(outputDir, "Old Notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed", async () => {
        await renameLocalFile(outputDir, "index.md", "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        await assertFileInState(outputDir, "renamed-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited", async () => {
        await renameLocalFile(outputDir, "index.md", "renamed-index.md");
        await modifyFile(outputDir, "renamed-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
        await assertFileInState(outputDir, "renamed-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, remote edited", async () => {
        await renameLocalFile(outputDir, "Bestiary.md", "renamed-bestiary.md");
        await setOlderContent(outputDir, "renamed-bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: "Bestiary.md" to "renamed-bestiary.md" (v2)',
        ]);
        await assertFileMatchesFixture(outputDir, "Bestiary.md", "renamed-bestiary.md");
        await assertFileInState(outputDir, "renamed-bestiary.md");
        await assertFileNotInState(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited, remote edited", async () => {
        await renameLocalFile(outputDir, "Bestiary.md", "renamed-bestiary.md");
        await setOlderContent(outputDir, "renamed-bestiary.md");
        await modifyFile(outputDir, "renamed-bestiary.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "Bestiary.md" to "renamed-bestiary.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "renamed-bestiary.md");
        await assertFileInState(outputDir, "renamed-bestiary.md");
        await assertFileNotInState(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, remote renamed", async () => {
        await setOlderFilename(outputDir, "index.md", "original.md");
        await renameLocalFile(outputDir, "original.md", "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        await assertFileInState(outputDir, "my-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertFileNotInState(outputDir, "original.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "index.md", "original.md");
        await renameLocalFile(outputDir, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        await assertFileInState(outputDir, "my-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertFileNotInState(outputDir, "original.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "index.md", "original.md");
        await setOlderContent(outputDir, "original.md");
        await renameLocalFile(outputDir, "original.md", "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
            'pull: "index.md" to "my-index.md" (v1)',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "my-index.md");
        await assertFileInState(outputDir, "my-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertFileNotInState(outputDir, "original.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited, remote edited, remote renamed", async () => {
        await setOlderFilename(outputDir, "index.md", "original.md");
        await setOlderContent(outputDir, "original.md");
        await renameLocalFile(outputDir, "original.md", "my-index.md");
        await modifyFile(outputDir, "my-index.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING rename "original.md" to "index.md", ' +
                'already "my-index.md" locally',
            'pull: SKIPPING pull "index.md" to "my-index.md", ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "my-index.md");
        await assertFileInState(outputDir, "my-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertFileNotInState(outputDir, "original.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, "Old Notes.md", token);
        await renameLocalFile(outputDir, "Old Notes.md", "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: deleted "Old Notes.md" (was "my-notes.md")',
        ]);
        await assertTrackedFileDeleted(outputDir, "my-notes.md");
        await assertFileNotInState(outputDir, "Old Notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited, remote deleted", async () => {
        await fileTracksDeletedRemote(outputDir, "Old Notes.md", token);
        await renameLocalFile(outputDir, "Old Notes.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "Old Notes.md" (at "my-notes.md"), ' +
                "local changes would be lost",
        ]);
        await assertFileUnchanged(outputDir, "my-notes.md");
        await assertFileInState(outputDir, "my-notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, stale file", async () => {
        await addStaleFile(outputDir, "original.md");
        await renameLocalFile(outputDir, "original.md", "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual(['pull: deleted "my-notes.md"']);
        await assertTrackedFileDeleted(outputDir, "my-notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local renamed, local edited, stale file", async () => {
        await addStaleFile(outputDir, "original.md");
        await renameLocalFile(outputDir, "original.md", "my-notes.md");
        await modifyFile(outputDir, "my-notes.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING delete "my-notes.md", local changes would be lost',
        ]);
        await assertFileUnchanged(outputDir, "my-notes.md");
        await assertFileInState(outputDir, "my-notes.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
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
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'info: detected rename "index.md" to "renamed-index.md"',
        ]);
        await assertFileMatchesFixture(outputDir, "index.md", "renamed-index.md");
        await assertFileInState(outputDir, "renamed-index.md");
        await assertFileNotInState(outputDir, "index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
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
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([
            'pull: SKIPPING pull "index.md", already deleted locally',
        ]);
        await assertFileUnchanged(outputDir, "renamed-index.md");
        await assertFileNotInState(outputDir, "renamed-index.md");
        await assertTrackedFileIntact(outputDir, "random-hexmap-7.png");
        await assertTrackedFileIntact(outputDir, "Home.md");
        await assertTrackedFileIntact(outputDir, "sessions/session-01.md");
        await assertTrackedFileIntact(outputDir, "Bestiary.md");
        await assertTrackedFileIntact(outputDir, "characters/NPCs.md");
        await assertTrackedFileIntact(outputDir, "The Old Café.md");
        await assertTrackedFileIntact(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });
});

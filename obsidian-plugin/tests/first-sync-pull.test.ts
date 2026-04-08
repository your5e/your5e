/**
 * First sync pull tests
 *
 * Tests for syncing to a directory that has never been synced before
 * (no .sync-state file exists), in pull-only mode.
 *
 * Ported from tests/first_sync_pull.bats
 */

import { afterEach, beforeAll, beforeEach, describe, expect, test } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import {
    API_BASE,
    assertDirMatchesFixture,
    assertFileDownloaded,
    assertFileIgnored,
    assertFileMatchesFixture,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertOutputDirExists,
    assertStateIsEmpty,
    assertStateMatchesFixture,
    cleanupTestDir,
    copyFixture,
    createFile,
    createTestDir,
    getToken,
    restoreDatabase,
} from "./helpers.js";

describe("first sync pull", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;

    beforeAll(async () => {
        token = await getToken();
    });

    beforeEach(async () => {
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
    });

    test("empty directory", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
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

        await assertFileNotDownloaded(outputDir, "Old Notes.md");
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("empty notebook", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/empty-notebook",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertOutputDirExists(outputDir);
        await assertStateIsEmpty(outputDir);
    });

    test("local files", async () => {
        await createFile(outputDir, "Home.md");
        await createFile(outputDir, "index.md");
        await createFile(outputDir, "notes.txt");
        await createFile(outputDir, "sessions/notes.txt");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: ERROR cannot pull "index.md", blocked by local file',
            'pull: ERROR cannot pull "Home.md", blocked by local file',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileIgnored(outputDir, "Home.md");
        await assertFileIgnored(outputDir, "index.md");
        await assertFileIgnored(outputDir, "notes.txt");
        await assertFileIgnored(outputDir, "sessions/notes.txt");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local matches remote", async () => {
        await copyFixture(outputDir, "Home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: tracking "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(outputDir);
    });

    test("local file clashes", async () => {
        await createFile(outputDir, "sessions");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            'pull: ERROR cannot pull "sessions/session-01.md", blocked by local file',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileIgnored(outputDir, "sessions");
        await assertFileNotDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "index.md");
        await assertFileDownloaded(outputDir, "Home.md");
        await assertFileDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("local dir clashes", async () => {
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

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: ERROR cannot pull "Bestiary.md", blocked by local directory',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileIgnored(outputDir, "Bestiary.md/notes.txt");
        await assertFileNotDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "index.md");
        await assertFileDownloaded(outputDir, "Home.md");
        await assertFileDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("hidden files ignored", async () => {
        await createFile(outputDir, ".hidden.md");
        await createFile(outputDir, ".obsidian/app.json");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
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

        await assertFileUnchanged(outputDir, ".hidden.md");
        await assertFileUnchanged(outputDir, ".obsidian/app.json");
        await assertStateMatchesFixture(outputDir);
    });

    test("case collision", async () => {
        await createFile(outputDir, "home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: ERROR cannot pull "Home.md", ' +
                "blocked by local file with different case",
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileIgnored(outputDir, "home.md");
        await assertFileNotInState(outputDir, "Home.md");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "index.md");
        await assertFileDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });

    test("case collision, matches", async () => {
        await copyFixture(outputDir, "Home.md", "home.md");

        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: ERROR cannot pull "Home.md", ' +
                "blocked by local file with different case",
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileMatchesFixture(outputDir, "Home.md", "home.md");
        await assertFileNotInState(outputDir, "Home.md");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "index.md");
        await assertFileDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });
});

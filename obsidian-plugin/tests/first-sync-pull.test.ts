/**
 * First sync pull tests
 *
 * Tests for syncing to a directory that has never been synced before
 * (no sync state exists), in pull-only mode.
 *
 * Ported from tests/first_sync_pull.bats
 */

import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
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
    assertLastUpdateIsEpoch,
    assertLastUpdateMatchesExpected,
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

        const originalFetch = global.fetch;
        vi.spyOn(global, "fetch").mockImplementation((input, init) => {
            const url = typeof input === "string" ? input : input.url;
            if (url.includes("since=")) {
                throw new Error("TEST GUARD: since parameter forbidden but was passed");
            }
            return originalFetch(input, init);
        });
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
        vi.restoreAllMocks();
    });

    function createSync(
        overrides: {
            notebook?: string;
        } = {},
    ): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: overrides.notebook ?? "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });
    }

    test("empty directory", async () => {
        const sync = createSync();

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

        await assertFileNotDownloaded(outputDir, "Old Notes.md", result.state);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("empty notebook", async () => {
        const sync = createSync({ notebook: "norm/empty-notebook" });

        const result = await sync.run();

        expect(result.output).toEqual([]);
        await assertOutputDirExists(outputDir);
        assertStateIsEmpty(result.state);
        assertLastUpdateIsEpoch(result.lastUpdate);
    });

    test("local files", async () => {
        await createFile(outputDir, "Home.md");
        await createFile(outputDir, "index.md");
        await createFile(outputDir, "notes.txt");
        await createFile(outputDir, "sessions/notes.txt");

        const sync = createSync();

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

        await assertFileIgnored(outputDir, "Home.md", result.state);
        await assertFileIgnored(outputDir, "index.md", result.state);
        await assertFileIgnored(outputDir, "notes.txt", result.state);
        await assertFileIgnored(outputDir, "sessions/notes.txt", result.state);
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "sessions/session-01.md", result.state);
        await assertFileDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local matches remote", async () => {
        await copyFixture(outputDir, "Home.md");

        const sync = createSync();

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
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local file clashes", async () => {
        await createFile(outputDir, "sessions");

        const sync = createSync();

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

        await assertFileIgnored(outputDir, "sessions", result.state);
        await assertFileNotDownloaded(
            outputDir,
            "sessions/session-01.md",
            result.state,
        );
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "index.md", result.state);
        await assertFileDownloaded(outputDir, "Home.md", result.state);
        await assertFileDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local dir clashes", async () => {
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = createSync();

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

        await assertFileIgnored(outputDir, "Bestiary.md/notes.txt", result.state);
        await assertFileNotDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "index.md", result.state);
        await assertFileDownloaded(outputDir, "Home.md", result.state);
        await assertFileDownloaded(outputDir, "sessions/session-01.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("hidden files ignored", async () => {
        await createFile(outputDir, ".hidden.md");
        await createFile(outputDir, ".obsidian/app.json");

        const sync = createSync();

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
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision", async () => {
        await createFile(outputDir, "home.md");

        const sync = createSync();

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

        await assertFileIgnored(outputDir, "home.md", result.state);
        assertFileNotInState("Home.md", result.state);
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "index.md", result.state);
        await assertFileDownloaded(outputDir, "sessions/session-01.md", result.state);
        await assertFileDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision, matches", async () => {
        await copyFixture(outputDir, "Home.md", "home.md");

        const sync = createSync();

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
        assertFileNotInState("Home.md", result.state);
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "index.md", result.state);
        await assertFileDownloaded(outputDir, "sessions/session-01.md", result.state);
        await assertFileDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });
});

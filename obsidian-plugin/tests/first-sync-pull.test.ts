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
    assertFileMatchesFixture,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertFixtureFilesDownloaded,
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
    guardNoSinceParameter,
    restoreDatabase,
    runSync,
    shortHostname,
} from "./helpers.js";

describe("first sync pull", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    let SHORT_HOST: string;

    beforeAll(async () => {
        token = await getToken();
        SHORT_HOST = shortHostname();
    });

    beforeEach(async () => {
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
        guardNoSinceParameter();
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
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

        const result = await runSync(sync);

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

        const result = await runSync(sync);

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

        const result = await runSync(sync);

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            `info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"`,
            'pull: "index.md" (v1)',
            `info: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"`,
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileUnchanged(outputDir, `Home (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`Home (conflict ${SHORT_HOST}).md`, result.state);
        await assertFileUnchanged(outputDir, `index (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`index (conflict ${SHORT_HOST}).md`, result.state);
        await assertFileUnchanged(outputDir, "notes.txt");
        await assertFileUnchanged(outputDir, "sessions/notes.txt");
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local matches remote", async () => {
        await copyFixture(outputDir, "Home.md");

        const sync = createSync();

        const result = await runSync(sync);

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

        const result = await runSync(sync);

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            `info: renamed "sessions" to "sessions (conflict ${SHORT_HOST})"`,
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileUnchanged(outputDir, `sessions (conflict ${SHORT_HOST})`);
        assertFileNotInState(`sessions (conflict ${SHORT_HOST})`, result.state);
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local dir clashes", async () => {
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileUnchanged(
            outputDir,
            `Bestiary (conflict ${SHORT_HOST}).md/notes.txt`,
        );
        assertFileNotInState(
            `Bestiary (conflict ${SHORT_HOST}).md/notes.txt`,
            result.state,
        );
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("hidden files ignored", async () => {
        await createFile(outputDir, ".hidden.md");
        await createFile(outputDir, ".obsidian/app.json");

        const sync = createSync();

        const result = await runSync(sync);

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
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision", async () => {
        await createFile(outputDir, "home.md");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            `info: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"`,
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileUnchanged(outputDir, `home (conflict ${SHORT_HOST}).md`);
        assertFileNotInState(`home (conflict ${SHORT_HOST}).md`, result.state);
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision, matches", async () => {
        await copyFixture(outputDir, "Home.md", "home.md");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            `info: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"`,
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];
        expect(result.output).toEqual(expectedOutput);

        await assertFileMatchesFixture(
            outputDir,
            "Home.md",
            `home (conflict ${SHORT_HOST}).md`,
        );
        assertFileNotInState(`home (conflict ${SHORT_HOST}).md`, result.state);
        await assertFixtureFilesDownloaded(outputDir);
        await assertStateMatchesFixture(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });
});

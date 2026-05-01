/**
 * First sync push tests
 *
 * Tests for syncing to a directory that has never been synced before
 * (no sync state exists), with push enabled.
 *
 * Ported from tests/first_sync_push.bats
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
    assertFilePushed,
    assertFileUnchanged,
    assertFixtureFilesDownloaded,
    assertFixtureFilesInState,
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

describe("first sync push", () => {
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
            `info: renamed "Home.md" to "Home (conflict ${SHORT_HOST}).md"`,
            `push: "Home (conflict ${SHORT_HOST}).md" (v1)`,
            `info: renamed "index.md" to "index (conflict ${SHORT_HOST}).md"`,
            `push: "index (conflict ${SHORT_HOST}).md" (v1)`,
            'push: "notes.txt" (v1)',
            'push: "sessions/notes.txt" (v1)',
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

        await assertFileUnchanged(outputDir, `Home (conflict ${SHORT_HOST}).md`);
        await assertFilePushed(
            outputDir,
            `Home (conflict ${SHORT_HOST}).md`,
            result.state,
            token,
            "text/markdown",
        );
        await assertFileUnchanged(outputDir, `index (conflict ${SHORT_HOST}).md`);
        await assertFilePushed(
            outputDir,
            `index (conflict ${SHORT_HOST}).md`,
            result.state,
            token,
            "text/markdown",
        );
        await assertFilePushed(
            outputDir,
            "notes.txt",
            result.state,
            token,
            "text/plain",
        );
        await assertFilePushed(
            outputDir,
            "sessions/notes.txt",
            result.state,
            token,
            "text/plain",
        );
        await assertFixtureFilesDownloaded(outputDir);
        await assertFixtureFilesInState(result.state);
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
            `push: ERROR cannot push "sessions": Filename must have an extension.`,
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
        await assertFixtureFilesInState(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("local dir clashes", async () => {
        await createFile(outputDir, "Bestiary.md/notes.txt");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            `info: renamed "Bestiary.md" to "Bestiary (conflict ${SHORT_HOST}).md"`,
            `push: "Bestiary (conflict ${SHORT_HOST}).md/notes.txt" (v1)`,
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

        await assertFileUnchanged(
            outputDir,
            `Bestiary (conflict ${SHORT_HOST}).md/notes.txt`,
        );
        await assertFilePushed(
            outputDir,
            `Bestiary (conflict ${SHORT_HOST}).md/notes.txt`,
            result.state,
            token,
            "text/plain",
        );
        await assertFixtureFilesDownloaded(outputDir);
        await assertFixtureFilesInState(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("hidden files ignored", async () => {
        await createFile(outputDir, ".hidden.md");
        await createFile(outputDir, ".obsidian/app.json");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            `push: ERROR cannot push ".hidden.md": No hidden files.`,
            `push: ERROR cannot push ".obsidian/app.json": No hidden files.`,
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
        await assertFixtureFilesInState(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision", async () => {
        await createFile(outputDir, "home.md");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            `info: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"`,
            `push: "home (conflict ${SHORT_HOST}).md" (v1)`,
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

        await assertFileUnchanged(outputDir, `home (conflict ${SHORT_HOST}).md`);
        await assertFilePushed(
            outputDir,
            `home (conflict ${SHORT_HOST}).md`,
            result.state,
            token,
            "text/markdown",
        );
        await assertFixtureFilesDownloaded(outputDir);
        await assertFixtureFilesInState(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });

    test("case collision, matches", async () => {
        await copyFixture(outputDir, "Home.md", "home.md");

        const sync = createSync();

        const result = await runSync(sync);

        const expectedOutput = [
            `info: renamed "home.md" to "home (conflict ${SHORT_HOST}).md"`,
            `push: "home (conflict ${SHORT_HOST}).md" (v1)`,
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

        await assertFileMatchesFixture(
            outputDir,
            "Home.md",
            `home (conflict ${SHORT_HOST}).md`,
        );
        await assertFilePushed(
            outputDir,
            `home (conflict ${SHORT_HOST}).md`,
            result.state,
            token,
            "text/markdown",
        );
        await assertFixtureFilesDownloaded(outputDir);
        await assertFixtureFilesInState(result.state);
        await assertLastUpdateMatchesExpected(result.lastUpdate);
    });
});

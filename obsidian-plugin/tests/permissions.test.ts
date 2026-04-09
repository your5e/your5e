/**
 * Sync permission tests
 *
 * Tests for sync script behaviour with different user permission levels.
 *
 * This file tests the reference implementation (sync-engine.ts) and documents
 * the expected behaviour of ANY notebook sync client. Implementers should use
 * these scenarios to verify their own sync logic produces the same outcomes.
 *
 * Ported from tests/sync_permissions.bats
 */

import { afterEach, beforeAll, beforeEach, describe, expect, test } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import {
    API_BASE,
    assertDirMatchesFixture,
    assertFileNotDownloaded,
    assertNoOutputDir,
    assertStateMatchesFixture,
    cleanupTestDir,
    createTestDir,
    getToken,
    restoreDatabase,
} from "./helpers.js";

describe("sync permissions", () => {
    let normToken: string;
    let susanToken: string;
    let hughToken: string;
    let wendyToken: string;
    let testDir: string;
    let outputDir: string;

    beforeAll(async () => {
        normToken = await getToken("norm");
        susanToken = await getToken("susan");
        hughToken = await getToken("hugh");
        wendyToken = await getToken("wendy");
    });

    beforeEach(async () => {
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
    });

    test("full sync switches to pull when user is viewer", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: susanToken,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
        });

        const result = await sync.run();

        const expectedOutput = [
            "sync: NOTE read-only access, switching to pull-only mode",
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
    });

    test("pull, non-collaborator, public", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: hughToken,
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

        await assertFileNotDownloaded(outputDir, "Old Notes.md", result.state);
        await assertDirMatchesFixture(outputDir);
        await assertStateMatchesFixture(result.state);
    });

    test("pull, non-collaborator, private", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: hughToken,
            notebook: "wendy/world-building",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, invalid token", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: "invalid-token-12345",
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("API token invalid");
        await assertNoOutputDir(outputDir);
    });

    test("pull, no token", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: "",
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("API token missing");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, owner", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: normToken,
            notebook: "norm/does-not-exist",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, editor", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: wendyToken,
            notebook: "norm/does-not-exist",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, viewer", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: susanToken,
            notebook: "norm/does-not-exist",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, non-collaborator", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token: hughToken,
            notebook: "norm/does-not-exist",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    // TODO: mid-sync tests require hook mechanism in SyncEngine
    // - mid-sync, revoked, new file
    // - mid-sync, downgraded, new file
    // - mid-sync, revoked, local update
    // - mid-sync, downgraded, local update
    // - mid-sync, revoked, local rename
    // - mid-sync, downgraded, local rename
    // - mid-sync, revoked, local delete
    // - mid-sync, downgraded, local delete
    // - mid-sync, revoked, content update
});

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

import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import type { SyncStateEntry } from "../src/sync/types.js";
import {
    API_BASE,
    assertDirMatchesFixture,
    assertFileModified,
    assertFileNotDownloaded,
    assertFileNotInState,
    assertFileUnchanged,
    assertLastUpdateMatchesExpected,
    assertNoOutputDir,
    assertServerEditedContent,
    assertStateMatchesFixture,
    assertSyncMetadataUpdated,
    assertTrackedFileIntact,
    assertTrackedFileMatchesFixture,
    assertTrackedFileNotRestored,
    cleanupTestDir,
    createFile,
    createTestDir,
    deletePageByUuid,
    downgradeToViewer,
    getToken,
    guardNoSinceParameter,
    guardRequireSinceParameter,
    initSyncedDir,
    invalidateToken,
    modifyFile,
    restoreDatabase,
    runSync,
    serverCreate,
    serverEditContent,
    trackedDelete,
    trackedRename,
    uuidFor,
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
        vi.restoreAllMocks();
    });

    function createSync(overrides: {
        token?: string;
        notebook?: string;
        pullOnly?: boolean;
        initialState?: Map<string, SyncStateEntry>;
        lastUpdate?: string;
        lastFullSync?: string;
        afterFetchHook?: () => Promise<void>;
    }): SyncEngine {
        return new SyncEngine({
            baseUrl: API_BASE,
            token: overrides.token ?? normToken,
            notebook: overrides.notebook ?? "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: overrides.pullOnly,
            initialState: overrides.initialState,
            lastUpdate: overrides.lastUpdate,
            lastFullSync: overrides.lastFullSync,
            afterFetchHook: overrides.afterFetchHook,
        });
    }

    test("full sync switches to pull", async () => {
        guardNoSinceParameter();
        const sync = createSync({ token: susanToken });

        const result = await runSync(sync);

        const expectedOutput = [
            "NOTE read-only access, switching to pull-only mode",
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

    test("pull, non-collaborator, public", async () => {
        guardNoSinceParameter();
        const sync = createSync({ token: hughToken, pullOnly: true });

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

    test("pull, non-collaborator, private", async () => {
        const sync = createSync({
            token: hughToken,
            notebook: "wendy/world-building",
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, invalid token", async () => {
        const sync = createSync({ token: "invalid-token-12345", pullOnly: true });

        await expect(sync.run()).rejects.toThrow("API token invalid");
        await assertNoOutputDir(outputDir);
    });

    test("pull, no token", async () => {
        const sync = createSync({ token: "", pullOnly: true });

        await expect(sync.run()).rejects.toThrow("API token missing");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, owner", async () => {
        const sync = createSync({ notebook: "norm/does-not-exist", pullOnly: true });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, editor", async () => {
        const sync = createSync({
            token: wendyToken,
            notebook: "norm/does-not-exist",
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, viewer", async () => {
        const sync = createSync({
            token: susanToken,
            notebook: "norm/does-not-exist",
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    test("pull, non-existent, non-collaborator", async () => {
        const sync = createSync({
            token: hughToken,
            notebook: "norm/does-not-exist",
            pullOnly: true,
        });

        await expect(sync.run()).rejects.toThrow("Notebook not found");
        await assertNoOutputDir(outputDir);
    });

    describe("mid-sync permission changes", () => {
        let initialState: Map<string, SyncStateEntry>;
        const recentSyncTime = new Date().toISOString();

        beforeEach(async () => {
            vi.restoreAllMocks();
            initialState = await initSyncedDir(outputDir, normToken);
            guardRequireSinceParameter();
        });

        test("mid-sync, revoked, new file", async () => {
            await createFile(outputDir, "newfile.md");
            const sync = createSync({
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    invalidateToken(normToken);
                },
            });

            await expect(sync.run()).rejects.toThrow("API token invalid");

            await assertFileUnchanged(outputDir, "newfile.md");
            await assertTrackedFileMatchesFixture(outputDir, initialState, "index.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "Bestiary.md",
            );
            await assertTrackedFileMatchesFixture(outputDir, initialState, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "random-hexmap-7.png",
            );
        });

        test("mid-sync, downgraded, new file", async () => {
            await serverEditContent(
                normToken,
                await uuidFor(initialState, "Bestiary.md"),
            );
            await createFile(outputDir, "newfile.md");
            const sync = createSync({
                token: wendyToken,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    downgradeToViewer("wendy", "norm", "campaign-notes");
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                "NOTE permission denied, switching to pull-only mode",
                'pull: "Bestiary.md" (v3)',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertFileUnchanged(outputDir, "newfile.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "index.md");
            await assertServerEditedContent(outputDir, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });

        test("mid-sync, revoked, local update", async () => {
            await modifyFile(outputDir, "index.md");
            const sync = createSync({
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    invalidateToken(normToken);
                },
            });

            await expect(sync.run()).rejects.toThrow("API token invalid");

            await assertFileModified(outputDir, "index.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "Bestiary.md",
            );
            await assertTrackedFileMatchesFixture(outputDir, initialState, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "random-hexmap-7.png",
            );
        });

        test("mid-sync, downgraded, local update", async () => {
            await serverEditContent(
                normToken,
                await uuidFor(initialState, "Bestiary.md"),
            );
            await modifyFile(outputDir, "index.md");
            const sync = createSync({
                token: wendyToken,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    downgradeToViewer("wendy", "norm", "campaign-notes");
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                "NOTE permission denied, switching to pull-only mode",
                'pull: "Bestiary.md" (v3)',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertFileModified(outputDir, "index.md");
            await assertServerEditedContent(outputDir, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });

        test("mid-sync, revoked, local rename", async () => {
            await trackedRename(outputDir, initialState, "index.md", "renamed.md");
            const sync = createSync({
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    invalidateToken(normToken);
                },
            });

            await expect(sync.run()).rejects.toThrow("API token invalid");

            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "index.md",
                "renamed.md",
            );
            await assertFileNotDownloaded(outputDir, "index.md", initialState);
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "Bestiary.md",
            );
            await assertTrackedFileMatchesFixture(outputDir, initialState, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "random-hexmap-7.png",
            );
        });

        test("mid-sync, downgraded, local rename", async () => {
            await serverEditContent(
                normToken,
                await uuidFor(initialState, "Bestiary.md"),
            );
            await trackedRename(outputDir, initialState, "index.md", "renamed.md");
            const sync = createSync({
                token: wendyToken,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    downgradeToViewer("wendy", "norm", "campaign-notes");
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                "NOTE permission denied, switching to pull-only mode",
                'pull: "Bestiary.md" (v3)',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "index.md",
                "renamed.md",
            );
            await assertFileNotDownloaded(outputDir, "index.md", result.state);
            await assertServerEditedContent(outputDir, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });

        test("mid-sync, revoked, local delete", async () => {
            await trackedDelete(outputDir, "index.md");
            const sync = createSync({
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    invalidateToken(normToken);
                },
            });

            await expect(sync.run()).rejects.toThrow("API token invalid");

            await assertTrackedFileNotRestored(outputDir, initialState, "index.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "Bestiary.md",
            );
            await assertTrackedFileMatchesFixture(outputDir, initialState, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "random-hexmap-7.png",
            );
        });

        test("mid-sync, downgraded, local delete", async () => {
            await serverEditContent(
                normToken,
                await uuidFor(initialState, "Bestiary.md"),
            );
            await trackedDelete(outputDir, "index.md");
            const sync = createSync({
                token: wendyToken,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    downgradeToViewer("wendy", "norm", "campaign-notes");
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                "NOTE permission denied, switching to pull-only mode",
                'pull: "Bestiary.md" (v3)',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertTrackedFileNotRestored(outputDir, result.state, "index.md");
            await assertServerEditedContent(outputDir, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });

        test("mid-sync, revoked, content update", async () => {
            await serverEditContent(
                normToken,
                await uuidFor(initialState, "Bestiary.md"),
            );
            const sync = createSync({
                pullOnly: true,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    invalidateToken(normToken);
                },
            });

            await expect(sync.run()).rejects.toThrow("API token invalid");

            await assertTrackedFileIntact(outputDir, initialState, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, initialState, "index.md");
            await assertTrackedFileMatchesFixture(outputDir, initialState, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                initialState,
                "random-hexmap-7.png",
            );
        });

        test("mid-sync, page deleted, content update", async () => {
            const bestiaryUuid = await uuidFor(initialState, "Bestiary.md");
            await serverEditContent(normToken, bestiaryUuid);
            await serverEditContent(normToken, await uuidFor(initialState, "Home.md"));
            const sync = createSync({
                pullOnly: true,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    deletePageByUuid(bestiaryUuid);
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                'pull: "Home.md" (v3)',
                'pull: SKIPPING "Bestiary.md", deleted remotely during sync',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertTrackedFileIntact(outputDir, result.state, "Bestiary.md");
            await assertTrackedFileMatchesFixture(outputDir, result.state, "index.md");
            await assertServerEditedContent(outputDir, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });

        test("mid-sync, page deleted, new file", async () => {
            const rumoursUuid = await serverCreate(normToken, "Rumours.md");
            await serverEditContent(normToken, await uuidFor(initialState, "Home.md"));
            const sync = createSync({
                pullOnly: true,
                initialState,
                lastUpdate: "2020-01-01T00:00:00Z",
                lastFullSync: recentSyncTime,
                afterFetchHook: async () => {
                    deletePageByUuid(rumoursUuid);
                },
            });

            const result = await runSync(sync);

            const expectedOutput = [
                'pull: SKIPPING "Rumours.md", deleted remotely during sync',
                'pull: "Home.md" (v3)',
            ];
            expect(result.output).toEqual(expectedOutput);

            await assertFileNotDownloaded(outputDir, "Rumours.md", result.state);
            assertFileNotInState("Rumours.md", result.state);
            await assertTrackedFileMatchesFixture(outputDir, result.state, "index.md");
            await assertServerEditedContent(outputDir, "Home.md");
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "characters/NPCs.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "sessions/session-01.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "Bestiary.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "The Old Café.md",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "random-hexmap-7.png",
            );
            await assertTrackedFileMatchesFixture(
                outputDir,
                result.state,
                "World Regions/Northern Kingdoms/Frosthold.md",
            );
            assertSyncMetadataUpdated(result.lastUpdate, result.lastFullSync);
        });
    });
});

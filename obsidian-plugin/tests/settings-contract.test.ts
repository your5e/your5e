import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import {
    type FolderMapping,
    type FolderRenameConfig,
    type FolderSyncState,
    type PluginSettings,
    type VaultRenameConfig,
    handleVaultRename,
    renameFolder,
} from "../src/settings.js";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import type { SyncStateEntry } from "../src/sync/types.js";
import {
    API_BASE,
    cleanupTestDir,
    createFile,
    createTestDir,
    getToken,
    restoreDatabase,
} from "./helpers.js";

describe("settings contract", () => {
    let normToken: string;
    let testDir: string;
    let outputDir: string;

    beforeAll(async () => {
        normToken = await getToken("norm");
    });

    beforeEach(async () => {
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
    });

    function buildSyncConfig(folderMapping: FolderMapping, globalToken: string) {
        const baseUrl = folderMapping.baseUrl || API_BASE;
        const token = folderMapping.token || globalToken;

        return {
            baseUrl,
            token,
            notebook: folderMapping.notebook,
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: folderMapping.pullOnly,
        };
    }

    test("pullOnly setting prevents local file from being pushed", async () => {
        const folderMapping: FolderMapping = {
            folder: "test-folder",
            notebook: "norm/campaign-notes",
            pullOnly: true,
        };

        const config = buildSyncConfig(folderMapping, normToken);
        const sync = new SyncEngine(config);

        await createFile(outputDir, "local-only.md", "this should not be pushed\n");

        const result = await sync.run();

        expect(result.output).not.toContainEqual(
            expect.stringMatching(/push:.*local-only\.md/),
        );

        // ensure file was not pushed to server
        const response = await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/`, {
            headers: { Authorization: `Token ${normToken}` },
        });
        const data = await response.json();
        const pushedFile = data.results.find(
            (p: { filename: string }) => p.filename === "local-only.md",
        );
        expect(pushedFile).toBeUndefined();
    });
});

interface MockConfigOverrides {
    vault?: Partial<FolderRenameConfig["vault"]>;
    settings?: Partial<PluginSettings>;
    isSyncing?: FolderRenameConfig["isSyncing"];
    abortSync?: FolderRenameConfig["abortSync"];
    scheduler?: FolderRenameConfig["scheduler"];
}

function createMockConfig(overrides: MockConfigOverrides = {}): FolderRenameConfig {
    return {
        vault: {
            getAbstractFileByPath: vi.fn().mockReturnValue(null),
            rename: vi.fn().mockResolvedValue(undefined),
            createFolder: vi.fn().mockResolvedValue(undefined),
            delete: vi.fn().mockResolvedValue(undefined),
            ...overrides.vault,
        },
        settings: {
            syncStates: {},
            ...overrides.settings,
        } as PluginSettings,
        isSyncing: overrides.isSyncing ?? vi.fn().mockReturnValue(false),
        abortSync: overrides.abortSync ?? vi.fn(),
        scheduler: overrides.scheduler ?? {
            cancelFolder: vi.fn(),
            addFolder: vi.fn(),
        },
    };
}

describe("folder rename", () => {
    describe("skips rename when", () => {
        test("old path is empty", async () => {
            const config = createMockConfig();
            const result = await renameFolder(config, "", "Spells");

            expect(result.action).toBe("skipped");
            expect(config.vault.rename).not.toHaveBeenCalled();
        });

        test("new path is empty", async () => {
            const config = createMockConfig();
            const result = await renameFolder(config, "Conjurations", "");

            expect(result.action).toBe("skipped");
            expect(config.vault.rename).not.toHaveBeenCalled();
        });

        test("paths are identical", async () => {
            const config = createMockConfig();
            const result = await renameFolder(config, "Spells", "Spells");

            expect(result.action).toBe("skipped");
            expect(config.vault.rename).not.toHaveBeenCalled();
        });
    });

    describe("aborts sync when", () => {
        test("sync is in progress", async () => {
            const config = createMockConfig({
                isSyncing: vi.fn().mockReturnValue(true),
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Conjurations", "Spells");

            expect(config.abortSync).toHaveBeenCalledWith("Conjurations");
            expect(result.action).toBe("renamed");
        });
    });

    describe("blocks rename when", () => {
        test("new folder already exists", async () => {
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Spells") {
                            return { path: "Spells" };
                        }
                        return null;
                    }),
                    rename: vi.fn(),
                },
            });

            const result = await renameFolder(config, "Conjurations", "Spells");

            expect(result.action).toBe("blocked");
            expect((result as { reason: string }).reason).toBe("folder already exists");
            expect(config.vault.rename).not.toHaveBeenCalled();
        });
    });

    describe("handles nested path", () => {
        test("moves folder into subfolder of itself", async () => {
            const spellsFolder = { path: "Spells" };
            const tempFolder = { path: "_temp_Spells" };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Spells") {
                            return spellsFolder;
                        }
                        if (path === "_temp_Spells") {
                            return tempFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                    createFolder: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Spells", "Spells/Spells");

            expect(result.action).toBe("renamed");
            expect(config.vault.rename).toHaveBeenCalledTimes(2);
            expect(config.vault.rename).toHaveBeenNthCalledWith(
                1,
                spellsFolder,
                "_temp_Spells",
            );
            expect(config.vault.createFolder).toHaveBeenCalledWith("Spells");
            expect(config.vault.rename).toHaveBeenNthCalledWith(
                2,
                tempFolder,
                "Spells/Spells",
            );
        });

        test("creates parent folder when renaming to nested path", async () => {
            const oldFolder = { path: "Conjurations" };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return oldFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                    createFolder: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Conjurations", "Spells/Spells");

            expect(result.action).toBe("renamed");
            expect(config.vault.createFolder).toHaveBeenCalledWith("Spells");
            expect(config.vault.rename).toHaveBeenCalledWith(
                oldFolder,
                "Spells/Spells",
            );
        });

        test("deletes empty parent folder after rename", async () => {
            const oldFolder = { path: "Spells/Spells" };
            const parentFolder = { path: "Spells", children: [] };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Spells/Spells") {
                            return oldFolder;
                        }
                        if (path === "Spells") {
                            return parentFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                    createFolder: vi.fn().mockResolvedValue(undefined),
                    delete: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Spells/Spells", "Conjurations");

            expect(result.action).toBe("renamed");
            expect(config.vault.rename).toHaveBeenCalledWith(oldFolder, "Conjurations");
            expect(config.vault.delete).toHaveBeenCalledWith(parentFolder);
        });

        test("keeps parent folder when not empty after rename", async () => {
            const oldFolder = { path: "Spells/Spells" };
            const otherChild = { path: "Spells/Other" };
            const parentFolder = { path: "Spells", children: [otherChild] };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Spells/Spells") {
                            return oldFolder;
                        }
                        if (path === "Spells") {
                            return parentFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                    createFolder: vi.fn().mockResolvedValue(undefined),
                    delete: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Spells/Spells", "Conjurations");

            expect(result.action).toBe("renamed");
            expect(config.vault.delete).not.toHaveBeenCalled();
        });

        test("moves folder out of parent to replace it", async () => {
            const oldFolder = { path: "Spells/Spells/Spells" };
            const intermediateFolder = { path: "Spells/Spells" };
            const parentFolder = { path: "Spells" };
            const tempFolder = { path: "_temp_Spells" };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Spells/Spells/Spells") {
                            return oldFolder;
                        }
                        if (path === "Spells/Spells") {
                            return intermediateFolder;
                        }
                        if (path === "Spells") {
                            return parentFolder;
                        }
                        if (path === "_temp_Spells") {
                            return tempFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                    createFolder: vi.fn().mockResolvedValue(undefined),
                    delete: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Spells/Spells/Spells", "Spells");

            expect(result.action).toBe("renamed");
            expect(config.vault.rename).toHaveBeenNthCalledWith(
                1,
                oldFolder,
                "_temp_Spells",
            );
            expect(config.vault.delete).toHaveBeenNthCalledWith(1, intermediateFolder);
            expect(config.vault.delete).toHaveBeenNthCalledWith(2, parentFolder);
            expect(config.vault.rename).toHaveBeenNthCalledWith(
                2,
                tempFolder,
                "Spells",
            );
        });
    });

    describe("renames folder when", () => {
        test("old folder exists in vault", async () => {
            const oldFolder = { path: "Conjurations" };
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return oldFolder;
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                },
            });

            const result = await renameFolder(config, "Conjurations", "Spells");

            expect(result.action).toBe("renamed");
            expect(config.vault.rename).toHaveBeenCalledWith(oldFolder, "Spells");
        });

        test("migrates sync state to new key", async () => {
            const entry: SyncStateEntry = {
                uuid: "uuid-1",
                serverFilename: "test.md",
                localFilename: "test.md",
                serverHash: "abc123",
                localHash: "abc123",
            };
            const syncState: FolderSyncState = {
                entries: { "uuid-1": entry },
                lastUpdate: "2024-01-01T00:00:00Z",
            };
            const config = createMockConfig({
                settings: {
                    syncStates: { Conjurations: syncState },
                },
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                },
            });

            await renameFolder(config, "Conjurations", "Spells");

            expect(config.settings.syncStates.Spells).toBe(syncState);
            expect(config.settings.syncStates.Conjurations).toBeUndefined();
        });

        test("updates scheduler", async () => {
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockResolvedValue(undefined),
                },
            });

            await renameFolder(config, "Conjurations", "Spells");

            expect(config.scheduler.cancelFolder).toHaveBeenCalledWith("Conjurations");
            expect(config.scheduler.addFolder).toHaveBeenCalledWith("Spells");
        });
    });

    describe("handles missing old folder", () => {
        test("updates setting without vault rename", async () => {
            const config = createMockConfig();

            const result = await renameFolder(config, "Rituals", "Spells");

            expect(result.action).toBe("updated");
            expect(config.vault.rename).not.toHaveBeenCalled();
        });

        test("still migrates sync state", async () => {
            const syncState: FolderSyncState = {
                entries: {},
                lastUpdate: "2024-01-01T00:00:00Z",
            };
            const config = createMockConfig({
                settings: {
                    syncStates: { Rituals: syncState },
                },
            });

            await renameFolder(config, "Rituals", "Spells");

            expect(config.settings.syncStates.Spells).toBe(syncState);
            expect(config.settings.syncStates.Rituals).toBeUndefined();
        });

        test("still updates scheduler", async () => {
            const config = createMockConfig();

            await renameFolder(config, "Rituals", "Spells");

            expect(config.scheduler.cancelFolder).toHaveBeenCalledWith("Rituals");
            expect(config.scheduler.addFolder).toHaveBeenCalledWith("Spells");
        });
    });

    describe("handles rename failure", () => {
        test("returns error result", async () => {
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockRejectedValue(new Error("Permission denied")),
                },
            });

            const result = await renameFolder(config, "Conjurations", "Spells");

            expect(result.action).toBe("error");
            expect((result as { reason: string }).reason).toBe("Permission denied");
        });

        test("does not migrate state on failure", async () => {
            const syncState: FolderSyncState = {
                entries: {},
                lastUpdate: "2024-01-01T00:00:00Z",
            };
            const config = createMockConfig({
                settings: {
                    syncStates: { Conjurations: syncState },
                },
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockRejectedValue(new Error("Permission denied")),
                },
            });

            await renameFolder(config, "Conjurations", "Spells");

            expect(config.settings.syncStates.Conjurations).toBe(syncState);
            expect(config.settings.syncStates.Spells).toBeUndefined();
        });

        test("does not update scheduler on failure", async () => {
            const config = createMockConfig({
                vault: {
                    getAbstractFileByPath: vi.fn().mockImplementation((path) => {
                        if (path === "Conjurations") {
                            return { path: "Conjurations" };
                        }
                        return null;
                    }),
                    rename: vi.fn().mockRejectedValue(new Error("Permission denied")),
                },
            });

            await renameFolder(config, "Conjurations", "Spells");

            expect(config.scheduler.cancelFolder).not.toHaveBeenCalled();
            expect(config.scheduler.addFolder).not.toHaveBeenCalled();
        });
    });
});

interface MockVaultRenameConfigOverrides {
    settings?: Partial<PluginSettings>;
    isSyncing?: VaultRenameConfig["isSyncing"];
    abortSync?: VaultRenameConfig["abortSync"];
    scheduler?: VaultRenameConfig["scheduler"];
    log?: VaultRenameConfig["log"];
}

function createMockVaultRenameConfig(
    overrides: MockVaultRenameConfigOverrides = {},
): VaultRenameConfig {
    return {
        settings: {
            folders: [],
            syncStates: {},
            ...overrides.settings,
        } as PluginSettings,
        isSyncing: overrides.isSyncing ?? vi.fn().mockReturnValue(false),
        abortSync: overrides.abortSync ?? vi.fn(),
        scheduler: overrides.scheduler ?? {
            cancelFolder: vi.fn(),
            addFolder: vi.fn(),
        },
        log: overrides.log ?? vi.fn(),
    };
}

describe("vault rename detection", () => {
    describe("ignores rename when", () => {
        test("old path is not a synced folder", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Hexes", notebook: "test" }],
                    syncStates: {},
                },
            });

            const result = handleVaultRename(config, "Cantrips", "Enchantments");

            expect(result.action).toBe("ignored");
            expect(config.scheduler.cancelFolder).not.toHaveBeenCalled();
        });
    });

    describe("blocks rename when", () => {
        test("new path already exists in settings", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [
                        { folder: "Conjurations", notebook: "test1" },
                        { folder: "Spells", notebook: "test2" },
                    ],
                    syncStates: {},
                },
            });

            const result = handleVaultRename(config, "Conjurations", "Spells");

            expect(result.action).toBe("conflict");
            expect((result as { reason: string }).reason).toBe(
                "another synced folder already uses this path",
            );
        });
    });

    describe("updates settings when", () => {
        test("synced folder is renamed", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Conjurations", notebook: "test" }],
                    syncStates: {},
                },
            });

            const result = handleVaultRename(config, "Conjurations", "Spells");

            expect(result.action).toBe("updated");
            expect(config.settings.folders[0].folder).toBe("Spells");
        });

        test("migrates sync state to new key", () => {
            const syncState: FolderSyncState = {
                entries: { "uuid-1": { uuid: "uuid-1" } as SyncStateEntry },
                lastUpdate: "2024-01-01T00:00:00Z",
            };
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Conjurations", notebook: "test" }],
                    syncStates: { Conjurations: syncState },
                },
            });

            handleVaultRename(config, "Conjurations", "Spells");

            expect(config.settings.syncStates.Spells).toBe(syncState);
            expect(config.settings.syncStates.Conjurations).toBeUndefined();
        });

        test("updates scheduler", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Conjurations", notebook: "test" }],
                    syncStates: {},
                },
            });

            handleVaultRename(config, "Conjurations", "Spells");

            expect(config.scheduler.cancelFolder).toHaveBeenCalledWith("Conjurations");
            expect(config.scheduler.addFolder).toHaveBeenCalledWith("Spells");
        });

        test("logs the change", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Conjurations", notebook: "test" }],
                    syncStates: {},
                },
            });

            handleVaultRename(config, "Conjurations", "Spells");

            expect(config.log).toHaveBeenCalledWith(
                "Spells",
                "Folder renamed from 'Conjurations'",
            );
        });
    });

    describe("aborts sync when", () => {
        test("sync is in progress", () => {
            const config = createMockVaultRenameConfig({
                settings: {
                    folders: [{ folder: "Conjurations", notebook: "test" }],
                    syncStates: {},
                },
                isSyncing: vi.fn().mockReturnValue(true),
            });

            handleVaultRename(config, "Conjurations", "Spells");

            expect(config.abortSync).toHaveBeenCalledWith("Conjurations");
        });
    });
});

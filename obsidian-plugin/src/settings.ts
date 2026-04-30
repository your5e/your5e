import type { SyncStateEntry } from "./sync/types.js";

export const DEFAULT_BASE_URL = "https://api.your5e.com";

export interface FolderMapping {
    folder: string;
    notebook: string;
    baseUrl?: string;
    token?: string;
    pullOnly?: boolean;
    active?: boolean;
}

export interface FolderSyncState {
    entries: { [uuid: string]: SyncStateEntry };
    lastUpdate?: string;
    lastFullSync?: string;
}

export interface PluginSettings {
    version: string;
    baseUrl: string;
    token: string;
    folders: FolderMapping[];
    syncStates: { [folder: string]: FolderSyncState };
}

export const DEFAULT_SETTINGS: PluginSettings = {
    version: "",
    baseUrl: "",
    token: "",
    folders: [],
    syncStates: {},
};

export interface FolderRenameConfig {
    vault: {
        getAbstractFileByPath(
            path: string,
        ): { path: string; children?: unknown[] } | null;
        rename(file: { path: string }, newPath: string): Promise<void>;
        createFolder(path: string): Promise<unknown>;
        delete(file: { path: string }): Promise<void>;
    };
    settings: PluginSettings;
    isSyncing: (folder: string) => boolean;
    abortSync: (folder: string) => void;
    scheduler: {
        cancelFolder(folder: string): void;
        addFolder(folder: string): void;
    };
}

export type FolderRenameResult =
    | { action: "skipped" }
    | { action: "blocked"; reason: string }
    | { action: "updated" }
    | { action: "renamed" }
    | { action: "error"; reason: string };

export async function renameFolder(
    config: FolderRenameConfig,
    oldPath: string,
    newPath: string,
): Promise<FolderRenameResult> {
    if (!oldPath || !newPath || oldPath === newPath) {
        return { action: "skipped" };
    }

    const isReplacingParent = oldPath.startsWith(newPath + "/");
    if (!isReplacingParent && config.vault.getAbstractFileByPath(newPath)) {
        return { action: "blocked", reason: "folder already exists" };
    }

    if (config.isSyncing(oldPath)) {
        config.abortSync(oldPath);
    }

    const oldFolder = config.vault.getAbstractFileByPath(oldPath);
    const isNestedPath = newPath.startsWith(oldPath + "/");

    if (oldFolder && isReplacingParent) {
        try {
            const tempPath = `_temp_${newPath}`;
            await config.vault.rename(oldFolder, tempPath);

            // Delete intermediate folders from deepest to shallowest
            const oldParts = oldPath.split("/");
            const newParts = newPath.split("/");
            for (let i = oldParts.length - 1; i >= newParts.length; i--) {
                const intermediatePath = oldParts.slice(0, i).join("/");
                const folder = config.vault.getAbstractFileByPath(intermediatePath);
                if (folder) {
                    await config.vault.delete(folder);
                }
            }

            const tempFolder = config.vault.getAbstractFileByPath(tempPath);
            if (!tempFolder) {
                return {
                    action: "error",
                    reason: "temp folder not found after rename",
                };
            }
            await config.vault.rename(tempFolder, newPath);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            return { action: "error", reason: message };
        }
    } else if (oldFolder && isNestedPath) {
        try {
            const tempPath = `_temp_${oldPath}`;
            await config.vault.rename(oldFolder, tempPath);
            await config.vault.createFolder(oldPath);
            const tempFolder = config.vault.getAbstractFileByPath(tempPath);
            if (!tempFolder) {
                return {
                    action: "error",
                    reason: "temp folder not found after rename",
                };
            }
            await config.vault.rename(tempFolder, newPath);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            return { action: "error", reason: message };
        }
    } else if (oldFolder) {
        try {
            const parentPath = newPath.split("/").slice(0, -1).join("/");
            if (parentPath && !config.vault.getAbstractFileByPath(parentPath)) {
                await config.vault.createFolder(parentPath);
            }
            await config.vault.rename(oldFolder, newPath);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            return { action: "error", reason: message };
        }
    }

    // Clean up empty parent folder after rename
    const oldParentPath = oldPath.split("/").slice(0, -1).join("/");
    if (oldParentPath) {
        const oldParent = config.vault.getAbstractFileByPath(oldParentPath);
        if (oldParent && "children" in oldParent && Array.isArray(oldParent.children)) {
            if (oldParent.children.length === 0) {
                await config.vault.delete(oldParent);
            }
        }
    }

    if (config.settings.syncStates[oldPath]) {
        config.settings.syncStates[newPath] = config.settings.syncStates[oldPath];
        delete config.settings.syncStates[oldPath];
    }

    config.scheduler.cancelFolder(oldPath);
    config.scheduler.addFolder(newPath);

    return oldFolder ? { action: "renamed" } : { action: "updated" };
}

export interface VaultRenameConfig {
    settings: PluginSettings;
    isSyncing: (folder: string) => boolean;
    abortSync: (folder: string) => void;
    scheduler: {
        cancelFolder(folder: string): void;
        addFolder(folder: string): void;
    };
    log: (folder: string, message: string) => void;
}

export type VaultRenameResult =
    | { action: "ignored" }
    | { action: "updated" }
    | { action: "conflict"; reason: string };

export function handleVaultRename(
    config: VaultRenameConfig,
    oldPath: string,
    newPath: string,
): VaultRenameResult {
    const mapping = config.settings.folders.find((f) => f.folder === oldPath);
    if (!mapping) {
        return { action: "ignored" };
    }

    const conflicting = config.settings.folders.find((f) => f.folder === newPath);
    if (conflicting) {
        return {
            action: "conflict",
            reason: "another synced folder already uses this path",
        };
    }

    if (config.isSyncing(oldPath)) {
        config.abortSync(oldPath);
    }

    mapping.folder = newPath;

    if (config.settings.syncStates[oldPath]) {
        config.settings.syncStates[newPath] = config.settings.syncStates[oldPath];
        delete config.settings.syncStates[oldPath];
    }

    config.scheduler.cancelFolder(oldPath);
    config.scheduler.addFolder(newPath);

    config.log(newPath, `Folder renamed from '${oldPath}'`);

    return { action: "updated" };
}

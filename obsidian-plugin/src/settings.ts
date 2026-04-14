import type { SyncStateEntry } from "./sync/types.js";

export const DEFAULT_BASE_URL = "https://api.your5e.com";

export interface FolderMapping {
    folder: string;
    notebook: string;
    baseUrl?: string;
    token?: string;
    pullOnly?: boolean;
}

export interface FolderSyncState {
    entries: { [uuid: string]: SyncStateEntry };
    lastUpdate?: string;
    lastFullSync?: string;
}

export interface PluginSettings {
    baseUrl: string;
    token: string;
    folders: FolderMapping[];
    syncStates: { [folder: string]: FolderSyncState };
}

export const DEFAULT_SETTINGS: PluginSettings = {
    baseUrl: "",
    token: "",
    folders: [],
    syncStates: {},
};

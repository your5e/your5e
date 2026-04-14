import * as path from "node:path";
import { Notice, Plugin } from "obsidian";
import { Your5eSyncSettingTab } from "./settings-tab.js";
import { DEFAULT_BASE_URL, DEFAULT_SETTINGS, type PluginSettings } from "./settings.js";
import { SyncScheduler } from "./sync-scheduler.js";
import { NodeFileSystem } from "./sync/node-fs.js";
import { SyncEngine } from "./sync/sync-engine.js";
import type { SyncConfig, SyncResult, SyncStateEntry } from "./sync/types.js";

export default class Your5eSyncPlugin extends Plugin {
    settings: PluginSettings;
    settingsOpen = false;
    private scheduler: SyncScheduler | null = null;

    async onload() {
        await this.loadSettings();

        this.addSettingTab(new Your5eSyncSettingTab(this.app, this));

        this.scheduler = new SyncScheduler({
            setTimeout: (fn, delay) => window.setTimeout(fn, delay),
            clearTimeout: (id) => window.clearTimeout(id),
            random: () => Math.random(),
            onSync: (folder) => this.runSyncForFolder(folder),
            onSchedule: () => {},
        });

        const folders = this.settings.folders.map((f) => f.folder);
        if (folders.length > 0) {
            this.scheduler.start(folders);
        }

        new Notice("Your5e Sync plugin loaded");
    }

    onunload() {
        this.scheduler?.stop();
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    private async runSyncForFolder(folder: string): Promise<void> {
        if (this.settingsOpen) {
            return;
        }

        const folderMapping = this.settings.folders.find((f) => f.folder === folder);
        if (!folderMapping) {
            return;
        }

        const baseUrl =
            folderMapping.baseUrl || this.settings.baseUrl || DEFAULT_BASE_URL;
        const token = folderMapping.token || this.settings.token;

        if (!baseUrl || !token) {
            return;
        }

        // biome-ignore lint/suspicious/noExplicitAny: basePath exists on FileSystemAdapter but isn't in public types
        const vaultPath = (this.app.vault.adapter as any).basePath as string;
        const outputDir = path.join(vaultPath, folderMapping.folder);

        const folderState = this.loadFolderState(folderMapping.folder);

        const config: SyncConfig = {
            baseUrl,
            token,
            notebook: folderMapping.notebook,
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: folderMapping.pullOnly,
            initialState: folderState.state,
            lastUpdate: folderState.lastUpdate,
            lastFullSync: folderState.lastFullSync,
        };

        try {
            const engine = new SyncEngine(config);
            const result = await engine.run();

            for (const line of result.output) {
                console.log(`[${folderMapping.folder}] ${line}`);
            }

            this.saveFolderState(folderMapping.folder, result);
            await this.saveSettings();
        } catch (error) {
            console.error(`Sync failed for folder "${folderMapping.folder}":`, error);
            new Notice(
                `Your5e sync failed for ${folderMapping.folder}: ${error.message}`,
            );
        }
    }

    private loadFolderState(folder: string): {
        state: Map<string, SyncStateEntry>;
        lastUpdate?: string;
        lastFullSync?: string;
    } {
        if (!this.settings.syncStates) {
            this.settings.syncStates = {};
        }

        const folderState = this.settings.syncStates[folder];
        if (!folderState) {
            return { state: new Map() };
        }

        const state = new Map<string, SyncStateEntry>();
        for (const [uuid, entry] of Object.entries(folderState.entries)) {
            state.set(uuid, entry);
        }
        return {
            state,
            lastUpdate: folderState.lastUpdate,
            lastFullSync: folderState.lastFullSync,
        };
    }

    private saveFolderState(folder: string, result: SyncResult): void {
        if (!this.settings.syncStates) {
            this.settings.syncStates = {};
        }

        const entries: { [uuid: string]: SyncStateEntry } = {};
        for (const [uuid, entry] of result.state) {
            entries[uuid] = entry;
        }
        this.settings.syncStates[folder] = {
            entries,
            lastUpdate: result.lastUpdate,
            lastFullSync: result.lastFullSync,
        };
    }
}

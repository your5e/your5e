import * as path from "node:path";
import { type App, FuzzySuggestModal, Notice, Plugin } from "obsidian";
import { Your5eSyncSettingTab } from "./settings-tab.js";
import {
    DEFAULT_BASE_URL,
    DEFAULT_SETTINGS,
    type FolderMapping,
    type PluginSettings,
} from "./settings.js";
import { SyncLog, SyncLogModal } from "./sync-log.js";
import { SyncScheduler } from "./sync-scheduler.js";
import { NodeFileSystem } from "./sync/node-fs.js";
import { SyncEngine } from "./sync/sync-engine.js";
import type { SyncConfig, SyncResult, SyncStateEntry } from "./sync/types.js";

class FolderSuggestModal extends FuzzySuggestModal<FolderMapping> {
    plugin: Your5eSyncPlugin;

    constructor(app: App, plugin: Your5eSyncPlugin) {
        super(app);
        this.plugin = plugin;
    }

    getItems(): FolderMapping[] {
        return this.plugin.settings.folders;
    }

    getItemText(folder: FolderMapping): string {
        return folder.folder;
    }

    onChooseItem(folder: FolderMapping): void {
        this.plugin.scheduler?.syncNow(folder.folder);
    }
}

export default class Your5eSyncPlugin extends Plugin {
    settings: PluginSettings;
    scheduler: SyncScheduler | null = null;
    syncLog: SyncLog = new SyncLog();
    private syncing: Set<string> = new Set();

    async onload() {
        await this.loadSettings();

        this.addSettingTab(new Your5eSyncSettingTab(this.app, this));

        this.addCommand({
            id: "sync-folder-now",
            name: "Sync folder now",
            callback: () => new FolderSuggestModal(this.app, this).open(),
        });

        this.addCommand({
            id: "show-sync-log",
            name: "Show sync log",
            callback: () => this.openSyncLogModal(),
        });

        this.addRibbonIcon("scroll", "Show sync log", () => this.openSyncLogModal());

        this.scheduler = new SyncScheduler({
            setTimeout: (fn, delay) => window.setTimeout(fn, delay),
            clearTimeout: (id) => window.clearTimeout(id),
            random: () => Math.random(),
            onSync: (folder) => this.syncFolder(folder),
            onSchedule: (folder, delay) => {
                const nextSync = new Date(Date.now() + delay);
                const time = nextSync.toTimeString().slice(0, 8);
                this.syncLog.log(folder, `next sync at ${time}`);
            },
        });

        const folders = this.settings.folders.map((f) => f.folder);
        if (folders.length > 0) {
            this.scheduler.start(folders);
        }
    }

    onunload() {
        this.scheduler?.stop();
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        this.settings.version = this.manifest.version;
        await this.saveData(this.settings);
    }

    openSyncLogModal(): void {
        new SyncLogModal(this.app, this.syncLog, {
            folders: this.settings.folders.map((f) => f.folder),
            onSync: (folder) => this.scheduler?.syncNow(folder),
        }).open();
    }

    async syncFolder(folder: string): Promise<void> {
        if (this.syncing.has(folder)) {
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

        this.syncing.add(folder);
        this.syncLog.log(folder, "sync starting");

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
            onOutput: (line) => this.syncLog.log(folder, line),
        };

        try {
            const engine = new SyncEngine(config);
            const result = await engine.run();
            this.saveFolderState(folderMapping.folder, result);
            await this.saveData(this.settings);
        } catch (error) {
            this.syncLog.log(folder, `sync failed: ${error.message}`);
            new Notice(
                `Your5e sync failed for ${folderMapping.folder}: ${error.message}`,
            );
        } finally {
            this.syncing.delete(folder);
        }
    }

    private loadFolderState(folder: string): {
        state: Map<string, SyncStateEntry>;
        lastUpdate?: string;
        lastFullSync?: string;
    } {
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

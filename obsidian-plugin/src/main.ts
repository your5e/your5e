import { Notice, Plugin } from "obsidian";
import { ObsidianFileSystem } from "./obsidian-fs.js";
import { DEFAULT_SETTINGS, type PluginSettings } from "./settings.js";
import { Your5eSyncSettingTab } from "./settings-tab.js";
import { SyncEngine } from "./sync/sync-engine.js";
import type { SyncConfig } from "./sync/types.js";

export default class Your5eSyncPlugin extends Plugin {
    settings: PluginSettings;

    async onload() {
        await this.loadSettings();

        this.addSettingTab(new Your5eSyncSettingTab(this.app, this));

        this.registerInterval(
            window.setInterval(() => this.runSync(), 60000),
        );

        new Notice("Your5e Sync plugin loaded");
    }

    async loadSettings() {
        this.settings = Object.assign(
            {},
            DEFAULT_SETTINGS,
            await this.loadData(),
        );
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    async runSync() {
        for (const folderMapping of this.settings.folders) {
            const baseUrl = folderMapping.baseUrl || this.settings.baseUrl;
            const token = folderMapping.token || this.settings.token;

            if (!baseUrl || !token) {
                console.warn(
                    `Skipping folder "${folderMapping.folder}": missing baseUrl or token`,
                );
                continue;
            }

            const fileSystem = new ObsidianFileSystem(
                this.app.vault,
                folderMapping.folder,
            );

            const config: SyncConfig = {
                baseUrl,
                token,
                notebook: folderMapping.notebook,
                outputDir: "",
                fileSystem,
            };

            try {
                const engine = new SyncEngine(config);
                const result = await engine.run();

                for (const line of result.output) {
                    console.log(
                        `[${folderMapping.folder}] ${line}`,
                    );
                }
            } catch (error) {
                console.error(
                    `Sync failed for folder "${folderMapping.folder}":`,
                    error,
                );
                new Notice(
                    `Your5e sync failed for ${folderMapping.folder}: ${error.message}`,
                );
            }
        }
    }
}

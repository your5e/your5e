import { type App, PluginSettingTab, Setting } from "obsidian";
import type Your5eSyncPlugin from "./main.js";
import type { FolderMapping } from "./settings.js";

export class Your5eSyncSettingTab extends PluginSettingTab {
    plugin: Your5eSyncPlugin;

    constructor(app: App, plugin: Your5eSyncPlugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display(): void {
        this.plugin.settingsOpen = true;

        const { containerEl } = this;
        containerEl.empty();

        containerEl.createEl("h2", { text: "Your5e Sync Settings" });

        new Setting(containerEl)
            .setName("Base URL")
            .setDesc("Default API endpoint for Your5e")
            .addText((text) =>
                text
                    .setPlaceholder("https://your5e.example.com")
                    .setValue(this.plugin.settings.baseUrl)
                    .onChange(async (value) => {
                        this.plugin.settings.baseUrl = value.trim();
                        await this.plugin.saveSettings();
                    }),
            );

        new Setting(containerEl)
            .setName("API Token")
            .setDesc("Default API token for authentication")
            .addText((text) =>
                text
                    .setPlaceholder("your-api-token")
                    .setValue(this.plugin.settings.token)
                    .onChange(async (value) => {
                        this.plugin.settings.token = value.trim();
                        await this.plugin.saveSettings();
                    }),
            );

        containerEl.createEl("h3", { text: "Folder Mappings" });

        for (let i = 0; i < this.plugin.settings.folders.length; i++) {
            const mapping = this.plugin.settings.folders[i];
            this.displayFolderMapping(containerEl, mapping, i);
        }

        new Setting(containerEl).addButton((button) =>
            button.setButtonText("Add folder mapping").onClick(async () => {
                this.plugin.settings.folders.push({
                    folder: "",
                    notebook: "",
                });
                await this.plugin.saveSettings();
                this.display();
            }),
        );
    }

    hide(): void {
        this.plugin.settingsOpen = false;
    }

    displayFolderMapping(
        containerEl: HTMLElement,
        mapping: FolderMapping,
        index: number,
    ): void {
        const settingContainer = containerEl.createDiv("setting-item-container");

        new Setting(settingContainer)
            .setName(`Folder ${index + 1}`)
            .addButton((button) =>
                button
                    .setButtonText("Remove")
                    .setWarning()
                    .onClick(async () => {
                        this.plugin.settings.folders.splice(index, 1);
                        await this.plugin.saveSettings();
                        this.display();
                    }),
            );

        new Setting(settingContainer)
            .setName("Vault folder")
            .setDesc("Path to folder in vault (relative to vault root)")
            .addText((text) =>
                text
                    .setPlaceholder("MyNotes")
                    .setValue(mapping.folder)
                    .onChange(async (value) => {
                        mapping.folder = value.trim();
                        await this.plugin.saveSettings();
                    }),
            );

        new Setting(settingContainer)
            .setName("Notebook ID")
            .setDesc("Your5e notebook identifier")
            .addText((text) =>
                text
                    .setPlaceholder("my-notebook")
                    .setValue(mapping.notebook)
                    .onChange(async (value) => {
                        mapping.notebook = value.trim();
                        await this.plugin.saveSettings();
                    }),
            );

        new Setting(settingContainer)
            .setName("Override Base URL")
            .setDesc("Optional: use a different API endpoint for this folder")
            .addText((text) =>
                text
                    .setPlaceholder("Leave empty to use default")
                    .setValue(mapping.baseUrl || "")
                    .onChange(async (value) => {
                        mapping.baseUrl = value.trim() || undefined;
                        await this.plugin.saveSettings();
                    }),
            );

        new Setting(settingContainer)
            .setName("Override API Token")
            .setDesc("Optional: use a different API token for this folder")
            .addText((text) =>
                text
                    .setPlaceholder("Leave empty to use default")
                    .setValue(mapping.token || "")
                    .onChange(async (value) => {
                        mapping.token = value.trim() || undefined;
                        await this.plugin.saveSettings();
                    }),
            );
    }
}

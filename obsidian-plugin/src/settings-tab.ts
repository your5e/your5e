import {
    type App,
    type ExtraButtonComponent,
    Notice,
    PluginSettingTab,
    Setting,
} from "obsidian";
import type Your5eSyncPlugin from "./main.js";
import { DEFAULT_BASE_URL, type FolderMapping, renameFolder } from "./settings.js";

function togglePasswordVisibility(button: ExtraButtonComponent): void {
    button.setIcon("eye").onClick(() => {
        const input = button.extraSettingsEl.parentElement?.querySelector(
            "input",
        ) as HTMLInputElement;
        if (input.type === "password") {
            input.type = "text";
            button.setIcon("eye-off");
        } else {
            input.type = "password";
            button.setIcon("eye");
        }
    });
}

export class Your5eSyncSettingTab extends PluginSettingTab {
    plugin: Your5eSyncPlugin;

    constructor(app: App, plugin: Your5eSyncPlugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display(): void {
        const { containerEl } = this;
        containerEl.empty();

        new Setting(containerEl)
            .setName("API Token")
            .setDesc("Required")
            .addExtraButton(togglePasswordVisibility)
            .addText((text) => {
                text.inputEl.type = "password";
                text.setPlaceholder("your-api-token")
                    .setValue(this.plugin.settings.token)
                    .onChange(async (value) => {
                        this.plugin.settings.token = value.trim();
                        await this.plugin.saveSettings();
                    });
            });

        new Setting(containerEl)
            .setName("API Base URL")
            .setDesc("Optional")
            .addText((text) =>
                text
                    .setPlaceholder(DEFAULT_BASE_URL)
                    .setValue(this.plugin.settings.baseUrl)
                    .onChange(async (value) => {
                        this.plugin.settings.baseUrl = value.trim().replace(/\/+$/, "");
                        await this.plugin.saveSettings();
                    }),
            );

        containerEl.createEl("h3", { text: "Synchronised Folders" });

        for (let i = 0; i < this.plugin.settings.folders.length; i++) {
            const mapping = this.plugin.settings.folders[i];
            this.displayFolderMapping(containerEl, mapping, i);
        }

        const addButton = containerEl.createEl("button", { text: "Add new folder" });
        addButton.addEventListener("click", async () => {
            this.plugin.settings.folders.push({
                folder: "",
                notebook: "",
            });
            await this.plugin.saveSettings();
            this.display();
        });
    }

    async hide(): Promise<void> {
        this.plugin.settings.folders = this.plugin.settings.folders.filter(
            (m) => m.folder || m.notebook,
        );
        await this.plugin.saveSettings();
    }

    displayFolderMapping(
        containerEl: HTMLElement,
        mapping: FolderMapping,
        index: number,
    ): void {
        const oldFolder = mapping.folder;
        const isComplete = mapping.folder && mapping.notebook;
        const wrapper = containerEl.createDiv("setting-item");
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "flex-start";
        wrapper.style.gap = "8px";

        const details = wrapper.createEl("details");
        details.style.flexGrow = "1";
        if (!isComplete) {
            details.setAttribute("open", "");
        }

        const summary = details.createEl("summary", {
            text: isComplete ? `${mapping.folder}: ${mapping.notebook}` : "New mapping",
        });

        const removeButton = wrapper.createEl("button", { text: "Remove" });
        removeButton.addClass("mod-warning");
        removeButton.addEventListener("click", async () => {
            this.plugin.abortSync(mapping.folder);
            this.plugin.scheduler?.cancelFolder(mapping.folder);
            this.plugin.settings.folders.splice(index, 1);
            delete this.plugin.settings.syncStates[mapping.folder];
            await this.plugin.saveSettings();
            this.plugin.syncLog.log(mapping.folder, "Removed synchronised folder");
            this.display();
        });

        const content = details.createDiv();
        content.createDiv("setting-item");

        let pendingFolder = mapping.folder;
        new Setting(content)
            .setName("Folder")
            .setDesc("Location of the folder in the vault")
            .addText((text) =>
                text
                    .setPlaceholder("MyNotes")
                    .setValue(mapping.folder)
                    .onChange((value) => {
                        pendingFolder = value.trim();
                    }),
            );

        new Setting(content)
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

        new Setting(content)
            .setName("Override API Token")
            .setDesc("Optional: use a different API token for this folder")
            .addExtraButton(togglePasswordVisibility)
            .addText((text) => {
                text.inputEl.type = "password";
                text.setPlaceholder("Leave empty to use default")
                    .setValue(mapping.token || "")
                    .onChange(async (value) => {
                        mapping.token = value.trim() || undefined;
                        await this.plugin.saveSettings();
                    });
            });

        new Setting(content)
            .setName("Override API URL")
            .setDesc("Optional: use a different API endpoint for this folder")
            .addText((text) =>
                text
                    .setPlaceholder(this.plugin.settings.baseUrl || DEFAULT_BASE_URL)
                    .setValue(mapping.baseUrl || "")
                    .onChange(async (value) => {
                        mapping.baseUrl = value.trim().replace(/\/+$/, "") || undefined;
                        await this.plugin.saveSettings();
                    }),
            );

        new Setting(content)
            .setName("Pull only")
            .setDesc("Only download changes from the server, never push")
            .addToggle((toggle) =>
                toggle.setValue(mapping.pullOnly ?? false).onChange(async (value) => {
                    mapping.pullOnly = value || undefined;
                    await this.plugin.saveSettings();
                }),
            );

        new Setting(content)
            .setName("Active")
            .setDesc("Enable automatic synchronisation for this folder")
            .addToggle((toggle) =>
                toggle.setValue(mapping.active ?? true).onChange(async (value) => {
                    mapping.active = value || undefined;
                    await this.plugin.saveSettings();
                    if (value) {
                        this.plugin.scheduler?.addFolder(mapping.folder);
                    } else {
                        this.plugin.scheduler?.cancelFolder(mapping.folder);
                    }
                }),
            );

        new Setting(content).addButton((button) =>
            button
                .setButtonText("Save")
                .setCta()
                .onClick(async () => {
                    if (oldFolder !== pendingFolder && this.plugin.scheduler) {
                        const result = await renameFolder(
                            {
                                vault: this.app.vault,
                                settings: this.plugin.settings,
                                isSyncing: (f) => this.plugin.isSyncing(f),
                                abortSync: (f) => this.plugin.abortSync(f),
                                scheduler: this.plugin.scheduler,
                            },
                            oldFolder,
                            pendingFolder,
                        );

                        if (result.action === "blocked" || result.action === "error") {
                            const msg = `Cannot rename '${oldFolder}' to '${pendingFolder}': ${result.reason}`;
                            this.plugin.syncLog.log(oldFolder, msg);
                            new Notice(msg);
                            return;
                        }

                        if (
                            result.action === "renamed" ||
                            result.action === "updated"
                        ) {
                            this.plugin.syncLog.log(
                                pendingFolder,
                                `Renamed folder from '${oldFolder}'`,
                            );
                        }
                    }

                    if (!oldFolder && pendingFolder) {
                        this.plugin.syncLog.log(
                            pendingFolder,
                            "Added synchronised folder",
                        );
                    }

                    mapping.folder = pendingFolder;
                    await this.plugin.saveSettings();
                    summary.textContent = `${mapping.folder}: ${mapping.notebook}`;
                    details.removeAttribute("open");
                    await this.plugin.scheduler?.syncNow(mapping.folder);
                }),
        );
    }
}

export interface FolderMapping {
    folder: string;
    notebook: string;
    baseUrl?: string;
    token?: string;
}

export interface PluginSettings {
    baseUrl: string;
    token: string;
    folders: FolderMapping[];
}

export const DEFAULT_SETTINGS: PluginSettings = {
    baseUrl: "",
    token: "",
    folders: [],
};

import { normalizePath, TFile, TFolder, Vault } from "obsidian";
import type { FileSystem } from "./sync/types.js";

export class ObsidianFileSystem implements FileSystem {
    constructor(
        private vault: Vault,
        private basePath: string,
    ) {}

    private getFullPath(relativePath: string): string {
        if (this.basePath === "") {
            return normalizePath(relativePath);
        }
        return normalizePath(`${this.basePath}/${relativePath}`);
    }

    async read(path: string): Promise<Buffer> {
        const fullPath = this.getFullPath(path);
        const file = this.vault.getAbstractFileByPath(fullPath);

        if (!(file instanceof TFile)) {
            throw new Error(`File not found: ${path}`);
        }

        const content = await this.vault.readBinary(file);
        return Buffer.from(content);
    }

    async write(path: string, content: Buffer): Promise<void> {
        const fullPath = this.getFullPath(path);
        const existing = this.vault.getAbstractFileByPath(fullPath);

        if (existing instanceof TFile) {
            await this.vault.modifyBinary(existing, content);
        } else {
            await this.vault.createBinary(fullPath, content);
        }
    }

    async rename(from: string, to: string): Promise<void> {
        const fullFrom = this.getFullPath(from);
        const fullTo = this.getFullPath(to);
        const file = this.vault.getAbstractFileByPath(fullFrom);

        if (!file) {
            throw new Error(`File not found: ${from}`);
        }

        await this.vault.rename(file, fullTo);
    }

    async delete(path: string): Promise<void> {
        const fullPath = this.getFullPath(path);
        const file = this.vault.getAbstractFileByPath(fullPath);

        if (!file) {
            return;
        }

        await this.vault.delete(file);
    }

    async list(dir: string): Promise<string[]> {
        const fullDir = this.getFullPath(dir);
        const folder = this.vault.getAbstractFileByPath(fullDir);

        if (!(folder instanceof TFolder) && fullDir !== "") {
            return [];
        }

        const results: string[] = [];
        const base = fullDir === "" ? "" : fullDir + "/";

        for (const file of this.vault.getFiles()) {
            if (file.path.startsWith(base)) {
                const relativePath = file.path.substring(base.length);
                results.push(relativePath);
            }
        }

        return results.sort();
    }

    async hash(path: string): Promise<string> {
        const content = await this.read(path);
        const hashBuffer = await crypto.subtle.digest("SHA-256", content);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    }

    async exists(path: string): Promise<boolean> {
        const fullPath = this.getFullPath(path);
        return this.vault.getAbstractFileByPath(fullPath) !== null;
    }

    async isFile(path: string): Promise<boolean> {
        const fullPath = this.getFullPath(path);
        const file = this.vault.getAbstractFileByPath(fullPath);
        return file instanceof TFile;
    }

    async isDirectory(path: string): Promise<boolean> {
        const fullPath = this.getFullPath(path);
        const folder = this.vault.getAbstractFileByPath(fullPath);
        return folder instanceof TFolder;
    }

    async mkdir(path: string): Promise<void> {
        const fullPath = this.getFullPath(path);
        const existing = this.vault.getAbstractFileByPath(fullPath);

        if (existing) {
            return;
        }

        await this.vault.createFolder(fullPath);
    }

    async findCaseInsensitive(dir: string, name: string): Promise<string | null> {
        const fullDir = this.getFullPath(dir);
        const folder = this.vault.getAbstractFileByPath(fullDir);

        if (!(folder instanceof TFolder)) {
            return null;
        }

        const lowerName = name.toLowerCase();

        for (const child of folder.children) {
            if (child.name.toLowerCase() === lowerName && child.name !== name) {
                return child.name;
            }
        }

        return null;
    }
}

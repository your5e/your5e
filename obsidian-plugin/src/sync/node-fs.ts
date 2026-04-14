import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { FileSystem } from "./types.js";

export class NodeFileSystem implements FileSystem {
    async read(filePath: string): Promise<Buffer> {
        return fs.readFile(filePath);
    }

    async write(filePath: string, content: Buffer): Promise<void> {
        await fs.mkdir(path.dirname(filePath), { recursive: true });
        await fs.writeFile(filePath, content);
    }

    async rename(from: string, to: string): Promise<void> {
        await fs.mkdir(path.dirname(to), { recursive: true });
        await fs.rename(from, to);
        await this.removeEmptyParents(path.dirname(from));
    }

    async delete(filePath: string): Promise<void> {
        await fs.unlink(filePath);
        await this.removeEmptyParents(path.dirname(filePath));
    }

    async list(dir: string): Promise<string[]> {
        const results: string[] = [];
        await this.listRecursive(dir, dir, results);
        return results.sort();
    }

    private async listRecursive(
        base: string,
        dir: string,
        results: string[],
    ): Promise<void> {
        let entries: Awaited<ReturnType<typeof fs.readdir<{ withFileTypes: true }>>>;
        try {
            entries = await fs.readdir(dir, { withFileTypes: true });
        } catch {
            return;
        }
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            const relativePath = path.relative(base, fullPath);
            if (entry.isDirectory()) {
                await this.listRecursive(base, fullPath, results);
            } else if (entry.isFile()) {
                results.push(relativePath);
            }
        }
    }

    async hash(filePath: string): Promise<string> {
        const content = await fs.readFile(filePath);
        return crypto.createHash("sha256").update(content).digest("hex");
    }

    async exists(filePath: string): Promise<boolean> {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    async isFile(filePath: string): Promise<boolean> {
        try {
            const stat = await fs.stat(filePath);
            return stat.isFile();
        } catch {
            return false;
        }
    }

    async isDirectory(filePath: string): Promise<boolean> {
        try {
            const stat = await fs.stat(filePath);
            return stat.isDirectory();
        } catch {
            return false;
        }
    }

    async mkdir(dir: string): Promise<void> {
        await fs.mkdir(dir, { recursive: true });
    }

    async findCaseInsensitive(dir: string, name: string): Promise<string | null> {
        try {
            const entries = await fs.readdir(dir);
            const lowerName = name.toLowerCase();
            for (const entry of entries) {
                if (entry.toLowerCase() === lowerName && entry !== name) {
                    return entry;
                }
            }
            return null;
        } catch {
            return null;
        }
    }

    private async removeEmptyParents(dir: string): Promise<void> {
        try {
            const entries = await fs.readdir(dir);
            if (entries.length === 0) {
                await fs.rmdir(dir);
                await this.removeEmptyParents(path.dirname(dir));
            }
        } catch {
            // Directory doesn't exist or not empty, stop
        }
    }
}

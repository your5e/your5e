import { execSync } from "node:child_process";
import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { expect } from "vitest";

const PROJECT_ROOT = path.resolve(import.meta.dirname, "../..");
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/fixtures");
const TOKEN_FILE = path.join(PROJECT_ROOT, "tests/norm.token");

export const API_BASE = "http://localhost:5844";

export async function getToken(user = "norm"): Promise<string> {
    const tokenFile = path.join(PROJECT_ROOT, `tests/${user}.token`);
    return (await fs.readFile(tokenFile, "utf-8")).trim();
}

export function restoreDatabase(): void {
    execSync(
        `
    COMPOSE_FILE=docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db-test \\
      psql -U your5e postgres <<-SQL
        SELECT pg_terminate_backend(pid)
          FROM pg_stat_activity WHERE datname = 'your5e_test';
        DROP DATABASE IF EXISTS your5e_test;
        CREATE DATABASE your5e_test WITH TEMPLATE your5e_seed;
SQL
  `,
        { cwd: PROJECT_ROOT, stdio: "pipe" },
    );
}

export async function createTempDir(): Promise<string> {
    return fs.mkdtemp(path.join(tmpdir(), "your5e-test-"));
}

export async function createFile(
    outputDir: string,
    filePath: string,
    content = "local content\n",
): Promise<void> {
    const fullPath = path.join(outputDir, filePath);
    await fs.mkdir(path.dirname(fullPath), { recursive: true });
    await fs.writeFile(fullPath, content);
}

export async function copyFixture(
    outputDir: string,
    source: string,
    dest?: string,
): Promise<void> {
    const srcPath = path.join(FIXTURES_DIR, "campaign-notes", source);
    const destPath = path.join(outputDir, dest ?? source);
    await fs.mkdir(path.dirname(destPath), { recursive: true });
    await fs.copyFile(srcPath, destPath);
}

async function hashFile(filePath: string): Promise<string> {
    const content = await fs.readFile(filePath);
    return crypto.createHash("sha256").update(content).digest("hex");
}

async function readSyncState(
    outputDir: string,
): Promise<Map<string, { serverFn: string; localFn: string; hash: string }>> {
    const stateFile = path.join(outputDir, ".sync-state");
    const state = new Map();
    try {
        const content = await fs.readFile(stateFile, "utf-8");
        for (const line of content.trim().split("\n")) {
            if (!line) {
                continue;
            }
            const [uuid, serverFn, localFn, serverHash] = line.split("\t");
            state.set(uuid, { serverFn, localFn, hash: serverHash });
        }
    } catch {
        // No state file
    }
    return state;
}

function findByLocalFilename(
    state: Map<string, { serverFn: string; localFn: string; hash: string }>,
    filename: string,
): { uuid: string; serverFn: string; localFn: string; hash: string } | null {
    for (const [uuid, entry] of state) {
        if (entry.localFn === filename) {
            return { uuid, ...entry };
        }
    }
    return null;
}

export async function assertFileDownloaded(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const fixturePath = path.join(FIXTURES_DIR, "campaign-notes", filename);

    const actual = await fs.readFile(filePath);
    const expected = await fs.readFile(fixturePath);
    expect(actual.equals(expected)).toBe(true);

    const state = await readSyncState(outputDir);
    const entry = findByLocalFilename(state, filename);
    expect(entry).not.toBeNull();
}

export async function assertFileNotDownloaded(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const isFile = await fs
        .stat(filePath)
        .then((stat) => stat.isFile())
        .catch(() => false);
    expect(isFile).toBe(false);

    const state = await readSyncState(outputDir);
    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeNull();
}

export async function assertFileIgnored(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe("local content\n");

    const state = await readSyncState(outputDir);
    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeNull();
}

export async function assertFileUnchanged(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe("local content\n");
}

export async function assertFileNotInState(
    outputDir: string,
    filename: string,
): Promise<void> {
    const state = await readSyncState(outputDir);
    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeNull();
}

export async function assertFileMatchesFixture(
    outputDir: string,
    fixture: string,
    filename?: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename ?? fixture);
    const fixturePath = path.join(FIXTURES_DIR, "campaign-notes", fixture);

    const actual = await fs.readFile(filePath);
    const expected = await fs.readFile(fixturePath);
    expect(actual.equals(expected)).toBe(true);
}

async function walkDir(
    base: string,
    dir: string,
    onFile: (relativePath: string, fullPath: string) => Promise<void>,
): Promise<void> {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
        if (entry.name === ".sync-state") {
            continue;
        }
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            await walkDir(base, fullPath, onFile);
        } else {
            await onFile(path.relative(base, fullPath), fullPath);
        }
    }
}

export async function assertDirMatchesFixture(outputDir: string): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");

    const actualFiles: string[] = [];
    await walkDir(outputDir, outputDir, async (relativePath) => {
        actualFiles.push(relativePath);
    });

    const expectedFiles: string[] = [];
    await walkDir(fixtureDir, fixtureDir, async (relativePath) => {
        expectedFiles.push(relativePath);
    });

    expect(actualFiles.sort()).toEqual(expectedFiles.sort());

    for (const file of expectedFiles) {
        const actualContent = await fs.readFile(path.join(outputDir, file));
        const expectedContent = await fs.readFile(path.join(fixtureDir, file));
        expect(actualContent.equals(expectedContent)).toBe(true);
    }
}

export async function assertStateMatchesFixture(outputDir: string): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");

    const expected = new Map<string, string>();
    await walkDir(fixtureDir, fixtureDir, async (relativePath, fullPath) => {
        const hash = await hashFile(fullPath);
        expected.set(relativePath, hash);
    });

    const state = await readSyncState(outputDir);
    const actual = new Map<string, string>();
    for (const [, entry] of state) {
        actual.set(entry.localFn, entry.hash);
    }

    expect(actual).toEqual(expected);
}

export async function assertFilePushed(
    outputDir: string,
    filename: string,
    token: string,
    expectedContentType?: string,
): Promise<void> {
    const state = await readSyncState(outputDir);
    const entry = findByLocalFilename(state, filename);
    if (!entry) {
        throw new Error(`File ${filename} not found in sync state`);
    }

    const filePath = path.join(outputDir, filename);
    const actualHash = await hashFile(filePath);
    expect(actualHash).toBe(entry.hash);

    const response = await fetch(
        `${API_BASE}/api/notebooks/norm/campaign-notes/${entry.uuid}`,
        { headers: { Authorization: `Token ${token}` } },
    );

    const localContent = await fs.readFile(filePath);
    const remoteContent = Buffer.from(await response.arrayBuffer());
    expect(localContent.equals(remoteContent)).toBe(true);

    if (expectedContentType) {
        const contentType = response.headers.get("content-type")?.split(";")[0];
        expect(contentType).toBe(expectedContentType);
    }
}

export async function cleanupTempDir(dir: string): Promise<void> {
    await fs.rm(dir, { recursive: true, force: true });
}

interface PageData {
    filename: string;
    uuid: string;
    contentHash: string;
    deletedAt: string | null;
}

interface StateEntry {
    uuid: string;
    serverFn: string;
    localFn: string;
    sHash: string;
    lHash: string;
}

let cachedPages: PageData[] | null = null;

async function fetchPagesData(token: string): Promise<PageData[]> {
    if (cachedPages) {
        return cachedPages;
    }

    const response = await fetch(`${API_BASE}/api/notebooks/norm/campaign-notes/`, {
        headers: { Authorization: `Token ${token}` },
    });
    const data = await response.json();
    const pages: PageData[] = data.results.map(
        (p: {
            filename: string;
            uuid: string;
            content_hash: string;
            deleted_at: string | null;
        }) => ({
            filename: p.filename,
            uuid: p.uuid,
            contentHash: p.content_hash,
            deletedAt: p.deleted_at,
        }),
    );
    cachedPages = pages;
    return pages;
}

export function clearPagesCache(): void {
    cachedPages = null;
}

function uuidFor(pages: PageData[], filename: string): string {
    const page = pages.find((p) => p.filename === filename);
    if (!page) {
        throw new Error(`No page found for ${filename}`);
    }
    return page.uuid;
}

async function copyDir(src: string, dest: string): Promise<void> {
    await fs.mkdir(dest, { recursive: true });
    const entries = await fs.readdir(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) {
            await copyDir(srcPath, destPath);
        } else {
            await fs.copyFile(srcPath, destPath);
        }
    }
}

export async function initSyncedDir(outputDir: string, token: string): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");
    await copyDir(fixtureDir, outputDir);

    const pages = await fetchPagesData(token);
    const lines: string[] = [];
    for (const page of pages) {
        if (page.deletedAt) {
            continue;
        }
        lines.push(
            [
                page.uuid,
                page.filename,
                page.filename,
                page.contentHash,
                page.contentHash,
            ].join("\t"),
        );
    }
    await fs.writeFile(path.join(outputDir, ".sync-state"), lines.join("\n"));
}

async function readSyncStateRaw(outputDir: string): Promise<StateEntry[]> {
    const stateFile = path.join(outputDir, ".sync-state");
    const content = await fs.readFile(stateFile, "utf-8");
    return content
        .trim()
        .split("\n")
        .filter((line) => line)
        .map((line) => {
            const [uuid, serverFn, localFn, sHash, lHash] = line.split("\t");
            return { uuid, serverFn, localFn, sHash, lHash };
        });
}

async function writeSyncStateRaw(
    outputDir: string,
    entries: StateEntry[],
): Promise<void> {
    const lines = entries.map((e) =>
        [e.uuid, e.serverFn, e.localFn, e.sHash, e.lHash].join("\t"),
    );
    await fs.writeFile(path.join(outputDir, ".sync-state"), lines.join("\n"));
}

async function removeEmptyParents(dir: string, stopAt: string): Promise<void> {
    if (dir === stopAt || dir === path.dirname(dir)) {
        return;
    }
    try {
        const entries = await fs.readdir(dir);
        if (entries.length === 0) {
            await fs.rmdir(dir);
            await removeEmptyParents(path.dirname(dir), stopAt);
        }
    } catch {
        // Directory doesn't exist or not empty
    }
}

export async function setOlderFilename(
    outputDir: string,
    from: string,
    to: string,
): Promise<void> {
    const fromPath = path.join(outputDir, from);
    const toPath = path.join(outputDir, to);
    await fs.mkdir(path.dirname(toPath), { recursive: true });
    await fs.rename(fromPath, toPath);
    await removeEmptyParents(path.dirname(fromPath), outputDir);

    const entries = await readSyncStateRaw(outputDir);
    for (const entry of entries) {
        if (entry.localFn === from) {
            entry.serverFn = to;
            entry.localFn = to;
        }
    }
    await writeSyncStateRaw(outputDir, entries);
}

export async function setOlderContent(
    outputDir: string,
    filename: string,
): Promise<void> {
    const content = "old content";
    const hash = crypto.createHash("sha256").update(content).digest("hex");

    await fs.writeFile(path.join(outputDir, filename), content);

    const entries = await readSyncStateRaw(outputDir);
    for (const entry of entries) {
        if (entry.localFn === filename) {
            entry.sHash = hash;
            entry.lHash = hash;
        }
    }
    await writeSyncStateRaw(outputDir, entries);
}

export async function modifyFile(outputDir: string, filename: string): Promise<void> {
    await fs.writeFile(path.join(outputDir, filename), "local content\n");
}

export async function renameLocalFile(
    outputDir: string,
    from: string,
    to: string,
): Promise<void> {
    const fromPath = path.join(outputDir, from);
    const toPath = path.join(outputDir, to);
    await fs.mkdir(path.dirname(toPath), { recursive: true });
    await fs.rename(fromPath, toPath);
    await removeEmptyParents(path.dirname(fromPath), outputDir);

    const entries = await readSyncStateRaw(outputDir);
    for (const entry of entries) {
        if (entry.localFn === from) {
            entry.localFn = to;
        }
    }
    await writeSyncStateRaw(outputDir, entries);
}

export async function renameLocalFileUntracked(
    outputDir: string,
    from: string,
    to: string,
): Promise<void> {
    const fromPath = path.join(outputDir, from);
    const toPath = path.join(outputDir, to);
    await fs.mkdir(path.dirname(toPath), { recursive: true });
    await fs.rename(fromPath, toPath);
    await removeEmptyParents(path.dirname(fromPath), outputDir);
}

export async function deleteTrackedFile(
    outputDir: string,
    filename: string,
): Promise<void> {
    await fs.unlink(path.join(outputDir, filename));
}

export async function untrackFile(outputDir: string, filename: string): Promise<void> {
    const entries = await readSyncStateRaw(outputDir);
    const filtered = entries.filter((e) => e.localFn !== filename);
    await writeSyncStateRaw(outputDir, filtered);
}

export async function untrackAndRemoveFile(
    outputDir: string,
    filename: string,
): Promise<void> {
    await untrackFile(outputDir, filename);
    await fs.rm(path.join(outputDir, filename), { recursive: true, force: true });
}

export async function addStaleFile(outputDir: string, filename: string): Promise<void> {
    const content = "local content";
    const hash = crypto.createHash("sha256").update(content).digest("hex");
    const uuid = `stale-uuid-${Math.random().toString(36).slice(2)}`;

    await fs.mkdir(path.dirname(path.join(outputDir, filename)), {
        recursive: true,
    });
    await fs.writeFile(path.join(outputDir, filename), content);

    const entries = await readSyncStateRaw(outputDir);
    const entry: StateEntry = {
        uuid,
        serverFn: filename,
        localFn: filename,
        sHash: hash,
        lHash: hash,
    };
    entries.push(entry);
    await writeSyncStateRaw(outputDir, entries);
}

export async function markFileStale(
    outputDir: string,
    filename: string,
): Promise<void> {
    const newUuid = `stale-uuid-${Math.random().toString(36).slice(2)}`;
    const entries = await readSyncStateRaw(outputDir);
    for (const entry of entries) {
        if (entry.localFn === filename) {
            entry.uuid = newUuid;
        }
    }
    await writeSyncStateRaw(outputDir, entries);
}

export async function fileTracksDeletedRemote(
    outputDir: string,
    filename: string,
    token: string,
): Promise<void> {
    const content = "# Old Notes\n\nThese notes are no longer needed.\n";
    const hash = crypto.createHash("sha256").update(content).digest("hex");
    const pages = await fetchPagesData(token);
    const uuid = uuidFor(pages, "Old Notes.md");

    await fs.mkdir(path.dirname(path.join(outputDir, filename)), {
        recursive: true,
    });
    await fs.writeFile(path.join(outputDir, filename), content);

    const entries = await readSyncStateRaw(outputDir);
    const entry: StateEntry = {
        uuid,
        serverFn: filename,
        localFn: filename,
        sHash: hash,
        lHash: hash,
    };
    entries.push(entry);
    await writeSyncStateRaw(outputDir, entries);
}

export async function assertTrackedFileIntact(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then((s) => s.isFile())
        .catch(() => false);
    expect(exists).toBe(true);

    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === filename);
    expect(entry).toBeDefined();

    const actualHash = await hashFile(filePath);
    expect(actualHash).toBe(entry?.sHash);
}

export async function assertTrackedFileDeleted(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);

    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === filename);
    expect(entry).toBeUndefined();
}

export async function assertTrackedFileNotRestored(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);

    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === filename);
    expect(entry).toBeDefined();
}

export async function assertEmptyDirRemoved(
    outputDir: string,
    dirname: string,
): Promise<void> {
    const dirPath = path.join(outputDir, dirname);
    const exists = await fs
        .stat(dirPath)
        .then((s) => s.isDirectory())
        .catch(() => false);
    expect(exists).toBe(false);
}

export async function assertFileInState(
    outputDir: string,
    filename: string,
): Promise<void> {
    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === filename);
    expect(entry).toBeDefined();
}

export async function assertNotInState(
    outputDir: string,
    pattern: string,
): Promise<void> {
    const stateFile = path.join(outputDir, ".sync-state");
    const content = await fs.readFile(stateFile, "utf-8");
    expect(content).not.toContain(pattern);
}

export async function assertTrackedFileMatchesFixture(
    outputDir: string,
    fixture: string,
    filename?: string,
): Promise<void> {
    const localFile = filename ?? fixture;
    const filePath = path.join(outputDir, localFile);
    const fixturePath = path.join(FIXTURES_DIR, "campaign-notes", fixture);

    const actual = await fs.readFile(filePath);
    const expected = await fs.readFile(fixturePath);
    expect(actual.equals(expected)).toBe(true);

    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === localFile);
    expect(entry).toBeDefined();
}

export async function assertServerFileDeleted(
    filename: string,
    token: string,
): Promise<void> {
    const response = await fetch(`${API_BASE}/api/notebooks/norm/campaign-notes/`, {
        headers: { Authorization: `Token ${token}` },
    });
    const data = await response.json();
    const page = data.results.find(
        (p: { filename: string }) => p.filename === filename,
    );
    expect(page).toBeDefined();
    expect(page.deleted_at).not.toBeNull();
}

export async function assertFileDeletedOnServer(
    outputDir: string,
    filename: string,
    token: string,
): Promise<void> {
    const entries = await readSyncStateRaw(outputDir);
    const entry = entries.find((e) => e.localFn === filename);
    expect(entry).toBeUndefined();

    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);

    await assertServerFileDeleted(filename, token);
}

export function invalidateToken(token: string): void {
    const tokenKey = token.slice(0, 15);
    execSync(
        `
    COMPOSE_FILE=docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db-test \\
      psql -U your5e your5e_test \\
      -c "DELETE FROM users_authtoken WHERE token_key = '${tokenKey}'"
  `,
        { cwd: PROJECT_ROOT, stdio: "pipe" },
    );
}

export function downgradeToViewer(
    username: string,
    notebookOwner: string,
    notebookSlug: string,
): void {
    execSync(
        `
    COMPOSE_FILE=docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db-test \\
      psql -U your5e your5e_test \\
      -c "UPDATE notebooks_notebookpermission SET role = 'viewer'
          FROM users_user u, notebooks_notebook n
          WHERE notebooks_notebookpermission.user_id = u.id
          AND notebooks_notebookpermission.notebook_id = n.wiki_ptr_id
          AND u.username = '${username}'
          AND n.owner_id = (
              SELECT id FROM users_user WHERE username = '${notebookOwner}')
          AND n.slug = '${notebookSlug}'"
  `,
        { cwd: PROJECT_ROOT, stdio: "pipe" },
    );
}

export async function assertNoOutputDir(outputDir: string): Promise<void> {
    const exists = await fs
        .stat(outputDir)
        .then((s) => s.isDirectory())
        .catch(() => false);
    expect(exists).toBe(false);
}

export async function removeFile(outputDir: string, filename: string): Promise<void> {
    await fs.unlink(path.join(outputDir, filename));
}

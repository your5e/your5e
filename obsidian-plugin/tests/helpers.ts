import { execSync } from "node:child_process";
import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import { hostname, tmpdir } from "node:os";
import * as path from "node:path";
import { expect } from "vitest";
import type { SyncStateEntry } from "../src/sync/types.js";

const PROJECT_ROOT = path.resolve(import.meta.dirname, "../..");
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/fixtures");

export const API_BASE = "http://localhost:5854";

export async function getToken(user = "norm"): Promise<string> {
    const tokenFile = path.join(PROJECT_ROOT, `tests/${user}.token`);
    return (await fs.readFile(tokenFile, "utf-8")).trim();
}

export function restoreDatabase(): void {
    execSync(
        `
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db \\
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

export async function createTestDir(): Promise<{
    testDir: string;
    outputDir: string;
}> {
    const testDir = await fs.mkdtemp(path.join(tmpdir(), "your5e-test-"));
    const outputDir = path.join(testDir, "output");
    return { testDir, outputDir };
}

export async function cleanupTestDir(testDir: string): Promise<void> {
    await fs.rm(testDir, { recursive: true, force: true });
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

function findByLocalFilename(
    state: Map<string, SyncStateEntry>,
    filename: string,
): SyncStateEntry | undefined {
    for (const entry of state.values()) {
        if (entry.localFilename === filename) {
            return entry;
        }
    }
    return undefined;
}

export async function assertFileDownloaded(
    outputDir: string,
    filename: string,
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const fixturePath = path.join(FIXTURES_DIR, "campaign-notes", filename);

    const actual = await fs.readFile(filePath);
    const expected = await fs.readFile(fixturePath);
    expect(actual.equals(expected)).toBe(true);

    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeDefined();
}

export async function assertFileNotDownloaded(
    outputDir: string,
    filename: string,
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const isFile = await fs
        .stat(filePath)
        .then((stat) => stat.isFile())
        .catch(() => false);
    expect(isFile).toBe(false);

    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeUndefined();
}

export async function assertFileIgnored(
    outputDir: string,
    filename: string,
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe("local content\n");

    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeUndefined();
}

export async function assertFileUnchanged(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe("local content\n");
}

export async function assertFileModified(
    outputDir: string,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe("modified local content\n");
}

export async function assertServerEditedContent(
    outputDir: string,
    filename: string,
    expectedContent = "server edited content\n",
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe(expectedContent);
}

export function assertFileNotInState(
    filename: string,
    state: Map<string, SyncStateEntry>,
): void {
    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeUndefined();
}

export function assertFileInState(
    filename: string,
    state: Map<string, SyncStateEntry>,
): void {
    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeDefined();
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

export async function assertStateMatchesFixture(
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");

    const expected = new Map<string, string>();
    await walkDir(fixtureDir, fixtureDir, async (relativePath, fullPath) => {
        const hash = await hashFile(fullPath);
        expected.set(relativePath, hash);
    });

    const actual = new Map<string, string>();
    for (const entry of state.values()) {
        actual.set(entry.localFilename, entry.serverHash);
    }

    expect(actual).toEqual(expected);
}

export async function assertFixtureFilesInState(
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");

    await walkDir(fixtureDir, fixtureDir, async (relativePath, fullPath) => {
        const expectedHash = await hashFile(fullPath);
        const entry = findByLocalFilename(state, relativePath);
        if (!entry) {
            throw new Error(`Fixture file ${relativePath} not found in sync state`);
        }
        expect(entry.serverHash).toBe(expectedHash);
    });
}

export async function assertFilePushed(
    outputDir: string,
    filename: string,
    state: Map<string, SyncStateEntry>,
    token: string,
    expectedContentType?: string,
): Promise<void> {
    const entry = findByLocalFilename(state, filename);
    if (!entry) {
        throw new Error(`File ${filename} not found in sync state`);
    }

    const filePath = path.join(outputDir, filename);
    const actualHash = await hashFile(filePath);
    expect(actualHash).toBe(entry.serverHash);

    const response = await fetch(
        `${API_BASE}/v1/notebooks/norm/campaign-notes/${entry.uuid}`,
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

export async function assertOutputDirExists(outputDir: string): Promise<void> {
    const exists = await fs
        .stat(outputDir)
        .then((s) => s.isDirectory())
        .catch(() => false);
    expect(exists).toBe(true);
}

export function assertStateIsEmpty(state: Map<string, SyncStateEntry>): void {
    expect(state.size).toBe(0);
}

export async function assertNoOutputDir(outputDir: string): Promise<void> {
    const exists = await fs
        .stat(outputDir)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);
}

export function assertNotInState(
    state: Map<string, SyncStateEntry>,
    uuidPrefix: string,
): void {
    for (const uuid of state.keys()) {
        if (uuid.startsWith(uuidPrefix)) {
            throw new Error(`Found entry with UUID starting with ${uuidPrefix}`);
        }
    }
}

export function assertInState(
    state: Map<string, SyncStateEntry>,
    uuidPrefix: string,
): void {
    for (const uuid of state.keys()) {
        if (uuid.startsWith(uuidPrefix)) {
            return;
        }
    }
    throw new Error(`No entry found with UUID starting with ${uuidPrefix}`);
}

// State building functions

interface PageData {
    filename: string;
    uuid: string;
    contentHash: string;
    deletedAt: string | null;
}

let cachedPages: PageData[] | null = null;

async function fetchPagesData(token: string): Promise<PageData[]> {
    if (cachedPages) {
        return cachedPages;
    }

    const response = await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/`, {
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

export async function initSyncedDir(
    outputDir: string,
    token: string,
): Promise<Map<string, SyncStateEntry>> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");
    await copyDir(fixtureDir, outputDir);

    const pages = await fetchPagesData(token);
    const state = new Map<string, SyncStateEntry>();

    for (const page of pages) {
        if (page.deletedAt) {
            continue;
        }
        state.set(page.uuid, {
            uuid: page.uuid,
            serverFilename: page.filename,
            localFilename: page.filename,
            serverHash: page.contentHash,
            localHash: page.contentHash,
        });
    }

    return state;
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

export async function serverEditContent(
    token: string,
    uuid: string,
    content = "server edited content\n",
): Promise<void> {
    await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/${uuid}`, {
        method: "PUT",
        headers: {
            Authorization: `Token ${token}`,
            "Content-Type": "text/markdown",
        },
        body: content,
    });
}

export async function serverRename(
    token: string,
    uuid: string,
    to: string,
): Promise<void> {
    await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/${uuid}`, {
        method: "PATCH",
        headers: {
            Authorization: `Token ${token}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename: to }),
    });
}

export async function serverDelete(token: string, uuid: string): Promise<void> {
    await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/${uuid}`, {
        method: "DELETE",
        headers: { Authorization: `Token ${token}` },
    });
}

export async function serverCreate(
    token: string,
    filename: string,
    content?: string,
): Promise<string> {
    const basename = path.basename(filename, path.extname(filename));
    const body = content ?? `# ${basename}\n`;

    const formData = new FormData();
    formData.append("file", new Blob([body]), filename);

    const response = await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/`, {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
        body: formData,
    });

    const data = await response.json();
    return data.uuid;
}

export async function modifyFile(outputDir: string, filename: string): Promise<void> {
    await fs.writeFile(path.join(outputDir, filename), "modified local content\n");
}

export async function renameLocalFile(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    from: string,
    to: string,
): Promise<void> {
    const fromPath = path.join(outputDir, from);
    const toPath = path.join(outputDir, to);
    await fs.mkdir(path.dirname(toPath), { recursive: true });
    await fs.rename(fromPath, toPath);
    await removeEmptyParents(path.dirname(fromPath), outputDir);

    for (const entry of state.values()) {
        if (entry.localFilename === from) {
            entry.localFilename = to;
        }
    }
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
    state?: Map<string, SyncStateEntry>,
): Promise<void> {
    await fs.unlink(path.join(outputDir, filename));
    // Mark as aware deletion
    if (state) {
        for (const entry of state.values()) {
            if (entry.localFilename === filename) {
                entry.localDeleted = true;
                return;
            }
        }
    }
}

export function untrackFile(
    state: Map<string, SyncStateEntry>,
    filename: string,
): void {
    for (const [uuid, entry] of state) {
        if (entry.localFilename === filename) {
            state.delete(uuid);
            return;
        }
    }
}

export async function untrackAndRemoveFile(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<void> {
    untrackFile(state, filename);
    await fs.rm(path.join(outputDir, filename), { recursive: true, force: true });
}

export async function addStaleFile(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<void> {
    const content = "local content\n";
    const hash = crypto.createHash("sha256").update(content).digest("hex");
    const uuid = `stale-uuid-${Math.random().toString(36).slice(2)}`;

    await fs.mkdir(path.dirname(path.join(outputDir, filename)), {
        recursive: true,
    });
    await fs.writeFile(path.join(outputDir, filename), content);

    state.set(uuid, {
        uuid,
        serverFilename: filename,
        localFilename: filename,
        serverHash: hash,
        localHash: hash,
    });
}

export function markFileStale(
    state: Map<string, SyncStateEntry>,
    filename: string,
): void {
    const newUuid = `stale-uuid-${Math.random().toString(36).slice(2)}`;
    for (const [uuid, entry] of state) {
        if (entry.localFilename === filename) {
            state.delete(uuid);
            entry.uuid = newUuid;
            state.set(newUuid, entry);
            return;
        }
    }
}

export function setBaseHash(
    state: Map<string, SyncStateEntry>,
    filename: string,
    hash: string,
): void {
    for (const entry of state.values()) {
        if (entry.localFilename === filename) {
            entry.serverHash = hash;
            return;
        }
    }
}

export async function assertTrackedFileIntact(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then((s) => s.isFile())
        .catch(() => false);
    expect(exists).toBe(true);

    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeDefined();

    const actualHash = await hashFile(filePath);
    expect(actualHash).toBe(entry?.serverHash);
}

export async function assertTrackedFileDeleted(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);

    const entry = findByLocalFilename(state, filename);
    expect(entry).toBeUndefined();
}

export async function assertTrackedFileNotRestored(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const exists = await fs
        .stat(filePath)
        .then(() => true)
        .catch(() => false);
    expect(exists).toBe(false);

    const entry = findByLocalFilename(state, filename);
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

export async function assertTrackedFileMatchesFixture(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    fixture: string,
    filename?: string,
): Promise<void> {
    const localFile = filename ?? fixture;
    const filePath = path.join(outputDir, localFile);
    const fixturePath = path.join(FIXTURES_DIR, "campaign-notes", fixture);

    const actual = await fs.readFile(filePath);
    const expected = await fs.readFile(fixturePath);
    expect(actual.equals(expected)).toBe(true);

    const entry = findByLocalFilename(state, localFile);
    expect(entry).toBeDefined();
}

export async function assertServerFileDeleted(
    filename: string,
    token: string,
): Promise<void> {
    const response = await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/`, {
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
    state: Map<string, SyncStateEntry>,
    filename: string,
    token: string,
): Promise<void> {
    const entry = findByLocalFilename(state, filename);
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
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db \\
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
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db \\
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

export function deletePageByUuid(uuid: string): void {
    execSync(
        `
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db \\
      psql -U your5e your5e_test \\
      -c "UPDATE wikis_page SET deleted_at = NOW() WHERE uuid = '${uuid}'"
  `,
        { cwd: PROJECT_ROOT, stdio: "pipe" },
    );
}

export function serverPurge(uuid: string): void {
    execSync(
        `
    COMPOSE_FILE=docker-compose.yml:docker-compose.test.yml \\
    docker compose -p your5e-test exec -T db \\
      psql -U your5e your5e_test <<-SQL
        DELETE FROM wikis_version WHERE page_id = (
            SELECT id FROM wikis_page WHERE uuid = '${uuid}'
        );
        DELETE FROM wikis_page WHERE uuid = '${uuid}';
SQL
  `,
        { cwd: PROJECT_ROOT, stdio: "pipe" },
    );
}

export async function uuidFor(
    state: Map<string, SyncStateEntry>,
    filename: string,
): Promise<string> {
    for (const [uuid, entry] of state) {
        if (entry.localFilename === filename) {
            return uuid;
        }
    }
    throw new Error(`No UUID found for ${filename}`);
}

export async function removeFile(outputDir: string, filename: string): Promise<void> {
    await fs.unlink(path.join(outputDir, filename));
}

export async function getExpectedLastUpdate(): Promise<string> {
    const expectedFile = path.join(PROJECT_ROOT, "tests/last_update");
    return (await fs.readFile(expectedFile, "utf-8")).trim();
}

export async function assertLastUpdateMatchesExpected(
    lastUpdate: string | undefined,
): Promise<void> {
    expect(lastUpdate).toBeDefined();
    const expected = await getExpectedLastUpdate();
    expect(lastUpdate).toBe(expected);
}

export function assertLastUpdateIsEpoch(lastUpdate: string | undefined): void {
    expect(lastUpdate).toBe("0001-01-01T00:00:00.000000Z");
}

export function assertLastUpdateExists(lastUpdate: string | undefined): void {
    expect(lastUpdate).toBeDefined();
}

export function assertSyncMetadataUpdated(
    lastUpdate: string | undefined,
    lastFullSync: string | undefined,
): void {
    expect(lastUpdate).toBeDefined();
    expect(lastUpdate).not.toBe("2020-01-01T00:00:00Z");

    expect(lastFullSync).toBeDefined();
    if (!lastFullSync) {
        throw new Error("lastFullSync is undefined");
    }

    const now = Date.now();
    const lastFullSyncTime = new Date(lastFullSync).getTime();
    const ageSeconds = (now - lastFullSyncTime) / 1000;
    expect(ageSeconds).toBeLessThan(60);
}

export function assertIncrementalResults(
    incrementalResults: number | undefined,
    expected: number,
): void {
    expect(incrementalResults).toBe(expected);
}

export function shortHostname(): string {
    return hostname().split(".")[0];
}

export function mergeableOrc(): string {
    return `# Bestiary

Creatures encountered.

## Goblin

Small and cunning.

## Orc

Large and aggressive.
`;
}

export function mergeableTroll(): string {
    return `# Bestiary

Creatures encountered.

## Goblin

Small and cunning.

## Troll

Regenerates health.
`;
}

export function mergedOrcTroll(): string {
    return `# Bestiary

Creatures encountered.

## Goblin

Small and cunning.

## Orc

Large and aggressive.

## Troll

Regenerates health.
`;
}

export async function modifyFileWithContent(
    outputDir: string,
    filename: string,
    content: string,
): Promise<void> {
    await fs.writeFile(path.join(outputDir, filename), content);
}

export async function assertFileContent(
    outputDir: string,
    filename: string,
    expectedContent: string,
): Promise<void> {
    const filePath = path.join(outputDir, filename);
    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toBe(expectedContent);
}

export async function assertFixtureFilesDownloaded(outputDir: string): Promise<void> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");

    async function checkFixtures(dir: string): Promise<void> {
        const entries = await fs.readdir(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                await checkFixtures(fullPath);
            } else {
                const relativePath = path.relative(fixtureDir, fullPath);
                const outputPath = path.join(outputDir, relativePath);
                const fixtureContent = await fs.readFile(fullPath);
                const outputContent = await fs.readFile(outputPath);
                expect(outputContent.equals(fixtureContent)).toBe(true);
            }
        }
    }

    await checkFixtures(fixtureDir);
}

export function assertUuidLocalFilename(
    state: Map<string, SyncStateEntry>,
    uuid: string,
    expectedFilename: string,
): void {
    const entry = state.get(uuid);
    expect(entry).toBeDefined();
    expect(entry?.localFilename).toBe(expectedFilename);
}

export function assertUuidRemoteFilename(
    state: Map<string, SyncStateEntry>,
    uuid: string,
    expectedFilename: string,
): void {
    const entry = state.get(uuid);
    expect(entry).toBeDefined();
    expect(entry?.serverFilename).toBe(expectedFilename);
}

async function getFixtureFiles(): Promise<string[]> {
    const fixtureDir = path.join(FIXTURES_DIR, "campaign-notes");
    const files: string[] = [];

    async function walk(dir: string): Promise<void> {
        const entries = await fs.readdir(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                await walk(fullPath);
            } else {
                files.push(path.relative(fixtureDir, fullPath));
            }
        }
    }

    await walk(fixtureDir);
    return files;
}

export async function assertFixturesIntact(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
): Promise<void> {
    await assertFixturesIntactExcept(outputDir, state);
}

export async function assertFixturesIntactExcept(
    outputDir: string,
    state: Map<string, SyncStateEntry>,
    ...excluded: string[]
): Promise<void> {
    const fixtureFiles = await getFixtureFiles();
    for (const file of fixtureFiles) {
        if (excluded.includes(file)) {
            continue;
        }
        await assertTrackedFileMatchesFixture(outputDir, state, file);
    }
}

export function todayDate(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
}

export function assertTimestampInRange(
    timestamp: string,
    before: string,
    after: string,
): void {
    expect(timestamp >= before).toBe(true);
    expect(timestamp <= after).toBe(true);
}

export function nowTimestamp(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    return `${year}${month}${day}${hours}${minutes}${seconds}`;
}

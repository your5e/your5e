import * as crypto from "node:crypto";
import * as path from "node:path";
import type { FileSystem, SyncConfig, SyncResult, SyncStateEntry } from "./types.js";

interface RemotePage {
    uuid: string;
    filename: string;
    content_hash: string;
    version: number;
    deleted_at: string | null;
}

const DEFAULT_TIMEOUT_MS = 30000;

export class SyncEngine {
    private output: string[] = [];
    private remotePages: Map<string, RemotePage> = new Map();
    private syncState: Map<string, SyncStateEntry> = new Map();
    private fs: FileSystem;
    private timeoutMs: number;
    private lastUpdate?: string;
    private lastFullSync?: string;
    private isIncrementalSync = false;
    private permissionDenied = false;

    constructor(private config: SyncConfig) {
        this.fs = config.fileSystem;
        this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
        this.lastUpdate = config.lastUpdate;
        this.lastFullSync = config.lastFullSync;
    }

    async run(): Promise<SyncResult> {
        this.output = [];
        this.remotePages = new Map();
        this.syncState = this.config.initialState ?? new Map();
        this.permissionDenied = false;

        if (!this.config.token) {
            this.output.push("sync: ERROR API token missing");
            throw new Error("API token missing");
        }

        // Determine if we should do incremental sync
        this.isIncrementalSync = this.shouldUseIncrementalSync();

        const editable = await this.fetchRemoteState();

        if (this.config.afterFetchHook) {
            await this.config.afterFetchHook();
        }

        if (!(await this.fs.isDirectory(this.config.outputDir))) {
            await this.fs.mkdir(this.config.outputDir);
        }

        await this.detectUntrackedRenames();

        let pullOnly = this.config.pullOnly;
        if (!pullOnly && !editable) {
            this.output.push(
                "sync: NOTE read-only access, switching to pull-only mode",
            );
            pullOnly = true;
        }

        if (!pullOnly) {
            await this.applyLocalUpdates();
        }

        const deletedUuids: string[] = [];
        const activeUuids: string[] = [];
        for (const [uuid, remote] of this.remotePages) {
            if (remote.deleted_at !== null) {
                deletedUuids.push(uuid);
            } else {
                activeUuids.push(uuid);
            }
        }

        await this.applyRemoteDeletions(deletedUuids);
        await this.applyRemoteUpdates(activeUuids, new Set<string>());

        // Skip stale file checks during incremental sync
        if (!this.isIncrementalSync) {
            await this.checkForStaleFiles();
        }

        // Update lastFullSync if we did a full sync
        if (!this.isIncrementalSync) {
            this.lastFullSync = new Date().toISOString();
        }

        return {
            output: this.output,
            state: this.syncState,
            lastUpdate: this.lastUpdate,
            lastFullSync: this.lastFullSync,
        };
    }

    private shouldUseIncrementalSync(): boolean {
        if (!this.lastUpdate || !this.lastFullSync) {
            return false;
        }

        const lastFullSyncTime = new Date(this.lastFullSync).getTime();
        const now = new Date().getTime();
        const oneHourInMs = 1 * 60 * 60 * 1000;

        return now - lastFullSyncTime < oneHourInMs;
    }

    private async detectUntrackedRenames(): Promise<void> {
        for (const [uuid, entry] of this.syncState) {
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            if (await this.fs.isFile(localPath)) {
                continue;
            }

            const newFilename = await this.findUntrackedFileByHash(entry.localHash);
            if (!newFilename) {
                continue;
            }

            this.output.push(
                `info: detected rename "${entry.localFilename}" to "${newFilename}"`,
            );
            this.updateSyncState(uuid, "", newFilename);
        }
    }

    private async findUntrackedFileByHash(targetHash: string): Promise<string | null> {
        const localFiles = await this.listLocalFiles();
        for (const file of localFiles) {
            if (file === ".sync-state") {
                continue;
            }
            if (this.fileIsTrackedByLocalFilename(file)) {
                continue;
            }

            const filePath = path.join(this.config.outputDir, file);
            const hash = await this.fs.hash(filePath);
            if (hash === targetHash) {
                return file;
            }
        }
        return null;
    }

    private async fetchRemoteState(): Promise<boolean> {
        let baseUrl = `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/`;

        // Add ?since= parameter for incremental sync
        if (this.isIncrementalSync && this.lastUpdate) {
            baseUrl += `?since=${encodeURIComponent(this.lastUpdate)}`;
        }

        let nextPage: string | null = baseUrl;
        let editable = true;

        while (nextPage) {
            const response = await fetch(nextPage, {
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            });

            if (response.status === 401 || response.status === 403) {
                this.output.push("sync: ERROR API token invalid");
                throw new Error("API token invalid");
            }
            if (response.status === 404) {
                this.output.push("sync: ERROR notebook not found");
                throw new Error("Notebook not found");
            }
            if (!response.ok) {
                this.output.push(
                    `sync: ERROR unexpected response (HTTP ${response.status})`,
                );
                throw new Error(`Unexpected response (HTTP ${response.status})`);
            }

            const data = await response.json();

            if (data.editable !== undefined) {
                editable = data.editable;
            }

            // Extract and store lastUpdate from API response
            if (data.last_update) {
                this.lastUpdate = data.last_update;
            }

            for (const page of data.results as RemotePage[]) {
                this.remotePages.set(page.uuid, page);
            }

            nextPage = data.next;
            if (nextPage && !nextPage.startsWith("http")) {
                nextPage = `${this.config.baseUrl}${nextPage}`;
            }
        }

        return editable;
    }

    private async applyLocalUpdates(): Promise<void> {
        const staleUuids: string[] = [];

        for (const [uuid, entry] of this.syncState) {
            const remote = this.remotePages.get(uuid);
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const localExists = await this.fs.isFile(localPath);

            if (!localExists) {
                await this.pushLocalDeletion(uuid, entry, remote);
                continue;
            }

            const currentHash = await this.fs.hash(localPath);
            const localEdited = currentHash !== entry.serverHash;
            const localRenamed = entry.localFilename !== entry.serverFilename;
            const isStale = !remote;

            if (isStale && localEdited) {
                const errorMsg = await this.tryCreateRemoteFile(entry.localFilename);
                if (errorMsg) {
                    this.output.push(
                        `push: ERROR cannot push "${entry.localFilename}": ${errorMsg}`,
                    );
                    staleUuids.push(uuid);
                } else {
                    this.deleteSyncState(uuid);
                }
                continue;
            }

            const remoteRenamed = remote && remote.filename !== entry.serverFilename;
            const remoteEdited = remote && remote.content_hash !== entry.serverHash;
            const remoteDeleted = remote && remote.deleted_at !== null;

            if (localRenamed) {
                const renameSucceeded = await this.pushLocalRename(uuid, entry, remote);
                if (!renameSucceeded) {
                    continue;
                }
            }

            if (localEdited) {
                if (remoteRenamed && !localRenamed && remote) {
                    const ok = await this.pushLocalRename(uuid, entry, remote);
                    if (!ok) {
                        continue;
                    }
                }
                await this.pushLocalEdit(
                    uuid,
                    entry,
                    remote,
                    remoteEdited ?? false,
                    remoteDeleted ?? false,
                );
            }
        }

        const localFiles = await this.listLocalFiles();
        for (const file of localFiles) {
            if (file === ".sync-state") {
                continue;
            }
            if (this.fileIsTrackedByLocalFilename(file)) {
                continue;
            }
            if (await this.remoteHasIdenticalFile(file)) {
                continue;
            }

            const errorMsg = await this.tryCreateRemoteFile(file);
            if (errorMsg) {
                this.output.push(`push: ERROR cannot push "${file}": ${errorMsg}`);
            }
        }

        // Clean up stale UUIDs after the untracked files loop, otherwise the
        // file would be picked up as "new" and tried again
        for (const uuid of staleUuids) {
            this.deleteSyncState(uuid);
        }
    }

    private async pushLocalDeletion(
        uuid: string,
        entry: SyncStateEntry,
        remote: RemotePage | undefined,
    ): Promise<void> {
        if (this.permissionDenied) {
            return;
        }
        if (!remote || remote.deleted_at !== null) {
            this.deleteSyncState(uuid);
            return;
        }

        // local file was deleted but renamed remotely;
        // rename it back before deleting as local change takes precedence
        if (remote.filename !== entry.localFilename) {
            const renameResponse = await fetch(
                `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
                {
                    method: "PATCH",
                    headers: {
                        Authorization: `Token ${this.config.token}`,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ filename: entry.localFilename }),
                    signal: AbortSignal.timeout(this.timeoutMs),
                },
            );

            if (this.handlePushAuthError(renameResponse)) {
                return;
            }
            if (renameResponse.ok) {
                this.output.push(
                    `push: renamed "${remote.filename}" to "${entry.localFilename}"`,
                );
                entry.serverFilename = entry.localFilename;
                remote.filename = entry.localFilename;
            } else {
                return;
            }
        }

        const remoteEdited = remote.content_hash !== entry.serverHash;
        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                method: "DELETE",
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (this.handlePushAuthError(response)) {
            return;
        }
        if (response.ok) {
            if (remoteEdited) {
                this.output.push(
                    `push: deleted "${entry.localFilename}" (had remote changes)`,
                );
            } else {
                this.output.push(`push: deleted "${entry.localFilename}"`);
            }
            this.deleteSyncState(uuid);
            this.remotePages.delete(uuid);
        }
    }

    private handlePushAuthError(response: Response): boolean {
        if (response.status === 401) {
            this.output.push("sync: ERROR API token invalid");
            throw new Error("API token invalid");
        }
        if (response.status === 403) {
            if (!this.permissionDenied) {
                this.output.push(
                    "sync: NOTE permission denied, switching to pull-only mode",
                );
                this.permissionDenied = true;
            }
            return true;
        }
        return false;
    }

    private async pushLocalRename(
        uuid: string,
        entry: SyncStateEntry,
        remote: RemotePage | undefined,
    ): Promise<boolean> {
        if (this.permissionDenied) {
            return false;
        }
        if (!remote) {
            return false;
        }

        const payload: Record<string, unknown> = { filename: entry.localFilename };
        if (remote.deleted_at !== null) {
            payload.restore = true;
        }

        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                method: "PATCH",
                headers: {
                    Authorization: `Token ${this.config.token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (this.handlePushAuthError(response)) {
            return false;
        }
        if (response.ok) {
            const data = await response.json();
            this.output.push(
                `push: renamed "${remote.filename}" to "${entry.localFilename}"`,
            );
            entry.serverFilename = entry.localFilename;
            remote.filename = entry.localFilename;
            remote.content_hash = data.content_hash;
            remote.version = data.version;
            remote.deleted_at = null;
            return true;
        }

        if (response.status === 400 || response.status === 409) {
            const data = await response.json();
            this.output.push(
                `push: ERROR cannot rename "${entry.localFilename}": ${data.error}`,
            );
        }
        return false;
    }

    private async pushLocalEdit(
        uuid: string,
        entry: SyncStateEntry,
        remote: RemotePage | undefined,
        remoteEdited: boolean,
        _remoteDeleted: boolean,
    ): Promise<void> {
        if (this.permissionDenied) {
            return;
        }
        const localPath = path.join(this.config.outputDir, entry.localFilename);
        const content = await this.fs.read(localPath);

        const ext = entry.localFilename.split(".").pop()?.toLowerCase();
        let contentType = "application/octet-stream";
        if (ext === "md") {
            contentType = "text/markdown";
        } else if (ext === "txt") {
            contentType = "text/plain";
        } else if (ext === "png") {
            contentType = "image/png";
        } else if (ext === "jpg" || ext === "jpeg") {
            contentType = "image/jpeg";
        }

        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                method: "PUT",
                headers: {
                    Authorization: `Token ${this.config.token}`,
                    "Content-Type": contentType,
                },
                body: content,
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (this.handlePushAuthError(response)) {
            return;
        }
        if (response.ok) {
            const data = await response.json();
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const actualHash = await this.fs.hash(localPath);

            if (data.content_hash !== actualHash) {
                // the server normalised the line endings
                await this.fetchRemoteFile(
                    uuid,
                    entry.localFilename,
                    data.content_hash,
                );
            }

            entry.serverHash = data.content_hash;
            entry.localHash = data.content_hash;

            if (remote) {
                remote.content_hash = data.content_hash;
                remote.version = data.version;
                remote.deleted_at = null;
            }

            if (remoteEdited) {
                this.output.push(
                    `push: "${entry.localFilename}" (v${data.version}, ` +
                        "remote changes overwritten)",
                );
            } else {
                this.output.push(`push: "${entry.localFilename}" (v${data.version})`);
            }
        }
    }

    private async applyRemoteDeletions(uuids: string[]): Promise<void> {
        for (const uuid of uuids) {
            const entry = this.syncState.get(uuid);
            if (!entry) {
                continue;
            }

            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const localExists = await this.fs.isFile(localPath);

            if (await this.hasLocalChanges(uuid, localPath)) {
                if (entry.localFilename !== entry.serverFilename) {
                    this.output.push(
                        `pull: SKIPPING delete "${entry.serverFilename}" ` +
                            `(at "${entry.localFilename}"), ` +
                            "local changes would be lost",
                    );
                } else {
                    this.output.push(
                        `pull: SKIPPING delete "${entry.localFilename}", ` +
                            "local changes would be lost",
                    );
                }
            } else {
                if (localExists) {
                    await this.fs.delete(localPath);
                }
                if (entry.localFilename !== entry.serverFilename) {
                    this.output.push(
                        `pull: deleted "${entry.serverFilename}" ` +
                            `(was "${entry.localFilename}")`,
                    );
                } else {
                    this.output.push(`pull: deleted "${entry.localFilename}"`);
                }
                this.deleteSyncState(uuid);
            }
        }
    }

    private async applyRemoteUpdates(
        uuids: string[],
        vacating: Set<string>,
    ): Promise<void> {
        // In order to handle rename cycles (file a renamed to b, b renamed c, c
        // renamed a), applyRemoteUpdates is a recursive function that can call itself
        // with the current argument removed. So two things are unintuitive about this
        // function, that it will process its arguments in reverse order (see below),
        // and that it will return success early when there are no arguments to signal
        // a cycle can be broken:
        if (uuids.length === 0) {
            return;
        }

        const uuid = uuids[0];
        const remaining = uuids.slice(1);

        const remote = this.remotePages.get(uuid);
        if (!remote) {
            await this.applyRemoteUpdates(remaining, vacating);
            return;
        }

        const destFile = remote.filename;
        const hash = remote.content_hash;
        const version = remote.version;

        const entry = this.syncState.get(uuid);
        const srcFile = entry?.localFilename ?? "";
        const srcPath = path.join(this.config.outputDir, srcFile);

        // To break rename cycles, we need to know which paths will be vacated by
        // other renames (when we get to processing c->a last, we need to know that a
        // is trying to move away to know we can rename it successfully). If any
        // intervening part of the cycle produces a complication, a would not be in
        // vacating, and the rename is therefore blocked.
        const newVacating = new Set(vacating);
        if (
            this.isBeingRenamed(uuid, destFile) &&
            (await this.fs.isFile(srcPath)) &&
            !(await this.hasLocalChanges(uuid, srcPath))
        ) {
            newVacating.add(srcFile);
        }

        await this.applyRemoteUpdates(remaining, newVacating);
        const destPath = path.join(this.config.outputDir, destFile);
        const cachedUuid = this.getUuidByLocalFilename(destFile);
        if (cachedUuid && this.isCachedUuidStale(cachedUuid, uuid)) {
            if (
                (await this.fs.isFile(destPath)) &&
                (await this.hasLocalChanges(cachedUuid, destPath))
            ) {
                this.output.push(
                    `pull: SKIPPING delete "${destFile}", ` +
                        "local changes would be lost",
                );
                return;
            }
            if (await this.fs.isFile(destPath)) {
                await this.fs.delete(destPath);
            }
            this.deleteSyncState(cachedUuid);
        }

        if (await this.fileBlockedByDirectory(destPath, uuid, destFile)) {
            this.output.push(
                `pull: ERROR cannot pull "${destFile}", blocked by local directory`,
            );
        } else if (await this.parentBlockedByFile(destFile)) {
            this.output.push(
                `pull: ERROR cannot pull "${destFile}", blocked by local file`,
            );
        } else if (await this.fileExistsWithDifferentCase(destFile)) {
            this.output.push(
                `pull: ERROR cannot pull "${destFile}", ` +
                    "blocked by local file with different case",
            );
        } else if ((await this.fileMatchesHash(destPath, hash)) && !entry) {
            this.output.push(`pull: tracking "${destFile}" (v${version})`);
            this.updateSyncState(uuid, destFile, destFile, hash, hash);
        } else if (entry && this.isBeingRenamed(uuid, destFile)) {
            // To break a rename cycle, the last in the chain is put in a
            // temporary location.
            let actualSrcPath = srcPath;
            const vacatedPath = srcPath + ".vacated";
            if (await this.fs.isFile(vacatedPath)) {
                actualSrcPath = vacatedPath;
            }

            if (this.isLocallyRenamed(uuid)) {
                const cachedRemoteFn = entry.serverFilename;
                this.output.push(
                    `pull: SKIPPING rename "${cachedRemoteFn}" to "${destFile}", ` +
                        `already "${srcFile}" locally`,
                );

                if (
                    this.hasRemoteChanges(uuid) &&
                    (await this.hasLocalChanges(uuid, actualSrcPath))
                ) {
                    this.output.push(
                        `pull: SKIPPING pull "${destFile}" to "${srcFile}", ` +
                            "local changes would be lost",
                    );
                } else if (this.hasRemoteChanges(uuid)) {
                    const fetched = await this.fetchRemoteToLocalPath(
                        uuid,
                        srcFile,
                        hash,
                    );
                    if (fetched) {
                        this.output.push(
                            `pull: "${destFile}" to "${srcFile}" (v${version})`,
                        );
                    }
                }
            } else if (await this.hasLocalChanges(uuid, actualSrcPath)) {
                this.output.push(
                    `pull: SKIPPING rename "${srcFile}" to "${destFile}", ` +
                        "local changes would be lost",
                );
            } else if (await this.destinationOccupied(destPath)) {
                if (vacating.has(destFile)) {
                    // Here is where the rename cycle is broken. The desired destination
                    // is going to be vacated, so this can be renamed, but needs to be
                    // moved aside temporarily.
                    await this.fs.rename(destPath, destPath + ".vacated");
                    await this.fs.rename(actualSrcPath, destPath);
                    this.output.push(`pull: renamed "${srcFile}" to "${destFile}"`);

                    if (await this.fileMatchesHash(destPath, hash)) {
                        this.updateSyncState(uuid, destFile, destFile, hash, hash);
                    } else {
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            destFile,
                            hash,
                        );
                        if (fetched) {
                            this.output.push(`pull: "${destFile}" (v${version})`);
                        }
                    }
                } else {
                    this.output.push(
                        `pull: ERROR cannot rename "${srcFile}" to "${destFile}", ` +
                            "blocked by local file",
                    );
                }
            } else if (await this.fs.isDirectory(destPath)) {
                this.output.push(
                    `pull: ERROR cannot rename "${srcFile}" to "${destFile}", ` +
                        "blocked by local directory",
                );
            } else if (await this.localFileWasRemoved(actualSrcPath)) {
                if (this.hasRemoteChanges(uuid)) {
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.output.push(`pull: "${destFile}" (v${version})`);
                    }
                } else {
                    this.output.push(
                        `pull: SKIPPING rename "${srcFile}" to "${destFile}", ` +
                            `"${srcFile}" deleted locally`,
                    );
                }
            } else {
                await this.fs.rename(actualSrcPath, destPath);
                this.output.push(`pull: renamed "${srcFile}" to "${destFile}"`);

                if (await this.fileMatchesHash(destPath, hash)) {
                    this.updateSyncState(uuid, destFile, destFile, hash, hash);
                } else {
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.output.push(`pull: "${destFile}" (v${version})`);
                    }
                }
            }
        } else if (await this.hasLocalChanges(uuid, destPath)) {
            if (!entry) {
                this.output.push(
                    `pull: ERROR cannot pull "${destFile}", blocked by local file`,
                );
            } else if (this.hasRemoteChanges(uuid)) {
                this.output.push(
                    `pull: SKIPPING pull "${destFile}", ` +
                        "local changes would be lost",
                );
            }
        } else if (await this.deletedLocallyNoNewContent(uuid, destFile, destPath)) {
            this.output.push(
                `pull: SKIPPING pull "${destFile}", already deleted locally`,
            );
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            !this.hasRemoteChanges(uuid)
        ) {
            // local rename, no remote changes - nothing to do
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            (await this.hasLocalChanges(uuid, srcPath))
        ) {
            this.output.push(
                `pull: SKIPPING pull "${destFile}" to "${srcFile}", ` +
                    "local changes would be lost",
            );
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            this.hasRemoteChanges(uuid)
        ) {
            const fetched = await this.fetchRemoteToLocalPath(uuid, srcFile, hash);
            if (fetched) {
                this.output.push(`pull: "${destFile}" to "${srcFile}" (v${version})`);
            }
        } else {
            if (await this.fileMatchesHash(destPath, hash)) {
                this.updateSyncState(uuid, destFile, destFile, hash, hash);
            } else {
                const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                if (fetched) {
                    this.output.push(`pull: "${destFile}" (v${version})`);
                }
            }
        }
    }

    private isBeingRenamed(uuid: string, destFile: string): boolean {
        const entry = this.syncState.get(uuid);

        if (!entry) {
            return false;
        }
        return entry.serverFilename !== destFile;
    }

    private isLocallyRenamed(uuid: string): boolean {
        const entry = this.syncState.get(uuid);

        if (!entry) {
            return false;
        }
        return entry.localFilename !== entry.serverFilename;
    }

    private hasRemoteChanges(uuid: string): boolean {
        const entry = this.syncState.get(uuid);
        const remote = this.remotePages.get(uuid);

        if (!entry || !remote) {
            return false;
        }
        return remote.content_hash !== entry.serverHash;
    }

    private async hasLocalChanges(uuid: string, filePath: string): Promise<boolean> {
        if (!(await this.fs.isFile(filePath))) {
            return false;
        }

        const entry = this.syncState.get(uuid);
        if (!entry) {
            return true;
        }
        const currentHash = await this.fs.hash(filePath);
        return currentHash !== entry.serverHash;
    }

    private isCachedUuidStale(cachedUuid: string | null, uuid: string): boolean {
        if (!cachedUuid) {
            return false;
        }
        if (cachedUuid === uuid) {
            return false;
        }

        for (const [remoteUuid, remote] of this.remotePages) {
            if (remoteUuid === cachedUuid && remote.deleted_at === null) {
                return false;
            }
        }
        return true;
    }

    private async fileBlockedByDirectory(
        destPath: string,
        uuid: string,
        destFile: string,
    ): Promise<boolean> {
        if (!(await this.fs.isDirectory(destPath))) {
            return false;
        }
        return !this.isBeingRenamed(uuid, destFile);
    }

    private async deletedLocallyNoNewContent(
        uuid: string,
        destFile: string,
        destPath: string,
    ): Promise<boolean> {
        if (await this.fs.isFile(destPath)) {
            return false;
        }

        const entry = this.syncState.get(uuid);
        if (!entry) {
            return false;
        }

        return (
            !this.isBeingRenamed(uuid, destFile) &&
            !this.isLocallyRenamed(uuid) &&
            !this.hasRemoteChanges(uuid)
        );
    }

    private async fetchRemoteToLocalPath(
        uuid: string,
        localFile: string,
        hash: string,
    ): Promise<boolean> {
        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (response.status === 401) {
            this.output.push("sync: ERROR API token invalid");
            throw new Error("API token invalid");
        }
        if (response.status === 404) {
            this.output.push(
                `pull: SKIPPING "${localFile}", deleted remotely during sync`,
            );
            return false;
        }
        if (!response.ok) {
            throw new Error(`Failed to fetch ${localFile}: HTTP ${response.status}`);
        }

        const content = Buffer.from(await response.arrayBuffer());
        const destPath = path.join(this.config.outputDir, localFile);
        await this.fs.write(destPath, content);

        const entry = this.syncState.get(uuid);
        if (entry) {
            entry.serverHash = hash;
            entry.localHash = hash;
        }
        return true;
    }

    private async fetchRemoteFile(
        uuid: string,
        destFile: string,
        hash: string,
    ): Promise<boolean> {
        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (response.status === 401) {
            this.output.push("sync: ERROR API token invalid");
            throw new Error("API token invalid");
        }
        if (response.status === 404) {
            this.output.push(
                `pull: SKIPPING "${destFile}", deleted remotely during sync`,
            );
            return false;
        }
        if (!response.ok) {
            throw new Error(`Failed to fetch ${destFile}: HTTP ${response.status}`);
        }

        const content = Buffer.from(await response.arrayBuffer());
        const destPath = path.join(this.config.outputDir, destFile);
        await this.fs.write(destPath, content);

        this.updateSyncState(uuid, destFile, destFile, hash, hash);
        return true;
    }

    private async checkForStaleFiles(): Promise<void> {
        for (const [uuid, entry] of this.syncState) {
            if (this.remotePages.has(uuid)) {
                continue;
            }

            // Stale file - UUID not found on server
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const localExists = await this.fs.isFile(localPath);

            if (!localExists) {
                // Already deleted locally - clean up state
                this.deleteSyncState(uuid);
                continue;
            }

            // Check if filename is now tracked under a different UUID on remote
            // (already handled in apply_remote_updates)
            if (this.getRemoteUuidByFilename(entry.localFilename)) {
                // Don't delete state here - keep it so the file remains tracked
                // under the stale UUID. apply_remote_updates already outputted
                // any necessary messages.
                continue;
            }

            const currentHash = await this.fs.hash(localPath);
            // Compare to serverHash - has file changed from what server knows?
            const hasChanges = currentHash !== entry.serverHash;

            if (hasChanges) {
                this.output.push(
                    `pull: SKIPPING delete "${entry.localFilename}", ` +
                        "local changes would be lost",
                );
                continue;
            }

            // Delete stale file
            await this.fs.delete(localPath);
            this.output.push(`pull: deleted "${entry.localFilename}"`);
            this.deleteSyncState(uuid);
        }
    }

    private getRemoteUuidByFilename(filename: string): string | null {
        for (const [uuid, remote] of this.remotePages) {
            if (remote.deleted_at !== null) {
                continue;
            }
            if (remote.filename === filename) {
                return uuid;
            }
        }
        return null;
    }

    private fileIsTrackedByLocalFilename(file: string): boolean {
        for (const [_uuid, entry] of this.syncState) {
            if (entry.localFilename === file) {
                return true;
            }
        }
        return false;
    }

    private getUuidByLocalFilename(file: string): string | null {
        for (const [uuid, entry] of this.syncState) {
            if (entry.localFilename === file) {
                return uuid;
            }
        }
        return null;
    }

    private async remoteHasIdenticalFile(file: string): Promise<boolean> {
        const filePath = path.join(this.config.outputDir, file);
        const localHash = await this.fs.hash(filePath);

        for (const remote of this.remotePages.values()) {
            if (remote.filename === file && !remote.deleted_at) {
                return remote.content_hash === localHash;
            }
        }
        return false;
    }

    private async tryCreateRemoteFile(file: string): Promise<string | null> {
        if (this.permissionDenied) {
            return null;
        }
        const filePath = path.join(this.config.outputDir, file);
        const content = await this.fs.read(filePath);

        const formData = new FormData();
        formData.append("file", new Blob([content]), file);
        formData.append("filename", file);

        const response = await fetch(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/`,
            {
                method: "POST",
                headers: { Authorization: `Token ${this.config.token}` },
                body: formData,
                signal: AbortSignal.timeout(this.timeoutMs),
            },
        );

        if (this.handlePushAuthError(response)) {
            return null;
        }
        if (response.status === 400 || response.status === 409) {
            const data = await response.json();
            return data.error;
        }

        if (response.status === 201) {
            const data = await response.json();
            const hash = await this.fs.hash(filePath);
            this.updateSyncState(data.uuid, file, file, data.content_hash, hash);
            // Add to remotePages so pull phase sees it
            this.remotePages.set(data.uuid, {
                uuid: data.uuid,
                filename: file,
                content_hash: data.content_hash,
                version: data.version,
                deleted_at: null,
            });
            this.output.push(`push: "${file}" (v${data.version})`);
            return null;
        }

        return `HTTP ${response.status}`;
    }

    private async parentBlockedByFile(file: string): Promise<boolean> {
        const parts = file.split("/");
        if (parts.length <= 1) {
            return false;
        }

        let checkPath = this.config.outputDir;
        for (let i = 0; i < parts.length - 1; i++) {
            checkPath = path.join(checkPath, parts[i]);
            if (await this.fs.isFile(checkPath)) {
                return true;
            }
        }
        return false;
    }

    private async fileExistsWithDifferentCase(file: string): Promise<boolean> {
        const dir = path.dirname(file);
        const name = path.basename(file);
        const checkDir =
            dir === "." ? this.config.outputDir : path.join(this.config.outputDir, dir);

        const conflict = await this.fs.findCaseInsensitive(checkDir, name);
        return conflict !== null;
    }

    private async fileMatchesHash(filePath: string, hash: string): Promise<boolean> {
        if (!(await this.fs.isFile(filePath))) {
            return false;
        }
        const localHash = await this.fs.hash(filePath);
        return localHash === hash;
    }

    private async listLocalFiles(): Promise<string[]> {
        try {
            return await this.fs.list(this.config.outputDir);
        } catch {
            return [];
        }
    }

    private async destinationOccupied(destPath: string): Promise<boolean> {
        return await this.fs.isFile(destPath);
    }

    private async localFileWasRemoved(filePath: string): Promise<boolean> {
        return !(await this.fs.isFile(filePath));
    }

    private updateSyncState(
        uuid: string,
        serverFn?: string,
        localFn?: string,
        serverHash?: string,
        localHash?: string,
    ): void {
        const entry = this.syncState.get(uuid);
        if (entry) {
            if (serverFn !== undefined && serverFn !== "") {
                entry.serverFilename = serverFn;
            }
            if (localFn !== undefined && localFn !== "") {
                entry.localFilename = localFn;
            }
            if (serverHash !== undefined && serverHash !== "") {
                entry.serverHash = serverHash;
            }
            if (localHash !== undefined && localHash !== "") {
                entry.localHash = localHash;
            }
        } else {
            this.syncState.set(uuid, {
                uuid,
                serverFilename: serverFn || "",
                localFilename: localFn || "",
                serverHash: serverHash || "",
                localHash: localHash || "",
            });
        }
    }

    private deleteSyncState(uuid: string): void {
        this.syncState.delete(uuid);
    }
}

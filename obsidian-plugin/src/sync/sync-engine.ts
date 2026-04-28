import * as crypto from "node:crypto";
import * as os from "node:os";
import * as path from "node:path";
import DiffMatchPatch from "diff-match-patch";
import type { FileSystem, SyncConfig, SyncResult, SyncStateEntry } from "./types.js";

interface RemotePage {
    uuid: string;
    filename: string;
    content_hash: string;
    version: number;
    deleted_at: string | null;
}

const DEFAULT_TIMEOUT_MS = 30000;

async function fetchWithContext(
    url: string,
    options: RequestInit,
    context: string,
): Promise<Response> {
    try {
        return await fetch(url, options);
    } catch {
        throw new Error(`Network request failed while ${context}`);
    }
}

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
    private incrementalResults?: number;
    private hostname: string;

    constructor(private config: SyncConfig) {
        this.fs = config.fileSystem;
        this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
        this.lastUpdate = config.lastUpdate;
        this.lastFullSync = config.lastFullSync;
        this.hostname = config.hostname ?? os.hostname().split(".")[0];
    }

    private log(line: string): void {
        this.output.push(line);
        this.config.onOutput?.(line);
    }

    private checkAborted(): void {
        if (this.config.abortSignal?.aborted) {
            throw new Error("Sync aborted");
        }
    }

    async run(): Promise<SyncResult> {
        this.output = [];
        this.remotePages = new Map();
        this.syncState = this.config.initialState ?? new Map();
        this.permissionDenied = false;
        this.incrementalResults = undefined;

        if (!this.config.token) {
            this.log("ERROR API token missing");
            throw new Error("API token missing");
        }

        // Determine if we should do incremental sync
        this.isIncrementalSync = this.shouldUseIncrementalSync();

        const editable = await this.fetchRemoteState();
        this.checkAborted();

        if (this.config.afterFetchHook) {
            await this.config.afterFetchHook();
        }

        if (!(await this.fs.isDirectory(this.config.outputDir))) {
            await this.fs.mkdir(this.config.outputDir);
        }

        await this.detectUntrackedRenames();
        this.checkAborted();

        let pullOnly = this.config.pullOnly;
        if (!pullOnly && !editable) {
            this.log("NOTE read-only access, switching to pull-only mode");
            pullOnly = true;
        }

        if (!pullOnly) {
            await this.applyLocalUpdates();
            this.checkAborted();
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
        this.checkAborted();

        const deferredUuids: string[] = [];
        await this.applyRemoteUpdates(activeUuids, new Set<string>(), deferredUuids);
        this.checkAborted();

        // Process any UUIDs that were deferred due to rename cycles
        if (deferredUuids.length > 0) {
            await this.applyRemoteUpdates(deferredUuids, new Set<string>(), []);
            this.checkAborted();
        }

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
            incrementalResults: this.incrementalResults,
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

            this.log(
                `info: detected rename "${entry.localFilename}" to "${newFilename}"`,
            );
            this.updateSyncState(uuid, "", newFilename);
        }
    }

    private async findUntrackedFileByHash(targetHash: string): Promise<string | null> {
        const localFiles = await this.listLocalFiles();
        for (const file of localFiles) {
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
            // Update our local cache of the remote state with the incremental
            // changes. The limitation is that a stale file (where the server
            // has purged a soft-deleted file) cannot be detected by this, so
            // we should still do a full fetch of the notebook state regularly
            // to catch purged files.
            for (const [uuid, entry] of this.syncState) {
                this.remotePages.set(uuid, {
                    uuid,
                    filename: entry.serverFilename,
                    content_hash: entry.serverHash,
                    version: 0,
                    deleted_at: null,
                });
            }
            baseUrl += `?since=${encodeURIComponent(this.lastUpdate)}`;
        }

        let nextPage: string | null = baseUrl;
        let editable = true;

        while (nextPage) {
            this.checkAborted();

            const response = await fetchWithContext(
                nextPage,
                {
                    headers: { Authorization: `Token ${this.config.token}` },
                    signal: AbortSignal.timeout(this.timeoutMs),
                },
                "fetching notebook state",
            );

            if (response.status === 401 || response.status === 403) {
                this.log("ERROR API token invalid");
                throw new Error("API token invalid");
            }
            if (response.status === 404) {
                this.log("ERROR notebook not found");
                throw new Error("Notebook not found");
            }
            if (!response.ok) {
                this.log(`sync: ERROR unexpected response (HTTP ${response.status})`);
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

            // Track total results for incremental sync (first page only)
            if (this.isIncrementalSync && this.incrementalResults === undefined) {
                this.incrementalResults = data.total_results ?? 0;
            }

            for (const page of data.results as RemotePage[]) {
                if (this.isIncrementalSync) {
                    for (const [existingUuid, existing] of this.remotePages) {
                        if (
                            existingUuid !== page.uuid &&
                            existing.filename === page.filename
                        ) {
                            this.remotePages.delete(existingUuid);
                            break;
                        }
                    }
                }
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

            if (entry.localDeleted) {
                const remoteEdited = remote && remote.content_hash !== entry.serverHash;
                if (localExists && remoteEdited) {
                    await this.renameBlockingPath(localPath);
                }
                await this.pushLocalDeletion(uuid, entry, remote);
                continue;
            }

            if (!localExists) {
                await this.pushLocalDeletion(uuid, entry, remote);
                continue;
            }

            const currentHash = await this.fs.hash(localPath);
            const localEdited = currentHash !== entry.serverHash;
            const localRenamed = entry.localFilename !== entry.serverFilename;
            const isStale = !remote;

            if (isStale && localEdited && !localRenamed) {
                const conflictName = await this.renameBlockingPath(localPath);
                const errorMsg = await this.tryCreateRemoteFile(conflictName);
                if (errorMsg) {
                    this.log(`push: ERROR cannot push "${conflictName}": ${errorMsg}`);
                    staleUuids.push(uuid);
                } else {
                    this.deleteSyncState(uuid);
                }
                continue;
            }

            const remoteRenamed = remote && remote.filename !== entry.serverFilename;

            if (localRenamed) {
                if (isStale) {
                    if (localEdited) {
                        this.deleteSyncState(uuid);
                    } else {
                        await this.fs.delete(localPath);
                        this.log(`pull: deleted "${entry.localFilename}"`);
                        this.deleteSyncState(uuid);
                    }
                    continue;
                }
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
                await this.pushLocalEdit(uuid, entry, remote);
            }
        }

        const localFiles = await this.listLocalFiles();
        for (const file of localFiles) {
            if (this.fileIsTrackedByLocalFilename(file)) {
                continue;
            }
            if (await this.remoteHasIdenticalFile(file)) {
                continue;
            }

            const errorMsg = await this.tryCreateRemoteFile(file);
            if (errorMsg) {
                if (this.isPathConflictError(errorMsg)) {
                    const conflictDir = this.findConflictingParentDir(file, errorMsg);
                    if (conflictDir) {
                        const dirPath = path.join(this.config.outputDir, conflictDir);
                        const newDir = await this.renameBlockingPath(dirPath);
                        const newFile = file.replace(conflictDir, newDir);
                        const retryError = await this.tryCreateRemoteFile(newFile);
                        if (retryError) {
                            this.log(
                                `push: ERROR cannot push "${newFile}": ` +
                                    `${retryError}`,
                            );
                        }
                    } else {
                        const filePath = path.join(this.config.outputDir, file);
                        const conflictName = await this.renameBlockingPath(filePath);
                        const err = await this.tryCreateRemoteFile(conflictName);
                        if (err) {
                            this.log(
                                `push: ERROR cannot push "${conflictName}": ` +
                                    `${err}`,
                            );
                        }
                    }
                } else {
                    this.log(`push: ERROR cannot push "${file}": ${errorMsg}`);
                }
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

        // server has updates we haven't seen - pull will revivify
        const remoteEdited = remote.content_hash !== entry.serverHash;
        if (remoteEdited) {
            return;
        }

        // local file was deleted but renamed remotely;
        // rename it back before deleting as local change takes precedence
        if (remote.filename !== entry.localFilename) {
            const renameResponse = await fetchWithContext(
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
                `renaming "${remote.filename}" before delete`,
            );

            if (this.handlePushAuthError(renameResponse)) {
                return;
            }

            this.checkAborted();
            if (renameResponse.ok) {
                this.log(
                    `push: renamed "${remote.filename}" to "${entry.localFilename}"`,
                );
                entry.serverFilename = entry.localFilename;
                remote.filename = entry.localFilename;
            } else {
                return;
            }
        }

        const response = await fetchWithContext(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                method: "DELETE",
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
            `deleting "${entry.localFilename}"`,
        );

        if (this.handlePushAuthError(response)) {
            return;
        }

        this.checkAborted();
        if (response.ok) {
            this.log(`push: deleted "${entry.localFilename}"`);
            this.deleteSyncState(uuid);
            this.remotePages.delete(uuid);
        } else if (response.status === 404) {
            // UUID is stale - doesn't exist on server
            this.deleteSyncState(uuid);
            this.remotePages.delete(uuid);
        }
    }

    private handlePushAuthError(response: Response): boolean {
        if (response.status === 401) {
            this.log("ERROR API token invalid");
            throw new Error("API token invalid");
        }
        if (response.status === 403) {
            if (!this.permissionDenied) {
                this.log("NOTE permission denied, switching to pull-only mode");
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
        const wasDeleted = remote.deleted_at !== null;
        if (wasDeleted) {
            payload.restore = true;
        }

        const response = await fetchWithContext(
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
            `renaming "${remote.filename}" to "${entry.localFilename}"`,
        );

        if (this.handlePushAuthError(response)) {
            return false;
        }

        this.checkAborted();
        if (response.ok) {
            const data = await response.json();
            const suffix = wasDeleted ? " (revivified)" : "";
            const msg =
                `push: renamed "${remote.filename}" to ` +
                `"${entry.localFilename}"${suffix}`;
            this.log(msg);
            entry.serverFilename = entry.localFilename;
            remote.filename = entry.localFilename;
            remote.content_hash = data.content_hash;
            remote.version = data.version;
            remote.deleted_at = null;
            return true;
        }

        if (response.status === 400 || response.status === 409) {
            const data = await response.json();
            this.log(
                `push: ERROR cannot rename "${remote.filename}" ` +
                    `to "${entry.localFilename}": ${data.error}`,
            );
        }
        return false;
    }

    private async pushLocalEdit(
        uuid: string,
        entry: SyncStateEntry,
        remote: RemotePage | undefined,
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

        const response = await fetchWithContext(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                method: "PUT",
                headers: {
                    Authorization: `Token ${this.config.token}`,
                    "Content-Type": contentType,
                    "Previous-Hash": entry.serverHash,
                },
                body: content,
                signal: AbortSignal.timeout(this.timeoutMs),
            },
            `pushing "${entry.localFilename}"`,
        );

        if (this.handlePushAuthError(response)) {
            return;
        }

        this.checkAborted();
        if (response.ok) {
            const data = await response.json();
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const actualHash = await this.fs.hash(localPath);
            const wasDeleted = remote && remote.deleted_at !== null;

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

            if (data.update === "merged" || data.update === "replaced") {
                this.log(
                    `push: "${entry.localFilename}" (v${data.version}, ${data.update})`,
                );
            } else if (wasDeleted) {
                this.log(
                    `push: "${entry.localFilename}" (v${data.version}, revivified)`,
                );
            } else if (data.update !== "unchanged") {
                this.log(`push: "${entry.localFilename}" (v${data.version})`);
            }
        } else if (response.status === 404) {
            // UUID is stale - the file no longer exists on the server
            const localPath = path.join(this.config.outputDir, entry.localFilename);
            const conflictName = await this.renameBlockingPath(localPath);
            this.syncState.delete(uuid);
            this.remotePages.delete(uuid);
            await this.tryCreateRemoteFile(conflictName);
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
                await this.renameBlockingPath(localPath);
                this.log(`pull: deleted "${entry.serverFilename}"`);
                this.deleteSyncState(uuid);
            } else {
                if (localExists) {
                    await this.fs.delete(localPath);
                }
                this.log(`pull: deleted "${entry.serverFilename}"`);
                this.deleteSyncState(uuid);
            }
        }
    }

    private async applyRemoteUpdates(
        uuids: string[],
        vacating: Set<string>,
        deferredUuids: string[],
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
            await this.applyRemoteUpdates(remaining, vacating, deferredUuids);
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
        if (this.isBeingRenamed(uuid, destFile) && (await this.fs.isFile(srcPath))) {
            if (
                !(await this.hasLocalChanges(uuid, srcPath)) ||
                this.hasRemoteChanges(uuid)
            ) {
                newVacating.add(srcFile);
            }
        }

        await this.applyRemoteUpdates(remaining, newVacating, deferredUuids);
        const destPath = path.join(this.config.outputDir, destFile);
        const blockingParentPath = await this.findBlockingParentPath(destFile);
        const caseCollisionPath = await this.findCaseCollisionPath(destFile);

        const cachedUuid = this.getUuidByLocalFilename(destFile);
        if (cachedUuid && this.isCachedUuidStale(cachedUuid, uuid)) {
            if (
                (await this.fs.isFile(destPath)) &&
                (await this.hasLocalChanges(cachedUuid, destPath))
            ) {
                await this.renameBlockingPath(destPath);
            } else if (await this.fs.isFile(destPath)) {
                await this.fs.delete(destPath);
            }
            this.deleteSyncState(cachedUuid);
        }

        if (await this.fileBlockedByDirectory(destPath, uuid, destFile)) {
            await this.renameBlockingPath(destPath);
            const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
            if (fetched) {
                this.log(`pull: "${destFile}" (v${version})`);
            }
        } else if (blockingParentPath) {
            await this.renameBlockingPath(blockingParentPath);
            const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
            if (fetched) {
                this.log(`pull: "${destFile}" (v${version})`);
            }
        } else if (caseCollisionPath) {
            await this.renameBlockingPath(caseCollisionPath);
            const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
            if (fetched) {
                this.log(`pull: "${destFile}" (v${version})`);
            }
        } else if ((await this.fileMatchesHash(destPath, hash)) && !entry) {
            this.log(`pull: tracking "${destFile}" (v${version})`);
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
                if (
                    this.hasRemoteChanges(uuid) &&
                    (await this.hasLocalChanges(uuid, actualSrcPath))
                ) {
                    if (
                        await this.tryThreeWayMerge(
                            uuid,
                            actualSrcPath,
                            entry.serverHash,
                            hash,
                        )
                    ) {
                        const mergedHash = await this.fs.hash(actualSrcPath);
                        this.updateSyncState(uuid, destFile, srcFile, hash, mergedHash);
                        this.log(
                            `pull: "${destFile}" to "${srcFile}" (v${version}, merged)`,
                        );
                    } else {
                        const conflictPath = actualSrcPath.replace(/\.vacated$/, "");
                        if (actualSrcPath !== conflictPath) {
                            await this.fs.rename(actualSrcPath, conflictPath);
                        }
                        await this.renameBlockingPath(conflictPath);
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            srcFile,
                            hash,
                            false,
                        );
                        if (fetched) {
                            this.log(
                                `pull: "${destFile}" to "${srcFile}" (v${version})`,
                            );
                        }
                    }
                } else if (this.hasRemoteChanges(uuid)) {
                    const fetched = await this.fetchRemoteFile(
                        uuid,
                        srcFile,
                        hash,
                        false,
                    );
                    if (fetched) {
                        this.updateSyncState(uuid, destFile, srcFile, hash, hash);
                        this.log(`pull: "${destFile}" to "${srcFile}" (v${version})`);
                    }
                } else {
                    this.updateSyncState(uuid, destFile, srcFile, hash, hash);
                }
            } else if (await this.hasLocalChanges(uuid, actualSrcPath)) {
                if (this.hasRemoteChanges(uuid)) {
                    if (
                        await this.tryThreeWayMerge(
                            uuid,
                            actualSrcPath,
                            entry.serverHash,
                            hash,
                        )
                    ) {
                        await this.fs.rename(actualSrcPath, destPath);
                        this.log(`pull: renamed "${srcFile}" to "${destFile}"`);
                        const mergedHash = await this.fs.hash(destPath);
                        this.updateSyncState(
                            uuid,
                            destFile,
                            destFile,
                            hash,
                            mergedHash,
                        );
                        this.log(`pull: "${destFile}" (v${version}, merged)`);
                    } else {
                        const conflictName = await this.generateConflictName(srcFile);
                        const conflictDir = this.config.outputDir;
                        const conflictPath = path.join(conflictDir, conflictName);
                        await this.fs.rename(actualSrcPath, conflictPath);
                        this.log(`pull: renamed "${srcFile}" to "${conflictName}"`);
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            destFile,
                            hash,
                        );
                        if (fetched) {
                            this.log(`pull: "${destFile}" (v${version})`);
                        }
                    }
                } else {
                    await this.fs.rename(actualSrcPath, destPath);
                    this.log(`pull: renamed "${srcFile}" to "${destFile}"`);
                    const localHash = await this.fs.hash(destPath);
                    this.updateSyncState(uuid, destFile, destFile, hash, localHash);
                }
            } else if (await this.destinationOccupied(destPath)) {
                if (vacating.has(destFile)) {
                    // Here is where the rename cycle is broken. The desired destination
                    // is going to be vacated, so this can be renamed, but needs to be
                    // moved aside temporarily.
                    await this.fs.rename(destPath, destPath + ".vacated");
                    await this.fs.rename(actualSrcPath, destPath);
                    this.log(`pull: renamed "${srcFile}" to "${destFile}"`);

                    if (await this.fileMatchesHash(destPath, hash)) {
                        this.updateSyncState(uuid, destFile, destFile, hash, hash);
                    } else {
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            destFile,
                            hash,
                        );
                        if (fetched) {
                            this.log(`pull: "${destFile}" (v${version})`);
                        }
                    }
                } else if (
                    (await this.localFileWasRemoved(actualSrcPath)) &&
                    this.hasRemoteChanges(uuid)
                ) {
                    await this.renameBlockingPath(destPath);
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.log(`pull: "${destFile}" (v${version}, revivified)`);
                    }
                } else {
                    await this.renameBlockingPath(destPath);
                    await this.fs.rename(actualSrcPath, destPath);
                    this.log(`pull: renamed "${srcFile}" to "${destFile}"`);

                    if (await this.fileMatchesHash(destPath, hash)) {
                        this.updateSyncState(uuid, destFile, destFile, hash, hash);
                    } else {
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            destFile,
                            hash,
                        );
                        if (fetched) {
                            this.log(`pull: "${destFile}" (v${version})`);
                        }
                    }
                }
            } else if (await this.fs.isDirectory(destPath)) {
                await this.renameBlockingPath(destPath);
                await this.fs.rename(actualSrcPath, destPath);
                this.log(`pull: renamed "${srcFile}" to "${destFile}"`);

                if (await this.fileMatchesHash(destPath, hash)) {
                    this.updateSyncState(uuid, destFile, destFile, hash, hash);
                } else {
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.log(`pull: "${destFile}" (v${version})`);
                    }
                }
            } else if (await this.localFileWasRemoved(actualSrcPath)) {
                if (this.hasRemoteChanges(uuid)) {
                    if (await this.fs.exists(destPath)) {
                        await this.renameBlockingPath(destPath);
                    }
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.log(`pull: "${destFile}" (v${version}, revivified)`);
                    }
                } else {
                    this.updateSyncState(uuid, destFile, destFile, hash, hash);
                }
            } else {
                await this.fs.rename(actualSrcPath, destPath);
                this.log(`pull: renamed "${srcFile}" to "${destFile}"`);

                if (await this.fileMatchesHash(destPath, hash)) {
                    this.updateSyncState(uuid, destFile, destFile, hash, hash);
                } else {
                    const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                    if (fetched) {
                        this.log(`pull: "${destFile}" (v${version})`);
                    }
                }
            }
        } else if (await this.hasLocalChanges(uuid, destPath)) {
            if (!entry && vacating.has(destFile)) {
                // destFile will be vacated by rename cycle; defer this fetch
                deferredUuids.push(uuid);
            } else if (!entry) {
                await this.renameBlockingPath(destPath);
                const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                if (fetched) {
                    this.log(`pull: "${destFile}" (v${version})`);
                }
            } else if (this.hasRemoteChanges(uuid)) {
                if (this.config.pullOnly) {
                    const localHash = await this.fs.hash(destPath);
                    if (localHash === hash) {
                        // Local and remote are identical, just update state
                        this.updateSyncState(uuid, destFile, destFile, hash, hash);
                    } else if (
                        await this.tryThreeWayMerge(
                            uuid,
                            destPath,
                            entry.serverHash,
                            hash,
                        )
                    ) {
                        const mergedHash = await this.fs.hash(destPath);
                        this.updateSyncState(
                            uuid,
                            destFile,
                            destFile,
                            hash,
                            mergedHash,
                        );
                        this.log(`pull: "${destFile}" (v${version}, merged)`);
                    } else {
                        await this.renameBlockingPath(destPath);
                        const fetched = await this.fetchRemoteFile(
                            uuid,
                            destFile,
                            hash,
                        );
                        if (fetched) {
                            this.log(`pull: "${destFile}" (v${version})`);
                        }
                    }
                }
            }
        } else if (await this.deletedLocallyNoNewContent(uuid, destFile, destPath)) {
            // Keep as deleted - user intentionally removed it
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            !this.hasRemoteChanges(uuid)
        ) {
            entry.serverFilename = destFile;
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            (await this.hasLocalChanges(uuid, srcPath))
        ) {
            if (await this.tryThreeWayMerge(uuid, srcPath, entry.serverHash, hash)) {
                const mergedHash = await this.fs.hash(srcPath);
                this.updateSyncState(uuid, destFile, srcFile, hash, mergedHash);
                this.log(`pull: "${destFile}" to "${srcFile}" (v${version}, merged)`);
            } else {
                await this.renameBlockingPath(srcPath);
                const fetched = await this.fetchRemoteFile(uuid, srcFile, hash, false);
                if (fetched) {
                    this.updateSyncState(uuid, destFile, srcFile, hash, hash);
                    this.log(`pull: "${destFile}" to "${srcFile}" (v${version})`);
                }
            }
        } else if (
            entry &&
            this.isLocallyRenamed(uuid) &&
            this.hasRemoteChanges(uuid)
        ) {
            const fetched = await this.fetchRemoteFile(uuid, srcFile, hash, false);
            if (fetched) {
                this.updateSyncState(uuid, destFile, srcFile, hash, hash);
                this.log(`pull: "${destFile}" to "${srcFile}" (v${version})`);
            }
        } else {
            if (await this.fileMatchesHash(destPath, hash)) {
                this.updateSyncState(uuid, destFile, destFile, hash, hash);
            } else if (entry && (await this.localFileWasRemoved(destPath))) {
                const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                if (fetched) {
                    this.log(`pull: "${destFile}" (v${version}, revivified)`);
                }
            } else {
                const fetched = await this.fetchRemoteFile(uuid, destFile, hash);
                if (fetched) {
                    this.log(`pull: "${destFile}" (v${version})`);
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

    private async fetchContentByHash(
        uuid: string,
        hash: string,
    ): Promise<Buffer | null> {
        const url =
            `${this.config.baseUrl}/v1/notebooks/` +
            `${this.config.notebook}/${uuid}?hash=${hash}`;
        const response = await fetchWithContext(
            url,
            {
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
            `fetching content by hash ${hash.slice(0, 8)}`,
        );

        if (response.status === 404) {
            return null;
        }
        if (!response.ok) {
            return null;
        }

        return Buffer.from(await response.arrayBuffer());
    }

    private async tryThreeWayMerge(
        uuid: string,
        localPath: string,
        baseHash: string,
        remoteHash: string,
    ): Promise<boolean> {
        const baseContent = await this.fetchContentByHash(uuid, baseHash);
        if (!baseContent) {
            return false;
        }

        const remoteContent = await this.fetchContentByHash(uuid, remoteHash);
        if (!remoteContent) {
            return false;
        }

        const localContent = await this.fs.read(localPath);

        const baseText = baseContent.toString("utf-8");
        const localText = localContent.toString("utf-8");
        const remoteText = remoteContent.toString("utf-8");

        const dmp = new DiffMatchPatch();
        const patches = dmp.patch_make(baseText, localText);
        const [merged, results] = dmp.patch_apply(patches, remoteText);

        if (!results.every((r) => r)) {
            return false;
        }

        await this.fs.write(localPath, Buffer.from(merged, "utf-8"));
        return true;
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

    private async fetchRemoteFile(
        uuid: string,
        destFile: string,
        hash: string,
        updateFilenames = true,
    ): Promise<boolean> {
        const response = await fetchWithContext(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/${uuid}`,
            {
                headers: { Authorization: `Token ${this.config.token}` },
                signal: AbortSignal.timeout(this.timeoutMs),
            },
            `pulling "${destFile}"`,
        );

        if (response.status === 401) {
            this.log("ERROR API token invalid");
            throw new Error("API token invalid");
        }
        if (response.status === 404) {
            this.log(`pull: SKIPPING "${destFile}", deleted remotely during sync`);
            return false;
        }
        if (!response.ok) {
            throw new Error(`Failed to pull "${destFile}": HTTP ${response.status}`);
        }

        this.checkAborted();
        const content = Buffer.from(await response.arrayBuffer());
        const destPath = path.join(this.config.outputDir, destFile);
        await this.fs.write(destPath, content);

        if (updateFilenames) {
            this.updateSyncState(uuid, destFile, destFile, hash, hash);
        } else {
            const entry = this.syncState.get(uuid);
            if (entry) {
                entry.serverHash = hash;
                entry.localHash = hash;
            }
        }
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
                await this.renameBlockingPath(localPath);
                this.deleteSyncState(uuid);
                continue;
            }

            // Delete stale file
            await this.fs.delete(localPath);
            this.log(`pull: deleted "${entry.localFilename}"`);
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

        const response = await fetchWithContext(
            `${this.config.baseUrl}/v1/notebooks/${this.config.notebook}/`,
            {
                method: "POST",
                headers: { Authorization: `Token ${this.config.token}` },
                body: formData,
                signal: AbortSignal.timeout(this.timeoutMs),
            },
            `creating "${file}"`,
        );

        if (this.handlePushAuthError(response)) {
            return null;
        }

        this.checkAborted();
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
            this.log(`push: "${file}" (v${data.version})`);
            return null;
        }

        return `HTTP ${response.status}`;
    }

    private async findBlockingParentPath(file: string): Promise<string | null> {
        const parts = file.split("/");
        if (parts.length <= 1) {
            return null;
        }

        let checkPath = this.config.outputDir;
        for (let i = 0; i < parts.length - 1; i++) {
            checkPath = path.join(checkPath, parts[i]);
            if (await this.fs.isFile(checkPath)) {
                return checkPath;
            }
        }
        return null;
    }

    private async findCaseCollisionPath(file: string): Promise<string | null> {
        const dir = path.dirname(file);
        const name = path.basename(file);
        const checkDir =
            dir === "." ? this.config.outputDir : path.join(this.config.outputDir, dir);

        const conflict = await this.fs.findCaseInsensitive(checkDir, name);
        if (conflict) {
            return path.join(checkDir, conflict);
        }
        return null;
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

    private isPathConflictError(errorMsg: string): boolean {
        const lowerError = errorMsg.toLowerCase();
        return (
            lowerError.includes("already exists") ||
            lowerError.includes("case-insensitive")
        );
    }

    private findConflictingParentDir(file: string, errorMsg: string): string | null {
        const match = errorMsg.match(/[Pp]ath '([^']+)'/);
        if (!match) {
            return null;
        }
        const conflictPath = match[1].toLowerCase();
        const conflictParts = conflictPath.split("/");
        const fileParts = file.split("/");
        if (fileParts.length <= conflictParts.length) {
            return null;
        }

        const parentDir = fileParts.slice(0, conflictParts.length).join("/");

        const parentSlug = parentDir
            .toLowerCase()
            .replace(/ /g, "-")
            .replace(/'/g, "")
            .replace(/\.md$/, "");

        if (parentSlug === conflictPath) {
            return parentDir;
        }
        return null;
    }

    private async generateConflictName(file: string): Promise<string> {
        const dir = path.dirname(file);
        const base = path.basename(file);
        const extIndex = base.lastIndexOf(".");
        let name: string;
        let ext: string;

        if (extIndex > 0) {
            name = base.slice(0, extIndex);
            ext = base.slice(extIndex);
        } else {
            name = base;
            ext = "";
        }

        let conflictName = `${name} (conflict ${this.hostname})${ext}`;
        let conflictPath = path.join(
            this.config.outputDir,
            dir === "." ? conflictName : path.join(dir, conflictName),
        );

        if (!(await this.fs.exists(conflictPath))) {
            return dir === "." ? conflictName : path.join(dir, conflictName);
        }

        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        const dateStr = `${year}${month}${day}`;
        conflictName = `${name} (conflict ${this.hostname} ${dateStr})${ext}`;
        conflictPath = path.join(
            this.config.outputDir,
            dir === "." ? conflictName : path.join(dir, conflictName),
        );

        if (!(await this.fs.exists(conflictPath))) {
            return dir === "." ? conflictName : path.join(dir, conflictName);
        }

        const hours = String(now.getHours()).padStart(2, "0");
        const minutes = String(now.getMinutes()).padStart(2, "0");
        const seconds = String(now.getSeconds()).padStart(2, "0");
        const timestamp = `${dateStr}${hours}${minutes}${seconds}`;
        conflictName = `${name} (conflict ${this.hostname} ${timestamp})${ext}`;
        return dir === "." ? conflictName : path.join(dir, conflictName);
    }

    private async renameBlockingPath(blockingPath: string): Promise<string> {
        const relativePath = path.relative(this.config.outputDir, blockingPath);
        const conflictName = await this.generateConflictName(relativePath);
        const conflictPath = path.join(this.config.outputDir, conflictName);

        await this.fs.rename(blockingPath, conflictPath);
        this.log(`info: renamed "${relativePath}" to "${conflictName}"`);

        return conflictName;
    }
}

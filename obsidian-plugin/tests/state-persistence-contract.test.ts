import { describe, expect, it } from "vitest";
import type { SyncConfig, SyncResult, SyncStateEntry } from "../src/sync/types";

describe("state persistence contract", () => {
    it("all SyncResult fields survive round-trip to SyncConfig", () => {
        // Simulate a sync result with all fields populated
        const result: SyncResult = {
            output: ["sync: pulled file.md"],
            state: new Map([
                [
                    "uuid-1",
                    {
                        uuid: "uuid-1",
                        serverFilename: "file.md",
                        localFilename: "file.md",
                        serverHash: "abc123",
                        localHash: "abc123",
                    },
                ],
            ]),
            lastUpdate: "2025-01-15T10:00:00Z",
            lastFullSync: "2025-01-15T10:00:00Z",
        };

        // Simulate what main.ts does: save then load
        const saved = saveFolderState(result);
        const config = loadFolderState(saved);

        // Verify all result fields that should inform the next sync are present
        expect(config.initialState).toEqual(result.state);
        expect(config.lastUpdate).toBe(result.lastUpdate);
        expect(config.lastFullSync).toBe(result.lastFullSync);
    });
});

// Mirrors main.ts persistence logic
function saveFolderState(result: SyncResult): unknown {
    const entries: { [uuid: string]: SyncStateEntry } = {};
    for (const [uuid, entry] of result.state) {
        entries[uuid] = entry;
    }
    return {
        entries,
        lastUpdate: result.lastUpdate,
        lastFullSync: result.lastFullSync,
    };
}

function loadFolderState(saved: unknown): Partial<SyncConfig> {
    const data = saved as {
        entries: { [uuid: string]: SyncStateEntry };
        lastUpdate?: string;
        lastFullSync?: string;
    };
    const state = new Map<string, SyncStateEntry>();
    for (const [uuid, entry] of Object.entries(data.entries)) {
        state.set(uuid, entry);
    }
    return {
        initialState: state,
        lastUpdate: data.lastUpdate,
        lastFullSync: data.lastFullSync,
    };
}

describe("folder state isolation", () => {
    it("each folder has independent state", () => {
        const syncStates: { [folder: string]: unknown } = {};

        const resultA: SyncResult = {
            output: [],
            state: new Map([
                [
                    "uuid-a1",
                    {
                        uuid: "uuid-a1",
                        serverFilename: "notes/session-1.md",
                        localFilename: "notes/session-1.md",
                        serverHash: "hash-a1",
                        localHash: "hash-a1",
                    },
                ],
            ]),
            lastUpdate: "2025-01-15T10:00:00Z",
            lastFullSync: "2025-01-15T10:00:00Z",
        };

        const resultB: SyncResult = {
            output: [],
            state: new Map([
                [
                    "uuid-b1",
                    {
                        uuid: "uuid-b1",
                        serverFilename: "characters/hero.md",
                        localFilename: "characters/hero.md",
                        serverHash: "hash-b1",
                        localHash: "hash-b1",
                    },
                ],
                [
                    "uuid-b2",
                    {
                        uuid: "uuid-b2",
                        serverFilename: "characters/villain.md",
                        localFilename: "characters/villain.md",
                        serverHash: "hash-b2",
                        localHash: "hash-b2",
                    },
                ],
            ]),
            lastUpdate: "2025-01-16T12:00:00Z",
            lastFullSync: "2025-01-16T12:00:00Z",
        };

        syncStates["Campaign/Notes"] = saveFolderState(resultA);
        syncStates["Campaign/Characters"] = saveFolderState(resultB);

        const loadedA = loadFolderState(syncStates["Campaign/Notes"]);
        const loadedB = loadFolderState(syncStates["Campaign/Characters"]);

        expect(loadedA.initialState?.size).toBe(1);
        expect(loadedA.initialState?.has("uuid-a1")).toBe(true);
        expect(loadedA.initialState?.has("uuid-b1")).toBe(false);
        expect(loadedA.lastUpdate).toBe("2025-01-15T10:00:00Z");

        expect(loadedB.initialState?.size).toBe(2);
        expect(loadedB.initialState?.has("uuid-b1")).toBe(true);
        expect(loadedB.initialState?.has("uuid-b2")).toBe(true);
        expect(loadedB.initialState?.has("uuid-a1")).toBe(false);
        expect(loadedB.lastUpdate).toBe("2025-01-16T12:00:00Z");
    });
});

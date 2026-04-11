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

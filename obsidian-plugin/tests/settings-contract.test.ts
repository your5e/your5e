import { afterEach, beforeAll, beforeEach, describe, expect, test } from "vitest";
import type { FolderMapping } from "../src/settings.js";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import {
    API_BASE,
    cleanupTestDir,
    createFile,
    createTestDir,
    getToken,
    restoreDatabase,
} from "./helpers.js";

describe("settings contract", () => {
    let normToken: string;
    let testDir: string;
    let outputDir: string;

    beforeAll(async () => {
        normToken = await getToken("norm");
    });

    beforeEach(async () => {
        restoreDatabase();
        ({ testDir, outputDir } = await createTestDir());
    });

    afterEach(async () => {
        await cleanupTestDir(testDir);
    });

    function buildSyncConfig(folderMapping: FolderMapping, globalToken: string) {
        const baseUrl = folderMapping.baseUrl || API_BASE;
        const token = folderMapping.token || globalToken;

        return {
            baseUrl,
            token,
            notebook: folderMapping.notebook,
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: folderMapping.pullOnly,
        };
    }

    test("pullOnly setting prevents local file from being pushed", async () => {
        const folderMapping: FolderMapping = {
            folder: "test-folder",
            notebook: "norm/campaign-notes",
            pullOnly: true,
        };

        const config = buildSyncConfig(folderMapping, normToken);
        const sync = new SyncEngine(config);

        await createFile(outputDir, "local-only.md", "this should not be pushed\n");

        const result = await sync.run();

        expect(result.output).not.toContainEqual(
            expect.stringMatching(/push:.*local-only\.md/),
        );

        // ensure file was not pushed to server
        const response = await fetch(`${API_BASE}/v1/notebooks/norm/campaign-notes/`, {
            headers: { Authorization: `Token ${normToken}` },
        });
        const data = await response.json();
        const pushedFile = data.results.find(
            (p: { filename: string }) => p.filename === "local-only.md",
        );
        expect(pushedFile).toBeUndefined();
    });
});

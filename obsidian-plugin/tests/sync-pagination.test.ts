/**
 * Sync pagination tests
 *
 * Tests for syncing when the notebook has more pages than fit in a single
 * API response, ensuring all pages are fetched across pagination boundaries.
 *
 * Ported from tests/sync_pagination.bats
 */

import { execSync } from "node:child_process";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { NodeFileSystem } from "../src/sync/node-fs.js";
import { SyncEngine } from "../src/sync/sync-engine.js";
import {
    API_BASE,
    assertFileDownloaded,
    assertFileInState,
    assertLastUpdateExists,
    cleanupTestDir,
    createTestDir,
    getToken,
    restoreDatabase,
} from "./helpers.js";

const PROJECT_ROOT = path.resolve(import.meta.dirname, "../..");
const PAGE_SIZE = 50;

describe("sync pagination", () => {
    let token: string;
    let testDir: string;
    let outputDir: string;
    const pagesToCreate = PAGE_SIZE + 1;

    beforeAll(async () => {
        token = await getToken();
        restoreDatabase();

        for (let i = 1; i <= pagesToCreate; i++) {
            execSync(
                `curl -s -X POST \\
          -H "Authorization: Token ${token}" \\
          -F "file=@-;filename=page-${i}.md" \\
          "${API_BASE}/v1/notebooks/norm/campaign-notes/" \\
          <<< "# Page ${i}"`,
                { cwd: PROJECT_ROOT, stdio: "pipe", shell: "/bin/bash" },
            );
        }

        ({ testDir, outputDir } = await createTestDir());
    });

    afterAll(async () => {
        await cleanupTestDir(testDir);
    });

    test("sync fetches all pages across pagination boundaries", async () => {
        const sync = new SyncEngine({
            baseUrl: API_BASE,
            token,
            notebook: "norm/campaign-notes",
            outputDir,
            fileSystem: new NodeFileSystem(),
            pullOnly: true,
        });

        const result = await sync.run();

        const expectedOutput = [
            'pull: "random-hexmap-7.png" (v1)',
            'pull: "index.md" (v1)',
            'pull: "Home.md" (v2)',
            'pull: "sessions/session-01.md" (v1)',
            'pull: "Bestiary.md" (v2)',
            'pull: "characters/NPCs.md" (v2)',
            'pull: "The Old Café.md" (v1)',
            'pull: "World Regions/Northern Kingdoms/Frosthold.md" (v1)',
        ];

        for (let i = 1; i <= pagesToCreate; i++) {
            expectedOutput.push(`pull: "page-${i}.md" (v1)`);
        }

        expect(result.output).toEqual(expectedOutput);

        for (let i = 1; i <= pagesToCreate; i++) {
            const filePath = path.join(outputDir, `page-${i}.md`);
            const content = await fs.readFile(filePath, "utf-8");
            expect(content).toBe(`# Page ${i}\n`);
            assertFileInState(`page-${i}.md`, result.state);
        }

        await assertFileDownloaded(outputDir, "Home.md", result.state);
        await assertFileDownloaded(outputDir, "Bestiary.md", result.state);
        await assertFileDownloaded(outputDir, "index.md", result.state);
        await assertFileDownloaded(outputDir, "random-hexmap-7.png", result.state);
        await assertFileDownloaded(outputDir, "sessions/session-01.md", result.state);
        await assertFileDownloaded(outputDir, "characters/NPCs.md", result.state);
        await assertFileDownloaded(outputDir, "The Old Café.md", result.state);
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
            result.state,
        );
        assertLastUpdateExists(result.lastUpdate);
    });
});

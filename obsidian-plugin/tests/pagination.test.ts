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
    getToken,
    restoreDatabase,
} from "./helpers.js";

const PROJECT_ROOT = path.resolve(import.meta.dirname, "../..");
const PAGE_SIZE = 50;

describe("sync pagination", () => {
    let token: string;
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
          "${API_BASE}/api/notebooks/norm/campaign-notes/" \\
          <<< "# Page ${i}"`,
                { cwd: PROJECT_ROOT, stdio: "pipe", shell: "/bin/bash" },
            );
        }

        outputDir = await fs.mkdtemp(path.join("/tmp", "your5e-test-"));
    });

    afterAll(async () => {
        await fs.rm(outputDir, { recursive: true, force: true });
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
            await assertFileInState(outputDir, `page-${i}.md`);
        }

        await assertFileDownloaded(outputDir, "Home.md");
        await assertFileDownloaded(outputDir, "Bestiary.md");
        await assertFileDownloaded(outputDir, "index.md");
        await assertFileDownloaded(outputDir, "random-hexmap-7.png");
        await assertFileDownloaded(outputDir, "sessions/session-01.md");
        await assertFileDownloaded(outputDir, "characters/NPCs.md");
        await assertFileDownloaded(outputDir, "The Old Café.md");
        await assertFileDownloaded(
            outputDir,
            "World Regions/Northern Kingdoms/Frosthold.md",
        );
    });
});

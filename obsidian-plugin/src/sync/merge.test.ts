import * as fs from "node:fs";
import * as path from "node:path";
import { describe, expect, test } from "vitest";
import { threeWayMerge } from "./merge.js";

const MERGE_DIR = path.join(__dirname, "../../../tests/merge");

function parseMatrix(): Array<[string, string]> {
    const content = fs.readFileSync(path.join(MERGE_DIR, "tests.md"), "utf-8");
    const lines = content.split("\n");
    const serverOps: string[] = [];
    const clientOps: string[] = [];

    for (const line of lines) {
        const isHeaderRow =
            line.startsWith("|") &&
            line.includes("unchanged") &&
            line.includes("append");
        const isDataRow = line.startsWith("| **");
        const isEndOfMatrix =
            serverOps.length > 0 && clientOps.length > 0 && !line.startsWith("|");

        if (isHeaderRow) {
            const parts = line.split("|").slice(2, -1);
            serverOps.push(...parts.map((h) => h.trim()));
        } else if (isDataRow) {
            const match = line.match(/\| \*\*(.+?)\*\*/);
            if (match) {
                clientOps.push(match[1]);
            }
        } else if (isEndOfMatrix) {
            break;
        }
    }

    const cases: Array<[string, string]> = [];
    for (const clientOp of clientOps) {
        for (const serverOp of serverOps) {
            cases.push([clientOp, serverOp]);
        }
    }
    return cases;
}

describe("three-way merge", () => {
    const testCases = parseMatrix();

    test.each(testCases)("client %s + server %s", (clientOp, serverOp) => {
        const base = fs.readFileSync(path.join(MERGE_DIR, "inputs/base.md"), "utf-8");
        const client = fs.readFileSync(
            path.join(MERGE_DIR, `inputs/${clientOp}.md`),
            "utf-8",
        );
        const server = fs.readFileSync(
            path.join(MERGE_DIR, `inputs/${serverOp}.md`),
            "utf-8",
        );
        const expected = fs.readFileSync(
            path.join(MERGE_DIR, `expected/${clientOp}-${serverOp}.md`),
            "utf-8",
        );

        const [merged] = threeWayMerge(base, server, client);

        expect(merged).toBe(expected);
    });
});

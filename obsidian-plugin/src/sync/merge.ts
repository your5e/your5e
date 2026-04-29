import DiffMatchPatch from "diff-match-patch";

/**
 * Three-way merge with client-wins semantics.
 *
 * Computes the diff of client changes from base, and applies that patch
 * to the server document. If all patches apply successfully, returns the
 * merged result. If any patch fails, falls back to the client version.
 *
 * @param base - The common ancestor (last sync point)
 * @param server - The server's current version
 * @param client - The client's current version
 * @returns A tuple of [merged content, success boolean]
 */
export function threeWayMerge(
    base: string,
    server: string,
    client: string,
): [string, boolean] {
    const dmp = new DiffMatchPatch();
    const patches = dmp.patch_make(base, client);
    const [merged, results] = dmp.patch_apply(patches, server);

    if (results.every((r) => r)) {
        return [merged, true];
    }
    return [client, false];
}

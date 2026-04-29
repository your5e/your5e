Improve that page content updates are always last-write-wins, with no attempt
to merge. If we know the previous version the update was made from, we can
use three-way merge with diff-match-patch to do a better job. Compute the
diff of the update from its previous veresion, and apply that patch
to the current server content.

@queue
# server-side merge @phase

- [X] add a merge update method for applying the diff from the previous hash
      to the current state

If the base hash cannot be found, attempt fuzzy patch or difflib merging,
then just continue with last-write-wins if it cannot be successfully merged.

- [#] determine fallback merge strategies when the the hash is purged
      (cancelled, no good strategy, last-write-wins remains)

Then use what has been provided.

- [X] update the notebook update view to pass the previous hash
- [X] update the API PATCH to accept a header with the previous hash
- [X] update sync-notebook.sh to provide the previous hash
- [X] update sync-engine.ts to provide the previous hash
- [X] local delete vs server modified file should no longer win, as we now can
      prove there are updates we didn't delete and that should take precedence
- [X] revisit "local renamed untracked" to ensure they are correct

# client-side merge @phase

In full sync, local changes are pushed before any pull, so any merging
always happens on the server. Merge on the client is only needed when in
pull-only mode.

To properly three-way merge requires a common ancestor (last sync point).
Keeping a copy of every synced document seems like overkill. When the server
and client both have modified copies, pull the original hash again, and use
that for the merge.

- [X] choose whether clients keep the version or we implement get-by-hash
- [X] modify the sync bash script to do three-way merge on pull-only
- [X] modify the obsidian engine to do three-way merge on pull-only

# conflict resolution @phase

In order to not have a permanent inability to finalise the sync, conflicts
should be resolved in some manner that shows the user in their files, rather
than in a log they are unlikely to ever look at.

Plus, at least some of the point is to have your notes on at least other
computer in case of data loss. That doesn't help if they never leave.

- [X] resolve blocked syncing by renaming the local file (bash script)
- [X] resolve blocked syncing by renaming the local file (obsidian engine)
- [X] add "local deleted, local edited, remote edited" scenario
- [X] add scenario for unmergeable server and local modifications
- [X] add "stale file, local edited, remote edited" scenario
- [X] add a test for conflict resolution filename being pushed also conflicting
- [X] update the sync doc to clarify that preserving content is the #1 goal

# further testing @phase

- [X] add file merge strategy tests
- [ ] add DMP merge API endpoint, replacing the git merge
- [ ] add a multiple scenario combined sync test
        - confirm what happens on conflicts, banned files, etc when repeatedly syncing

# stale-branches

Lists local git branches that have had no commits for a while, and can delete them safely.

    stale-branches                          # branches idle for 30+ days
    stale-branches --days 90                # custom threshold
    stale-branches --keep main --keep dev   # never list or delete these
    stale-branches --delete                 # ask before deleting each one

Example:

    $ stale-branches --keep staging
    feature/old-experiment                   idle   662 days  last commit by dev
    feature/old-login                        idle   662 days  last commit by dev

Deletion uses `git branch -d`, so git refuses to delete branches that aren't merged. Git counts a branch as merged when its commits are already in the branch you are on (or in its upstream), so run `--delete` from your main branch. The tool never force-deletes anything.

Always skipped, even without `--keep`:

- `main`, `master`, `develop` and the remote's default branch (`origin/HEAD`)
- the current branch
- branches checked out in another worktree

Needs Python 3.7+ and git. No other dependencies.

## Install

macOS and Linux: copy `stale-branches` somewhere on your PATH and make it executable:

    chmod +x stale-branches
    ./stale-branches

Windows: there is no executable bit, so run it through Python:

    python stale-branches --keep main

## Tests

    python -m unittest discover -s tests -v

The tests create throwaway repositories and run the real script against them. GitHub Actions runs them on Linux, Windows and macOS.

## License

MIT, see LICENSE.

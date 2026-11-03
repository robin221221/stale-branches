# stale-branches

Lists local git branches that have had no commits for a while, and can delete them safely.

    stale-branches                # branches idle for 30+ days
    stale-branches --days 90      # custom threshold
    stale-branches --delete       # ask before deleting each one

Deletion uses `git branch -d`, so git refuses to delete branches that aren't merged. The tool never force-deletes anything. The current branch is always skipped.

Needs Python 3 and git. No other dependencies.

Install: copy `stale-branches` somewhere on your PATH and make it executable (`chmod +x stale-branches`).

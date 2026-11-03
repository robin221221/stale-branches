"""End-to-end tests: build throwaway repos and run the real script against them.

Run with:  python -m unittest discover -s tests -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stale-branches")
OLD = "2020-01-01T12:00:00+0000"


class StaleBranchesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stale-branches-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # isolate from the developer's own git config (signing, hooks, default branch...)
        gitconfig = os.path.join(self.tmp, "gitconfig")
        open(gitconfig, "w").close()
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL=gitconfig, GIT_CONFIG_NOSYSTEM="1",
            GIT_CEILING_DIRECTORIES=self.tmp,
            GIT_AUTHOR_NAME="Tester", GIT_AUTHOR_EMAIL="tester@example.com",
            GIT_COMMITTER_NAME="Tester", GIT_COMMITTER_EMAIL="tester@example.com",
        )
        self.repo = os.path.join(self.tmp, "repo")
        os.mkdir(self.repo)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.commit("init", OLD)
        # typical layout: old main, we are working on a fresh feature branch
        self.git("checkout", "-q", "-b", "work")
        self.commit("fresh work")

    # helpers ---------------------------------------------------------------
    def git(self, *args, cwd=None, **env):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.repo, env=dict(self.env, **env),
            check=True, capture_output=True, encoding="utf-8", errors="replace",
        )

    def commit(self, message, date=None, **env):
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self.git("commit", "-q", "--allow-empty", "-m", message, **env)

    def run_tool(self, *args, stdin="", cwd=None):
        return subprocess.run(
            [sys.executable, SCRIPT, *args], cwd=cwd or self.repo, env=self.env,
            input=stdin, capture_output=True, encoding="utf-8", errors="replace",
        )

    @staticmethod
    def listed(output):
        return {line.split()[0] for line in output.splitlines() if " idle " in line}

    def branches(self):
        out = self.git("for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads").stdout
        return set(out.split())

    # behaviour -------------------------------------------------------------
    def test_lists_only_old_branches(self):
        self.git("branch", "old", "main")
        self.git("branch", "recent", "work")
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.listed(result.stdout), {"old"})

    def test_main_is_never_offered_or_deleted(self):
        self.git("branch", "old", "main")
        result = self.run_tool("--delete", stdin="y\n" * 5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("main", self.listed(result.stdout))
        self.assertIn("main", self.branches())
        self.assertNotIn("old", self.branches())

    def test_origin_default_branch_is_kept(self):
        self.git("branch", "trunk", "main")
        self.git("update-ref", "refs/remotes/origin/trunk", "main")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        self.assertNotIn("trunk", self.listed(self.run_tool().stdout))

    def test_keep_option(self):
        self.git("branch", "staging", "main")
        result = self.run_tool("--keep", "staging")
        self.assertIn("No local branches idle", result.stdout)

    def test_unmerged_branch_is_not_deleted(self):
        self.git("checkout", "-q", "-b", "side", "main")
        self.commit("side work", OLD)
        self.git("checkout", "-q", "work")
        result = self.run_tool("--delete", stdin="y\n")
        self.assertIn("skipped side", result.stdout)
        self.assertNotIn("hint:", result.stdout)
        self.assertIn("side", self.branches())

    def test_branch_in_other_worktree_is_skipped(self):
        self.git("branch", "elsewhere", "main")
        self.git("worktree", "add", "-q", os.path.join(self.tmp, "wt"), "elsewhere")
        self.assertNotIn("elsewhere", self.listed(self.run_tool().stdout))

    def test_shows_committer_not_author(self):
        self.git("checkout", "-q", "-b", "picked", "main")
        self.commit("cherry-picked", OLD, GIT_AUTHOR_NAME="Original Author", GIT_COMMITTER_NAME="Rebaser")
        self.git("checkout", "-q", "work")
        self.assertIn("last commit by Rebaser", self.run_tool().stdout)

    def test_unicode_branch_name(self):
        self.git("branch", "фича-старая", "main")
        self.assertIn("фича-старая", self.listed(self.run_tool().stdout))

    def test_rejects_bad_days(self):
        for value in ("0", "-3", "abc"):
            with self.subTest(days=value):
                result = self.run_tool("--days", value)
                self.assertEqual(result.returncode, 2)

    def test_closed_stdin_deletes_nothing(self):
        self.git("branch", "old", "main")
        result = self.run_tool("--delete", stdin="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("old", self.branches())

    def test_outside_a_repository(self):
        outside = os.path.join(self.tmp, "not-a-repo")
        os.mkdir(outside)
        result = self.run_tool(cwd=outside)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not inside a git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()

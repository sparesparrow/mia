"""tools/scripts/mia-update-checkout.sh, step 1 of the production deploy (REQ-DEP-008).

Real git repositories in a temporary directory: an origin with two commits and a clone left on the first, with the
kinds of local state found on the production Pi (hand-copied fixes that equal the next commit, run-time data the
repository does not track) and the kinds the deploy must refuse to overwrite.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.req("REQ-DEP-008"),
    pytest.mark.skipif(shutil.which("git") is None, reason="needs git"),
]

SCRIPT = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "mia-update-checkout.sh"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(cwd: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repos(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    (origin / "api.py").write_text("v1\n")
    (origin / "keep.py").write_text("same\n")
    _git(origin, "add", ".")
    _git(origin, "commit", "-qm", "one")
    first = _git(origin, "rev-parse", "HEAD")
    (origin / "api.py").write_text("v2\n")
    (origin / "pairing.py").write_text("new\n")
    _git(origin, "add", ".")
    _git(origin, "commit", "-qm", "two")
    second = _git(origin, "rev-parse", "HEAD")

    checkout = tmp_path / "checkout"
    _git(tmp_path, "clone", "-q", str(origin), str(checkout))
    _git(checkout, "checkout", "-q", "--detach", first)
    return origin, checkout, first, second


def _run(checkout: Path, *args: str, **env: str):
    return subprocess.run(
        ["bash", str(SCRIPT), str(checkout), *args],
        env={**os.environ, **GIT_ENV, **env},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_clean_checkout_moves_to_origin_main_detached(repos):
    _, checkout, _, second = repos
    result = _run(checkout)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == second
    assert _git(checkout, "rev-parse", "HEAD") == second
    detached = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=checkout, capture_output=True)
    assert detached.returncode == 1  # a deploy pins a commit; HEAD is not a branch
    assert (checkout / "api.py").read_text() == "v2\n"


def test_hand_copied_fixes_equal_to_the_target_are_dropped_and_data_is_kept(repos):
    """The Pi's state on 2026-11-26: files copied from the next commit by hand, plus untracked run-time data."""
    _, checkout, _, second = repos
    (checkout / "api.py").write_text("v2\n")  # tracked, edited to the target's content
    (checkout / "pairing.py").write_text("new\n")  # untracked, the target tracks it with this content
    (checkout / "data").mkdir()
    (checkout / "data" / "voice.onnx").write_text("model\n")  # untracked, the target does not track it

    result = _run(checkout)

    assert result.returncode == 0, result.stderr
    assert _git(checkout, "rev-parse", "HEAD") == second
    assert (checkout / "data" / "voice.onnx").read_text() == "model\n"
    assert _git(checkout, "status", "--porcelain", "--untracked-files=no") == ""


@pytest.mark.parametrize(
    "path,content",
    [("api.py", "someone's local fix\n"), ("pairing.py", "different\n")],
    ids=["tracked-edit", "untracked-file"],
)
def test_local_changes_that_differ_stop_the_deploy_and_stay(repos, path, content):
    _, checkout, first, _ = repos
    (checkout / path).write_text(content)

    result = _run(checkout)

    assert result.returncode != 0
    assert path in result.stderr
    assert "nothing was changed" in result.stderr
    assert _git(checkout, "rev-parse", "HEAD") == first
    assert (checkout / path).read_text() == content


def test_an_explicit_ref_and_skip_fetch(repos):
    origin, checkout, first, _ = repos
    (origin / "api.py").write_text("v3\n")
    _git(origin, "commit", "-qam", "three")

    # Without a fetch the clone does not know the third commit: origin/main is still the second.
    skipped = _run(checkout, first, MIA_DEPLOY_SKIP_FETCH="1")
    assert skipped.returncode == 0, skipped.stderr
    assert skipped.stdout.strip().splitlines()[-1] == first

    unknown = _run(checkout, "no-such-ref", MIA_DEPLOY_SKIP_FETCH="1")
    assert unknown.returncode != 0
    assert "unknown ref" in unknown.stderr


def test_not_a_checkout_fails(tmp_path):
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "not a git checkout" in result.stderr


def test_git_runs_as_the_checkout_owner():
    """As root, git refuses another user's repository; the script switches to the owner instead of failing."""
    text = SCRIPT.read_text()
    assert 'OWNER="$(stat -c %U "$CHECKOUT/.git")"' in text
    assert 'runuser -u "$OWNER" --' in text
    assert "safe.directory" not in text


def _origin_and_checkout(tmp_path: Path, first: dict, second: dict, force_add=()):
    """An origin whose two commits hold exactly the given files, and a clone left detached on the first."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    commits = []
    for files in (first, second):
        for old in [p for p in origin.iterdir() if p.name != ".git"]:
            old.unlink()
        for name, content in files.items():
            (origin / name).write_text(content)
        _git(origin, "add", "-A")
        for name in force_add:
            if name in files:
                _git(origin, "add", "-f", name)
        _git(origin, "commit", "-qm", f"commit {len(commits) + 1}")
        commits.append(_git(origin, "rev-parse", "HEAD"))
    checkout = tmp_path / "checkout"
    _git(tmp_path, "clone", "-q", str(origin), str(checkout))
    _git(checkout, "checkout", "-q", "--detach", commits[0])
    return checkout, commits[0], commits[1]


IGNORE_LOCAL = "*.local\n"


def test_an_ignored_local_file_the_target_tracks_with_other_content_stops_the_deploy_and_stays(tmp_path):
    """git checkout overwrites ignored files without asking; an operator's ignored settings file is local work too."""
    checkout, first, _ = _origin_and_checkout(
        tmp_path,
        {".gitignore": IGNORE_LOCAL, "api.py": "v1\n"},
        {".gitignore": IGNORE_LOCAL, "api.py": "v2\n", "settings.local": "target\n"},
        force_add=("settings.local",),
    )
    (checkout / "settings.local").write_text("the operator's settings\n")

    result = _run(checkout)

    assert result.returncode != 0
    assert "settings.local" in result.stderr
    assert "nothing was changed" in result.stderr
    assert _git(checkout, "rev-parse", "HEAD") == first
    assert (checkout / "settings.local").read_text() == "the operator's settings\n"


def test_an_ignored_local_file_equal_to_the_target_is_dropped_and_other_ignored_files_stay(tmp_path):
    checkout, _, second = _origin_and_checkout(
        tmp_path,
        {".gitignore": IGNORE_LOCAL, "api.py": "v1\n"},
        {".gitignore": IGNORE_LOCAL, "api.py": "v2\n", "settings.local": "target\n"},
        force_add=("settings.local",),
    )
    (checkout / "settings.local").write_text("target\n")
    (checkout / "other.local").write_text("ignored, not tracked by the target\n")

    result = _run(checkout)

    assert result.returncode == 0, result.stderr
    assert _git(checkout, "rev-parse", "HEAD") == second
    assert (checkout / "settings.local").read_text() == "target\n"
    assert (checkout / "other.local").read_text() == "ignored, not tracked by the target\n"


def test_a_staged_rename_never_leaves_a_file_missing(tmp_path):
    """A staged `git mv keep.py moved.py`; the target adds moved.py with keep.py's content and keeps keep.py.

    With rename detection the diff lists only moved.py, which equals the target and is dropped; the staged deletion
    of keep.py is never seen, the checkout carries it over and the deployed tree lacks keep.py.
    """
    checkout, first, second = _origin_and_checkout(
        tmp_path,
        {"keep.py": "same\n", "api.py": "v1\n"},
        {"keep.py": "same\n", "moved.py": "same\n", "api.py": "v2\n"},
    )
    _git(checkout, "mv", "keep.py", "moved.py")

    result = _run(checkout)

    if result.returncode == 0:
        assert _git(checkout, "rev-parse", "HEAD") == second
        assert (checkout / "keep.py").read_text() == "same\n"
        assert _git(checkout, "status", "--porcelain", "--untracked-files=no") == ""
    else:
        # The staged deletion of keep.py is a local change the target does not share: a loud stop, nothing changed.
        assert "keep.py" in result.stderr
        assert "nothing was changed" in result.stderr
        assert _git(checkout, "rev-parse", "HEAD") == first
        assert (checkout / "moved.py").read_text() == "same\n"


def test_a_staged_rename_the_target_also_made_is_dropped_cleanly(tmp_path):
    checkout, _, second = _origin_and_checkout(
        tmp_path,
        {"keep.py": "same\n", "api.py": "v1\n"},
        {"moved.py": "same\n", "api.py": "v2\n"},
    )
    _git(checkout, "mv", "keep.py", "moved.py")

    result = _run(checkout)

    assert result.returncode == 0, result.stderr
    assert _git(checkout, "rev-parse", "HEAD") == second
    assert not (checkout / "keep.py").exists()
    assert (checkout / "moved.py").read_text() == "same\n"
    assert _git(checkout, "status", "--porcelain", "--untracked-files=no") == ""


def test_the_checkout_sees_ignored_files_and_renames_and_checks_its_result():
    text = SCRIPT.read_text()
    assert "--exclude-standard" not in text
    assert "diff --name-only --no-renames -z HEAD" in text
    # A tree that still differs from the target after the checkout fails the deploy instead of being installed.
    assert "status --porcelain --untracked-files=no" in text

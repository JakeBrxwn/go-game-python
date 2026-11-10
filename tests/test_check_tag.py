"""
Checks scripts/check_tag.py releases only the tags it should.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import check_tag  # noqa: E402

@pytest.mark.parametrize("version, on_main, prerelease", [
    ("0.1.0", True, False),
    ("10.20.30", True, False),
    ("0.1.0rc1", False, True),
    ("0.1.0rc12", True, True),
])
def test_releases(version: str, on_main: bool, prerelease: bool) -> None:
    """Check a final version on main and any pre-release are released"""
    assert check_tag.is_prerelease(f"v{version}", version, on_main) \
        == prerelease

@pytest.mark.parametrize("tag, version, on_main, why", [
    ("v0.1.0", "0.1.0", False, "is not on main"),
    ("v0.1.1", "0.1.0", True, "must be v0.1.0"),
    ("0.1.0", "0.1.0", True, "must be v0.1.0"),
    ("v0.1.00", "0.1.00", True, "must be like"),
    ("v0.01.0", "0.01.0", True, "must be like"),
    ("v0.1.0rc0", "0.1.0rc0", False, "must be like"),
    ("v0.1.0-rc.1", "0.1.0-rc.1", False, "must be like"),
    ("v0.1.0a1", "0.1.0a1", False, "must be like"),
    ("v0.1", "0.1", True, "must be like"),
])
def test_refuses(tag: str, version: str, on_main: bool, why: str) -> None:
    """Check a wrong tag, a version pip would rename and a final version off
    main are all refused"""
    with pytest.raises(SystemExit, match=why):
        check_tag.is_prerelease(tag, version, on_main)

def git(*args: str) -> str:
    """
    Runs git in the current folder, as a made-up person.

    Args:
        args: The git command

    Returns: Its output
    """
    person = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
              "GIT_COMMITTER_NAME": "Test",
              "GIT_COMMITTER_EMAIL": "test@example.com"}
    return subprocess.run(["git", *args], input="", capture_output=True,
                          text=True, check=True,
                          env=os.environ | person).stdout.strip()

def commit(*parents: str) -> str:
    """
    Makes an empty commit, without hooks or signing, as plumbing never runs
    them.

    Args:
        parents: Its parent commits

    Returns: Its hash
    """
    tree = git("mktree")
    return git("commit-tree", "--no-gpg-sign", "-m", "test", tree,
               *(arg for parent in parents for arg in ("-p", parent)))

def test_main_asks_git_if_the_tag_is_on_main(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Check main() releases a final version only when origin/main holds
    the checked-out commit"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(check_tag, "__version__", "0.1.0")
    monkeypatch.setattr(sys, "argv", ["check_tag.py", "v0.1.0"])
    git("init", "-q")
    main = commit()
    git("update-ref", "refs/remotes/origin/main", main)
    git("update-ref", "HEAD", main)
    check_tag.main()
    assert capsys.readouterr().out == "prerelease=false\n"
    git("update-ref", "HEAD", commit(main))
    with pytest.raises(SystemExit, match="is not on main"):
        check_tag.main()

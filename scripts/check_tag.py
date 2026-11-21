"""
Checks a tag before .github/workflows/release.yml publishes it, and prints
whether it makes a pre-release, as a line for GITHUB_OUTPUT. Exits with a
message if the tag must not be released. Run it from the repo root:

    python scripts/check_tag.py v0.1.0
"""
import re
import subprocess
import sys

from go_python import __version__

# No leading zeros, which pip drops: 0.1.00 would publish files named 0.1.0
PART = r"(0|[1-9][0-9]*)"
FINAL = rf"{PART}\.{PART}\.{PART}"
PRE = rf"{FINAL}rc[1-9][0-9]*"

def is_prerelease(tag: str, version: str, on_main: bool) -> bool:
    """
    Checks a tag can be released.

    Args:
        tag: The tag, like v0.1.0
        version: The version in the code
        on_main: True if the tagged commit is on main

    Returns: True for a pre-release, like 0.1.0rc1, which need not be on main

    Raises:
        SystemExit: If the tag is not v plus the version, the version is like
        neither 0.1.0 nor 0.1.0rc1, or a final version is not on main
    """
    if tag != f"v{version}":
        sys.exit(f"Tag {tag} must be v{version}")
    if re.fullmatch(PRE, version):
        return True
    if not re.fullmatch(FINAL, version):
        sys.exit(f"Version {version} must be like 0.1.0, or 0.1.0rc1")
    if not on_main:
        sys.exit(f"{tag} is not on main")
    return False

def main() -> None:
    """
    Checks the tag given as the first argument against this checkout.
    """
    # Exit 1 means not on main; any other failure counts as not on main too
    on_main = subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD",
                              "origin/main"]).returncode == 0
    prerelease = is_prerelease(sys.argv[1], __version__, on_main)
    print(f"prerelease={str(prerelease).lower()}")

if __name__ == "__main__":
    main()

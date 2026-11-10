"""
Checks scripts/third_party_licenses.py: THIRD_PARTY_LICENSES.txt is up to
date, and its check finds what the apps hold that no entry covers.
"""
import importlib.metadata
import io
import py_compile
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import third_party_licenses as tpl  # noqa: E402

# Names the release apps hold, a few from each OS, as bundled lists them
HELD = [
    "base_library.zip", "libpython3.14.so.1.0", "libssl.so.3", "libz.so.1",
    "libffi.so.8", "python3.14/lib-dynload/_ssl.cpython-314-x86_64-linux-gnu.so",
    "_sysconfigdata__linux_x86_64-linux-gnu", "libstdc++.so.6",
    "pygame_ce.libs/libSDL2-2-50d19f93.0.so.0.3200.10",
    "libFLAC-e7027ec5.so.14.0.0", "pygame/base.cpython-314-x86_64-linux-gnu.so",
    "pygame/freesansbold.ttf", "click", "colorama", "pygame",
    "click-8.5.1.dist-info/licenses/LICENSE.txt",
    "pyiboot01_bootstrap", "pyimod01_archive", "pyimod04_pywin32",
    "pyi_rth_inspect",
    "python314.dll", "_bz2.pyd", "_decimal.pyd", "libcrypto-3.dll",
    "libffi-8.dll", "ucrtbase.dll", "api-ms-win-crt-heap-l1-1-0.dll",
    "pygame/SDL2_ttf.dll", "pygame/_sdl2/video.cp314-win_amd64.pyd",
    "portmidi.dll", "libopusfile-0.dll",
    "Python", "Python.framework/Versions/3.14/Resources/Info.plist",
    "pygame/.dylibs/libz.1.3.1.zlib-ng.dylib", "libzstd.1.dylib",
    "pygame/_sdl2/audio.cpython-314-darwin.so",
]

def test_file_is_up_to_date() -> None:
    """Check the committed file has DIGEST, the header and every entry, in
    order"""
    assert not tpl.stale()

def test_finds_a_changed_text(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Check a cut licence text makes the file out of date, though every head
    is still there"""
    changed = tmp_path / "licences.txt"
    changed.write_text(tpl.OUTPUT.read_text(encoding="utf-8")[:-100],
                       encoding="utf-8")
    monkeypatch.setattr(tpl, "OUTPUT", changed)
    assert tpl.stale()

def test_finds_a_changed_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a changed entry makes the file out of date"""
    first = tpl.DEPENDENCIES[0]
    changed = tpl.Dependency(first.name, "MIT", first.website, first.where,
                             first.texts, first.files)
    monkeypatch.setattr(tpl, "DEPENDENCIES", [changed, *tpl.DEPENDENCIES[1:]])
    assert tpl.stale()

def test_finds_entries_out_of_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check swapped entries make the file out of date"""
    first, second, *rest = tpl.DEPENDENCIES
    monkeypatch.setattr(tpl, "DEPENDENCIES", [second, first, *rest])
    assert tpl.stale()

def test_finds_a_changed_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a new pygame-ce version in the header makes the file out of
    date"""
    monkeypatch.setattr(tpl, "HEADER", tpl.HEADER.replace(tpl.PYGAME_CE, "9.9.9"))
    assert tpl.stale()

def test_write_names_a_repeated_text(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Check write prints a text once, names the first entry that had it
    where it comes again, and gives the digest that makes the file current"""
    monkeypatch.setattr(tpl, "OUTPUT", tmp_path / "licences.txt")
    monkeypatch.setattr(tpl, "DEPENDENCIES", [
        tpl.Dependency(name, "Zlib", "site", "here", (f"{name}/a", f"{name}/b"))
        for name in ["First", "Second", "Third"]])
    monkeypatch.setattr(tpl, "fetch", lambda url: url if url == "First/a" else "zlib")
    monkeypatch.setattr(tpl, "DIGEST", tpl.write())
    text = tpl.OUTPUT.read_text(encoding="utf-8")
    for dependency in tpl.DEPENDENCIES:
        assert f"\n\n{tpl.entry_head(dependency)}" in text
    assert "\nFirst/a\n" in text
    assert text.count("\nzlib\n") == 1
    assert text.count("(The same text as for First, above.)") == 4
    assert not tpl.stale()

def test_fetch_gives_a_text(tmp_path: Path) -> None:
    """Check fetch reads UTF-8 and gives a text with \\n line ends and
    without the blank lines around it or the spaces that end its lines,
    whatever its line ends were"""
    path = tmp_path / "COPYING"
    path.write_bytes(b" \r\n\r\nCopyright \xc2\xa9 2026  \r\nyou may\r\n \r\n")
    assert tpl.fetch(path.as_uri()) == "Copyright © 2026\nyou may"

def test_fetch_gives_a_range_of_lines(tmp_path: Path) -> None:
    """Check fetch gives lines a to b for #L<a>-L<b>, without the indent
    they share, and refuses a range past the file's end"""
    path = tmp_path / "source.c"
    path.write_text("/*\n *  Copyright 2007 Red Hat  \n *    may use\n */\n",
                    encoding="utf-8")
    assert (tpl.fetch(f"{path.as_uri()}#L2-L3")
            == "*  Copyright 2007 Red Hat\n*    may use")
    with pytest.raises(ValueError, match="fewer lines"):
        tpl.fetch(f"{path.as_uri()}#L3-L5")

def test_fetch_refuses_a_web_page(tmp_path: Path) -> None:
    """Check fetch refuses a page, as a moved file's URL can give"""
    path = tmp_path / "COPYING"
    path.write_text("  <!DOCTYPE html><html>Not found</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="web page"):
        tpl.fetch(path.as_uri())

def test_fetch_reads_a_file_in_a_tarball(tmp_path: Path) -> None:
    """Check fetch takes #NAME from the tarball's top folder, not a file of
    the same name further down"""
    tarball = tmp_path / "project-1.0.tar.gz"
    with tarfile.open(tarball, "w:gz") as archive:
        for name, text in [("project-1.0/doc/COPYING", b"not this"),
                           ("project-1.0/COPYING", b"this\n")]:
            info = tarfile.TarInfo(name)
            info.size = len(text)
            archive.addfile(info, io.BytesIO(text))
    assert tpl.fetch(f"{tarball.as_uri()}#COPYING") == "this"
    with pytest.raises(KeyError):
        tpl.fetch(f"{tarball.as_uri()}#LICENSE")

def test_lists_what_an_app_holds(tmp_path: Path) -> None:
    """Check bundled lists files, data, links, non-standard packages and
    PyInstaller's modules and scripts, but not options or the standard
    library's or the app's own modules and scripts"""
    writers = pytest.importorskip("PyInstaller.archive.writers")
    source = tmp_path / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")
    compiled = py_compile.compile(str(source), cfile=str(tmp_path / "module.pyc"))
    modules = ["colorama", "colorama.ansi", "json", "go_python.cli"]
    pyz = tmp_path / "PYZ.pyz"
    writers.ZlibArchiveWriter(
        str(pyz), [(name, str(source), "PYMODULE") for name in modules],
        code_dict={name: compile("x = 1\n", "module.py", "exec")
                   for name in modules})
    app = tmp_path / "app"
    writers.CArchiveWriter(str(app), [
        ("libx.so.1", str(source), False, "b"),
        ("data\\file.txt", str(source), False, "x"),
        ("link.so", "libx.so.1", False, "n"),
        ("PYZ.pyz", str(pyz), False, "z"),
        ("pyi-python-flag X utf8", "", False, "o"),
        ("struct", compiled, False, "m"),
        ("pyimod01_archive", compiled, False, "m"),
        ("go_python", compiled, False, "M"),
        ("pyi_rth_inspect", str(source), False, "s"),
        ("go-python-tui", str(source), False, "s"),
    ], "libpython3.14.so")
    assert tpl.bundled(str(app)) == ["libx.so.1", "data/file.txt", "link.so",
                                     "colorama", "pyimod01_archive",
                                     "pyi_rth_inspect"]

def test_covers_what_the_apps_hold() -> None:
    """Check every name from the release apps is covered"""
    assert tpl.uncovered(HELD) == []

@pytest.mark.parametrize("name", [
    # A package's own .pyd is not Python's
    "numpy/_core/_multiarray_umath.cp314-win_amd64.pyd",
    "_cffi_backend.cp314-win_amd64.pyd",
    # pygame-ce's folders hold only its own modules besides those named
    "pygame/libSDL3.so", "pygame/_sdl2/new_lib.dll",
    "libavif.so.16", "pygame/libavif-16.dll", "numpy", "pygame/new_font.ttf",
    "pyi_splash", "numpy-2.0.dist-info/METADATA", "libzmq.so.5",
    "pygame/libSDL2_gfx.dll", "python3.14/lib-dynload/x/y.so",
    # Not a standard-library module, though it starts like _ctypes
    "_ctypes_test.pyd",
])
def test_finds_what_no_entry_covers(name: str) -> None:
    """Check a new library, package, module or data file is left over"""
    assert tpl.uncovered([*HELD, name]) == [name]

def test_installed_reads_each_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check installed gives the running Python's version, not the one in
    VERSIONS, and each package's own"""
    monkeypatch.setattr(tpl.platform, "python_version", lambda: "3.99.1")
    assert tpl.installed("Python") == "3.99.1"
    for name in ["click", "colorama"]:
        assert tpl.installed(name) == importlib.metadata.version(name)

def test_check_reads_the_apps_freeze_built(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check check with no apps reads the two freeze.py writes to dist/"""
    read = []

    def bundled(app: str) -> list[str]:
        read.append(app)
        return HELD
    monkeypatch.setattr(tpl, "stale", lambda: False)
    monkeypatch.setattr(tpl, "installed", tpl.VERSIONS.get)
    monkeypatch.setattr(tpl, "bundled", bundled)
    tpl.check([])
    suffix = ".exe" if sys.platform == "win32" else ""
    assert read == [str(Path("dist", tpl.binary_name("go-python") + suffix)),
                    str(Path("dist", tpl.binary_name("go-python-tui") + suffix))]

def test_check_fails_on_an_uncovered_file(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Check check passes covered apps and names the file in one that is not"""
    monkeypatch.setattr(tpl, "stale", lambda: False)
    monkeypatch.setattr(tpl, "installed", tpl.VERSIONS.get)
    monkeypatch.setattr(tpl, "bundled", lambda app: HELD)
    tpl.check(["ok-app"])
    assert "ok ok-app is covered" in capsys.readouterr().out
    monkeypatch.setattr(tpl, "bundled", lambda app: [*HELD, "libnew.so.1"])
    with pytest.raises(SystemExit, match=r"bad-app .*\['libnew.so.1'\]"):
        tpl.check(["bad-app"])

@pytest.mark.parametrize("project", list(tpl.VERSIONS))
def test_check_fails_on_another_version(
        monkeypatch: pytest.MonkeyPatch, project: str) -> None:
    """Check check refuses a build with a version the file is not for"""
    monkeypatch.setattr(tpl, "stale", lambda: False)
    monkeypatch.setattr(tpl, "installed", lambda name: (
        "9.9.9" if name == project else tpl.VERSIONS[name]))
    with pytest.raises(SystemExit, match=f"{project} is 9.9.9"):
        tpl.check(["app"])

def test_check_fails_on_a_stale_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check check refuses an out-of-date file"""
    monkeypatch.setattr(tpl, "stale", lambda: True)
    with pytest.raises(SystemExit, match="out of date"):
        tpl.check(["app"])

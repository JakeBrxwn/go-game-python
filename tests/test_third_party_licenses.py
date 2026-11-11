"""
Checks scripts/third_party_licenses.py: THIRD_PARTY_LICENSES.txt is up to
date, and its check finds what the apps hold that no entry covers.
"""
import dataclasses
import importlib.metadata
import io
import py_compile
import sys
import tarfile
from pathlib import Path
from typing import Any

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
    "pygame_ce.libs/libharfbuzz-672f7280.so.0.61430.0",
    "pygame/.dylibs/libharfbuzz.0.dylib",
]

def test_file_is_up_to_date() -> None:
    """Check the committed file has DIGEST, the header and every entry, in
    order"""
    assert not tpl.stale()

def test_reads_a_checkout_with_crlf_line_ends(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Check the file is still up to date with the \\r\\n line ends git can
    check it out with on Windows"""
    crlf = tmp_path / "licences.txt"
    text = tpl.OUTPUT.read_text(encoding="utf-8")
    crlf.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    monkeypatch.setattr(tpl, "OUTPUT", crlf)
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

@pytest.mark.parametrize("change", [
    {"name": "Renamed"}, {"licence": "MIT-0"}, {"website": "https://example.org/"},
    {"where": "Elsewhere"}, {"texts": ("https://example.org/LICENSE",)}])
@pytest.mark.parametrize("at", [0, 20, -1])
def test_finds_a_changed_entry(monkeypatch: pytest.MonkeyPatch, at: int,
                               change: dict[str, Any]) -> None:
    """Check an entry whose name, licence, website, place in the apps or text
    URLs changed, first, in the middle or last, makes the file out of date"""
    dependencies = list(tpl.DEPENDENCIES)
    dependencies[at] = dataclasses.replace(dependencies[at], **change)
    monkeypatch.setattr(tpl, "DEPENDENCIES", dependencies)
    assert tpl.stale()

@pytest.mark.parametrize("at", [0, 20, len(tpl.DEPENDENCIES)])
def test_finds_an_added_entry(
        monkeypatch: pytest.MonkeyPatch, at: int) -> None:
    """Check an entry the script added, first, in the middle or last, makes
    the file out of date"""
    dependencies = list(tpl.DEPENDENCIES)
    dependencies.insert(at, dataclasses.replace(dependencies[0], name="New"))
    monkeypatch.setattr(tpl, "DEPENDENCIES", dependencies)
    assert tpl.stale()

@pytest.mark.parametrize("at", [0, 20, len(tpl.DEPENDENCIES) - 2])
def test_finds_entries_out_of_order(
        monkeypatch: pytest.MonkeyPatch, at: int) -> None:
    """Check two swapped entries, first, in the middle or last, make the
    file out of date"""
    dependencies = list(tpl.DEPENDENCIES)
    dependencies[at], dependencies[at + 1] = dependencies[at + 1], dependencies[at]
    monkeypatch.setattr(tpl, "DEPENDENCIES", dependencies)
    assert tpl.stale()

def test_finds_a_changed_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a new pygame-ce version in the header makes the file out of
    date"""
    monkeypatch.setattr(tpl, "HEADER", tpl.HEADER.replace(tpl.PYGAME_CE, "9.9.9"))
    assert tpl.stale()

@pytest.mark.parametrize("header", [
    tpl.HEADER.split("\n", 1)[1],
    tpl.HEADER.removesuffix("\n").rsplit("\n", 1)[0] + "\n",
    tpl.HEADER.removesuffix("\n").rsplit("\n\n", 1)[0] + "\n"])
def test_finds_a_cut_header(
        monkeypatch: pytest.MonkeyPatch, header: str) -> None:
    """Check a header that lost its first line, last line or last paragraph
    makes the file out of date"""
    monkeypatch.setattr(tpl, "HEADER", header)
    assert tpl.stale()

@pytest.mark.parametrize("at", [0, 20, -1])
def test_finds_a_removed_entry(
        monkeypatch: pytest.MonkeyPatch, at: int) -> None:
    """Check an entry the script dropped, first, in the middle or last,
    makes the file out of date"""
    dependencies = list(tpl.DEPENDENCIES)
    del dependencies[at]
    monkeypatch.setattr(tpl, "DEPENDENCIES", dependencies)
    assert tpl.stale()

def test_write_names_a_repeated_text(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Check write prints a text once, names the first entry that had it
    where it comes again, and gives the digest that makes the file current,
    though a text holds lines shaped like an entry's head: a rule, a name
    and licence, a line, and a rule"""
    monkeypatch.setattr(tpl, "OUTPUT", tmp_path / "licences.txt")
    monkeypatch.setattr(tpl, "DEPENDENCIES", [
        tpl.Dependency(name, "Zlib", "site", "here", (f"{name}/a", f"{name}/b"))
        for name in ["First", "Second", "Third"]])
    monkeypatch.setattr(tpl, "fetch", lambda url: (
        f"{url}\n{tpl.RULE}\nA | B\nC\n{tpl.RULE}" if url == "First/a"
        else "zlib"))
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
    whatever its line ends were. Its lines keep their indent, even one they
    all share, as in a centred title"""
    path = tmp_path / "COPYING"
    path.write_bytes(b" \r\n\r\n     LICENCE\r\n"
                     b"  Copyright \xc2\xa9 2026  \r\n  you may\r\n \r\n")
    assert (tpl.fetch(path.as_uri())
            == "     LICENCE\n  Copyright © 2026\n  you may")

def test_fetch_gives_a_range_of_lines(tmp_path: Path) -> None:
    """Check fetch gives lines a to b for #L<a>-L<b>, numbered at line ends
    only, as GitHub does, without the indent they share but keeping each
    line's own, and refuses a range backwards or past the file's end"""
    path = tmp_path / "source.xml"
    path.write_bytes(b"<copyright>\x0c\n  Copyright \xc2\xa9 2007 Red Hat  \r\n"
                     b"  1. You may use\n     it freely\n</copyright>\n")
    assert (tpl.fetch(f"{path.as_uri()}#L2-L4")
            == "Copyright © 2007 Red Hat\n1. You may use\n   it freely")
    assert tpl.fetch(f"{path.as_uri()}#L5-L5") == "</copyright>"
    with pytest.raises(ValueError, match="fewer lines"):
        tpl.fetch(f"{path.as_uri()}#L4-L6")
    for backwards in ["#L4-L2", "#L3-L2", "#L0-L2"]:
        with pytest.raises(ValueError, match="not a range"):
            tpl.fetch(path.as_uri() + backwards)

def test_fetch_refuses_a_text_not_in_utf8(tmp_path: Path) -> None:
    """Check fetch fails on a text it cannot read, rather than drop bytes"""
    path = tmp_path / "COPYING"
    path.write_bytes(b"Copyright \xa9 2026")
    with pytest.raises(UnicodeDecodeError):
        tpl.fetch(path.as_uri())

@pytest.mark.parametrize("lines", ["", "#L1-L1"])
@pytest.mark.parametrize("page", ["  <!DOCTYPE html><html>Not found</html>",
                                  "<HTML><body>Not found</body></HTML>"])
def test_fetch_refuses_a_web_page(tmp_path: Path, page: str, lines: str) -> None:
    """Check fetch refuses a page, as a moved file's URL can give, for the
    whole file or a range of its lines"""
    path = tmp_path / "COPYING"
    path.write_text(page, encoding="utf-8")
    with pytest.raises(ValueError, match="web page"):
        tpl.fetch(path.as_uri() + lines)

def test_fetch_reads_a_file_in_a_tarball(tmp_path: Path) -> None:
    """Check fetch takes #NAME from the tarball's top folder, the first
    member's, not a file of the same name further down or in a later
    folder"""
    tarball = tmp_path / "project-1.0.tar.gz"
    with tarfile.open(tarball, "w:gz") as archive:
        for name, text in [("project-1.0/doc/COPYING", b"not this"),
                           ("project-1.0/COPYING", b"this  \r\nand that\r\n"),
                           ("other/COPYING", b"nor this")]:
            info = tarfile.TarInfo(name)
            info.size = len(text)
            archive.addfile(info, io.BytesIO(text))
    assert tpl.fetch(f"{tarball.as_uri()}#COPYING") == "this\nand that"
    with pytest.raises(KeyError):
        tpl.fetch(f"{tarball.as_uri()}#LICENSE")

def test_lists_what_an_app_holds(tmp_path: Path) -> None:
    """Check bundled lists files, even one named like a standard-library
    module, data, links, non-standard packages and single modules, and
    PyInstaller's modules and scripts, but not options or the standard
    library's or the app's own modules and scripts"""
    writers = pytest.importorskip("PyInstaller.archive.writers")
    source = tmp_path / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")
    compiled = py_compile.compile(str(source), cfile=str(tmp_path / "module.pyc"))
    modules = ["colorama", "colorama.ansi", "six", "json", "go_python.cli"]
    pyz = tmp_path / "PYZ.pyz"
    writers.ZlibArchiveWriter(
        str(pyz), [(name, str(source), "PYMODULE") for name in modules],
        code_dict={name: compile("x = 1\n", "module.py", "exec")
                   for name in modules})
    app = tmp_path / "app"
    writers.CArchiveWriter(str(app), [
        ("libx.so.1", str(source), False, "b"),
        ("sqlite3.dll", str(source), False, "b"),
        ("data\\sub\\file.txt", str(source), False, "x"),
        ("link.so", "libx.so.1", False, "n"),
        ("PYZ.pyz", str(pyz), False, "z"),
        ("pyi-python-flag X utf8", "", False, "o"),
        ("struct", compiled, False, "m"),
        ("pyimod01_archive", compiled, False, "m"),
        ("go_python", compiled, False, "M"),
        ("pyi_rth_inspect", str(source), False, "s"),
        ("go-python-tui", str(source), False, "s"),
    ], "libpython3.14.so")
    assert tpl.bundled(str(app)) == ["libx.so.1", "sqlite3.dll",
                                     "data/sub/file.txt", "link.so", "colorama",
                                     "six", "pyimod01_archive", "pyi_rth_inspect"]

def test_covers_what_the_apps_hold() -> None:
    """Check every name from the release apps is covered"""
    assert tpl.uncovered(HELD) == []

@pytest.mark.parametrize("name", [
    # A package's own .pyd is not Python's
    "numpy/_core/_multiarray_umath.cp314-win_amd64.pyd",
    "_cffi_backend.cp314-win_amd64.pyd",
    # Nor is SQLite, which Python for Windows ships beside _sqlite3.pyd
    "sqlite3.dll",
    # pygame-ce's folders hold only its own modules besides those named
    "pygame/libSDL3.so", "pygame/_sdl2/new_lib.dll",
    "libavif.so.16", "pygame/libavif-16.dll", "numpy", "pygame/new_font.ttf",
    "pyi_splash", "numpy-2.0.dist-info/METADATA", "libzmq.so.5",
    "pygame/libSDL2_gfx.dll", "python3.14/lib-dynload/x/y.so",
    "Python.framework/Versions/3.14/lib/libtcl9.0.dylib",
    # Not a standard-library module, though it starts like _ctypes
    "_ctypes_test.pyd",
    # Each pattern stays as narrow as its project: other projects, folders
    # and versions are left over
    "click_plugins", "pygame_ce.libs/libopenjp2-1a2b3c4d.so.2.5.0",
    "pygame_ce.libs/libssl-1a2b3c4d.so.3", "pkg/_ssl.cp314-win_amd64.pyd",
    "Python.framework/Versions/3.14/Resources/libtcl9.0.dylib",
    "pygame_ce.libs/libharfbuzz-subset-1a2b3c4d.so.0",
    "pygame/.dylibs/libz.1.3.1.dylib", "pygame/libwildmidi-2.dll",
    "libgccjit.so.0", "libpython2.7.so.1.0", "MSVCP140.dll",
    # Projects whose names start like a covered one's
    "pygame_gui", "click_plugins-1.1.1.dist-info/METADATA", "SDL2_gfx.dll",
    "pythoncom314.dll", "pygame/SDL3_image.dll", "pygame/SDL3_mixer.dll",
    "pygame/SDL3_ttf.dll", "pygame_ce.libs/libSDL3_image-1a2b3c4d.so.0.2.4",
    "pygame_ce.libs/libSDL3_mixer-1a2b3c4d.so.0.1.0",
    "pygame_ce.libs/libSDL3_ttf-1a2b3c4d.so.0.2.2",
    "pygame/libharfbuzz-subset-0.dll",
    "pygame/.dylibs/libharfbuzz-subset.0.dylib",
    "pygame/.dylibs/libspng.0.dylib", "libossp-uuid-16.dll",
    "pygame/libout123-0.dll", "libwebm-1a2b3c4d.so.1",
    # A zip the app adds is not Python's base library
    "data.zip",
    # A library the apps hold only at the top, from the build machine, is
    # left over in a package's folder, or in another platform's form
    "pygame_ce.libs/libbz2-1a2b3c4d.so.1.0.8",
    "pygame_ce.libs/libcrypto-1a2b3c4d.so.3",
    "pygame_ce.libs/libffi-1a2b3c4d.so.8",
    "pygame_ce.libs/libuuid-1a2b3c4d.so.1.3.0",
    "pygame/.dylibs/liblzma.5.dylib", "pygame/.dylibs/libzstd.1.5.7.dylib",
    "libgcc_s-1a2b3c4d.so.1", "libgcc_s.1.1.dylib", "libstdc++-1a2b3c4d.so.6",
    "libstdc++.6.dylib", "libz.1.dylib",
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
    monkeypatch.setattr(tpl, "bundled",
                        lambda app: [*HELD, "libnew.so.1", "libnext.so.2"])
    with pytest.raises(SystemExit,
                       match=r"bad-app .*\['libnew.so.1', 'libnext.so.2'\]"):
        tpl.check(["bad-app"])

@pytest.mark.parametrize("change", ["newer", "older", "longer", "post"])
@pytest.mark.parametrize("project", list(tpl.VERSIONS))
def test_check_fails_on_another_version(
        monkeypatch: pytest.MonkeyPatch, project: str, change: str) -> None:
    """Check check refuses a build with a version the file is not for, even
    one patch release newer or older, or one that starts with the file's"""
    version = tpl.VERSIONS[project]
    head, _, patch = version.rpartition(".")
    other = {"newer": f"{head}.{int(patch) + 1}",
             "older": f"{head}.{int(patch) - 1}",
             "longer": f"{version}0", "post": f"{version}.post1"}[change]
    monkeypatch.setattr(tpl, "stale", lambda: False)
    monkeypatch.setattr(tpl, "installed", lambda name: (
        other if name == project else tpl.VERSIONS[name]))
    with pytest.raises(SystemExit, match=f"{project} is {other}"):
        tpl.check(["app"])

def test_check_fails_on_a_stale_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check check refuses an out-of-date file"""
    monkeypatch.setattr(tpl, "stale", lambda: True)
    with pytest.raises(SystemExit, match="out of date"):
        tpl.check(["app"])

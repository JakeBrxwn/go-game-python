"""
Checks scripts/third_party_licenses.py: THIRD_PARTY_LICENSES.txt is up to
date, and its check finds what the apps hold that no entry covers.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import third_party_licenses as tpl  # noqa: E402

# Names the release apps hold, a few from each OS, as bundled lists them
HELD = [
    "base_library.zip", "libpython3.14.so.1.0", "libssl.so.3",
    "python3.14/lib-dynload/_ssl.cpython-314-x86_64-linux-gnu.so",
    "_sysconfigdata__linux_x86_64-linux-gnu", "libstdc++.so.6",
    "pygame_ce.libs/libSDL2-2-50d19f93.0.so.0.3200.10",
    "libFLAC-e7027ec5.so.14.0.0", "pygame/base.cpython-314-x86_64-linux-gnu.so",
    "pygame/freesansbold.ttf", "click", "colorama", "pygame",
    "click-8.5.1.dist-info/licenses/LICENSE.txt",
    "python314.dll", "_bz2.pyd", "ucrtbase.dll", "api-ms-win-crt-heap-l1-1-0.dll",
    "pygame/SDL2_ttf.dll", "pygame/_sdl2/video.cp314-win_amd64.pyd",
    "portmidi.dll", "libopusfile-0.dll",
    "Python", "Python.framework/Versions/3.14/Resources/Info.plist",
    "pygame/.dylibs/libz.1.3.1.zlib-ng.dylib", "libzstd.1.dylib",
]

def test_file_is_up_to_date() -> None:
    """Check the committed file has the header and every entry, in order"""
    assert not tpl.stale()

def test_finds_a_changed_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a changed entry makes the file out of date"""
    first = tpl.DEPENDENCIES[0]
    changed = tpl.Dependency(first.name, "MIT", first.website, first.where,
                             first.texts, first.files)
    monkeypatch.setattr(tpl, "DEPENDENCIES", [changed, *tpl.DEPENDENCIES[1:]])
    assert tpl.stale()

def test_finds_a_changed_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check a new pygame-ce version in the header makes the file out of
    date"""
    monkeypatch.setattr(tpl, "HEADER", tpl.HEADER.replace(tpl.PYGAME_CE, "9.9.9"))
    assert tpl.stale()

def test_write_names_a_repeated_text(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Check write prints a text met before by name, and is then not stale"""
    monkeypatch.setattr(tpl, "OUTPUT", tmp_path / "licences.txt")
    monkeypatch.setattr(tpl, "fetch", lambda url: "zlib" if "SDL" in url else url)
    tpl.write()
    text = tpl.OUTPUT.read_text(encoding="utf-8")
    assert text.count("\nzlib\n") == 1
    assert "(The same text as for SDL2, above.)" in text
    assert not tpl.stale()

def test_lists_what_an_app_holds(tmp_path: Path) -> None:
    """Check bundled lists files, data and links, and non-standard packages,
    but not PyInstaller's own scripts and options"""
    writers = pytest.importorskip("PyInstaller.archive.writers")
    source = tmp_path / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")
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
        ("bootstrap", str(source), False, "s"),
    ], "libpython3.14.so")
    assert tpl.bundled(str(app)) == ["libx.so.1", "data/file.txt", "link.so",
                                     "colorama"]

def test_covers_what_the_apps_hold() -> None:
    """Check every name from the release apps is covered"""
    assert tpl.uncovered(HELD) == []

@pytest.mark.parametrize("name", [
    # A package's own .pyd is not Python's, which sit at the top
    "numpy/_core/_multiarray_umath.cp314-win_amd64.pyd",
    "libavif.so.16", "pygame/libavif-16.dll", "numpy", "pygame/new_font.ttf",
])
def test_finds_what_no_entry_covers(name: str) -> None:
    """Check a new library, package or data file is left over"""
    assert tpl.uncovered([*HELD, name]) == [name]

def test_check_fails_on_an_uncovered_file(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Check check passes covered apps and names the file in one that is not"""
    monkeypatch.setattr(tpl.importlib.metadata, "version",
                        lambda name: tpl.PYGAME_CE)
    monkeypatch.setattr(tpl, "bundled", lambda app: HELD)
    tpl.check(["ok-app"])
    assert "ok ok-app is covered" in capsys.readouterr().out
    monkeypatch.setattr(tpl, "bundled", lambda app: [*HELD, "libnew.so.1"])
    with pytest.raises(SystemExit, match=r"bad-app .*\['libnew.so.1'\]"):
        tpl.check(["bad-app"])

def test_check_fails_on_another_pygame_ce(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Check check refuses a build whose pygame-ce the file does not name"""
    monkeypatch.setattr(tpl.importlib.metadata, "version", lambda name: "9.9.9")
    with pytest.raises(SystemExit, match="pygame-ce is 9.9.9"):
        tpl.check(["app"])

def test_check_fails_on_a_stale_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check check refuses an out-of-date file"""
    monkeypatch.setattr(tpl, "stale", lambda: True)
    with pytest.raises(SystemExit, match="out of date"):
        tpl.check(["app"])

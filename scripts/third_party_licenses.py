"""
Writes and checks THIRD_PARTY_LICENSES.txt: the licences of the software the
release apps bundle besides Go Python. Run it from the repo root:

    python scripts/third_party_licenses.py write
        Fetches each licence text below and rewrites the file.
    python scripts/third_party_licenses.py check [APP ...]
        Fails if an app holds a file no entry below covers, if the file is
        out of date with the entries, or if pygame-ce is not PYGAME_CE.
        With no apps, it checks the two that scripts/freeze.py built. Needs
        PyInstaller: pip install ".[release]".

To upgrade pygame-ce, change PYGAME_CE and its pin in pyproject.toml, look up
the versions pygame-ce builds (see its buildconfig), update the URLs below,
and run write.
"""
import importlib.metadata
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from freeze import APPS, binary_name

OUTPUT = Path(__file__).parent.parent / "THIRD_PARTY_LICENSES.txt"
# pygame-ce sets the versions of SDL and the other libraries it ships with
PYGAME_CE = "2.5.8"
PG = f"https://raw.githubusercontent.com/pygame-community/pygame-ce/{PYGAME_CE}/docs"
GH = "https://raw.githubusercontent.com"

@dataclass(frozen=True)
class Dependency:
    """
    One project the apps bundle.

    Attributes:
        name: The project's name
        licence: Its licence, as an SPDX identifier where one exists
        website: Where its source is published
        where: Where it is in the apps, for the reader
        texts: URLs of its licence texts, pinned to the version bundled
        files: What it is in the apps, as patterns for PurePosixPath's
            full_match: * stays within one folder and ** spans any. A Python
            package with no files of its own is its bare name.
    """
    name: str
    licence: str
    website: str
    where: str
    texts: tuple[str, ...]
    files: tuple[str, ...] = ()

DEPENDENCIES = [
    Dependency(
        "Python", "PSF-2.0", "https://www.python.org/",
        "All apps. The licence page below also covers the OpenSSL, libffi, "
        "zlib, expat, libmpdec and mimalloc code that comes with it.",
        (f"{GH}/python/cpython/3.14/Doc/license.rst",),
        ("base_library.zip", "libpython3*", "python3*.dll", "*.pyd",
         "python3.*/lib-dynload/*", "Python", "Python.framework/**",
         "_sysconfigdata_*", "libssl*", "libcrypto*", "libffi*", "libz.so*")),
    Dependency(
        "HACL*", "MIT", "https://github.com/hacl-star/hacl-star",
        "All apps, built into Python's hash modules.",
        (f"{GH}/hacl-star/hacl-star/8ba599b2f6c9701b3dc961db895b0856a2210f76"
         "/dist/LICENSE.txt",)),
    Dependency(
        "bzip2", "bzip2-1.0.6", "https://sourceware.org/bzip2/",
        "The Linux apps, and built into Python's _bz2 module on Windows.",
        ("https://sourceware.org/git/?p=bzip2.git;a=blob_plain;f=LICENSE;"
         "hb=bzip2-1.0.8",),
        ("libbz2*",)),
    Dependency(
        "XZ Utils (liblzma)", "0BSD", "https://tukaani.org/xz/",
        "The Linux apps, and built into Python's _lzma module on Windows "
        "and macOS.",
        (f"{GH}/tukaani-project/xz/v5.8.1/COPYING",),
        ("liblzma*",)),
    Dependency(
        "Zstandard", "BSD-3-Clause", "https://facebook.github.io/zstd/",
        "The Linux and macOS apps, and built into Python's _zstd module on "
        "Windows.",
        (f"{GH}/facebook/zstd/v1.5.7/LICENSE",),
        ("libzstd*",)),
    Dependency(
        "libuuid (util-linux)", "BSD-3-Clause",
        "https://github.com/util-linux/util-linux",
        "The Linux apps. Copyright (C) 1996, 1997, 1998, 1999 Theodore Ts'o.",
        (f"{GH}/util-linux/util-linux/v2.37.2/libuuid/COPYING",
         f"{GH}/util-linux/util-linux/v2.37.2/Documentation/licenses"
         "/COPYING.BSD-3-Clause"),
        ("libuuid*",)),
    Dependency(
        "GCC runtime libraries", "GPL-3.0-or-later WITH GCC-exception-3.1",
        "https://gcc.gnu.org/", "The Linux window app.",
        (f"{GH}/gcc-mirror/gcc/releases/gcc-12.3.0/COPYING.RUNTIME",),
        ("libgcc_s.so*", "libstdc++.so*")),
    Dependency(
        "Microsoft C runtime", "Microsoft distributable code",
        "https://visualstudio.microsoft.com/", "The Windows apps.",
        (f"{GH}/python/cpython/3.14/PC/crtlicense.txt",),
        ("VCRUNTIME140*.dll", "ucrtbase.dll", "api-ms-win-*.dll")),
    Dependency(
        "pygame-ce", "LGPL-2.1-or-later", "https://pyga.me/",
        f"The window apps, version {PYGAME_CE}. After the LGPL come the "
        "licences pygame-ce gives for code in its own modules: SDL_gfx, "
        "sse2neon and NumPy.",
        (f"{PG}/LGPL.txt", f"{PG}/licenses/LICENSE.sdl_gfx.txt",
         f"{PG}/licenses/LICENSE.sse2neon-h.txt",
         f"{PG}/licenses/LICENSE.numpy.txt"),
        ("pygame", "pygame/*.so", "pygame/*.pyd", "pygame/_sdl2/*",
         "pygame/pygame_icon*.bmp")),
    Dependency(
        "SDL2", "Zlib", "https://www.libsdl.org/", "The window apps.",
        (f"{GH}/libsdl-org/SDL/release-2.32.10/LICENSE.txt",),
        ("**/libSDL2-2*", "**/SDL2.dll")),
    Dependency(
        "SDL2_image", "Zlib", "https://github.com/libsdl-org/SDL_image",
        "The window apps. It holds QOI, below.",
        (f"{GH}/libsdl-org/SDL_image/release-2.8.12/LICENSE.txt",),
        ("**/libSDL2_image*", "**/SDL2_image.dll")),
    Dependency(
        "QOI", "MIT", "https://github.com/phoboslab/qoi",
        "The window apps, built into SDL2_image.",
        (f"{GH}/phoboslab/qoi/ffb2d2cb74a1de60819b21b939f7209aa53e91c1"
         "/LICENSE",)),
    Dependency(
        "SDL2_mixer", "Zlib", "https://github.com/libsdl-org/SDL_mixer",
        "The window apps. It holds Timidity, whose licence is the second "
        "text below, and on Windows also minimp3 (CC0) and stb_vorbis "
        "(public domain).",
        (f"{GH}/libsdl-org/SDL_mixer/release-2.8.2/LICENSE.txt",
         f"{GH}/libsdl-org/SDL_mixer/release-2.8.2/src/codecs/timidity/COPYING"),
        ("**/libSDL2_mixer*", "**/SDL2_mixer.dll")),
    Dependency(
        "SDL2_ttf", "Zlib", "https://github.com/libsdl-org/SDL_ttf",
        "The window apps. On Windows it holds HarfBuzz, below.",
        (f"{GH}/libsdl-org/SDL_ttf/release-2.24.0/LICENSE.txt",),
        ("**/libSDL2_ttf*", "**/SDL2_ttf.dll")),
    Dependency(
        "FreeType", "FTL", "https://freetype.org/",
        "The window apps. Portions of this software are copyright © 2026 "
        "The FreeType Project (www.freetype.org). All rights reserved.",
        ("https://gitlab.freedesktop.org/freetype/freetype/-/raw/VER-2-14-3"
         "/LICENSE.TXT",
         "https://gitlab.freedesktop.org/freetype/freetype/-/raw/VER-2-14-3"
         "/docs/FTL.TXT"),
        ("**/libfreetype*", "**/freetype.dll")),
    Dependency(
        "HarfBuzz", "MIT-Modern-Variant", "https://harfbuzz.github.io/",
        "The window apps. Its Microsoft USE data has the second licence.",
        (f"{GH}/harfbuzz/harfbuzz/14.3.0/COPYING",
         f"{GH}/harfbuzz/harfbuzz/14.3.0/src/ms-use/COPYING"),
        ("**/libharfbuzz*",)),
    Dependency(
        "Brotli", "MIT", "https://github.com/google/brotli",
        "The Linux and macOS window apps.",
        (f"{GH}/google/brotli/v1.2.0/LICENSE",),
        ("**/libbrotli*",)),
    Dependency(
        "libjpeg-turbo", "IJG AND BSD-3-Clause AND Zlib",
        "https://libjpeg-turbo.org/",
        "The window apps. This software is based in part on the work of the "
        "Independent JPEG Group.",
        (f"{GH}/libjpeg-turbo/libjpeg-turbo/3.1.4.1/LICENSE.md",
         f"{PG}/licenses/LICENSE.jpeg.txt"),
        ("**/libjpeg*",)),
    Dependency(
        "libpng", "libpng-2.0", "http://www.libpng.org/pub/png/libpng.html",
        "The window apps.", (f"{PG}/licenses/LICENSE.png.txt",),
        ("**/libpng*",)),
    Dependency(
        "LibTIFF", "libtiff", "https://libtiff.gitlab.io/libtiff/",
        "The window apps.", (f"{PG}/licenses/LICENSE.tiff.txt",),
        ("**/libtiff*",)),
    Dependency(
        "libwebp", "BSD-3-Clause", "https://chromium.googlesource.com/webm/libwebp",
        "The window apps, with its libsharpyuv and libwebpdemux.",
        (f"{PG}/licenses/LICENSE.webp.txt",),
        ("**/libwebp*", "**/libsharpyuv*")),
    Dependency(
        "Ogg and Vorbis", "BSD-3-Clause", "https://xiph.org/",
        "The window apps; Vorbis only on Linux and macOS.",
        (f"{PG}/licenses/LICENSE.ogg-vorbis.txt",),
        ("**/libogg*", "**/libvorbis*")),
    Dependency(
        "Opus and opusfile", "BSD-3-Clause", "https://opus-codec.org/",
        "The window apps.",
        (f"{PG}/licenses/LICENSE.opus.txt", f"{PG}/licenses/LICENSE.opusfile.txt"),
        ("**/libopus*",)),
    Dependency(
        "FLAC", "BSD-3-Clause", "https://xiph.org/flac/",
        "The Linux and macOS window apps.",
        (f"{PG}/licenses/LICENSE.FLAC.txt",),
        ("**/libFLAC*",)),
    Dependency(
        "mpg123", "LGPL-2.1-only", "https://www.mpg123.de/",
        "The Linux and macOS window apps.",
        (f"{PG}/licenses/LICENSE.mpg123.txt",),
        ("**/libmpg123*",)),
    Dependency(
        "FluidSynth", "LGPL-2.1-or-later", "https://www.fluidsynth.org/",
        "The Linux and macOS window apps.",
        (f"{PG}/licenses/LICENSE.fluidsynth.txt",),
        ("**/libfluidsynth*",)),
    Dependency(
        "libsndfile", "LGPL-2.1-or-later", "https://libsndfile.github.io/libsndfile/",
        "The Linux and macOS window apps.",
        (f"{GH}/libsndfile/libsndfile/1.2.2/COPYING",),
        ("**/libsndfile*",)),
    Dependency(
        "WavPack", "BSD-3-Clause", "https://www.wavpack.com/",
        "The window apps.", (f"{GH}/dbry/WavPack/5.9.0/COPYING",),
        ("**/libwavpack*",)),
    Dependency(
        "libxmp", "MIT", "https://xmp.sourceforge.net/",
        "The window apps.", (f"{GH}/libxmp/libxmp/libxmp-4.7.2/docs/COPYING",),
        ("**/libxmp*",)),
    Dependency(
        "PortMidi", "MIT", "https://github.com/PortMidi/portmidi",
        "The Windows window app.",
        (f"{GH}/PortMidi/portmidi/v2.0.7/license.txt",),
        ("**/portmidi.dll",)),
    Dependency(
        "zlib-ng", "Zlib", "https://github.com/zlib-ng/zlib-ng",
        "The macOS window app, and built into python314.dll on Windows.",
        (f"{GH}/zlib-ng/zlib-ng/2.3.3/LICENSE.md",),
        ("**/libz.*zlib-ng*",)),
    Dependency(
        "FreeSans font", "GPL", "https://savannah.gnu.org/projects/freefont/",
        "The window apps' text, as pygame/freesansbold.ttf. Copyright 2002 "
        "Free Software Foundation. Its licence names the GNU General Public "
        "License with no version, and version 3 follows. Its source is the "
        "font file, also in pygame-ce's source (see Source code, above).",
        ("https://www.gnu.org/licenses/gpl-3.0.txt",),
        ("pygame/freesansbold.ttf",)),
    Dependency(
        "click", "BSD-3-Clause", "https://palletsprojects.com/p/click/",
        "All apps.", (f"{GH}/pallets/click/8.5.1/LICENSE.txt",),
        ("click", "click-*.dist-info/**")),
    Dependency(
        "colorama", "BSD-3-Clause", "https://github.com/tartley/colorama",
        "All apps.", (f"{GH}/tartley/colorama/0.4.6/LICENSE.txt",),
        ("colorama",)),
]

HEADER = f"""\
Third-party licences
====================

The Go Python apps in each release are single files that bundle Python,
pygame-ce, SDL and the other software below, each under its own licence.
Go Python's own code is under the MIT licence, in LICENSE. The wheel and the
sdist bundle none of this software: pip installs what they need separately.

Each entry gives a project's licence, its website, where it is in the apps,
and where its licence text was taken from, then the text.

Source code
-----------

Each project below publishes its source at its website. The apps bundle
pygame-ce {PYGAME_CE} and the libraries it ships with, which include the LGPL
libraries mpg123, FluidSynth and libsndfile:

- pygame-ce's source: https://pypi.org/project/pygame-ce/{PYGAME_CE}/#files
- the libraries it builds, by version:
  https://github.com/pygame-community/pygame-ce/tree/{PYGAME_CE}/buildconfig

To run Go Python with a changed pygame-ce or library, install Go Python from
its wheel or sdist with pip, as README.md shows, then install your version
into the same environment.

The apps are built with PyInstaller, whose bootloader licence asks for no
notice.
"""
RULE = "-" * 80

def entry_head(dependency: Dependency) -> str:
    """
    Writes the lines that open a dependency's entry.

    Args:
        dependency: The dependency

    Returns: The lines, ending in a newline
    """
    sources = "".join(f"Text from: {url}\n" for url in dependency.texts)
    return (f"{RULE}\n{dependency.name} | {dependency.licence}\n"
            f"Website: {dependency.website}\nIn the apps: {dependency.where}\n"
            f"{sources}{RULE}\n")

def fetch(url: str) -> str:
    """
    Fetches a licence text.

    Args:
        url: Where it is

    Returns: The text, without trailing whitespace on any line

    Raises:
        ValueError: If the URL gave a web page, not a text
    """
    request = urllib.request.Request(url, headers={"User-Agent": "go-python"})
    with urllib.request.urlopen(request, timeout=30) as response:
        text: str = response.read().decode("utf-8")
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError(f"{url} gave a web page")
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines())

def write() -> None:
    """
    Fetches every licence text and rewrites THIRD_PARTY_LICENSES.txt.
    """
    parts = [HEADER]
    seen: dict[str, str] = {}
    for dependency in DEPENDENCIES:
        parts.append(f"\n{entry_head(dependency)}")
        for url in dependency.texts:
            text = fetch(url)
            # A text met before, like SDL's, is named, not printed again
            parts.append(f"\n(The same text as for {seen[text]}, above.)\n"
                         if text in seen else f"\n{text}\n")
            seen.setdefault(text, dependency.name)
    OUTPUT.write_text("".join(parts), encoding="utf-8", newline="\n")

def stale() -> bool:
    """
    Tells whether THIRD_PARTY_LICENSES.txt is out of date with
    DEPENDENCIES: its header, and every entry's head in order.

    Returns: True if it is out of date
    """
    text = OUTPUT.read_text(encoding="utf-8")
    if not text.startswith(HEADER):
        return True
    at = 0
    for dependency in DEPENDENCIES:
        at = text.find(f"\n{entry_head(dependency)}", at)
        if at < 0:
            return True
    return False

def bundled(app: str) -> list[str]:
    """
    Lists what a PyInstaller one-file app holds: its files and symlinks,
    with / between folders, and the top-level packages of its non-standard
    Python modules besides go_python.

    Args:
        app: The app's path

    Returns: The names
    """
    # Imported here so the tests run without PyInstaller
    from PyInstaller.archive.readers import CArchiveReader

    reader = CArchiveReader(app)
    names = []
    for name, entry in reader.toc.items():
        kind = entry[-1]
        if kind == "z":
            modules = reader.open_embedded_archive(name).toc
            names += sorted({module.split(".")[0] for module in modules}
                            - set(sys.stdlib_module_names) - {"go_python"})
        # Not PyInstaller's own modules, scripts and options
        elif kind not in "mMso":
            names.append(name.replace("\\", "/"))
    return names

def uncovered(names: list[str]) -> list[str]:
    """
    Finds the names no dependency covers.

    Args:
        names: What an app holds, from bundled

    Returns: The names left over
    """
    patterns = [pattern for dependency in DEPENDENCIES
                for pattern in dependency.files]
    return [name for name in names
            if not any(PurePosixPath(name).full_match(pattern)
                       for pattern in patterns)]

def check(apps: list[str]) -> None:
    """
    Checks THIRD_PARTY_LICENSES.txt covers the apps, exiting on a problem.

    Args:
        apps: The apps' paths, or none for the two freeze.py built
    """
    if stale():
        sys.exit(f"FAIL {OUTPUT.name} is out of date: run "
                 "python scripts/third_party_licenses.py write")
    installed = importlib.metadata.version("pygame-ce")
    if installed != PYGAME_CE:
        sys.exit(f"FAIL pygame-ce is {installed}, but {OUTPUT.name} is for "
                 f"{PYGAME_CE}: see this script's docstring")
    suffix = ".exe" if sys.platform == "win32" else ""
    for app in apps or [str(Path("dist", binary_name(name) + suffix))
                        for name in APPS]:
        left = uncovered(bundled(app))
        if left:
            sys.exit(f"FAIL {app} holds files {OUTPUT.name} does not "
                     f"cover; add them to DEPENDENCIES: {left}")
        print("ok", app, "is covered")

if __name__ == "__main__":
    if sys.argv[1:2] == ["write"]:
        write()
    elif sys.argv[1:2] == ["check"]:
        check(sys.argv[2:])
    else:
        sys.exit(__doc__)

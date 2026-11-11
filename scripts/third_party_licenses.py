"""
Writes and checks THIRD_PARTY_LICENSES.txt: the licences of the software the
release apps bundle besides Go Python. Run it from the repo root:

    python scripts/third_party_licenses.py write
        Fetches each licence text below, rewrites the file, and prints the
        digest to set DIGEST to.
    python scripts/third_party_licenses.py check [APP ...]
        Fails if an app holds a file no entry below covers, if the file is
        out of date with the entries or DIGEST, or if a project in VERSIONS
        is installed at another version. With no apps, it checks the two that
        scripts/freeze.py built. Needs PyInstaller: pip install ".[release]".

To upgrade a project in VERSIONS, change it there and where it is pinned:
the release extra in pyproject.toml, or python-version in
.github/workflows/build.yml for Python. Then look up the versions of the
libraries it bundles (pygame-ce's are in its buildconfig), update the entries
below, run write, and set DIGEST. Check each library's source too: code it
builds in from other holders often carries a notice of its own, which goes in
as a #L<a>-L<b> text.
"""
import hashlib
import importlib.metadata
import io
import platform
import re
import sys
import tarfile
import textwrap
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from freeze import APPS, binary_name

OUTPUT = Path(__file__).parent.parent / "THIRD_PARTY_LICENSES.txt"
# The file's SHA-256, so a changed or cut text is found
DIGEST = "7e6746a209416968ad9e9fc5e85981950af02faf0306562e1091361c2283c53f"
# What the build installs, which sets what the apps bundle: Python and
# pygame-ce also set the versions of the libraries that come with them
VERSIONS = {"Python": "3.14.10", "pygame-ce": "2.5.8", "PyInstaller": "6.22.3",
            "click": "8.5.1", "colorama": "0.4.6"}
PYTHON = VERSIONS["Python"]
PYGAME_CE = VERSIONS["pygame-ce"]
GH = "https://raw.githubusercontent.com"
PG = f"{GH}/pygame-community/pygame-ce/{PYGAME_CE}/docs"
FT = "https://gitlab.freedesktop.org/freetype/freetype/-/raw"
SDL = f"{GH}/libsdl-org/SDL/release-2.32.10"
SDL_IMAGE = f"{GH}/libsdl-org/SDL_image/release-2.8.12"
# The Wayland protocols the Linux SDL2 is built with, and the lines of each
# one's copyright notice
WAYLAND = {
    "cursor-shape-v1": "L4-L22", "fractional-scale-v1": "L4-L23",
    "idle-inhibit-unstable-v1": "L5-L24",
    "keyboard-shortcuts-inhibit-unstable-v1": "L5-L24",
    "pointer-constraints-unstable-v1": "L5-L25",
    "primary-selection-unstable-v1": "L4-L23",
    "relative-pointer-unstable-v1": "L5-L25", "tablet-unstable-v2": "L5-L27",
    "text-input-unstable-v3": "L5-L29", "viewporter": "L5-L24",
    "wayland": "L5-L28", "xdg-activation-v1": "L5-L25",
    "xdg-decoration-unstable-v1": "L4-L23", "xdg-output-unstable-v1": "L5-L24",
    "xdg-shell": "L5-L29", "xdg-toplevel-icon-v1": "L5-L25",
}
# The source of the parts under the LGPL, which HEADER gives
SOURCES = {
    f"pygame-ce {PYGAME_CE}": "https://files.pythonhosted.org/packages/source/p/"
                              f"pygame_ce/pygame_ce-{PYGAME_CE}.tar.gz",
    "mpg123 1.33.7": "https://downloads.sourceforge.net/sourceforge/mpg123/"
                     "mpg123-1.33.7.tar.bz2",
    "FluidSynth 2.5.7": "https://github.com/FluidSynth/fluidsynth/archive/refs/"
                        "tags/v2.5.7.tar.gz",
    "libsndfile 1.2.2": "https://github.com/libsndfile/libsndfile/releases/"
                        "download/1.2.2/libsndfile-1.2.2.tar.xz",
}
# pygame-ce's folders for its libraries on Linux, Windows and macOS. Another
# package's copy of one, or the build machine's own, is not pygame-ce's, so
# it is left over
PYGAME_LIBS = ("pygame_ce.libs/", "pygame/", "pygame/.dylibs/")

def in_pygame(*names: str) -> tuple[str, ...]:
    """
    Gives patterns for libraries that come with pygame-ce.

    Args:
        names: The libraries' names, as patterns

    Returns: Each name in each of PYGAME_LIBS, and as a DLL at the top,
        where the Windows apps also hold them. On Linux and macOS what is at
        the top is a symlink, which bundled leaves out
    """
    return tuple(pattern for name in names for pattern in (
        *(folder + name for folder in PYGAME_LIBS),
        name if name.endswith(".dll") else f"{name}.dll"))

@dataclass(frozen=True)
class Dependency:
    """
    One project the apps bundle.

    Attributes:
        name: The project's name
        licence: Its licence, as an SPDX identifier where one exists
        website: Where its source is published
        where: Where it is in the apps, for the reader
        texts: URLs of its licence texts, pinned to the versions bundled. A
            URL ending in #L<a>-L<b> gives lines a to b of the file, for a
            notice inside a source file. A URL ending in another #NAME is a
            tarball's, and the text is the file NAME in its top folder.
        files: What it is in the apps, as patterns for PurePosixPath's
            full_match: * stays within one folder and ** spans any. A Python
            package or module with no files of its own is its bare name.
    """
    name: str
    licence: str
    website: str
    where: str
    texts: tuple[str, ...]
    files: tuple[str, ...] = ()

DEPENDENCIES = [
    Dependency(
        "Python", "PSF-2.0 AND MIT AND HPND", "https://www.python.org/",
        f"All apps, version {PYTHON}. The licence page below also covers the "
        "code Python holds, such as libmpdec on Linux and mimalloc. Then come "
        "the licence of the expat 2.9.0 in the macOS apps, and the notices of "
        "Python's files by other holders: tarfile, logging, platform, the "
        "Unicode object, getopt, the locale module and, on Windows, _winapi. "
        "The libraries it is built with have their own entries.",
        tuple(f"{GH}/python/cpython/v{PYTHON}/{name}" for name in [
            "Doc/license.rst", "Modules/expat/COPYING", "Lib/tarfile.py#L4-L26",
            "Lib/logging/__init__.py#L1-L15", "Lib/platform.py#L93-L109",
            "Objects/unicodeobject.c#L14-L36", "Python/getopt.c#L6-L20",
            "Modules/_localemodule.c#L2-L8", "Modules/_winapi.c#L7-L30"]),
        ("base_library.zip", "libpython3*", "python3*.dll",
         # Only the standard library's: a package's own is not Python's
         *(f"{module}.*pyd" for module in sorted(sys.stdlib_module_names)),
         "python3.*/lib-dynload/*", "Python.framework/Versions/3.*/Python",
         "Python.framework/Versions/3.*/Resources/Info.plist", "_sysconfigdata_*")),
    Dependency(
        "HACL*", "MIT", "https://github.com/hacl-star/hacl-star",
        "All apps, built into Python's hash modules.",
        (f"{GH}/hacl-star/hacl-star/8ba599b2f6c9701b3dc961db895b0856a2210f76"
         "/dist/LICENSE.txt",)),
    Dependency(
        "OpenSSL", "Apache-2.0", "https://www.openssl.org/",
        "All apps: 3.0.2 on Linux, and 3.5.9 on Windows and macOS.",
        (f"{GH}/openssl/openssl/openssl-3.0.2/LICENSE.txt",
         f"{GH}/openssl/openssl/openssl-3.5.9/LICENSE.txt"),
        ("libssl*", "libcrypto*")),
    Dependency(
        "zlib", "Zlib", "https://zlib.net/",
        "The Linux apps (1.2.11). On Windows it is built into the apps' "
        "loader (1.3.2) and libpng16-16.dll (1.3.1), and into freetype.dll "
        "(1.1.4) and SDL2_ttf.dll (1.3) as FreeType's own copies. Its notice "
        "ends each README below.",
        tuple(f"{GH}/madler/zlib/v{version}/README"
              for version in ["1.2.11", "1.3.2", "1.3.1", "1.1.4", "1.3"]),
        ("libz.so*",)),
    Dependency(
        "libffi", "MIT", "https://sourceware.org/libffi/",
        "The Linux apps (3.4.2) and the Windows apps (3.4.4).",
        (f"{GH}/libffi/libffi/v3.4.2/LICENSE",
         f"{GH}/libffi/libffi/v3.4.4/LICENSE"),
        ("libffi*",)),
    Dependency(
        "mpdecimal", "BSD-2-Clause", "https://www.bytereef.org/mpdecimal/",
        "Built into Python's _decimal module: 4.0.0 on Windows and 4.0.1 on "
        "macOS. On Linux, _decimal uses Python's own copy.",
        (f"{GH}/python/cpython-source-deps/mpdecimal-4.0.0/COPYRIGHT.txt",
         "https://www.bytereef.org/software/mpdecimal/releases/"
         "mpdecimal-4.0.1.tar.gz#COPYRIGHT.txt")),
    Dependency(
        "bzip2", "bzip2-1.0.6", "https://sourceware.org/bzip2/",
        "The Linux apps, and built into Python's _bz2 module on Windows; "
        "1.0.8 on both.",
        ("https://sourceware.org/git/?p=bzip2.git;a=blob_plain;f=LICENSE;"
         "hb=bzip2-1.0.8",),
        ("libbz2*",)),
    Dependency(
        "XZ Utils (liblzma)", "public domain", "https://tukaani.org/xz/",
        "The Linux apps (5.2.5), and built into Python's _lzma module on "
        "Windows (5.2.5) and macOS (5.2.3).",
        (f"{GH}/tukaani-project/xz/v5.2.5/COPYING",
         f"{GH}/tukaani-project/xz/v5.2.3/COPYING"),
        ("liblzma*",)),
    Dependency(
        "Zstandard", "BSD-3-Clause AND MIT AND BSD-2-Clause",
        "https://facebook.github.io/zstd/",
        "The Linux apps (1.4.8) and the macOS apps (1.5.7), and built into "
        "Python's _zstd module on Windows (1.5.7). After the licences come "
        "the notices of code in it by other holders: Yuta Mori's divsufsort; "
        "the legacy format decoders, in 1.5.7 then 1.4.8, on Linux and macOS "
        "only; and Tino Reichardt's threading code, on Windows, under the "
        "licence above.",
        (f"{GH}/facebook/zstd/v1.4.8/LICENSE",
         f"{GH}/facebook/zstd/v1.5.7/LICENSE",
         f"{GH}/facebook/zstd/v1.5.7/lib/dictBuilder/divsufsort.c#L3-L24",
         f"{GH}/facebook/zstd/v1.5.7/lib/legacy/zstd_v05.c#L621-L646",
         f"{GH}/facebook/zstd/v1.4.8/lib/legacy/zstd_v05.c#L676-L701",
         f"{GH}/facebook/zstd/v1.5.7/lib/common/threading.c#L2-L3"),
        ("libzstd*",)),
    Dependency(
        "libuuid (util-linux)", "BSD-3-Clause",
        "https://github.com/util-linux/util-linux",
        "The Linux apps. Copyright (C) 1996, 1997, 1998, 1999 Theodore Ts'o. "
        "The last text is the notice of Philip Prindeville's predefined.c.",
        (f"{GH}/util-linux/util-linux/v2.37.2/libuuid/COPYING",
         f"{GH}/util-linux/util-linux/v2.37.2/Documentation/licenses"
         "/COPYING.BSD-3-Clause",
         f"{GH}/util-linux/util-linux/v2.37.2/libuuid/src/predefined.c#L4-L31"),
        ("libuuid*",)),
    Dependency(
        "GCC runtime libraries", "GPL-3.0-or-later WITH GCC-exception-3.1 AND "
        "GPL-2.0-or-later WITH GCC-exception-2.0 AND LGPL-2.1-or-later AND MIT "
        "AND HPND-sell-variant", "https://gcc.gnu.org/",
        "The Linux window app: libstdc++ and libgcc_s from GCC 12. The "
        "runtime library exception, first, adds to the GPL that follows it, "
        "and libgcc_s's soft-float code is under the LGPL after that. Then "
        "come the notices of code in libstdc++ by other holders: fast_float, "
        "and Hewlett-Packard's and Silicon Graphics' STL. Last is the notice "
        "of its demangler, from GCC's libiberty: the GPL, version 2 or later, "
        "with an exception of its own.",
        tuple(f"{GH}/gcc-mirror/gcc/releases/gcc-12.3.0/{name}" for name in [
            "COPYING.RUNTIME", "COPYING3", "COPYING.LIB",
            "libstdc++-v3/src/c++17/fast_float/fast_float.h#L15-L39",
            "libstdc++-v3/src/c++98/tree.cc#L27-L48",
            "libstdc++-v3/src/c++98/strstream.cc#L26-L35",
            "libiberty/cp-demangle.c#L2-L28"]),
        ("libgcc_s.so*", "libstdc++.so*")),
    Dependency(
        "Microsoft C runtime", "Microsoft distributable code",
        "https://visualstudio.microsoft.com/", "The Windows apps.",
        (f"{GH}/python/cpython/v{PYTHON}/PC/crtlicense.txt",),
        ("VCRUNTIME140*.dll", "ucrtbase.dll", "api-ms-win-*.dll")),
    Dependency(
        "PyInstaller", "GPL-2.0-or-later WITH Bootloader-exception AND Apache-2.0",
        "https://pyinstaller.org/",
        f"All apps, version {VERSIONS['PyInstaller']}: its loader, which the "
        "bootloader exception lets the apps bundle, and its run-time hooks, "
        "which are under the Apache License 2.0 at the end of the text below.",
        (f"{GH}/pyinstaller/pyinstaller/v{VERSIONS['PyInstaller']}/COPYING.txt",),
        ("pyiboot01_bootstrap", "pyimod0*", "pyi_rth_*")),
    Dependency(
        "pygame-ce", "LGPL-2.1-or-later", "https://pyga.me/",
        f"The window apps, version {PYGAME_CE}. After the LGPL come the "
        "licences pygame-ce gives for code in its own modules: SDL_gfx, "
        "sse2neon and NumPy, then the notice of Donald W. Gillies' bit "
        "count, which its Windows mask module holds.",
        (f"{PG}/LGPL.txt", f"{PG}/licenses/LICENSE.sdl_gfx.txt",
         f"{PG}/licenses/LICENSE.sse2neon-h.txt",
         f"{PG}/licenses/LICENSE.numpy.txt",
         f"{GH}/pygame-community/pygame-ce/{PYGAME_CE}/src_c/bitmask.c#L44-L46"),
        ("pygame", "pygame/*.cpython-*.so", "pygame/*.pyd",
         "pygame/_sdl2/*.cpython-*.so", "pygame/_sdl2/*.pyd",
         "pygame/pygame_icon*.bmp")),
    Dependency(
        "SDL2", "Zlib AND BSD-3-Clause AND MIT", "https://www.libsdl.org/",
        "The window apps. After its licence come the notices of code it is "
        "built with: HIDAPI, yuv2rgb and Sun's math code, then on Linux "
        "edid-parse.c, imKStoUCS.c, the Wayland protocols, and Qt's touch, "
        "surface and window manager protocols, which its Qt touch code is "
        "generated from and which share the last text.",
        (f"{SDL}/LICENSE.txt", f"{SDL}/src/hidapi/LICENSE-orig.txt",
         f"{SDL}/src/video/yuv2rgb/LICENSE", f"{SDL}/src/libm/e_atan2.c#L3-L8",
         f"{SDL}/src/video/x11/edid-parse.c#L2-L20",
         f"{SDL}/src/events/imKStoUCS.c#L2-L24",
         *(f"{SDL}/wayland-protocols/{name}.xml#{lines}"
           for name, lines in WAYLAND.items()),
         f"{GH}/qt/qtwayland/v5.4.0/src/extensions/touch-extension.xml#L4-L36"),
        in_pygame("libSDL2-2*", "SDL2.dll")),
    Dependency(
        "SDL2_image", "Zlib AND HPND", "https://github.com/libsdl-org/SDL_image",
        "The window apps. It holds QOI, below, and after its licence come "
        "the notices of nanosvg and of its GIF code, from XPaint.",
        (f"{SDL_IMAGE}/LICENSE.txt", f"{SDL_IMAGE}/src/nanosvg.h#L2-L25",
         f"{SDL_IMAGE}/src/IMG_gif.c#L30-L37"),
        in_pygame("libSDL2_image*", "SDL2_image.dll")),
    Dependency(
        "QOI", "MIT", "https://github.com/phoboslab/qoi",
        "The window apps, built into SDL2_image. The text is the notice in "
        "the qoi.h it is built from.",
        (f"{SDL_IMAGE}/src/qoi.h#L10-L27",)),
    Dependency(
        "SDL2_mixer", "Zlib", "https://github.com/libsdl-org/SDL_mixer",
        "The window apps. It holds Timidity, whose licence is the second "
        "text below, and on Windows also minimp3 (CC0), dr_flac (public "
        "domain or MIT-0) and stb_vorbis (public domain).",
        (f"{GH}/libsdl-org/SDL_mixer/release-2.8.2/LICENSE.txt",
         f"{GH}/libsdl-org/SDL_mixer/release-2.8.2/src/codecs/timidity/COPYING"),
        in_pygame("libSDL2_mixer*", "SDL2_mixer.dll")),
    Dependency(
        "SDL2_ttf", "Zlib", "https://github.com/libsdl-org/SDL_ttf",
        "The window apps. On Windows it holds FreeType 2.13.2 and HarfBuzz "
        "8.1.1, below.",
        (f"{GH}/libsdl-org/SDL_ttf/release-2.24.0/LICENSE.txt",),
        in_pygame("libSDL2_ttf*", "SDL2_ttf.dll")),
    Dependency(
        "FreeType", "FTL AND MIT AND MIT-open-group", "https://freetype.org/",
        "The window apps: 2.14.3 on Linux and macOS, and on Windows 2.11.1 "
        "as freetype.dll and 2.13.2 in SDL2_ttf.dll. Portions of this "
        "software are copyright © 2021, 2023 and 2026 The FreeType Project "
        "(www.freetype.org). All rights reserved. For each version, after "
        "the FTL come the licences of its BDF and PCF font drivers, then the "
        "notices of its pcfutil.c and fthash.c.",
        tuple(f"{FT}/{tag}/{name}"
              for tag, bdf in [("VER-2-14-3", "L99-L144"),
                               ("VER-2-13-2", "L99-L144"),
                               ("VER-2-11-1", "L95-L140")]
              for name in ["LICENSE.TXT", "docs/FTL.TXT", f"src/bdf/README#{bdf}",
                           "src/pcf/README#L66-L88", "src/pcf/pcfutil.c#L3-L23",
                           "src/base/fthash.c#L10-L30"]),
        in_pygame("libfreetype*", "freetype.dll")),
    Dependency(
        "HarfBuzz", "MIT-Modern-Variant AND MIT AND ISC AND Unicode-3.0 AND "
        "Unicode-DFS-2016", "https://harfbuzz.github.io/",
        "The window apps: 14.3.0 on Linux and macOS, and 8.1.1 in "
        "SDL2_ttf.dll on Windows, whose COPYING is the same. Its Microsoft "
        "USE data has the second licence. Then come, for each version, the "
        "notices of its fasthash, hb-ucd.cc and BASE table code, whose "
        "holders COPYING does not name, and last the licences of its Unicode "
        "data: Unicode-3.0 for 14.3.0, and Unicode-DFS-2016 for 8.1.1.",
        (f"{GH}/harfbuzz/harfbuzz/14.3.0/COPYING",
         f"{GH}/harfbuzz/harfbuzz/14.3.0/src/ms-use/COPYING",
         *(f"{GH}/harfbuzz/harfbuzz/{tag}/src/{name}"
           for tag, algs in [("14.3.0", "L423-L443"), ("8.1.1", "L259-L279")]
           for name in [f"hb-algs.hh#{algs}", "hb-ucd.cc#L2-L14",
                        "hb-ot-layout-base-table.hh#L2-L24"]),
         f"{GH}/unicode-org/icu/release-78.1/LICENSE#L1-L39",
         f"{GH}/unicode-org/icu/release-72-1/icu4c/LICENSE#L1-L46"),
        # Not libharfbuzz-subset, which holds another notice
        in_pygame("libharfbuzz.*", "libharfbuzz-????????.so*")),
    Dependency(
        "Brotli", "MIT", "https://github.com/google/brotli",
        "The Linux and macOS window apps, version 1.2.0.",
        (f"{GH}/google/brotli/v1.2.0/LICENSE",),
        in_pygame("libbrotli*")),
    Dependency(
        "libjpeg-turbo", "IJG AND BSD-3-Clause AND Zlib",
        "https://libjpeg-turbo.org/",
        "The window apps, version 3.1.4.1. This software is based in part on "
        "the work of the Independent JPEG Group.",
        (f"{GH}/libjpeg-turbo/libjpeg-turbo/3.1.4.1/LICENSE.md",
         f"{GH}/libjpeg-turbo/libjpeg-turbo/3.1.4.1/README.ijg"),
        in_pygame("libjpeg*")),
    Dependency(
        "MinGW-w64 winpthreads", "MIT AND BSD-3-Clause", "https://www.mingw-w64.org/",
        "The Windows window app, built into libjpeg-62.dll with MinGW-w64 v5, "
        "whose text below is the same in each v5 release.",
        (f"{GH}/mirror/mingw-w64/v5.0.4/mingw-w64-libraries/winpthreads/COPYING",)),
    Dependency(
        "libpng", "libpng-2.0", "http://www.libpng.org/pub/png/libpng.html",
        "The window apps, version 1.6.58.",
        (f"{GH}/pnggroup/libpng/v1.6.58/LICENSE",),
        in_pygame("libpng*")),
    Dependency(
        "LibTIFF", "libtiff AND MIT", "https://libtiff.gitlab.io/libtiff/",
        "The window apps: 4.7.2 on Linux and macOS, and 4.2.0 on Windows. "
        "Then come the notices of its files by other holders: LogLuv, in "
        "both versions, and PixarLog, old-style JPEG and the hash set, in "
        "4.7.2.",
        ("https://gitlab.com/libtiff/libtiff/-/raw/v4.7.2/LICENSE.md",
         "https://gitlab.com/libtiff/libtiff/-/raw/v4.2.0/COPYRIGHT",
         *(f"https://gitlab.com/libtiff/libtiff/-/raw/v4.7.2/libtiff/{name}"
           for name in ["tif_luv.c#L2-L22", "tif_pixarlog.c#L2-L22",
                        "tif_ojpeg.c#L26-L37", "tif_hash_set.c#L8-L26"])),
        in_pygame("libtiff*")),
    Dependency(
        "libwebp", "BSD-3-Clause", "https://chromium.googlesource.com/webm/libwebp",
        "The window apps, with its libsharpyuv and libwebpdemux: 1.6.0 on "
        "Linux and macOS, and 1.0.3 on Windows.",
        (f"{GH}/webmproject/libwebp/v1.6.0/COPYING",
         f"{GH}/webmproject/libwebp/v1.0.3/COPYING"),
        in_pygame("libwebp*", "libsharpyuv*")),
    Dependency(
        "Ogg and Vorbis", "BSD-3-Clause AND TU-Berlin-1.0", "https://xiph.org/",
        "The window apps: Ogg 1.3.6 and Vorbis 1.3.7 on Linux and macOS, "
        "and Ogg 1.3.5 on Windows. Vorbis's LPC code has the TU Berlin "
        "notice that is the last text.",
        (f"{GH}/xiph/ogg/v1.3.6/COPYING", f"{GH}/xiph/vorbis/v1.3.7/COPYING",
         f"{GH}/xiph/ogg/v1.3.5/COPYING", f"{GH}/xiph/vorbis/v1.3.7/lib/lpc.c#L25-L41"),
        in_pygame("libogg*", "libvorbis*")),
    Dependency(
        "Opus and opusfile", "BSD-3-Clause", "https://opus-codec.org/",
        "The window apps: Opus 1.6.1 and opusfile 0.12 on Linux and macOS, "
        "and on Windows opusfile 0.13 and an Opus 14 commits past 1.4 "
        "(it reports 1.4-14-ge6fd7f5-dirty, so its build tree had changes), "
        "with 1.4's COPYING. The fourth text is the "
        "one SDL2_mixer ships opusfile 0.13 with. The rest are the notices of "
        "Opus files whose holders its COPYING does not name: Google, Koen Vos "
        "and Vidyo on every OS, Cisco and John Ridges on Linux and Windows, "
        "and Arm in 1.6.1.",
        (f"{GH}/xiph/opus/v1.6.1/COPYING", f"{GH}/xiph/opusfile/v0.12/COPYING",
         f"{GH}/xiph/opus/v1.4/COPYING",
         f"{GH}/libsdl-org/SDL_mixer/release-2.8.2/VisualC/external/optional"
         "/x64/LICENSE.opusfile.txt",
         *(f"{GH}/xiph/opus/v1.6.1/{name}" for name in [
             "src/mapping_matrix.c#L1-L25", "silk/LPC_fit.c#L2-L25",
             "silk/NSQ.h#L2-L26", "silk/x86/NSQ_sse4_1.c#L1-L25",
             "celt/x86/pitch_sse.h#L1-L30", "src/opus.c#L1-L26"])),
        in_pygame("libopus*")),
    Dependency(
        "FLAC", "BSD-3-Clause", "https://xiph.org/flac/",
        "The Linux and macOS window apps, version 1.5.0.",
        (f"{GH}/xiph/flac/1.5.0/COPYING.Xiph",),
        in_pygame("libFLAC*")),
    Dependency(
        "mpg123", "LGPL-2.1-only", "https://www.mpg123.de/",
        "The Linux and macOS window apps, version 1.33.7.",
        (f"{SOURCES['mpg123 1.33.7']}#COPYING",),
        in_pygame("libmpg123*")),
    Dependency(
        "FluidSynth", "LGPL-2.1-or-later", "https://www.fluidsynth.org/",
        "The Linux and macOS window apps, version 2.5.7.",
        (f"{GH}/FluidSynth/fluidsynth/v2.5.7/LICENSE",),
        in_pygame("libfluidsynth*")),
    Dependency(
        "libsndfile", "LGPL-2.1-or-later AND TU-Berlin-1.0 AND Apache-2.0",
        "https://libsndfile.github.io/libsndfile/",
        "The Linux and macOS window apps, version 1.2.2. It holds GSM 06.10, "
        "whose notice is the second text, and Apple's ALAC, whose notice is "
        "the third, under the Apache License 2.0 that is the last.",
        (f"{GH}/libsndfile/libsndfile/1.2.2/COPYING",
         f"{GH}/libsndfile/libsndfile/1.2.2/src/GSM610/COPYRIGHT",
         f"{GH}/libsndfile/libsndfile/1.2.2/src/ALAC/alac_decoder.c#L2-L19",
         f"{GH}/openssl/openssl/openssl-3.0.2/LICENSE.txt"),
        in_pygame("libsndfile*")),
    Dependency(
        "WavPack", "BSD-3-Clause", "https://www.wavpack.com/",
        "The window apps: 5.9.0 on Linux and macOS, and 5.6.0 on Windows, "
        "which also holds LoRd_MuldeR's Unicode file name code, whose notice "
        "is the last text.",
        (f"{GH}/dbry/WavPack/5.9.0/COPYING", f"{GH}/dbry/WavPack/5.6.0/COPYING",
         f"{GH}/dbry/WavPack/5.6.0/cli/win32_unicode_support.c#L1-L28"),
        in_pygame("libwavpack*")),
    Dependency(
        "libxmp", "MIT AND ISC", "https://xmp.sourceforge.net/",
        "The window apps: 4.7.2 on Linux and macOS, and 4.6.3 on Windows. "
        "After each version's licence come the notices of code in it by "
        "other authors: in 4.7.2, ProWizard, lhasa, miniz, and Alice Rowan's "
        "and Stephen J Leary's code; in 4.6.3, built without ProWizard and "
        "the depackers, miniz, Alice Rowan's and Stephen J Leary's.",
        (*(f"{GH}/libxmp/libxmp/libxmp-4.7.2/{name}" for name in [
            "docs/COPYING", "src/loaders/prowizard/LICENSE.txt",
            "docs/CREDITS#L200-L214", "src/depackers/miniz_zip.c#L3-L24",
            "src/depackers/arc.c#L2-L20", "src/loaders/abk_load.c#L3-L21"]),
         *(f"{GH}/libxmp/libxmp/libxmp-4.6.3/{name}" for name in [
             "docs/COPYING", "src/miniz_tinfl.c#L3-L23", "src/loaders/lzw.c#L2-L20",
             "src/loaders/xmf_load.c#L2-L20", "src/loaders/abk_load.c#L3-L21"])),
        in_pygame("libxmp*")),
    Dependency(
        "PortMidi", "MIT", "https://github.com/PortMidi/portmidi",
        "The Windows window app, from a build before 2.0. The licence text "
        "has not changed since 2021.",
        (f"{GH}/PortMidi/portmidi/v2.0.7/license.txt",),
        in_pygame("portmidi.dll")),
    Dependency(
        "zlib-ng", "Zlib", "https://github.com/zlib-ng/zlib-ng",
        "The macOS window app (2.3.3), and built into python314.dll on "
        "Windows (2.2.4), whose texts are the same.",
        (f"{GH}/zlib-ng/zlib-ng/2.3.3/LICENSE.md",),
        in_pygame("libz.*zlib-ng*")),
    Dependency(
        "FreeSans font", "GPL", "https://savannah.gnu.org/projects/freefont/",
        "The window apps' text, as pygame/freesansbold.ttf. Copyright 2002 "
        "Free Software Foundation. Its licence names the GNU General Public "
        "License with no version, and version 3 follows. Its source is the "
        "font file itself, also at src_py/freesansbold.ttf in pygame-ce's "
        "source (see Source code, above), which a font editor such as "
        "FontForge opens. GNU FreeFont's editable sources, from 2005 on, "
        "are at https://download.savannah.gnu.org/releases/freefont/.",
        (f"{GH}/gcc-mirror/gcc/releases/gcc-12.3.0/COPYING3",),
        ("pygame/freesansbold.ttf",)),
    Dependency(
        "click", "BSD-3-Clause", "https://palletsprojects.com/p/click/",
        f"All apps, version {VERSIONS['click']}. Its parser holds code from "
        "Python's optparse, whose notice is the second text.",
        (f"{GH}/pallets/click/{VERSIONS['click']}/LICENSE.txt",
         f"{GH}/python/cpython/v{PYTHON}/Lib/optparse.py#L38-L66"),
        ("click", "click-*.dist-info/**")),
    Dependency(
        "colorama", "BSD-3-Clause", "https://github.com/tartley/colorama",
        f"All apps, version {VERSIONS['colorama']}.",
        (f"{GH}/tartley/colorama/{VERSIONS['colorama']}/LICENSE.txt",),
        ("colorama",)),
]

LGPL_SOURCES = "\n".join(f"- {name}:\n  {url}" for name, url in SOURCES.items())
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

Each project below publishes its source at its website. The window apps
bundle these parts under the GNU LGPL (mpg123, FluidSynth and libsndfile on
Linux and macOS only), and this is their source:

{LGPL_SOURCES}

pygame-ce's build scripts name the version of each library it ships with:
https://github.com/pygame-community/pygame-ce/tree/{PYGAME_CE}/buildconfig

To run Go Python with a changed pygame-ce or LGPL library, build pygame-ce
with your library, then either:

- install Go Python from its wheel or sdist with pip, as README.md shows,
  and install your pygame-ce into the same environment; or
- rebuild the apps: in Go Python's source at the release's tag, from
  https://github.com/JakeBrxwn/go-game-python, run pip install ".[release]",
  install your pygame-ce over the one it installed, and run
  python scripts/freeze.py. The apps it writes to dist/ use your version.
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
        url: Where it is: a file, a file's URL ending in #L<a>-L<b> for its
            lines a to b, or a tarball's URL ending in #NAME for the file NAME
            in the tarball's top folder

    Returns: The text, without trailing whitespace on any line, and without
        the indent its lines share if it is a range of lines

    Raises:
        ValueError: If the URL gave a web page, not a text, or its range
            runs backwards or past the file's end
        KeyError: If the tarball has no such file
    """
    address, _, name = url.partition("#")
    lines = re.fullmatch(r"L(\d+)-L(\d+)", name)
    request = urllib.request.Request(address, headers={"User-Agent": "go-python"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data: bytes = response.read()
    if name and not lines:
        with tarfile.open(fileobj=io.BytesIO(data)) as tarball:
            top = tarball.getnames()[0].split("/")[0]
            file = tarball.extractfile(f"{top}/{name}")
            if file is None:
                raise ValueError(f"{url} is not a file")
            data = file.read()
    text = data.decode("utf-8")
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError(f"{url} gave a web page")
    if lines:
        first, last = int(lines[1]), int(lines[2])
        if not 0 < first <= last:
            raise ValueError(f"{url} is not a range of lines")
        # bytes split only at line ends, as GitHub numbers lines; str also
        # splits at form feeds
        chunk = data.splitlines()[first - 1:last]
        if len(chunk) != last - first + 1:
            raise ValueError(f"{url} has fewer lines than that")
        text = textwrap.dedent(b"\n".join(chunk).decode("utf-8"))
    return "\n".join(line.rstrip() for line in text.splitlines()).strip("\n")

def digest(text: str) -> str:
    """
    Hashes the file's text.

    Args:
        text: The text, with newlines as \\n

    Returns: Its SHA-256, in hex
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write() -> str:
    """
    Fetches every licence text and rewrites THIRD_PARTY_LICENSES.txt.

    Returns: The file's digest, for DIGEST
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
    text = "".join(parts)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    return digest(text)

def stale() -> bool:
    """
    Tells whether THIRD_PARTY_LICENSES.txt is out of date: its digest is not
    DIGEST, or its header and entry heads are not exactly the script's, in
    order.

    Returns: True if it is out of date
    """
    # Read as text, so a checkout with \r\n line ends hashes the same
    text = OUTPUT.read_text(encoding="utf-8")
    # A head is a rule, "name | licence", its website and the lines up to
    # the next rule; a text may hold a rule of its own
    heads = re.findall(f"\n({RULE}\n.+ \\| .+\nWebsite: (?:.+\n)+?{RULE}\n)", text)
    return (digest(text) != DIGEST
            or not text.startswith(f"{HEADER}\n{RULE}\n")
            or heads != [entry_head(dependency) for dependency in DEPENDENCIES])

def bundled(app: str) -> list[str]:
    """
    Lists what a PyInstaller one-file app holds besides the standard library
    and Go Python: its files, with / between folders, but not its symlinks,
    its modules and scripts, such as PyInstaller's loader and run-time hooks,
    and the top-level packages of its Python modules.

    Args:
        app: The app's path

    Returns: The names
    """
    # Imported here so the tests run without PyInstaller
    from PyInstaller.archive.readers import CArchiveReader

    own = {*sys.stdlib_module_names, *APPS, "go_python"}
    reader = CArchiveReader(app)
    names = []
    for name, entry in reader.toc.items():
        kind = entry[-1]
        # A symlink holds nothing of its own: PyInstaller makes one only to a
        # file it also holds
        if kind == "n":
            continue
        if kind == "z":
            modules = reader.open_embedded_archive(name).toc
            names += sorted({module.split(".")[0] for module in modules} - own)
        # Not the standard library's or the app's own modules and scripts
        elif not (kind in "mMs" and name.split(".")[0] in own):
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

def installed(name: str) -> str:
    """
    Finds the version of a project in VERSIONS that this Python has.

    Args:
        name: The project

    Returns: Its version
    """
    if name == "Python":
        return platform.python_version()
    return importlib.metadata.version(name)

def check(apps: list[str]) -> None:
    """
    Checks THIRD_PARTY_LICENSES.txt covers the apps, exiting on a problem.

    Args:
        apps: The apps' paths, or none for the two freeze.py built
    """
    if stale():
        sys.exit(f"FAIL {OUTPUT.name} is out of date: run "
                 "python scripts/third_party_licenses.py write")
    for name, version in VERSIONS.items():
        if installed(name) != version:
            sys.exit(f"FAIL {name} is {installed(name)}, but {OUTPUT.name} is "
                     f"for {version}: see this script's docstring")
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
        print(f'Wrote {OUTPUT.name}: set DIGEST = "{write()}"')
    elif sys.argv[1:2] == ["check"]:
        check(sys.argv[2:])
    else:
        sys.exit(__doc__)

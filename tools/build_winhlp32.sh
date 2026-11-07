#!/bin/sh
# Builds Wine 6.0's WinHelp (winhlp32.exe.so) with data/wine-6.0-winhlp32-popup.patch, which adds
# the popups Wine never implemented for WinHelp(HELP_CONTEXTPOPUP): the "?" buttons in Kaiser's
# dialogs. Same Wine version as Boxedwine's image; only WinHelp is built, not all of Wine.
#
# Needs Linux with a 32-bit C compiler, flex and bison (Debian/Ubuntu: gcc-multilib flex bison).
# Usage: tools/build_winhlp32.sh OUTPUT [WORKDIR]
set -eu

out=$(realpath -m "$1")
work=$(realpath -m "${2:-${TMPDIR:-/tmp}/kaiser-winhlp32}")
here=$(cd "$(dirname "$0")/.." && pwd)
patch_file="$here/data/wine-6.0-winhlp32-popup.patch"
url=https://dl.winehq.org/wine/source/6.0/wine-6.0.tar.xz
sha=b493065f2f83ee429c62e2ec58698a3cf63ef78722e1b20765823152e8582c56

mkdir -p "$work"
cd "$work"
if ! echo "$sha  wine-6.0.tar.xz" | sha256sum -c --status 2>/dev/null; then
    curl -fsSL --retry 4 -o wine-6.0.tar.xz "$url"
    echo "$sha  wine-6.0.tar.xz" | sha256sum -c --quiet
fi
rm -rf wine-6.0
tar xf wine-6.0.tar.xz
cd wine-6.0
patch -p1 --quiet < "$patch_file"

# WinHelp as an ELF module like the rest of Boxedwine's Wine (no MinGW, so no PE build)
./configure -q --disable-tests --without-x --without-freetype --without-mingw \
    CFLAGS="-O2 -fno-stack-protector -fcommon" > ../configure.log 2>&1 \
    || { tail -30 ../configure.log; exit 1; }
make -j"$(nproc)" __tooldeps__ > ../tools.log 2>&1 || { tail -30 ../tools.log; exit 1; }
make -j"$(nproc)" -C programs/winhlp32 > ../winhlp32.log 2>&1 || { tail -30 ../winhlp32.log; exit 1; }

mkdir -p "$(dirname "$out")"
strip -o "$out" programs/winhlp32/winhlp32.exe.so
echo "built $out"

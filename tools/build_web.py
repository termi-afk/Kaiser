"""Builds the browser version of Kaiser (GitHub Pages) into build/site.

Kaiser 1.22a and 1.23 run unchanged (the original 16-bit Windows programs) in Boxedwine, Wine
compiled to WebAssembly. Like build.ps1, nothing of the game is stored in the repository: every
input is downloaded and checked against its SHA-256.

    python tools/build_web.py [site-dir]
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
BUILD = os.path.join(ROOT, "build", "web")
SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "build", "site")
DATA = os.path.join(ROOT, "data")
TOOLS = os.path.join(ROOT, "tools")

SOURCES = {
    "k122": ("https://web.archive.org/web/20050119184711id_/http://yadam.de:80/KAISER/Kai122a.zip",
             "Kai122a.zip", "b57fd65bf067f3a79542e18b8e4e857db09217adcffe75ebfc48fea88e15ff4c"),
    "k123": ("https://github.com/LarsGehrmann/Kaiser-decompile/releases/download/v1.0.2/Kaiser-Classic-1.0.2-Windows-x64.zip",
             "Kaiser-Classic-1.0.2-Windows-x64.zip", "baaf6f214a2477686b6b7c13be3fb42708b54ba1a6b0502b764fe8063c812e9f"),
    # Boxedwine 26R1 web build (Emscripten) with its stripped-down Wine 6.0 file system
    "boxedwine": ("https://github.com/danoon2/Boxedwine/releases/download/26R1.0/Boxedwine26R1Web.zip",
                  "Boxedwine26R1Web.zip", "ebc634e921f7c65980a7094f3efad84873cede8011eb7dd204446ff1de982945"),
    # the full Wine 6.0 file system of the same Boxedwine build: WinHelp is missing from the web one
    "wine6": ("https://boxedwine.org/v2/2/TinyCore15Wine6.0.zip",
              "TinyCore15Wine6.0.zip", "ef1aa2e7d350751e2b324a9aa27beb3c22c82a6207b1a02fa18dbb7ba5551efe"),
    # General-MIDI synthesizer for the music: Boxedwine has no MIDI output in the browser
    "tinysynth": ("https://registry.npmjs.org/webaudio-tinysynth/-/webaudio-tinysynth-1.1.3.tgz",
                  "webaudio-tinysynth-1.1.3.tgz", "e9f154131b55cadda7a5919ef8a88f2a53be189448d45e7de897dd4992095e47"),
}

WINHELP = ["opt/wine/lib/wine/winhlp32.exe.so", "opt/wine/lib/wine/winhelp.exe16.so",
           "opt/wine/lib/wine/fakedlls/winhlp32.exe", "opt/wine/lib/wine/fakedlls/winhelp.exe16"]
WINE_C = "home/username/.wine/drive_c"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get(key):
    url, name, digest = SOURCES[key]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path) or sha256(path) != digest:
        for attempt in range(1, 5):
            print("download", url, flush=True)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "kaiser-web-build"})
                with urllib.request.urlopen(req, timeout=300) as r, open(path + ".part", "wb") as f:
                    shutil.copyfileobj(r, f)
                os.replace(path + ".part", path)
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(5 * attempt)
    got = sha256(path)
    if got != digest:
        sys.exit(f"SHA-256 mismatch for {name}: {got}")
    return path


def member(z, name):
    """Zip member by case-insensitive name (the 1.22a archive is from a DOS world)."""
    for n in z.namelist():
        if n.lower() == name.lower():
            return n
    raise KeyError(name)


def write_zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in entries:
            z.writestr(arc, data)


def main():
    shutil.rmtree(SITE, ignore_errors=True)
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(SITE)
    os.makedirs(BUILD)

    # --- Boxedwine (single-threaded build: GitHub Pages cannot send the COOP/COEP headers the
    #     multi-threaded one needs, and its audio does not work from a worker thread anyway)
    with zipfile.ZipFile(get("boxedwine")) as z:
        for f in ["boxedwine-shell.js", "boxedwine.js", "boxedwine.wasm", "boxedwine.zip"]:
            data = z.read("SingleThreaded/" + f)
            if f == "boxedwine.js":   # keep our page title instead of "BoxedWine 42 MIPS"
                old = b"var _emscripten_set_window_title = (title) => document.title = UTF8ToString(title);"
                assert old in data, "boxedwine.js: window title hook not found"
                data = data.replace(old, b"var _emscripten_set_window_title = (title) => {};")
            with open(os.path.join(SITE, f), "wb") as out:
                out.write(data)
        boxedwine_readme = z.read("readme.txt")

    # --- WinHelp for the in-game help (the "?" buttons and the Hilfe menu)
    with zipfile.ZipFile(get("wine6")) as src, zipfile.ZipFile(os.path.join(SITE, "winhelp.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for n in WINHELP:
            z.writestr(src.getinfo(n), src.read(n))

    # --- the games; each in its own folder C:\files\<name>
    with zipfile.ZipFile(get("k122")) as z:
        k122 = {f: z.read(member(z, f)) for f in ["KAISER.EXE", "KAISER.HLP", "kaiser.mid", "versions.txt"]}
    with zipfile.ZipFile(get("k123")) as z:
        c = "Kaiser Classic/"
        k123 = {"KAISER.EXE": z.read(c + "Kaiser/kaiser.exe"), "kaiser.mid": z.read(c + "Kaiser/kaiser.mid")}
        manual = z.read(c + "docs/manual.md")
    k123["KAISER.HLP"] = k122["KAISER.HLP"]     # 1.23's own .HLP is not public (see README)
    k123["KAISER.INI"] = open(os.path.join(DATA, "kaiser123.ini"), "rb").read()

    write_zip(os.path.join(SITE, "kaiser122.zip"), [("kaiser122/" + f, d) for f, d in k122.items()])
    write_zip(os.path.join(SITE, "kaiser123.zip"), [("kaiser123/" + f, d) for f, d in k123.items()])
    # 1.22a keeps its settings in C:\WINDOWS\kaiser.ini: preset 800x600, sound and music on
    write_zip(os.path.join(SITE, "kaiser122-ini.zip"),
              [(WINE_C + "/windows/kaiser.ini", open(os.path.join(DATA, "kaiser.ini"), "rb").read())])
    for name, files in [("kaiser122", k122), ("kaiser123", k123)]:
        with open(os.path.join(SITE, name + ".mid"), "wb") as f:
            f.write(files["kaiser.mid"])

    # --- music synthesizer
    with tarfile.open(get("tinysynth")) as t:
        for f, out in [("package/webaudio-tinysynth.js", "webaudio-tinysynth.js"),
                       ("package/LICENSE", "LICENSE-webaudio-tinysynth.txt")]:
            with open(os.path.join(SITE, out), "wb") as o:
                o.write(t.extractfile(f).read())

    # --- 1.23 manual as HTML (same as in the installer)
    raw = os.path.join(BUILD, "raw")
    os.makedirs(raw)
    for n, d in [("k122.hlp", k122["KAISER.HLP"]), ("k123.exe", k123["KAISER.EXE"]), ("manual.md", manual)]:
        with open(os.path.join(raw, n), "wb") as f:
            f.write(d)
    py = [sys.executable, "-I"]
    subprocess.run(py + [os.path.join(TOOLS, "hlp_bitmaps.py"), os.path.join(raw, "k122.hlp"), os.path.join(BUILD, "pics122")],
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(py + [os.path.join(TOOLS, "ne_bitmaps.py"), os.path.join(raw, "k123.exe"), os.path.join(BUILD, "bmp123")],
                   check=True, stdout=subprocess.DEVNULL)
    help_dir = os.path.join(SITE, "handbuch-1.23")
    os.makedirs(os.path.join(help_dir, "bilder"))
    mapping = json.load(open(os.path.join(DATA, "pictures.json"), encoding="utf-8"))["map"]
    for pic, src in mapping.items():
        kind, ident = src.split(":", 1)
        folder = "pics122" if kind == "hlp122" else "bmp123"
        shutil.copy(os.path.join(BUILD, folder, ident + ".png"), os.path.join(help_dir, "bilder", pic + ".png"))
    subprocess.run(py + [os.path.join(TOOLS, "md_to_html.py"), os.path.join(raw, "manual.md"),
                         os.path.join(help_dir, "index.html"), "bilder"], check=True)

    # --- pages
    for f in os.listdir(os.path.join(ROOT, "web")):
        shutil.copy(os.path.join(ROOT, "web", f), SITE)
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    with open(os.path.join(SITE, "THIRD-PARTY.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(THIRD_PARTY + "\n--- Boxedwine readme.txt ---\n" + boxedwine_readme.decode("utf-8", "replace"))

    total = sum(os.path.getsize(os.path.join(d, n)) for d, _, ns in os.walk(SITE) for n in ns)
    print(f"built {SITE} ({total / 1e6:.1f} MB)")


THIRD_PARTY = """Kaiser im Browser - third-party components

Kaiser 1.22a and 1.23 beta (c) Stefan Maday, offered as freeware on the author's website.
  1.22a: Kai122a.zip from yadam.de via the Internet Archive
  1.23:  kaiser.exe / kaiser.mid / docs/manual.md from github.com/LarsGehrmann/Kaiser-decompile v1.0.2

Boxedwine 26R1 (GPL-2.0) - https://github.com/danoon2/Boxedwine (source: tag 26R1.0)
  boxedwine.js, boxedwine.wasm, boxedwine-shell.js, and the file system boxedwine.zip
Wine 6.0 (LGPL-2.1) - https://www.winehq.org, as built for Boxedwine
  boxedwine.zip, winhelp.zip (winhlp32 from https://boxedwine.org/v2/2/TinyCore15Wine6.0.zip)
WebAudio-TinySynth 1.1.3 (Apache-2.0) - https://github.com/g200kg/webaudio-tinysynth
  webaudio-tinysynth.js, see LICENSE-webaudio-tinysynth.txt
"""

if __name__ == "__main__":
    main()

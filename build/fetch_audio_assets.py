"""One-time, opt-in download of audio runtime assets.

Fetches the FluidSynth Windows runtime DLLs and a permissively-licensed
General MIDI SoundFont into music_theory/resources/. This is the ONLY place in
the project that touches the network, and it runs at build/setup time - never
during normal app use. Sources are official GitHub repositories; the
downloads are pinned to immutable refs and verified against pinned SHA-256s.

Usage:
    python build\\fetch_audio_assets.py
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "music_theory" / "resources"
FLUID_DIR = RES / "fluidsynth"
SF_DIR = RES / "soundfonts"

FLUIDSYNTH_URL = (
    "https://github.com/FluidSynth/fluidsynth/releases/download/"
    "v2.5.4/fluidsynth-v2.5.4-win10-x64-glib.zip"
)
FLUIDSYNTH_SHA256 = "fad6d822f1b7dff4fa9a4757023d23dbdb71822f5a747c583dec1ec69eb5aa00"

# GeneralUser GS v2.0.3, pinned to the commit that introduced it so the
# content can never drift; verified below against SOUNDFONT_SHA256.
SOUNDFONT_URL = (
    "https://github.com/mrbumpy409/GeneralUser-GS/raw/"
    "97049183643d5fc5a9322a69c5b09efb667c6c3a/GeneralUser-GS.sf2"
)
SOUNDFONT_SHA256 = "9575028c7a1f589f5770fccc8cff2734566af40cd26ed836944e9a5152688cfe"
SOUNDFONT_NAME = "GeneralUser-GS.sf2"

_UA = {"User-Agent": "MusicTheoryMaster-setup/1.0"}


def _download(url: str) -> bytes:
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - pinned hosts
        return resp.read()


def fetch_fluidsynth() -> bool:
    FLUID_DIR.mkdir(parents=True, exist_ok=True)
    if (FLUID_DIR / "libfluidsynth-3.dll").exists():
        print("fluidsynth: already present, skipping.")
        return True
    print("fluidsynth: fetching runtime DLLs...")
    data = _download(FLUIDSYNTH_URL)
    digest = hashlib.sha256(data).hexdigest()
    if digest != FLUIDSYNTH_SHA256:
        print(f"  ERROR: sha256 mismatch!\n   expected {FLUIDSYNTH_SHA256}\n   got      {digest}")
        return False
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename
            if name.lower().endswith(".dll") and "/bin/" in name.replace("\\", "/"):
                target = FLUID_DIR / Path(name).name
                target.write_bytes(zf.read(info))
                count += 1
    print(f"  extracted {count} DLLs to {FLUID_DIR}")
    return (FLUID_DIR / "libfluidsynth-3.dll").exists()


def fetch_soundfont() -> bool:
    SF_DIR.mkdir(parents=True, exist_ok=True)
    target = SF_DIR / SOUNDFONT_NAME
    if target.exists() and target.stat().st_size > 1_000_000:
        print("soundfont: already present, skipping.")
        return True
    print("soundfont: fetching GeneralUser GS...")
    data = _download(SOUNDFONT_URL)
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOUNDFONT_SHA256:
        print(f"  ERROR: sha256 mismatch!\n   expected {SOUNDFONT_SHA256}\n   got      {digest}")
        return False
    if data[:4] != b"RIFF" or b"sfbk" not in data[:64]:
        print("  ERROR: downloaded file is not a valid SoundFont (RIFF/sfbk).")
        return False
    target.write_bytes(data)
    print(f"  saved {len(data) // (1024 * 1024)} MB to {target}")
    return True


def main() -> int:
    print("Fetching audio assets (one-time network step)...")
    ok_fluid = fetch_fluidsynth()
    ok_sf = fetch_soundfont()
    if ok_fluid and ok_sf:
        print("\nDone. Realistic SoundFont audio is ready.")
        return 0
    print("\nSome assets failed; the app will fall back to the built-in synth.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

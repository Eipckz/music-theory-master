# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Music Theory Master (single-file Windows build).

Design notes (hard-won):
* We deliberately avoid ``collect_all('music21')``. It returns *every* music21
  submodule as a hidden import, and PyInstaller then imports each one inside an
  isolated subprocess. On this toolchain (Python 3.14 + PyInstaller 6.20) one of
  those imports deadlocks the build. Instead we collect only music21's data
  files and let static bytecode analysis pull in the submodules our code uses.
* We never force-import ``fluidsynth`` (pyfluidsynth runs an os.add_dll_directory
  landmine at import time -> access violation in an isolated probe). Our guarded
  ``import fluidsynth`` shim is still picked up by static analysis.
* music21's huge score *corpus* is trimmed out; we use music21 only for
  analysis (roman numerals, chord/set identification), not the corpus.
"""

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None


def _is_corpus(dest: str) -> bool:
    return "corpus" in dest.replace("\\", "/").lower().split("/")


datas = [("music_theory/resources", "music_theory/resources")]
datas += [(s, d) for (s, d) in collect_data_files("music21") if not _is_corpus(d)]

hiddenimports = [
    "sounddevice", "pygame", "pygame.midi", "scipy.signal",
    # music21 pieces our code touches (and their common dependencies). Listing
    # them explicitly is cheap and avoids relying on lazy imports being found.
    "music21", "music21.chord", "music21.roman", "music21.pitch",
    "music21.interval", "music21.key", "music21.scale", "music21.note",
    "music21.stream", "music21.duration", "music21.meter",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "PyQt5", "PySide6", "PySide2",
              "IPython", "pytest", "notebook",
              # music21 treats these as optional; we never use them. Excluding
              # them avoids native isolated-import issues and slims the build.
              "numba", "llvmlite", "pandas",
              # CRITICAL: torch is installed in this environment and gets pulled
              # into the graph, but we never use it. During binary-dependency
              # analysis PyInstaller imports torch in an isolated child, whose
              # _load_dll_libraries() blocks forever loading torch's DLLs and
              # deadlocks the whole build. Exclude it (and friends) outright.
              "torch", "torchvision", "torchaudio", "tensorflow", "jax"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MusicTheoryMaster",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon="music_theory/resources/icons/icon.ico",
    version="build/version_info.txt",
)

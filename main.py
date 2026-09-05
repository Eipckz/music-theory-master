"""Music Theory Master - application entry point."""

import sys
import os

# Windowed PyInstaller apps have no console streams. Some optional-library
# warnings (notably music21) write to stderr during import; provide a sink.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from music_theory.app import main

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from music_theory.selftest import run_self_test
        report = sys.argv[sys.argv.index("--self-test") + 1]
        sys.exit(run_self_test(report))
    sys.exit(main())

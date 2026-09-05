"""Music Theory Master - application entry point."""

import sys

from music_theory.app import main

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from music_theory.selftest import run_self_test
        report = sys.argv[sys.argv.index("--self-test") + 1]
        sys.exit(run_self_test(report))
    sys.exit(main())
